from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

Category = Literal["Billing", "Technical Issue", "Account Access", "Delivery", "Other"]
Priority = Literal["Low", "Medium", "High"]

class TicketInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ticket_id: str | None = None
    text: str = Field(min_length=1, max_length=10000)

class TicketOutput(BaseModel):
    ticket_id: str | None = None
    category: Category
    priority: Priority
    order_id: str | None = None
    product_id: str | None = None
    requested_action: str | None = None
    deadline: str | None = None
    summary: str
    evidence: str
