# Support Ticket Intelligence --- Design Note

## 1. Project Overview

Support Ticket Intelligence is a ticket-analysis application that
classifies customer-support tickets by category and priority, extracts
structured fields, and produces a concise summary with supporting
evidence.

The application uses FastAPI for its API layer and a Groq-hosted
language model (`openai/gpt-oss-120b`) for ticket analysis.
Deterministic extraction patterns are used for structured fields, and
the pipeline combines model analysis, extracted fields, summary, and
evidence into a `TicketOutput`.

## 2. Evaluation Dataset

The evaluation dataset is stored at `data/evaluation_tickets.csv`.

-   Number of labelled evaluation tickets: **30**
-   Dataset format: CSV
-   Required fields: `ticket_id`, `text`, `expected_category`,
    `expected_priority`
-   The 30 synthetic evaluation tickets are separate from the six
    smoke-test examples.
-   Expected category and priority labels were assigned manually.

The dataset is synthetic and relatively small. Results describe
performance on this set and should not be interpreted as a guarantee of
performance on real customer-support traffic.

## 3. Label Definitions and Labelling Rules

### Categories

The application supports these categories:

-   **Billing:** Invoices, unexpected subscription fees, incorrect
    charges, duplicate payments, and payment-method billing requests.
-   **Account Access:** Login problems, password resets, and sign-in
    email changes.
-   **Delivery:** Shipping, missing orders, replacement deliveries, and
    replacement status.
-   **Technical Issue:** Unresolved technical faults and troubleshooting
    needs.
-   **Other:** General information requests or issues that do not fit
    the other categories.

Tickets should be labelled according to the customer's primary issue or
request, rather than isolated keywords. Resolved replacement/delivery
cases need a consistent policy: this evaluation treats a resolved
replacement case such as E24 as **Delivery**, because the ticket's
subject is the replacement delivery.

Routine product-usage questions can be ambiguous. For example, E11 asks
how to change a dashboard theme. If the category policy reserves
Technical Issue for faults and troubleshooting, this is better treated
as Other; if the project intentionally includes product how-to questions
under Technical Issue, that policy should be explicitly documented and
applied consistently.

### Priorities

The application supports **Low**, **Medium**, and **High** priorities.

-   **High:** A serious or time-sensitive issue with significant impact,
    such as a repeated service failure preventing access to a core
    feature, a critical access problem, a significant payment issue, a
    time-sensitive missing order, or a potential security issue
    requiring prompt review.
-   **Medium:** A meaningful problem requiring attention or
    investigation without a clearly urgent deadline or severe impact.
-   **Low:** Routine information requests, ordinary profile
    customisation, or issues explicitly resolved with no remaining
    problem or request.

Priority should reflect the underlying issue, impact, and urgency---not
merely words such as "ASAP." Potential security reports should be routed
for prompt review under the chosen policy, without assuming that a
vulnerability is confirmed.

These rules are operational definitions for this project. Ambiguous
cases should be reviewed and documented rather than relabelled only to
improve the score.

## 4. Evaluation Method

The evaluation script compares the model's predicted category and
priority against the manually assigned expected labels.

-   Category and priority are evaluated separately.
-   Category metrics include accuracy, per-class precision/recall/F1,
    and a confusion matrix.
-   Priority metrics include accuracy, per-class precision/recall/F1,
    and a confusion matrix.
-   The script also counts tickets where an expected High priority was
    predicted as Low.
-   The baseline run is stored in `data/evaluation_predictions.csv`,
    with metrics in `reports/evaluation_metrics.json`.
-   The fresh updated-prompt run is stored separately in
    `data/evaluation_predictions_v2.csv`, with metrics in
    `reports/evaluation_metrics_v2.json`.

The updated-prompt run processed all 30 tickets and used separate output
files so the original baseline was preserved.

## 5. Results

### Baseline and updated-prompt comparison

  Metric                                                   Baseline   Updated prompt
  ------------------------------------------------ ---------------- ----------------
  Tickets evaluated                                         30 / 30          30 / 30
  Category accuracy                                  93.33% (28/30)   96.67% (29/30)
  Priority accuracy                                  73.33% (22/30)   86.67% (26/30)
  Expected High predicted as Low                                  1                0
  Tickets with at least one classification error                  9                5

The updated-prompt run improved category accuracy by 3.34 percentage
points and priority accuracy by 13.34 percentage points on this dataset.
The count of tickets with at least one classification error decreased
from nine to five, and the fresh run had no expected-High tickets
predicted as Low.

These results show improvement on the current synthetic evaluation set.
They do not prove that the same performance will generalise to unseen or
real-world tickets. Language-model outputs can vary, and the prompt was
refined after reviewing evaluation errors.

## 6. Manual Error Analysis

Five cases from the updated evaluation were manually reviewed. The
following notes distinguish observed prediction errors from potential
ambiguity in the expected labels.

### E09 --- Repeated analytics-page error

**Ticket:** "I get error 503 every time I open the analytics page.
Please help me fix it."

-   Expected category: Technical Issue
-   Predicted category: Technical Issue
-   Expected priority: High
-   Predicted priority: Medium

**Assessment:** Priority mismatch under the project's labelling policy.
The phrase "every time" indicates a recurring failure, and the analytics
page appears inaccessible.

**Potential improvement:** Clarify that repeated service errors
preventing access to a core application feature warrant High priority.
Do not classify every isolated technical error as High.

### E11 --- Dashboard theme question

**Ticket:** "How can I change the dashboard theme from light to dark?"

-   Expected category: Technical Issue
-   Predicted category: Other
-   Expected priority: Low
-   Predicted priority: Low

**Assessment:** Potentially an ambiguous category label. The ticket asks
how to change a preference and does not report a malfunction. If
Technical Issue is reserved for faults and troubleshooting, Other is
more consistent with the category definition.

**Potential improvement:** Decide and document whether routine product
how-to questions belong in Other or Technical Issue, then apply that
policy consistently.

### E16 --- Display-name change

**Ticket:** "How do I change my display name in my profile settings?"

-   Expected category: Account Access
-   Predicted category: Account Access
-   Expected priority: Low
-   Predicted priority: Medium

**Assessment:** Priority mismatch under the current labels. This is
routine profile customisation, not a sign-in or access problem.

**Potential improvement:** Explicitly classify routine profile
customisation, such as changing a display name, as Low unless the ticket
describes urgency or a separate meaningful problem. The Account Access
category for profile-name changes should also be reviewed for
consistency with the category taxonomy.

### E20 --- Missing item

**Ticket:** "My order arrived with one item missing. Please send the
missing item as soon as possible."

-   Expected category: Delivery
-   Predicted category: Delivery
-   Expected priority: High
-   Predicted priority: Medium

**Assessment:** Priority mismatch under the project's labelling policy.
The customer reports an incomplete order and explicitly requests prompt
action.

**Potential improvement:** Clarify when a missing item with an explicit
prompt-replacement request should be High, while routine delivery
questions without significant impact may remain Medium or Low.

### E28 --- Possible security issue

**Ticket:** "I need to report a possible security issue in the public
documentation; please route this to the right team."

-   Expected category: Other
-   Predicted category: Other
-   Expected priority: High
-   Predicted priority: Low

**Assessment:** Priority mismatch under the current labels. A potential
security report may require timely triage, but the ticket alone does not
establish that a vulnerability is confirmed or exploitable.

**Potential improvement:** Define a clear routing and priority rule for
reports of potential security issues. Prompt review can be required
without claiming that the vulnerability is confirmed.

## 7. Cost of High-to-Low Priority Errors

Incorrectly predicting a High-priority ticket as Low is particularly
costly because it can delay triage of serious service failures,
time-sensitive customer problems, or potential security reports. This
project therefore tracks the number of tickets whose expected priority
is High but whose predicted priority is Low.

In the baseline run, this occurred once. In the updated-prompt run, it
occurred zero times. This is encouraging, but the sample is small; zero
such errors in 30 synthetic tickets does not guarantee that the system
will never make this mistake in production. A deployed system should use
appropriate validation, monitoring, and human escalation for high-impact
cases.

## 8. Avoiding an Overly Narrow Evaluation

The 30-ticket evaluation set was kept separate from the six smoke-test
examples and contains manually assigned expected category and priority
labels. Results were measured separately for category and priority, and
the baseline predictions were preserved before running the updated
prompt.

However, some evaluation failures were reviewed and used to refine the
prompt. Therefore, the updated-prompt score is not a fully independent
estimate of generalisation: the prompt has been tuned with knowledge of
this evaluation set. The results should be described as performance on
the current synthetic dataset, not as an unbiased benchmark.

A stronger next step is to create a new holdout set of unseen tickets,
label it before evaluating the model, and avoid using those examples for
further prompt tuning. Real or carefully reviewed representative tickets
would provide additional evidence beyond synthetic examples.

## 9. Limitations and Future Improvements

-   The evaluation set contains only 30 synthetic tickets.
-   Some categories and priority levels are subjective unless the
    labelling rules are explicit.
-   Prompt tuning based on observed errors can overfit the current set.
-   Model outputs may vary between runs.
-   The evaluation does not establish performance on real
    customer-support traffic.
-   Future work should include a larger, independently labelled holdout
    set, consistent label adjudication, and monitoring of per-class
    performance.
-   High-impact cases, especially potential security issues and repeated
    service failures, should have clear escalation rules.

## 10. Reproducibility and Output Files

Key files:

-   `data/evaluation_tickets.csv` --- labelled evaluation dataset
-   `data/evaluation_predictions.csv` --- baseline predictions
-   `reports/evaluation_metrics.json` --- baseline metrics
-   `reports/evaluation_errors.csv` --- baseline errors
-   `data/evaluation_predictions_v2.csv` --- updated-prompt predictions
-   `reports/evaluation_metrics_v2.json` --- updated-prompt metrics
-   `reports/evaluation_errors_v2.csv` --- updated-prompt errors
-   `evaluate.py` --- original evaluation script
-   `evaluate_v2.py` --- fresh evaluation script with separate output
    files

Run automated tests with:

``` powershell
python -m pytest -v
```

Run the fresh evaluation script only when a new live model evaluation is
intended, because it makes Groq API calls.
