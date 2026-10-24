"""Evaluate Support Ticket Intelligence on a separately labelled holdout set.

Run from the project root so `app.pipeline` can be imported:
    python evaluate_holdout.py

This script makes live LLM calls through the existing application pipeline.
It does not tune prompts or change the application code.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "holdout_evaluation_tickets.csv"
OUTPUT_DIR = ROOT / "reports"
PREDICTIONS_PATH = OUTPUT_DIR / "holdout_predictions.csv"
METRICS_PATH = OUTPUT_DIR / "holdout_metrics.json"
ERRORS_PATH = OUTPUT_DIR / "holdout_errors.csv"
CATEGORIES = ["Billing", "Technical Issue", "Account Access", "Delivery", "Other"]
PRIORITIES = ["Low", "Medium", "High"]
REQUIRED_COLUMNS = {"ticket_id", "text", "expected_category", "expected_priority"}


def load_dataset(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            missing = sorted(REQUIRED_COLUMNS - set(reader.fieldnames or []))
            raise ValueError(f"Dataset is missing required columns: {missing}")
        rows = list(reader)
    if not rows:
        raise ValueError("Evaluation dataset is empty.")
    ids = [r["ticket_id"].strip() for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("ticket_id values must be unique.")
    for row in rows:
        row["ticket_id"] = row["ticket_id"].strip()
        row["text"] = row["text"].strip()
        row["expected_category"] = row["expected_category"].strip()
        row["expected_priority"] = row["expected_priority"].strip()
        if not row["text"]:
            raise ValueError(f"Empty ticket text for {row['ticket_id']}")
        if row["expected_category"] not in CATEGORIES:
            raise ValueError(f"Unknown expected category for {row['ticket_id']}: {row['expected_category']}")
        if row["expected_priority"] not in PRIORITIES:
            raise ValueError(f"Unknown expected priority for {row['ticket_id']}: {row['expected_priority']}")
    return rows


def get_value(result: Any, field: str) -> str:
    """Read a field from either a Pydantic model or a dictionary."""
    if isinstance(result, dict):
        value = result.get(field)
    else:
        value = getattr(result, field, None)
    if value is None:
        return ""
    return str(value).strip()


def predict(row: dict[str, str]) -> dict[str, Any]:
    # Import only after validating the dataset. The existing project pipeline
    # is responsible for Groq configuration and application-specific processing.
    from app.pipeline import process_ticket

    result = process_ticket({"ticket_id": row["ticket_id"], "text": row["text"]})
    category = get_value(result, "category")
    priority = get_value(result, "priority")
    if category not in CATEGORIES:
        raise ValueError(f"Invalid category returned for {row['ticket_id']}: {category!r}")
    if priority not in PRIORITIES:
        raise ValueError(f"Invalid priority returned for {row['ticket_id']}: {priority!r}")
    return {
        "ticket_id": row["ticket_id"],
        "text": row["text"],
        "expected_category": row["expected_category"],
        "predicted_category": category,
        "expected_priority": row["expected_priority"],
        "predicted_priority": priority,
        "category_correct": category == row["expected_category"],
        "priority_correct": priority == row["expected_priority"],
        "high_predicted_low": row["expected_priority"] == "High" and priority == "Low",
    }


def classification_metrics(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict[str, Any]:
    total = len(y_true)
    correct = sum(a == b for a, b in zip(y_true, y_pred))
    per_class: dict[str, dict[str, Any]] = {}
    for label in labels:
        tp = sum(t == label and p == label for t, p in zip(y_true, y_pred))
        fp = sum(t != label and p == label for t, p in zip(y_true, y_pred))
        fn = sum(t == label and p != label for t, p in zip(y_true, y_pred))
        support = sum(t == label for t in y_true)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "support": support,
        }
    confusion = {
        actual: {predicted: sum(t == actual and p == predicted for t, p in zip(y_true, y_pred)) for predicted in labels}
        for actual in labels
    }
    macro = {
        metric: round(sum(per_class[label][metric] for label in labels) / len(labels), 4)
        for metric in ("precision", "recall", "f1_score")
    }
    weighted = {}
    for metric in ("precision", "recall", "f1_score"):
        weighted[metric] = round(
            sum(per_class[label][metric] * per_class[label]["support"] for label in labels) / total,
            4,
        ) if total else 0.0
    return {
        "accuracy": round(correct / total, 4) if total else 0.0,
        "correct": correct,
        "total": total,
        "per_class": per_class,
        "macro_avg": macro,
        "weighted_avg": weighted,
        "confusion_matrix_rows_actual_columns_predicted": confusion,
    }


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate ticket classification on the holdout dataset.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite previous holdout output files.")
    args = parser.parse_args()

    try:
        rows = load_dataset(DATA_PATH)
    except Exception as exc:
        print(f"Dataset error: {exc}", file=sys.stderr)
        return 2

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = [PREDICTIONS_PATH, METRICS_PATH, ERRORS_PATH]
    if not args.overwrite and any(p.exists() for p in outputs):
        print("Holdout output already exists. To preserve the previous run, move/back up its files first. "
              "Use --overwrite only if you intentionally want to replace them.", file=sys.stderr)
        return 2

    print(f"Evaluating {len(rows)} labelled holdout tickets. This makes live Groq API calls.")
    predictions: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        try:
            item = predict(row)
            predictions.append(item)
            print(f"[{index}/{len(rows)}] {row['ticket_id']}: "
                  f"category={'OK' if item['category_correct'] else 'ERROR'}, "
                  f"priority={'OK' if item['priority_correct'] else 'ERROR'}")
            # Save progress after each completed ticket so partial runs are recoverable.
            write_csv(PREDICTIONS_PATH, predictions, list(predictions[0].keys()))
        except Exception as exc:
            print(f"Stopped at {row['ticket_id']}: {exc}", file=sys.stderr)
            print("No aggregate metrics were written because the full holdout run did not complete.", file=sys.stderr)
            return 1

    category = classification_metrics(
        [r["expected_category"] for r in predictions],
        [r["predicted_category"] for r in predictions], CATEGORIES,
    )
    priority = classification_metrics(
        [r["expected_priority"] for r in predictions],
        [r["predicted_priority"] for r in predictions], PRIORITIES,
    )
    errors = [r for r in predictions if not r["category_correct"] or not r["priority_correct"]]
    high_to_low = sum(r["high_predicted_low"] for r in predictions)
    metrics = {
        "evaluation_name": "separate_synthetic_holdout",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(DATA_PATH.relative_to(ROOT)),
        "dataset_size": len(rows),
        "note": "Synthetic labels are manually assigned. This holdout is only independent if its tickets and labels were not used to tune prompts or rules.",
        "category": category,
        "priority": priority,
        "safety_metric": {
            "expected_high_predicted_low_count": high_to_low,
            "expected_high_count": sum(r["expected_priority"] == "High" for r in predictions),
            "rate_among_expected_high": round(
                high_to_low / sum(r["expected_priority"] == "High" for r in predictions), 4
            ) if any(r["expected_priority"] == "High" for r in predictions) else None,
            "why_it_matters": "A High-to-Low error can delay urgent service, payment, access, delivery, or security triage.",
        },
        "tickets_with_any_error": len(errors),
        "limitations": [
            "Small synthetic dataset; not representative of all production tickets.",
            "Results are meaningful as a holdout only if these examples were not used for prompt/rule development.",
            "One run does not guarantee performance on future or real-world tickets.",
        ],
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    write_csv(ERRORS_PATH, errors, list(predictions[0].keys()))
    print("\nEvaluation complete")
    print(f"Category accuracy: {category['correct']}/{category['total']} ({category['accuracy']:.2%})")
    print(f"Priority accuracy: {priority['correct']}/{priority['total']} ({priority['accuracy']:.2%})")
    print(f"Expected High predicted Low: {high_to_low}")
    print(f"Tickets with any error: {len(errors)}")
    print(f"Predictions: {PREDICTIONS_PATH}")
    print(f"Metrics: {METRICS_PATH}")
    print(f"Errors: {ERRORS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
