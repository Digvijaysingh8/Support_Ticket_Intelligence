# Independent Holdout Evaluation

This evaluation package adds a separately labelled 30-ticket synthetic holdout set for Support Ticket Intelligence. It is designed to be kept out of prompt/rule development.

## Files

- `data/holdout_evaluation_tickets.csv`: ticket text and manually assigned expected category/priority labels.
- `evaluate_holdout.py`: runs the existing `app.pipeline.process_ticket` and computes separate category and priority metrics.
- Outputs are created under `reports/` in the same project root.

## Install and run

Copy `data/holdout_evaluation_tickets.csv` into your project's `data/` directory and copy `evaluate_holdout.py` into the project root. From the project root, activate your virtual environment, install the project's requirements, and ensure `.env` contains a valid `GROQ_API_KEY`.

```powershell
python evaluate_holdout.py
```

The script makes live Groq calls. It will refuse to overwrite prior output files unless you explicitly pass `--overwrite`. The output files are:

- `reports/holdout_predictions.csv`
- `reports/holdout_metrics.json`
- `reports/holdout_errors.csv`

If a run fails partway through, the partial predictions CSV is retained for recovery. Back it up or move it before starting a fresh run. The script intentionally does not report aggregate metrics unless all tickets finish.

## Metrics

Category and priority are reported separately with accuracy, per-class precision/recall/F1, macro and weighted averages, and confusion matrices. The report also counts expected High tickets predicted as Low.

## Label policy

- Billing: charges, invoices, payments, subscription billing.
- Account Access: sign-in, credentials, locked accounts, authentication.
- Delivery: shipping, tracking, missing or replacement items.
- Technical Issue: an actual product malfunction or technical failure requiring troubleshooting.
- Other: general information, feature questions, feedback, or profile customisation that is not access-related.
- High: serious or time-sensitive impact, widespread/core-feature failure, critical account lockout, significant payment discrepancy, urgent missing delivery, or a potential security report needing prompt triage.
- Medium: meaningful issue needing investigation without evidence of immediate severe impact.
- Low: routine questions, non-urgent requests, or informational queries.

These are policy choices, not universal truths. Review ambiguous labels before running, document changes, and do not change labels after seeing predictions just to improve scores.

## Avoiding leakage

Do not use these holdout tickets to tune prompts, rules, or thresholds. Keep the existing 30-ticket development/evaluation set for prompt iteration. If you change the prompt after seeing holdout results, this holdout has become development data; create a new unseen set for the next final evaluation.

This is a small synthetic set and does not establish production performance. The reported score is meaningful as a holdout only if these exact examples have not previously been used to tune the model or its prompt.
