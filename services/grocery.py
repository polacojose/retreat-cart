import asyncio
import uuid
from enum import Enum
from typing import Any, List, Protocol, Self

from pydantic import SecretStr

from repos.woolworths.client import WoolworthsAPI
from services.shoppinglist import Category, ProductResponse


class GroceryStore(Protocol):
    async def authenticate(username: str, password: str): ...
    async def close(self): ...

    async def search(self, name_search: str) -> List[ProductResponse]: ...

    async def add_to_cart(self, id: str, amount: int): ...


class GroceryStoreType(str, Enum):
    Woolworths = "woolworths"


class GroceryStoreCacher:
    def __init__(self):
        self.__cache = {}
        self.__sem = asyncio.Semaphore(1)

    async def generate_session(
        self, grocery_store_type: GroceryStoreType, username: str, password: SecretStr
    ) -> uuid.UUID:
        async with self.__sem:
            match grocery_store_type:
                case GroceryStoreType.Woolworths:
                    grocery_store = WoolworthsAPI()
                    await grocery_store.authenticate(username, password)
                case _:
                    raise ValueError(
                        f"Invalid GroceryStoryType ({grocery_store_type}) provided."
                    )

            id = uuid.uuid4()
            self.__cache[id] = grocery_store
            return id

    def get_session(self, session_id: uuid.UUID) -> GroceryStore:
        if session_id in self.__cache:
            return self.__cache[session_id]
        raise ValueError(f"Invalid session_id ({session_id}).")


class GroceryStoreService:
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
