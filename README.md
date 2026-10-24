
# Support Ticket Intelligence

**Live Demo:** https://support-ticket-intelligence-i68m.onrender.com

A FastAPI-based AI application that classifies customer support tickets, predicts their priority, extracts important information, and generates concise summaries with supporting evidence.

> **Note:** The application is hosted on Render's free instance. The first request after inactivity may take some time to respond.

## Features

- Responsive web interface served by FastAPI.
- Ticket classification into five categories:
  - Billing
  - Technical Issue
  - Account Access
  - Delivery
  - Other
- Priority prediction: Low, Medium, or High.
- Extracts order ID, product ID, requested action, and deadline when present.
- Returns missing extracted fields as JSON `null`.
- Single-ticket classification and batch processing.
- Supports JSON and CSV batch uploads and downloadable results.
- Input validation using Pydantic.
- Automated tests using pytest.
- Separate labelled evaluation dataset containing 30 synthetic tickets.
- Evaluation reports for category and priority predictions.

## Technology Stack

- **Backend:** Python, FastAPI
- **Validation:** Pydantic
- **AI/LLM:** Groq API, `openai/gpt-oss-120b`
- **Frontend:** HTML, CSS, JavaScript
- **Testing:** pytest
- **Deployment:** Render
- **Evaluation:** Python, pandas, CSV and JSON reports

## Project Structure

```text
Support-Ticket-Intelligence/
├── app/
│   ├── main.py
│   ├── schemas.py
│   ├── extractor.py
│   ├── pipeline.py
│   ├── summarizer.py
│   └── llm_analyzer.py
├── data/
│   ├── sample_tickets.json
│   ├── evaluation_tickets.json
│   ├── evaluation_tickets.csv
│   └── evaluation_predictions_v2.csv
├── reports/
│   ├── evaluation_metrics_v2.json
│   └── evaluation_errors_v2.csv
├── static/
│   └── index.html
├── tests/
│   └── test_pipeline.py
├── outputs/
├── .env.example
├── .gitignore
├── evaluate.py
├── evaluate_v2.py
├── requirements.txt
├── render.yaml
└── README.md
```

*The structure above describes the expected layout; adjust filenames to match the files actually present in your repository.*

## Prerequisites

- Python 3.11 or later recommended.
- pip.
- A Groq API key.
- Git, if cloning the repository.

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/Digvijaysingh8/Support_Ticket_Intelligence.git
cd Support_Ticket_Intelligence
```

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux:**

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
```

Replace the placeholder with your actual Groq API key.

**Security:** Never commit `.env` or expose your API key publicly. Keep `.env` in `.gitignore`. Commit `.env.example` only if it contains placeholders and no real secrets.

## Running the Application

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload
```

Open the following URLs:

| URL | Purpose |
|---|---|
| http://127.0.0.1:8000/ | Web interface |
| http://127.0.0.1:8000/health | Health check |
| http://127.0.0.1:8000/docs | Interactive Swagger API documentation |

Press `Ctrl+C` to stop the development server.

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /` | Serves the web interface |
| `GET /health` | Checks application health |
| `POST /classify` | Classifies a single support ticket |
| `POST /batch` | Processes a batch of tickets |
| `POST /batch/upload` | Processes uploaded JSON or CSV data |

Use `/docs` to inspect the actual request schemas, required fields, supported upload formats, and response structures.

### Example: Classify a Ticket

**Request:**

```json
{
  "ticket_id": "T-100",
  "text": "I was charged twice for order ORD-4821. Please reverse the extra payment before my invoice closes tomorrow."
}
```

**Expected interpretation:**

- Category: Billing
- Priority: Determined by the model based on the ticket and classification rules.
- Order ID: `ORD-4821`
- Requested action: Reverse the extra payment.
- Deadline: Extracted from the wording when supported by the extraction rules.

The exact response fields and values depend on the implemented extraction and classification logic.

## Testing

Run the automated test suite from the project root:

```bash
pytest -q
```

The tests cover the implemented pipeline and validation behavior. Check the test output to confirm that all tests pass.

## Evaluation

The project includes a labelled synthetic evaluation dataset of 30 support tickets, separate from the six smoke-test examples.

Each ticket has an expected category and priority. The evaluation compares the model's predictions with these expected labels.

### Run the evaluation

```bash
python evaluate_v2.py
```

Use the script's actual output to report the latest results. Do not assume previously reported metrics are still current if the dataset, labels, prompt, or evaluation code has changed.

### Evaluation artifacts

The fresh evaluation workflow uses these files:

- `data/evaluation_predictions_v2.csv` — ticket-level predictions and expected labels.
- `reports/evaluation_metrics_v2.json` — aggregate evaluation metrics.
- `reports/evaluation_errors_v2.csv` — tickets with classification errors.

**Important:** The fresh evaluation script may refuse to run if its predictions file already exists. Follow the script's behavior rather than deleting evaluation data without a backup.

### Metrics to report

**Category classification**
- Accuracy: percentage of tickets assigned the correct category.
- Per-class precision and recall, if calculated by the evaluation script.

**Priority classification**
- Accuracy: percentage of tickets assigned the correct priority.
- High-to-Low errors: count of genuinely High-priority tickets predicted as Low.

High-to-Low mistakes deserve special attention because urgent issues may be delayed or overlooked.

### Labelling rules

- **Billing:** Payment, invoice, refund, or charging issues.
- **Technical Issue:** Product faults, errors, or failures requiring technical investigation.
- **Account Access:** Login, authentication, or account-access problems.
- **Delivery:** Shipping, tracking, missing items, or delivery-related problems.
- **Other:** Requests or questions that do not fit the other categories.

Choose the category based on the ticket's primary intent rather than an isolated keyword.

Priority depends on urgency, impact, and severity:

- **High:** Serious or time-sensitive issues, significant service failures, or potentially urgent security concerns.
- **Medium:** Meaningful issues that need support investigation but do not show immediate severe impact.
- **Low:** Routine information requests, minor changes, and non-urgent issues.

Apply these rules consistently. If a ticket's expected label is ambiguous, review and document the labelling decision.

### Error analysis

Review `reports/evaluation_errors_v2.csv` and manually inspect at least three failures or uncertain cases. Record:

1. The ticket and expected label.
2. The model's predicted label.
3. Why the prediction may have failed.
4. A proposed improvement to the prompt, labelling rules, extraction logic, or evaluation process.

### Evaluation limitations

The evaluation dataset is small, synthetic, and manually labelled. Some errors were reviewed during prompt development, so the final results are not an independent estimate of generalization to unseen tickets.

A stronger evaluation would use a separate held-out dataset that was not used to develop or tune the prompt, ideally including real-world tickets with appropriate privacy safeguards.

## Design Choices and Limitations

### Classification

The application uses a hosted Groq LLM with the `openai/gpt-oss-120b` model to classify ticket category and priority. The configured temperature is 0 to reduce sampling variability, although outputs are not guaranteed to be perfectly reproducible.

### Field Extraction and Summarization

Selected fields are extracted using deterministic rules and patterns. Summaries are generated using the project's rule-based summarization logic.

This design makes extraction behavior easier to inspect, but pattern-based approaches can struggle with ambiguous wording, unusual formats, and complex dates.

### Known Limitations

- Ambiguous or mixed-intent tickets may be misclassified.
- Negation, spelling variations, paraphrases, and multilingual messages can affect predictions.
- Priority is an estimate, not an SLA guarantee.
- Rule-based extraction may miss information or normalize dates imperfectly.
- Extractive summaries may retain unnecessary wording.
- A small synthetic evaluation set may not reflect production ticket distributions.
- Hosted LLM availability, latency, and rate limits can affect requests.

### Potential Improvements

- Evaluate on an independent, held-out ticket dataset.
- Add confidence estimation and human review for uncertain cases.
- Improve date and entity extraction.
- Add caching, rate limiting, and request monitoring.
- Add authentication and stricter upload limits.
- Track classification performance by category and priority over time.

## Privacy and Security

Ticket text is sent to the Groq API for classification and priority estimation. Extraction and summarization run locally according to the current implementation.

Do not upload real sensitive customer information to a public demo.

Before production use, consider:

- Authentication and authorization.
- Rate limiting.
- File-size and request-size limits.
- Logging and data-retention controls.
- Secure secret management.
- Appropriate handling of customer data and third-party API policies.

Never commit API keys, `.env` files, passwords, or other credentials to GitHub.

## Deployment to Render

The repository is intended to support Render Blueprint deployment through `render.yaml`.

### Deployment steps

1. Push the project to GitHub.
2. Open the Render dashboard.
3. Select **New + → Blueprint**.
4. Connect the repository containing the project.
5. Review the detected service configuration.
6. Set `GROQ_API_KEY` in the Render environment settings.
7. Deploy the application.
8. Verify the public web interface, `/health`, `/docs`, single-ticket classification, and batch upload.

The Blueprint should define the build command, start command, health-check path, and environment-variable configuration. Verify these values in the actual `render.yaml` before deployment.

A typical FastAPI start command is:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Render free web services can spin down after inactivity. The first request after a pause may take longer than usual.

### Optional Keep-Alive Workflow

If `.github/workflows/keep-alive.yml` is present, inspect its schedule and confirm that it requests the deployed `/health` endpoint.

GitHub Actions schedules are not guaranteed to run at the exact scheduled minute. Keep-alive requests should not be treated as a guarantee against service suspension or as a substitute for checking the hosting provider's current limits and policies.

## Future Scope

- Add more labelled tickets and an independent test dataset.
- Improve prioritization for urgent service and security issues.
- Add multilingual ticket support.
- Improve entity extraction and deadline normalization.
- Introduce human-in-the-loop review.
- Add monitoring for latency, API failures, and classification drift.

## Author

Developed as a Support Ticket Intelligence prototype using FastAPI, Python, and a hosted large language model.
