from models.product import ProductResponse, Measure, SaleType
from clients.paknsave.models import PaknSaveProduct
from models.category import Category

test_cranberry_product = {
    "productId": "5119168-KGM-000",
    "name": "Cranberries, Sliced",
    "displayName": "kg",
    "availability": ["IN_STORE", "ONLINE"],
    "saleType": "WEIGHT",
    "restrictedFlag": False,
    "liquorFlag": False,
    "tobaccoFlag": False,
    "originRegulated": False,
    "variableWeight": {
        "minOrderQuantity": 100,
        "stepSize": 50,
        "stepUnitOfMeasure": "g",
    },
    "singlePrice": {
        "price": 2490,
        "comparativePrice": {
            "pricePerUnit": 2490,
            "unitQuantity": 1,
            "unitQuantityUom": "kg",
            "measureDescription": "1kg",
        },
    },
    "facets": [{"itemCode": "00020012", "itemDescription": "Non-GMO"}],
    "categoryTrees": [
        {
            "level0": "Pantry",
            "level1": "Bulk Foods",
            "level2": "Bulk Dried Fruit",
        }
    ],
    "cateredFlag": False,
    "algoliaAnalytics": {
        "searchQueryID": "af04cd5b81194f29df896966a5e3771e",
        "searchPosition": 4,
    },
    "boughtBefore": False,
}


def test_paknsave_product_parse():
    product = PaknSaveProduct.model_validate(test_cranberry_product)
    assert product.sale_type == "WEIGHT"


def test_service_product_parse():
    product = PaknSaveProduct.model_validate(test_cranberry_product).to_product()

    assert isinstance(product, ProductResponse)
    assert product.id == "5119168-KGM-000"
    assert product.name == "Cranberries, Sliced"
    assert product.category == Category.Pantry
    assert product.sale_type == SaleType.Weight
    assert product.cost_per_unit == 24.90
    assert product.value is not None
    assert product.value.cost_per == 24.90
    assert product.value.amount.number == 1000
    assert product.value.amount.measurement == Measure.Gram
