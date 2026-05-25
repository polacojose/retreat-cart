from typing import Literal

from pydantic import BaseModel


class Amount(BaseModel):
    amount: float
    type: Literal["g", "ml", "each"]


class Product(BaseModel):
    name: str
    amount: Amount
