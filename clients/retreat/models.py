import re
from typing import Literal

from pydantic import BaseModel, model_validator

from services.shoppinglist import Category, Measurement, ProductRequest


class RetreatAmount(BaseModel):
    amount: float
    type: Literal["g", "ml", "each"]

    @model_validator(mode="before")
    @classmethod
    def parse_measurement_string(cls, value):
        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            match = re.match(r"^([\d.]+)\s*([a-zA-Z]+)$", value.strip())
            if not match:
                raise ValueError(f"Could not parse measurement string: '{value}'")

            raw_amount, raw_unit = match.groups()
            num = float(raw_amount)
            unit = raw_unit.lower()

            # Normalize units and handle conversions

            if unit in ("g", "grams"):
                return {"amount": float(num), "type": "g"}
            elif unit in ("kg"):
                return {"amount": float(num * 1000), "type": "g"}
            elif unit in ("tins"):
                return {"amount": float(num * 400), "type": "g"}

            elif unit in ("ml"):
                return {"amount": float(num), "type": "ml"}
            elif unit in ("l", "litres"):
                return {"amount": float(num * 1000), "type": "ml"}

            elif unit in ("ea", "x", "bulbs", "packs", "loaves", "bunch"):
                return {"amount": float(num), "type": "each"}
            else:
                raise ValueError(f"Unsupported unit: '{raw_unit}'")

        raise ValueError("Input must be a string or a dictionary")


class RetreatProduct(BaseModel):
    name: str
    amount: RetreatAmount
    category: str

    def to_product(self) -> ProductRequest:
        return ProductRequest(
            id=self.name,
            name=self.name,
            amount=self.amount.amount,
            measurement=Measurement(self.amount.type),
            category=Category.best_guess(self.category),
        )


class Retreat(BaseModel):
    id: int
    name: str
