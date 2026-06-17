from typing import List, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    model_validator,
)
from pydantic.alias_generators import to_camel

from models.category import Category
from models.product import (
    CartParameters,
    Measure,
    PossibleProductResponse,
    ProductError,
    ProductResponse,
    Value,
    SaleType,
    Amount,
    ProductRequest,
)

# {
#    "name": "Loose Red Tomatoes",
#    "unitOfMeasure": "KGM",
#    "price": 699,
#    "nonLoyaltyCardPrice": 699,
#    "productId": "5040098-KGM-000",
#    "weighable": {
#        "avgWeightUoM": "g",
#        "avgWeightPerUnit": 140,
#        "minOrderQty": 150,
#        "stepSize": 100
#    },
#    "sku": "4064",
#    "comparativePricePerUnit": 699,
#    "comparativeUnitQuantity": 1,
#    "comparativeUnitQuantityUoM": "kg",
#    "comparativeUnitMeasureDescription": "1kg",
#    "saleType": "BOTH",
#    "ingredientStatement": "TOMATOES",
#    "fsIngredientStatement": "TOMATOES",
#    "fsValidation": {
#        "allergens": {
#            "status": "PASSED",
#            "pealStatus": "PASSED"
#        }
#    },
#    "restrictedFlag": false,
#    "netContent": 1,
#    "netContentUOM": "kg",
#    "displayName": "kg",
#    "height": 80,
#    "width": 1,
#    "categories": [
#        "Vegetables",
#        "Tomatoes, Cucumber & Capsicum"
#    ],
#    "availability": [
#        "IN_STORE",
#        "ONLINE"
#    ],
#    "originRegulated": true,
#    "originStatement": "Product of New Zealand",
#    "categoryTrees": [
#        {
#            "level0": "Fruit & Vegetables",
#            "level1": "Vegetables",
#            "level2": "Tomatoes, Cucumber & Capsicum"
#        }
#    ],
#    "fulfilmentOptions": [
#        {
#            "method": "COLLECT",
#            "collectionPointType": "COUNTER",
#            "available": true
#        }
#    ],
#    "cateredFlag": false,
#    "images": {
#        "primaryImages": {
#            "100px": "https://a.fsimg.co.nz/product/retail/fan/image/100x100/5040098.png",
#            "200px": "https://a.fsimg.co.nz/product/retail/fan/image/200x200/5040098.png",
#            "300px": "https://a.fsimg.co.nz/product/retail/fan/image/300x300/5040098.png",
#            "400px": "https://a.fsimg.co.nz/product/retail/fan/image/400x400/5040098.png",
#            "500px": "https://a.fsimg.co.nz/product/retail/fan/image/500x500/5040098.png"
#        },
#        "alternateImages": []
#    }
# }


class PaknSaveMeasurement(BaseModel):
    number: int
    measurement: Literal["g", "ml", "each", "sheets"]

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
                case "ea":
                    return {"number": int(num), "measurement": "each"}
                case "ea":
                    return {"number": int(num), "measurement": "each"}
                case "sheets":
                    return {"number": int(num), "measurement": "sheets"}
                case _:
                    raise ValueError(f"Unsupported unit: '{value}'")

        raise ValueError("Input must be a string or a dictionary")


class VariableWeight(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
    )
    min_order_quantity: int
    average_weight: Optional[int] = None


class ComparativePrice(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
    )
    price_per_unit: int
    unit_quantity: int
    unit_quantity_uom: PaknSaveMeasurement


class SinglePrice(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
    )
    price: int
    comparative_price: Optional[ComparativePrice] = None


class PaknSaveProduct(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
    )
    product_id: str
    brand: Optional[str] = None
    name: str
    sale_type: SaleType
    single_price: SinglePrice
    variable_weight: Optional[VariableWeight] = None
    category_trees: Optional[List[dict[str, str]]] = None

    def to_product(
        self, product_request: Optional[ProductRequest] = None
    ) -> PossibleProductResponse:

        try:
            name = (
                f"{self.brand.strip()} {self.name.strip()}"
                if self.brand
                else self.name.strip()
            )

            value = (
                Value(
                    cost_per=self.single_price.comparative_price.price_per_unit / 100.0,
                    amount=Amount(
                        number=self.single_price.comparative_price.unit_quantity
                        * self.single_price.comparative_price.unit_quantity_uom.number,
                        measurement=Measure(
                            self.single_price.comparative_price.unit_quantity_uom.measurement
                        ),
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
                name=name,
                value=value,
                sale_type=SaleType(self.sale_type),
                category=Category.best_guess(self.category_trees[0]["level0"])
                if self.category_trees is not None
                else Category.Other,
                cart_parameters=cart_parameters,
            )
        except Exception as e:
            return ProductError(
                message=f"Unable to convert product response: {self}",
                exception_error_message=str(e),
            )


class PaknSaveDirectProduct(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
    )
    product_id: str
    brand: Optional[str] = None
    name: str
    sale_type: SaleType
    price: int
    variable_weight: Optional[VariableWeight] = None
    categories: Optional[List[str]] = None

    def to_product(self) -> PossibleProductResponse:

        try:
            name = (
                f"{self.brand.strip()} {self.name.strip()}"
                if self.brand
                else self.name.strip()
            )

            return ProductResponse(
                id=self.product_id,
                cost_per_unit=self.price / 100.0,
                name=name,
                value=None,
                sale_type=SaleType(self.sale_type),
                category=Category.best_guess(self.categories[0])
                if self.categories is not None
                else Category.Other,
                cart_parameters=None,
            )
        except Exception as e:
            return ProductError(
                message=f"Unable to convert product response: {self}",
                exception_error_message=str(e),
            )
