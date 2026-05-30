from enum import Enum
from typing import List, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    model_validator,
)
from pydantic.alias_generators import to_camel

from services.shoppinglist import (
    CartParameters,
    Category,
    Measurement,
    PossibleProductResponse,
    ProductError,
    ProductResponse,
    Value,
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


class Measure(BaseModel):
    number: int
    measurement: Literal["g", "ml", "each"]

    @model_validator(mode="before")
    @classmethod
    def parse_measurement_string(cls, value):
        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            num = float(1)
            unit = value.lower()

            match unit:
                case "g":
                    return {"number": int(num), "measurement": "g"}
                case "kg":
                    return {"number": int(num * 1000), "measurement": "g"}
                case "ml":
                    return {"number": int(num), "measurement": "ml"}
                case "l":
                    return {"number": int(num * 1000), "measurement": "ml"}
                case _:
                    raise ValueError(f"Unsupported unit: '{value}'")

        raise ValueError("Input must be a string or a dictionary")


class VariableWeight(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    min_order_quantity: int
    average_weight: int


class ComparativePrice(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    price_per_unit: int
    unit_quantity: int
    unit_quantity_uom: Measure


class SinglePrice(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    price: int
    comparative_price: Optional[ComparativePrice] = None


class PaknSaveProduct(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
    product_id: str
    name: str
    single_price: SinglePrice
    variable_weight: Optional[VariableWeight] = None
    category_trees: List[dict[str, str]]

    def to_product(self) -> PossibleProductResponse:

        try:
            value = (
                Value(
                    cost_per=self.single_price.comparative_price.price_per_unit / 100.0,
                    number=self.single_price.comparative_price.unit_quantity
                    * self.single_price.comparative_price.unit_quantity_uom.number,
                    measure=Measurement(
                        self.single_price.comparative_price.unit_quantity_uom.measurement
                    ),
                )
                if self.single_price.comparative_price
                else None
            )

            cart_parameters = (
                CartParameters(
                    min=self.variable_weight.min_order_quantity,
                    increment=self.variable_weight.average_weight,
                )
                if self.variable_weight
                else None
            )

            return ProductResponse(
                id=self.product_id,
                cost_per_unit=self.single_price.price / 100.0,
                name=self.name.strip(),
                value=value,
                category=Category.best_guess(self.category_trees[0]["level0"]),
                cart_parameters=cart_parameters,
            )
        except Exception as e:
            return ProductError(
                message=f"Unable to convert product response: {self}",
                exception_error_message=str(e),
            )
