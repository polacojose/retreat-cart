from models import product
import re
from enum import Enum
from typing import Annotated, Any, Callable, List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    WrapValidator,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel

from models.product import (
    CartParameters,
    Category,
    PossibleProductResponse,
    ProductError,
    ProductResponse,
    Value,
    Amount,
)


class Unit(str, Enum):
    KG = "Kg"
    EACH = "Each"


class Price(BaseModel):
    """
    {
        "originalPrice": 7.95,
        "salePrice": 7.95,
        "savePrice": 0,
        "savePercentage": 0,
        "canShowSavings": true,
        "hasBonusPoints": false,
        "isClubPrice": false,
        "isSpecial": false,
        "isNew": false,
        "canShowOriginalPrice": true,
        "discount": null,
        "total": null,
        "isTargetedOffer": false,
        "averagePricePerSingleUnit": 0.95,
        "isBoostOffer": false,
        "purchasingUnitPrice": null,
        "orderedPrice": null,
        "isUsingOrderedPrice": false,
        "currentPricingMatchesOrderedPricing": null,
        "extendedListPrice": null,
        "originalAveragePricePerSingleUnit": null,
        "promotionStartDate": null,
        "promotionEndDate": null
      }
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
    )
    original_price: float
    sale_price: Optional[float]


class Quanity(BaseModel):
    """
    {
      "min": 0.2,
      "max": 100,
      "increment": 0.1,
      "value": null,
      "quantityInOrder": null,
      "purchasingQuantityString": null
    }
    """

    min: float
    max: float
    increment: float


class WoolworthsMeasurement(BaseModel):
    number: int
    measurement: product.Measure

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
                return {"number": int(num), "measurement": product.Measure.Gram}
            elif unit in ("kg"):
                return {
                    "number": int(num * 1000),
                    "measurement": product.Measure.Gram,
                }
            elif unit in ("ml"):
                return {
                    "number": int(num),
                    "measurement": product.Measure.Milliliters,
                }
            elif unit in ("l"):
                return {
                    "number": int(num * 1000),
                    "measurement": product.Measure.Milliliters,
                }
            elif unit in ("ea"):
                return {
                    "number": int(num),
                    "measurement": product.Measure.Each,
                }
            elif unit in ("ss"):
                return {
                    "number": int(num),
                    "measurement": product.Measure.Sheets,
                }
            else:
                raise ValueError(f"Unsupported unit: '{raw_measurement}'")

        raise ValueError("Input must be a string or a dictionary")


def invalid_to_none(v: Any, handler: Callable[[Any], Any]) -> Any:
    try:
        return handler(v)
    except Exception:
        return None


class Size(BaseModel):
    """
    {
        "cupListPrice": 7.95,
        "cupPrice": 7.95,
        "cupMeasure": "1kg",
        "packageType": null,
        "volumeSize": "per kg"
      }
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
    )
    cup_list_price: float
    cup_price: float
    cup_measure: Annotated[
        Optional[WoolworthsMeasurement], WrapValidator(invalid_to_none)
    ] = None
    volume_size: Annotated[
        Optional[WoolworthsMeasurement], WrapValidator(invalid_to_none)
    ] = None

    @field_validator("volume_size", "cup_measure", mode="before")
    @classmethod
    def eval(cls, value: str) -> str | None:
        if value is not None:
            if value == "":
                return None
            else:
                return value.replace("per ", "1").replace("min order ", "")


class AvailabilityStatus(str, Enum):
    in_stock = "In Stock"
    low_stock = "Low Stock"
    out_of_stock = "Out of Stock"


class Department(BaseModel):
    """
    {
      "id": 1,
      "name": "Fruit & Veg"
    }
    """

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


class WoolworthsProduct(BaseModel):
    """
    {
      "type": "Product",
      "name": "fresh tomatoes loose",
      "barcode": "9414742353200",
      "variety": "loose",
      "brand": "fresh",
      "slug": "fresh-tomatoes-loose",
      "sku": "149681",
      "unit": "Kg",
      "selectedPurchasingUnit": null,
      "price": {...},
      "images": {
        "small": "https://assets.woolworths.com.au/images/2010/149681.jpg?impolicy=wowcdxwbjbx&w=65&h=65",
        "big": "https://assets.woolworths.com.au/images/2010/149681.jpg?impolicy=wowcdxwbjbx&w=200&h=200"
      },
      "quantity": {...},
      "stockLevel": 3,
      "eachUnitQuantity": null,
      "averageWeightPerUnit": 0.12,
      "size": {...},
      "hasShopperNotes": null,
      "productTag": {
        "tagType": "Other",
        "multiBuy": null,
        "bonusPoints": null,
        "additionalTag": {
          "name": "Countdown's Own",
          "link": "/shop/productgroup/80842",
          "imagePath": "/Content/PromotionTags/F24_Own_brand.png",
          "linkTarget": "_self",
          "altText": null
        },
        "targetedOffer": null,
        "boostOffer": null
      },
      "departments": [...],
      "subsAllowed": false,
      "supportsBothEachAndKgPricing": true,
      "adId": null,
      "brandSuggestionId": null,
      "brandSuggestionName": null,
      "priceUnitLabel": null,
      "availabilityStatus": "In Stock",
      "onlineSample": null,
      "onlineSampleRealProductMapId": 0,
      "isAgeRestricted": false,
      "isTobaccoProduct": false
    },
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
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

        try:
            if self.size.cup_measure is not None:
                return ProductResponse(
                    id=self.sku,
                    cost_per_unit=self.price.sale_price
                    if self.price.sale_price is not None
                    else self.price.original_price,
                    name=self.name.strip(),
                    category=category,
                    value=Value(
                        cost_per=self.size.cup_price,
                        amount=Amount(
                            number=self.size.cup_measure.number,
                            measurement=self.size.cup_measure.measurement,
                        ),
                    ),
                    cart_parameters=CartParameters(
                        min=self.quantity.min,
                        max=self.quantity.max,
                        increment=self.quantity.increment,
                    ),
                )
        except Exception as e:
            return ProductError(
                message=f"Unable to convert product response: {self}",
                exception_error_message=str(e),
            )

        return ProductError(message=f"Product missing measure size: {self}")
