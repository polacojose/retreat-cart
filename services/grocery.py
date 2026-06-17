import asyncio
import time
import uuid
from enum import Enum
from typing import Annotated, Any, List, Literal, Protocol, Self, Union, cast

from fastapi import Form
from pydantic import BaseModel, Field, SecretStr, TypeAdapter

from clients.paknsave.client import PaknSaveClient
from clients.woolworths.client import WoolworthsClient
from core import APP_CONFIG, log
from models.grocery import AddToCartItem, GroceryStore
from models.product import (
    PossibleProductResponse,
    ProductError,
    ProductRequest,
    ProductResponse,
)


class GroceryChainClient(Protocol):
    async def authenticated_client(self, username: str, password: SecretStr): ...
    async def public_client(self): ...

    async def stores(self) -> List[GroceryStore]:
        raise Exception("Grocery Store listing not supported.")

    async def select_store(self, grocery_store_id: str):
        _ = grocery_store_id
        raise Exception("Grocery Store selection not supported.")

    async def search(
        self, product_request: ProductRequest
    ) -> List[PossibleProductResponse]: ...

    async def add_to_cart(self, items: List[AddToCartItem]): ...

    async def close(self): ...


class GroceryChain(str, Enum):
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


class GroceryChainSessionCacherItem(BaseModel):
    cache_time: float
    grocery_chain_client: Any


class GroceryChainSessionCacher:
    def __init__(self):
        self.__cache: dict[uuid.UUID, GroceryChainSessionCacherItem] = {}
        self.__sem = asyncio.Semaphore(1)

    async def generate_session(
        self, grocery_chain_type: GroceryChain, request: SessionRequest
    ) -> uuid.UUID:
        async with self.__sem:
            match grocery_chain_type:
                case GroceryChain.Woolworths:
                    grocery_chain = cast(GroceryChainClient, WoolworthsClient())
                case GroceryChain.PaknSave:
                    grocery_chain = cast(GroceryChainClient, PaknSaveClient())

            if isinstance(request, PublicSession):
                await grocery_chain.public_client()
            else:
                await grocery_chain.authenticated_client(
                    request.username, request.password
                )

            id = uuid.uuid4()
            self.__cache[id] = GroceryChainSessionCacherItem(
                cache_time=time.time(), grocery_chain_client=grocery_chain
            )

            return id

    def get_session(self, session_id: uuid.UUID) -> GroceryChainClient:
        if (cache_item := self.__cache.get(session_id)) is not None:
            if time.time() - cache_item.cache_time > APP_CONFIG.grocery_chain_cache_ttl:
                del self.__cache[session_id]
                raise Exception("Session timed out")
            return cache_item.grocery_chain_client
        raise ValueError(f"Invalid session_id ({session_id}).")


class GroceryStoreService:
    __grocery_chain: GroceryChainClient

    def __init__(self, grocery_store: GroceryChainClient):
        self.__grocery_chain = grocery_store

    async def stores(self) -> List[GroceryStore]:
        return await self.__grocery_chain.stores()

    async def select_store(self, grocery_store_id: str):
        return await self.__grocery_chain.select_store(grocery_store_id)

    async def search(
        self, product_request: ProductRequest
    ) -> List[PossibleProductResponse]:
        try:
            products = await self.__grocery_chain.search(product_request)
            if product_request.category is not None:
                products = [
                    p
                    for p in products
                    if isinstance(p, ProductError)
                    or (
                        isinstance(p, ProductResponse)
                        and p.category == product_request.category
                    )
                ]
            return products
        except Exception as e:
            log.error(f"Unable to perform search: {e}")
            raise e

    async def add_to_cart(self, items: List[AddToCartItem]):
        await self.__grocery_chain.add_to_cart(items)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: Any):
        pass
