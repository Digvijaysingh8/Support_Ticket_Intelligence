
from app.extractor import extract_fields
from app.summarizer import summarize
from app.schemas import TicketInput, TicketOutput
from app.llm_analyzer import analyze_ticket


def process_ticket(ticket: TicketInput | dict) -> TicketOutput:
    if isinstance(ticket, dict):
        ticket = TicketInput.model_validate(ticket)

    text = ticket.text.strip()

    # Analyze the ticket using the LLM.
    analysis = analyze_ticket(text)

    # Extract structured fields using deterministic patterns.
    fields = extract_fields(text)
    fields["requested_action"] = analysis.requested_action

    # Generate a concise summary.
    summary = summarize(text)

    # Combine the model's supporting evidence.
    evidence = (
        f"Category: {analysis.category_evidence} "
        f"Priority: {analysis.priority_evidence}"
    )

    return TicketOutput(
        ticket_id=ticket.ticket_id,
        category=analysis.category,
        priority=analysis.priority,
        summary=summary,
        evidence=evidence,
        **fields,
    )
