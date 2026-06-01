from models.product import PossibleProductResponse, ProductError
from models.category import Category
from typing import Any, Self, List

from services.grocery import GroceryChainClient


class ShoppingListConversionService:
    __grocery_store: GroceryChainClient

    def __init__(self, grocery_store: GroceryChainClient):
        self.__grocery_store = grocery_store

    async def search(
        self, name_search: str, category: Category | None = None
    ) -> List[PossibleProductResponse]:
        products = await self.__grocery_store.search(name_search)
        if category is not None:
            products = [
                p
                for p in products
                if isinstance(p, ProductError) or p.category == category
            ]
        return products

    async def add_to_cart(self, id: str, amount: int):
        await self.__grocery_store.add_to_cart(id, amount)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: Any):
        _ = exc
        await self.__grocery_store.close()
