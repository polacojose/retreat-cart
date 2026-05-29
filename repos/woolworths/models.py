import re
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator, field_validator
from pydantic.alias_generators import to_camel

from services.shoppinglist import (
    ProductResponse,
    Category,
    Measurement,
    CartParameters, PossibleProductResponse, ProductError,
)


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


class VolumeSize(BaseModel):
    number: int
    measurement: Literal["g", "ml", "each"]

    @model_validator(mode="before")
    @classmethod
    def parse_measurement_string(cls, value):
        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            match = re.match(r"^([\d.]+)\s*([a-zA-Z]+)$", value.strip())
            if not match:
                raise ValueError(f"Could not parse measurement string: '{value}'")

            raw_number, raw_measurement = match.groups()
            num = float(raw_number)
            unit = raw_measurement.lower()

            # Normalize units and handle conversions
            if unit in ("g"):
                return {"number": int(num), "measurement": "g"}
            elif unit in ("kg"):
                return {"number": int(num * 1000), "measurement": "g"}
            elif unit in ("ml"):
                return {"number": int(num), "measurement": "ml"}
            elif unit in ("l"):
                return {"number": int(num * 1000), "measurement": "ml"}
            elif unit in ("ea"):
                return {"number": int(num), "measurement": "each"}
            else:
                raise ValueError(f"Unsupported unit: '{raw_measurement}'")

        raise ValueError("Input must be a string or a dictionary")


class Size(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    cup_list_price: float
    cup_price: float
    volume_size: Optional[VolumeSize] = None

    @field_validator("volume_size", mode="before")
    @classmethod
    def eval(cls, value: str) -> str | None:
        value = value.strip()
        if value == "":
            return None
        else:
            return value.replace("per ", "1").replace("min order ", "")


class AvailabilityStatus(str, Enum):
    in_stock = "In Stock"
    low_stock = "Low Stock"
    out_of_stock = "Out of Stock"


class Department(BaseModel):
    name: str


category_map = {
    "Fruit & Veg": Category.FruitVegetables,
    "Meat & Poultry": Category.MeatPoultrySeafood,
    "Fish & Seafood": Category.MeatPoultrySeafood,
    "Fridge & Deli": Category.FridgeDeliEggs,
    "Bakery": Category.Bakery,
    "Frozen": Category.Frozen,
    "Pantry": Category.Pantry,
    "Beer & Wine": Category.BeerWineCider,
    "Drinks": Category.HotColdDrinks,
    "Health & Body": Category.HealthBody,
    "Household": Category.HouseholdCleaning,
    "Baby & Child": Category.BabyToddler,
    "Pet": Category.Pets,
}


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

    def to_product(self) -> PossibleProductResponse:

        category = Category.Other
        if len(self.departments) >= 1:
            cat_name = self.departments[0].name.strip()
            if cat_name in category_map:
                category = category_map[cat_name]
            else:
                category = Category.best_guess(cat_name)

        price = self.price.original_price
        if self.price.sale_price is not None:
            price = self.price.sale_price

        try:
            if self.size.volume_size is not None:
                return ProductResponse(
                    id=self.sku,
                    cost=price,
                    name=self.name.strip(),
                    amount=self.size.volume_size.number,
                    measurement=Measurement(self.size.volume_size.measurement),
                    category=category,
                    cart_parameters=CartParameters(
                        min=self.quantity.min,
                        max=self.quantity.max,
                        increment=self.quantity.increment,
                    ),
                )
        except Exception as e:
            return ProductError(error=f"Unable to convert product response: {self}: {e}")

        return ProductError(error=f"Product missing volume size: {self}")
