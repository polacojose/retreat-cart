from pydantic import BaseModel
from typing import Optional


class GroceryStore(BaseModel):
    id: str
    name: str
    address: Optional[str] = None
    notes: Optional[str] = None
