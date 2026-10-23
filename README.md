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
Classification and priority are produced by a hosted LLM (Groq, `openai/gpt-oss-120b`) at temperature 0; field extraction and summaries stay deterministic and rule-based so IDs, actions, and deadlines remain reproducible. Keyword/pattern overlap can still misclassify ambiguous or mixed-intent tickets, and the LLM can be sensitive to paraphrases, negation, spelling variations, and multilingual messages. Priority is a heuristic estimate, not an SLA guarantee. Summary is extractive and may retain unnecessary wording. The synthetic evaluation set is small and may not represent real ticket distributions. Improvements include calibrated confidence, abstention/human review for ambiguous cases, richer date normalization, caching, and evaluation on a held-out real-world dataset.

## Privacy and security
Ticket text is sent to the Groq API for classification and priority estimation; field extraction and summarization run locally. Do not upload real sensitive customer information to a public demo. For production, add authentication, rate limits, logging controls, retention policies, and stricter file-size limits.

## Deploy to Render
This repository includes `render.yaml` for Render Blueprint deployment.

1. Push the project to GitHub (the repo must be the one connected to Render).
2. In Render, choose **New + → Blueprint**, connect the repository, and apply the detected service.
3. When prompted, set `GROQ_API_KEY` to your Groq API key. It is marked `sync: false`, so it is entered once in the dashboard and never stored in git.
4. Deploy. Once live, verify `/`, `/health`, `/docs`, single-ticket analysis, and batch upload from the public URL.

Service settings used by the blueprint: Python 3.12.7, build `pip install --upgrade pip && pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health check `/health`. Free-tier services spin down after inactivity, so the first request after a pause may take ~30–60 seconds.
