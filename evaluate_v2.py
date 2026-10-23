
import json
import time
from pathlib import Path

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)

from app.pipeline import process_ticket
from app.schemas import TicketInput


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
REPORT_DIR = ROOT / "reports"

DATASET_PATH = DATA_DIR / "evaluation_tickets.csv"
PREDICTIONS_PATH = DATA_DIR / "evaluation_predictions_v2.csv"
METRICS_PATH = REPORT_DIR / "evaluation_metrics_v2.json"
ERRORS_PATH = REPORT_DIR / "evaluation_errors_v2.csv"

CATEGORIES = [
    "Billing",
    "Technical Issue",
    "Account Access",
    "Delivery",
    "Other",
]
PRIORITIES = ["Low", "Medium", "High"]


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(DATASET_PATH).fillna("")

    required = {
        "ticket_id",
        "text",
        "expected_category",
        "expected_priority",
    }
    if not required.issubset(dataset.columns):
        raise ValueError(f"Missing columns: {required - set(dataset.columns)}")
    if dataset.empty or dataset["ticket_id"].duplicated().any():
        raise ValueError("Dataset is empty or contains duplicate ticket IDs.")

    if set(dataset["expected_category"]) - set(CATEGORIES):
        raise ValueError("Invalid expected category in dataset.")
    if set(dataset["expected_priority"]) - set(PRIORITIES):
        raise ValueError("Invalid expected priority in dataset.")
    if (dataset["text"].astype(str).str.strip() == "").any():
        raise ValueError("Dataset contains empty ticket text.")

    # Refuse to overwrite an earlier v2 run.
    if PREDICTIONS_PATH.exists():
        raise FileExistsError(
            f"{PREDICTIONS_PATH} already exists. "
            "Rename or back it up before starting another run."
        )

    results = []

    for _, row in dataset.iterrows():
        ticket_id = str(row["ticket_id"])
        print(f"Evaluating {ticket_id}...")

        try:
            output = process_ticket(
                TicketInput(ticket_id=ticket_id, text=str(row["text"]))
            )
            results.append({
                "ticket_id": ticket_id,
                "text": str(row["text"]),
                "expected_category": row["expected_category"],
                "predicted_category": output.category,
                "expected_priority": row["expected_priority"],
                "predicted_priority": output.priority,
                "summary": output.summary,
                "evidence": output.evidence,
            })

            # Save progress after every successful prediction.
            pd.DataFrame(results).to_csv(PREDICTIONS_PATH, index=False)
            time.sleep(1)

        except Exception as exc:
            if results:
                pd.DataFrame(results).to_csv(PREDICTIONS_PATH, index=False)
            print(f"Stopped at {ticket_id}: {type(exc).__name__}: {exc}")
            print("Completed predictions were saved. Do not delete them.")
            return

    predictions = pd.DataFrame(results)
    reports = {}

    for name, expected_col, predicted_col, labels in [
        ("category", "expected_category", "predicted_category", CATEGORIES),
        ("priority", "expected_priority", "predicted_priority", PRIORITIES),
    ]:
        y_true = predictions[expected_col].astype(str)
        y_pred = predictions[predicted_col].astype(str)
        reports[name] = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "classification_report": classification_report(
                y_true, y_pred, labels=labels,
                output_dict=True, zero_division=0,
            ),
            "confusion_matrix": confusion_matrix(
                y_true, y_pred, labels=labels
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
        "high_expected_but_predicted_low_ticket_ids":
            high_to_low["ticket_id"].astype(str).tolist(),
        "error_count": len(errors),
        "error_ticket_ids": errors["ticket_id"].astype(str).tolist(),
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("\n=== FRESH EVALUATION RESULTS ===")
    print(f"Tickets evaluated: {len(predictions)} / {len(dataset)}")
    print(f"Category accuracy: {reports['category']['accuracy']:.2%}")
    print(f"Priority accuracy: {reports['priority']['accuracy']:.2%}")
    print(f"High -> Low errors: {len(high_to_low)}")
    print(f"Tickets with any error: {len(errors)}")
    print(f"Predictions: {PREDICTIONS_PATH}")
    print(f"Metrics: {METRICS_PATH}")
    print(f"Errors: {ERRORS_PATH}")


if __name__ == "__main__":
    main()
