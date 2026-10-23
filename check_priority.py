from app.pipeline import process_ticket

tickets = [
    {
        "ticket_id": "E09",
        "text": "How do I change the email address used to sign in?",
    },
    {
        "ticket_id": "E27",
        "text": "I need my account restored because I cannot sign in to work.",
    },
]

for ticket in tickets:
    result = process_ticket(ticket)
    print(
        ticket["ticket_id"],
        result.category,
        result.priority,
    )