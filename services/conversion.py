from typing import Any, Self, List

from services.grocery import GroceryStore
from services.shoppinglist import Category, ProductResponse


class ShoppingListConversionService:
    __grocery_store: GroceryStore

    def __init__(self, grocery_store: GroceryStore):
        self.__grocery_store = grocery_store

    async def search(
        self, name_search: str, category: Category | None = None
    ) -> List[ProductResponse]:
        products = await self.__grocery_store.search(name_search)
        if category is not None:
            products = [p for p in products if p.category == category]
        return products

    async def add_to_cart(self, id: str, amount: int):
        await self.__grocery_store.add_to_cart(id, amount)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: Any):
        await self.__grocery_store.close()
