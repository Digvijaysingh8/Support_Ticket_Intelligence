
from app.pipeline import process_ticket
from app.schemas import TicketInput
from app.llm_analyzer import TicketAnalysis
from pydantic import ValidationError


def make_analysis(
    category="Other",
    priority="Low",
    requested_action=None,
    category_evidence="General question",
    priority_evidence="No urgency stated",
):
    return TicketAnalysis(
        category=category,
        priority=priority,
        requested_action=requested_action,
        category_evidence=category_evidence,
        priority_evidence=priority_evidence,
    )


def test_sample_duplicate_charge(monkeypatch):
    monkeypatch.setattr(
        "app.pipeline.analyze_ticket",
        lambda text: make_analysis(
            category="Billing",
            priority="High",
            requested_action="Reverse extra payment",
            category_evidence="charged twice",
            priority_evidence="Reverse the extra payment",
        ),
    )

    result = process_ticket(
        TicketInput(
            text="I was charged twice for order ORD-4821. "
                 "Reverse the extra payment tomorrow."
        )
    )

    assert result.category == "Billing"
    assert result.priority == "High"
    assert result.order_id == "ORD-4821"


def test_unknown_fields_are_null(monkeypatch):
    monkeypatch.setattr(
        "app.pipeline.analyze_ticket",
        lambda text: make_analysis(),
    )

    result = process_ticket(
        TicketInput(text="Hello, I have a general question.")
    )

    assert result.order_id is None
    assert result.product_id is None
    assert result.deadline is None


def test_resolved_ticket_low_priority(monkeypatch):
    monkeypatch.setattr(
        "app.pipeline.analyze_ticket",
        lambda text: make_analysis(
            priority="Low",
            priority_evidence="No further action needed",
        ),
    )

    result = process_ticket(
        TicketInput(
            text="Thanks, it is working now. No further action needed."
        )
    )

    assert result.priority == "Low"


def test_empty_text_rejected():
    try:
        TicketInput(text="")
        assert False, "Expected empty text to be rejected"
    except ValidationError:
        pass
