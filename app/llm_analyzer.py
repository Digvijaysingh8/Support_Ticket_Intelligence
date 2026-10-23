
import json
import os
from typing import Literal

from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel, Field


load_dotenv()


class TicketAnalysis(BaseModel):
    category: Literal[
        "Billing",
        "Technical Issue",
        "Account Access",
        "Delivery",
        "Other",
    ]

    priority: Literal["Low", "Medium", "High"]

    requested_action: str | None = Field(
        default=None,
        description="The action the customer wants the support team to take, or null if none is stated",
    )

    category_evidence: str = Field(
        min_length=1,
        description="Words or phrases from the ticket supporting the category",
    )

    priority_evidence: str = Field(
        min_length=1,
        description="Words or phrases from the ticket supporting the priority",
    )


def analyze_ticket(ticket_text: str) -> TicketAnalysis:
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Check your .env file."
        )

    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "system",
                "content": """
You are a customer-support ticket analysis system.

Analyze the ticket and return valid JSON with these fields:
category, priority, requested_action, category_evidence,
priority_evidence.

Allowed categories:
- Billing
- Account Access
- Delivery
- Technical Issue
- Other

Allowed priorities:
- Low
- Medium
- High

Priority guidelines:
- High: The ticket describes a serious or time-sensitive problem with significant customer impact, such as a payment amount deducted despite a failed transaction, a missing order needed for an upcoming event, an urgent delivery issue, or a security issue requiring prompt investigation.
- High: Duplicate charges or being billed twice for the same item, even when the customer does not explicitly request urgent action.
- High: Account access problems that prevent the customer from working or performing essential tasks.
- High: Repeated HTTP 5xx errors that prevent access to a core application feature, especially when the issue occurs every time the user tries.
- High: A missing or delayed order that has remained unresolved for several days, or a missing item for which the customer explicitly requests prompt replacement.
- Medium: A meaningful problem requiring investigation or resolution, such as an unexpected fee, an incorrect charge, a delayed order without a stated deadline, or an account problem that does not prevent essential work.
- Medium: Routine account-setting changes, including updating a payment method or changing the email address used to sign in.
- Medium: A password reset request when the customer can still access their account and no urgent impact is described.
- Medium: A general question that requires clarification about account or workspace functionality.
- Medium: Uncertainty about whether an order was successfully submitted
  when confirmation is unclear and verification may be required.
- Medium: Workspace capability questions when the answer affects a team's
  ability to use or configure the product.
- Low: Routine information requests, invoice copies, general questions, or requests explicitly phrased as "when convenient" or "whenever you get a chance", unless the ticket describes a meaningful unresolved problem.
- Low: Issues that are explicitly resolved, with no remaining problem or request.
- Low: General questions about order status when there is no evidence of a failed, delayed, or missing order.
- Judge urgency based on the actual problem, its impact, and any explicit urgency—not merely the presence of words such as "tomorrow" or "ASAP".
- Do not classify a ticket as High solely because the customer uses urgent wording; the underlying issue must justify high priority.
- When evidence is insufficient to establish urgency, choose the lower priority supported by the ticket.
- Low: Routine requests to update a billing contact email or invoice
  email when there is no billing error, payment issue, or urgency.
- Low: Routine profile customization, such as changing a display name,
  when no access problem or business impact is described.


Category guidelines:
- Billing: Invoices, unexpected subscription fees, incorrect charges,
  duplicate payments, and payment-method billing requests.
- Account Access: Login problems, password resets, and changes to the
  email address used to sign in.
- Delivery: Shipping, missing orders, replacement deliveries, and
  replacement status.
- If a replacement has arrived and the customer confirms everything is
  working, classify it as Delivery, not Technical Issue.
- Technical Issue: Technical faults or troubleshooting needs that remain
  unresolved.
- Classify based on the customer's primary issue or request, not isolated keywords.
- Delivery: Use when the primary issue concerns shipping, a missing or delayed order, replacement delivery, or replacement status.
- Other: Use for general questions, capability questions, security reports without a more specific category, and order-submission uncertainty when no delivery or billing problem is established.
- A confirmation email with uncertainty about whether an order was submitted is Other unless the ticket establishes a specific billing, delivery, account-access, or technical problem.
- A resolved delivery or replacement issue remains Delivery when the ticket is primarily about that delivery or replacement, even if no further action is needed.  
- Technical Issue: Errors, service failures, and troubleshooting requests
  involving application functionality.
- Other: Routine how-to questions about preferences or settings when no
  technical fault is reported.

  
Requested action:
- Describe the action the customer explicitly wants, if any.
- Return null if no specific action is requested.
- Do not invent a request.

Evidence:
- Use only information supported by the ticket.
- Evidence must quote or closely reference actual ticket wording.
- Do not invent order IDs, product IDs, or deadlines.
- category_evidence must contain a short quote or close reference supporting the selected category.
- priority_evidence must contain a short quote or close reference supporting the selected priority.
- Both evidence fields must be non-empty strings. If the ticket provides little evidence, use the closest relevant wording from the ticket and do not invent facts.
- Return JSON only.
"""
            },
            {
                "role": "user",
                "content": ticket_text,
            },
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError("The model returned an empty response.")

    result = json.loads(content)

    return TicketAnalysis.model_validate(result)
