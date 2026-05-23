import re
from typing import Optional, Literal, List
from pydantic.alias_generators import to_camel
from pydantic import BaseModel, ConfigDict, model_validator
from enum import Enum


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


class Product(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    name: str
    unit: Unit
    price: Price
    quantity: Quanity
    size: Size
    availability_status: AvailabilityStatus
    departments: List[Department]
