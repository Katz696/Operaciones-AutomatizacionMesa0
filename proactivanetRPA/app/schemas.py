from pydantic import BaseModel
from typing import List

class Ticket(BaseModel):
    incident_id: str
    type_id: str

class BatchRequest(BaseModel):
    tickets: List[Ticket]