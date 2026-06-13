from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, field_validator

from models.category import Category


class Measure(str, Enum):
    Gram = "g"
    Milliliters = "ml"
    Each = "each"
    Sheets = "sheets"


class ProductBase(BaseModel):
    id: str
    name: str
    category: Optional[Category]

    @field_validator("category", mode="before")
    @classmethod
    def eval(cls, value: str) -> Category:
        if value in Category:
            return Category(value)
        else:
            return Category.Other


class Amount(BaseModel):
    number: float
    measurement: Measure


class ProductRequest(ProductBase):
    amount: Amount


class ProductError(BaseModel):
    message: str
    exception_error_message: Optional[str] = None


type PossibleProductResponse = Union[ProductResponse, ProductError]


class Value(BaseModel):
    cost_per: float
    amount: Amount


class CartParameters(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    increment: Optional[float] = None


class SaleType(str, Enum):
    Units = "UNITS"
    Weight = "WEIGHT"
    Both = "BOTH"


class ProductResponse(ProductBase):
    cost_per_unit: float
    """In dollars."""
    value: Optional[Value] = None
    sale_type: Optional[SaleType] = SaleType.Units
    cart_parameters: Optional[CartParameters] = None

    @field_validator("category", mode="before")
    @classmethod
    def eval(cls, value: str) -> Category:
        if value in Category:
            return Category(value)
        else:
            return Category.Other
