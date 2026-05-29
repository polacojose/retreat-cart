from services.shoppinglist import ProductResponse, Category, Measurement


def test_product_parse():
    product = ProductResponse.model_validate(
        {
            "id": "test_id",
            "name": "Test Product",
            "cost": 2,
            "amount": 100,
            "measurement": Measurement.Gram,
            "category": "stuff",
        }
    )
    assert product.category == Category.Other

    product = ProductResponse.model_validate(
        {
            "id": "test_id",
            "name": "Test Product",
            "cost": 2,
            "amount": 100,
            "measurement": Measurement.Gram,
            "category": Category.best_guess("Fruits Vegetables"),
        }
    )
    assert product.category == Category.FruitVegetables


def test_category_guess():
    assert Category.best_guess("Fruit & Veg") == Category.FruitVegetables
    assert Category.best_guess("frozen") == Category.Frozen
