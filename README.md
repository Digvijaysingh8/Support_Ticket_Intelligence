# Support Ticket Intelligence

A reproducible prototype that routes support tickets, estimates priority, extracts selected fields, and produces a concise summary and evidence phrase.

## Features
- Responsive browser UI served by FastAPI at `/`
- Categories: Billing, Technical Issue, Account Access, Delivery, Other
- Priority: Low, Medium, High
- Extracts order ID, product ID, requested action, and deadline when present
- Missing fields are returned as JSON `null`
- Single-ticket and batch endpoints; JSON and CSV upload/output
- Pydantic validation, tests, and a separate 30-ticket synthetic evaluation set

## Setup (Python 3.11+ recommended)
```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run
```bash
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/ for the browser UI, or http://127.0.0.1:8000/docs to try `POST /classify`, `POST /batch`, or `POST /batch/upload`. The UI supports single-ticket analysis and JSON/CSV batch uploads with downloadable results.

## Test and evaluate
```bash
pytest -q
python evaluate.py
```
The evaluation labels are synthetic and hand-authored, not a representative production dataset. Report the actual metrics produced by `evaluate.py`; do not claim expected results without running it. Inspect `outputs/evaluation_errors.json` and document at least three errors or edge cases.

## Example
Request:
```json
{
  "ticket_id": "T-100",
  "text": "I was charged twice for order ORD-4821. Please reverse the extra payment before my invoice closes tomorrow."
}
```
Output fields include category, priority, order_id, requested_action, deadline, summary, and evidence.

## Design choices and limitations
The baseline is intentionally rule-based for transparent, deterministic behavior without external APIs or secrets. Keyword overlap can misclassify ambiguous or mixed-intent tickets; rules can be brittle to paraphrases, negation, spelling variations, and multilingual messages. Priority is a heuristic estimate, not an SLA guarantee. Summary is extractive and may retain unnecessary wording. The synthetic evaluation set is small and may not represent real ticket distributions. Improvements include a learned classifier trained on a larger labeled dataset, calibrated confidence, abstention/human review for ambiguous cases, richer date normalization, and evaluation on a held-out real-world dataset.

## Privacy and security
No external model/API is called and no ticket text is sent to a third party by this prototype. Do not upload real sensitive customer information to a public demo. For production, add authentication, rate limits, logging controls, retention policies, and stricter file-size limits.

## Deploy to Render
This repository includes `render.yaml`. Push the project to GitHub, then create a Render Web Service from the repository (Blueprint deployment is also supported). Confirm the build command is `pip install -r requirements.txt`, the start command is `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, and the health-check path is `/health`. After deployment, verify `/`, `/health`, `/docs`, single-ticket analysis, and batch upload from the public URL.
