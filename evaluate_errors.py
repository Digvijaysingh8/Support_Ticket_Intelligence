
import json
import time
from pathlib import Path

import pandas as pd

from app.pipeline import process_ticket
from app.schemas import TicketInput


ROOT = Path(__file__).resolve().parent
PREDICTIONS_PATH = ROOT / "data" / "evaluation_predictions.csv"
ERRORS_PATH = ROOT / "reports" / "evaluation_errors.csv"
OUTPUT_PATH = ROOT / "reports" / "targeted_evaluation.csv"


def main():
    baseline = pd.read_csv(PREDICTIONS_PATH)
    errors = pd.read_csv(ERRORS_PATH)

    # Select only tickets that had a category or priority error.
    ticket_ids = errors["ticket_id"].astype(str).tolist()
    selected = baseline[
        baseline["ticket_id"].astype(str).isin(ticket_ids)
    ].copy()

    if selected.empty:
        print("No baseline error tickets found.")
        return

    results = []

    for _, row in selected.iterrows():
        ticket_id = str(row["ticket_id"])
        ticket_text = row["text"]

        print(f"Re-evaluating {ticket_id}...")

        try:
            result = process_ticket(
                TicketInput(text=str(ticket_text))
            )

            # Support either a Pydantic model or a dictionary.
            if hasattr(result, "model_dump"):
                prediction = result.model_dump()
            elif isinstance(result, dict):
                prediction = result
            else:
                raise TypeError(
                    f"Unexpected result type: {type(result).__name__}"
                )

            results.append({
                "ticket_id": ticket_id,
                "text": ticket_text,
                "expected_category": row["expected_category"],
                "baseline_category": row["predicted_category"],
                "new_category": prediction.get("category"),
                "expected_priority": row["expected_priority"],
                "baseline_priority": row["predicted_priority"],
                "new_priority": prediction.get("priority"),
                "category_evidence": prediction.get("category_evidence"),
                "priority_evidence": prediction.get("priority_evidence"),
                "error": None,
            })

        except Exception as exc:
            print(f"Failed on {ticket_id}: {exc}")
            results.append({
                "ticket_id": ticket_id,
                "text": ticket_text,
                "expected_category": row["expected_category"],
                "baseline_category": row["predicted_category"],
                "new_category": prediction.get("category"),
                "expected_priority": row["expected_priority"],
                "baseline_priority": row["predicted_priority"],
                "new_priority": prediction.get("priority"),
                "summary":None,
                "evidence": None,
                "error": None,
            })

            # Stop if the API fails, while preserving completed results.
            pd.DataFrame(results).to_csv(OUTPUT_PATH, index=False)
            break

        pd.DataFrame(results).to_csv(OUTPUT_PATH, index=False)
        time.sleep(1)

    if results:
        df = pd.DataFrame(results)
        completed = df[df["error"].isna()]

        if not completed.empty:
            category_accuracy = (
                completed["new_category"]
                == completed["expected_category"]
            ).mean() * 100

            priority_accuracy = (
                completed["new_priority"]
                == completed["expected_priority"]
            ).mean() * 100

            high_to_low = (
                (completed["expected_priority"] == "High")
                & (completed["new_priority"] == "Low")
            ).sum()

            print("\nTargeted evaluation results")
            print(f"Completed: {len(completed)} / {len(selected)}")
            print(f"Category accuracy: {category_accuracy:.2f}%")
            print(f"Priority accuracy: {priority_accuracy:.2f}%")
            print(f"High -> Low errors: {high_to_low}")

        print(f"\nResults saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
