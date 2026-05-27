from pydantic import SecretStr
import uuid
from repos.woolworths.client import WoolworthsAPI
from enum import Enum
import asyncio
from typing import List, Protocol

from services.shoppinglist import Product


class GroceryStore(Protocol):
    async def authenticate(username: str, password: str): ...
    async def close(): ...

    async def search(
        self, name_search: str, department_search: str | None = None
    ) -> List[Product]: ...

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

    async def get_session(self, session_id: uuid.UUID) -> GroceryStore:
        if session_id in self.__cache:
            return self.__cache[session_id]
        raise ValueError(f"Invalid session_id ({session_id}).")
