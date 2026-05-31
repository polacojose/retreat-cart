from clients.paknsave.client import PaknSaveClient
from clients.woolworths.client import WoolworthsClient
import asyncio
import uuid
from enum import Enum
from typing import Annotated, Any, List, Literal, Protocol, Self, Union, cast

from fastapi import Form
from pydantic import BaseModel, Field, SecretStr, TypeAdapter

from services.shoppinglist import (
    Category,
    PossibleProductResponse,
    ProductError,
    ProductResponse,
)


class GroceryStore(Protocol):
    async def authenticated_client(self, username: str, password: SecretStr): ...
    async def public_client(self): ...

    async def search(self, name_search: str) -> List[PossibleProductResponse]: ...
    async def add_to_cart(self, id: str, amount: int): ...

    async def close(self): ...


class GroceryStoreType(str, Enum):
    Woolworths = "woolworths"
    PaknSave = "paknsave"


class SessionType(str, Enum):
    Authenticated = "authenticated"
    Public = "public"


class PublicSession(BaseModel):
    session_type: Literal[SessionType.Public]


class AuthenticatedSession(BaseModel):
    session_type: Literal[SessionType.Authenticated]
    username: Annotated[str, Form()]
    password: Annotated[SecretStr, Form()]


SessionRequest = Annotated[
    Union[PublicSession, AuthenticatedSession], Field(discriminator="session_type")
]
session_request_adapter = TypeAdapter(SessionRequest)


class GroceryStoreCacher:
    def __init__(self):
        self.__cache = {}
        self.__sem = asyncio.Semaphore(1)

    async def generate_session(
        self, grocery_store_type: GroceryStoreType, request: SessionRequest
    ) -> uuid.UUID:
        async with self.__sem:
            match grocery_store_type:
                case GroceryStoreType.Woolworths:
                    grocery_store = WoolworthsClient()
                case GroceryStoreType.PaknSave:
                    grocery_store = PaknSaveClient()
                case _:
                    raise ValueError(
                        f"Invalid GroceryStoryType ({grocery_store_type}) provided."
                    )

            if isinstance(request, PublicSession):
                await cast(GroceryStore, grocery_store).public_client()
            else:
                await cast(GroceryStore, grocery_store).authenticated_client(
                    request.username, request.password
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
    ) -> List[PossibleProductResponse]:
        products = await self.__grocery_store.search(name_search)
        if category is not None:
            products = [
                p
                for p in products
                if isinstance(p, ProductError)
                or (isinstance(p, ProductResponse) and p.category == category)
            ]
        return products

    async def add_to_cart(self, id: str, amount: int):
        await self.__grocery_store.add_to_cart(id, amount)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: Any):
        pass
