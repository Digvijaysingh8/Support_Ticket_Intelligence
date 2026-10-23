
import json
import time
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from app.pipeline import process_ticket
from app.schemas import TicketInput


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
REPORT_DIR = ROOT / "reports"

DATASET_PATH = DATA_DIR / "evaluation_tickets.csv"
PREDICTIONS_PATH = DATA_DIR / "evaluation_predictions.csv"
METRICS_PATH = REPORT_DIR / "evaluation_metrics.json"
ERRORS_PATH = REPORT_DIR / "evaluation_errors.csv"

CATEGORIES = [
    "Billing",
    "Technical Issue",
    "Account Access",
    "Delivery",
    "Other",
]

PRIORITIES = ["Low", "Medium", "High"]


def save_predictions(results):
    pd.DataFrame(results).to_csv(PREDICTIONS_PATH, index=False)


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    dataset = pd.read_csv(DATASET_PATH).fillna("")

    required = {
        "ticket_id",
        "text",
        "expected_category",
        "expected_priority",
    }
    missing = required - set(dataset.columns)

    if missing:
        raise ValueError(f"Missing dataset columns: {sorted(missing)}")

    if dataset.empty:
        raise ValueError("Evaluation dataset is empty.")

    if dataset["ticket_id"].duplicated().any():
        raise ValueError("Evaluation ticket IDs must be unique.")

    if (dataset["text"].astype(str).str.strip() == "").any():
        raise ValueError("Evaluation dataset contains empty ticket text.")

    if not set(dataset["expected_category"]).issubset(CATEGORIES):
        raise ValueError("Dataset contains an invalid expected category.")

    if not set(dataset["expected_priority"]).issubset(PRIORITIES):
        raise ValueError("Dataset contains an invalid expected priority.")

    # Resume from saved predictions if a previous run was interrupted.
    results = []
    completed_ids = set()

    if PREDICTIONS_PATH.exists():
        previous = pd.read_csv(PREDICTIONS_PATH).fillna("")
        if {"ticket_id", "predicted_category", "predicted_priority"}.issubset(
            previous.columns
        ):
            valid_ids = set(dataset["ticket_id"].astype(str))
            previous = previous[
                previous["ticket_id"].astype(str).isin(valid_ids)
            ]
            results = previous.to_dict(orient="records")
            completed_ids = {
                str(row["ticket_id"]) for row in results
            }

    for _, row in dataset.iterrows():
        ticket_id = str(row["ticket_id"])

        if ticket_id in completed_ids:
            continue

        try:
            output = process_ticket(
                TicketInput(
                    ticket_id=ticket_id,
                    text=str(row["text"]),
                )
            )

            result = {
                "ticket_id": ticket_id,
                "text": str(row["text"]),
                "expected_category": row["expected_category"],
                "predicted_category": output.category,
                "expected_priority": row["expected_priority"],
                "predicted_priority": output.priority,
                "summary": output.summary,
                "evidence": output.evidence,
            }

            results.append(result)
            save_predictions(results)
            print(f"Evaluated {ticket_id}")

            # Small pause between API calls.
            time.sleep(1)

        except Exception as exc:
            save_predictions(results)
            print(
                f"Stopped at {ticket_id}: "
                f"{type(exc).__name__}: {exc}"
            )
            print("Completed predictions have been saved.")
            print("Fix the issue or wait for quota reset, then rerun.")
            return

    predictions = pd.DataFrame(results)

    if predictions.empty:
        print("No predictions available.")
        return

    # Evaluate category and priority independently.
    reports = {}

    for name, expected_col, predicted_col, labels in [
        (
            "category",
            "expected_category",
            "predicted_category",
            CATEGORIES,
        ),
        (
            "priority",
            "expected_priority",
            "predicted_priority",
            PRIORITIES,
        ),
    ]:
        y_true = predictions[expected_col].astype(str)
        y_pred = predictions[predicted_col].astype(str)

        reports[name] = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "classification_report": classification_report(
                y_true,
                y_pred,
                labels=labels,
                output_dict=True,
                zero_division=0,
            ),
            "confusion_matrix": confusion_matrix(
                y_true,
                y_pred,
                labels=labels,
            ).tolist(),
            "labels": labels,
        }

    high_to_low = predictions[
        (predictions["expected_priority"] == "High")
        & (predictions["predicted_priority"] == "Low")
    ]

    errors = predictions[
        (predictions["expected_category"] != predictions["predicted_category"])
        | (predictions["expected_priority"] != predictions["predicted_priority"])
    ].copy()

    errors.to_csv(ERRORS_PATH, index=False)

    metrics = {
        "dataset": DATASET_PATH.name,
        "total_tickets": len(dataset),
        "evaluated_tickets": len(predictions),
        "category": reports["category"],
        "priority": reports["priority"],
        "high_expected_but_predicted_low_count": len(high_to_low),
        "high_expected_but_predicted_low_ticket_ids": (
            high_to_low["ticket_id"].astype(str).tolist()
        ),
        "error_count": len(errors),
        "error_ticket_ids": errors["ticket_id"].astype(str).tolist(),
    }

    METRICS_PATH.write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    print("\n=== EVALUATION RESULTS ===")
    print(f"Tickets evaluated: {len(predictions)} / {len(dataset)}")
    print(f"Category accuracy: {reports['category']['accuracy']:.2%}")
    print(f"Priority accuracy: {reports['priority']['accuracy']:.2%}")
    print(f"High -> Low priority errors: {len(high_to_low)}")
    print(f"Tickets with any classification error: {len(errors)}")
    print(f"Predictions: {PREDICTIONS_PATH}")
    print(f"Metrics: {METRICS_PATH}")
    print(f"Errors: {ERRORS_PATH}")


if __name__ == "__main__":
    main()
