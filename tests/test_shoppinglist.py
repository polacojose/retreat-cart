from services.shoppinglist import Product, Amount, Category, AmountType


def test_product_parse():
    product = Product.model_validate(
        {
            "id": "test_id",
            "name": "Test Product",
            "amount": Amount(amount=100, type=AmountType.Gram),
            "category": "stuff",
        }
    )
    assert product.category == Category.Other

    product = Product.model_validate(
        {
            "id": "test_id",
            "name": "Test Product",
            "amount": Amount(amount=100, type=AmountType.Gram),
            "category": "Fruit & Vegetables",
        }
    )
    assert product.category == Category.FruitVegetables


def test_category_guess():

    assert Category.best_guess("Fruit & Veg") == Category.FruitVegetables
    assert Category.best_guess("frozen") == Category.Frozen
