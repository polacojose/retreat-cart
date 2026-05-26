import services.shoppinglist
import re
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel

from services.shoppinglist import Product, Amount


class Unit(str, Enum):
    KG = "Kg"
    EACH = "Each"


class Price(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    original_price: float
    sale_price: Optional[float]


class Quanity(BaseModel):
    min: float
    max: float
    increment: float


class CupMeasure(BaseModel):
    amount: int
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
            if unit in ("g"):
                return {"amount": int(num), "type": "g"}
            elif unit in ("kg"):
                return {"amount": int(num * 1000), "type": "g"}
            elif unit in ("ml"):
                return {"amount": int(num), "type": "ml"}
            elif unit in ("l"):
                return {"amount": int(num * 1000), "type": "ml"}
            elif unit in ("ea"):
                return {"amount": int(num), "type": "each"}
            else:
                raise ValueError(f"Unsupported unit: '{raw_unit}'")

        raise ValueError("Input must be a string or a dictionary")


class Size(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    cup_list_price: float
    cup_price: float
    cup_measure: Optional[CupMeasure] = None


class AvailabilityStatus(str, Enum):
    in_stock = "In Stock"
    low_stock = "Low Stock"
    out_of_stock = "Out of Stock"


class Department(BaseModel):
    name: str


class WoolWorthsProduct(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    sku: str
    name: str
    unit: Unit
    price: Price
    quantity: Quanity
    size: Size
    availability_status: AvailabilityStatus
    departments: List[Department]

    def to_product(self) -> Product | None:
        if self.size.cup_measure is not None:
            return Product(
                id=self.sku,
                name=self.name,
                amount=Amount(
                    amount=self.size.cup_measure.amount, type=self.size.cup_measure.type
                ),
            )
