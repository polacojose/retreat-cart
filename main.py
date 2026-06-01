from models.category import Category
from models.product import ProductRequest, PossibleProductResponse
from pydantic import SecretStr, BaseModel, Field
import asyncio
import uuid
from enum import Enum
from typing import Annotated, List, Optional

from fastapi import FastAPI, Form, HTTPException, Depends

from core import log
from clients.retreat.client import RetreatManagerClient
from clients.retreat.models import Retreat
from services.grocery import (
    GroceryStoreCacher,
    GroceryStoreService,
    SessionType,
    session_request_adapter,
    GroceryStore,
    GroceryChain,
)


class Tags(str, Enum):
    Auth = "Authentication"
    Retreat = "Retreat Manager"
    Grocery = "Grocery Chain"
    Conversion = "Conversion"


grocery_chain_cacher = GroceryStoreCacher()
app = FastAPI()


class SessionParams(BaseModel):
    grocery_chain: GroceryChain
    session_type: SessionType
    username: Optional[Annotated[str, Form()]] = None
    password: Optional[Annotated[SecretStr, Form()]] = None


def validate_session_params(
    grocery_chain: GroceryChain,
    session_type: SessionType,
    username: Optional[Annotated[str, Form()]] = None,
    password: Optional[Annotated[SecretStr, Form()]] = None,
) -> SessionParams:
    if session_type == SessionType.Authenticated and (
        username is None or password is None
    ):
        raise HTTPException(
            status_code=422,
            detail="Username and Password are required for authenticated sessions.",
        )

    return SessionParams(
        grocery_chain=grocery_chain,
        session_type=session_type,
        username=username,
        password=password,
    )


####################
# RetreatManager
####################
@app.get("/retreats", tags=[Tags.Retreat])
async def retreats() -> List[Retreat]:
    """Retrieves of list of Retreats from RetreatManager."""

    try:
        log.info("Getting retreats...")
        async with RetreatManagerClient() as retreats_manager:
            retreats = await retreats_manager.get_retreats()
            return [r.model_dump() for r in retreats]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve list of retreats: {e}"
        )


@app.get("/retreats/shopping_list", tags=[Tags.Retreat])
async def retreat_shopping_list(retreat_id: int) -> List[ProductRequest]:
    """Displays a retreat's shopping list."""

    try:
        log.info("Retrieving shopping list...")
        async with RetreatManagerClient() as retreats_manager:
            return await retreats_manager.get_shopping_list(retreat_id)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve retreat shopping list: {e}"
        )


@app.get("/add_shopping_list_to_cart", tags=[Tags.Retreat])
async def add_shopping_list_to_cart(
    retreat_id: int, grocery_chain_session_id: uuid.UUID
) -> List[PossibleProductResponse]:
    """Responsible for pairing a retreat's shopping list with a grocery store's products"""

    try:
        log.info("Retrieving shopping list...")
        async with RetreatManagerClient() as retreats_manager:
            shopping_list = await retreats_manager.get_shopping_list(retreat_id)

        log.info("Searching for items in grocery...")
        async with GroceryStoreService(
            grocery_chain_cacher.get_session(grocery_chain_session_id)
        ) as service:
            async with asyncio.TaskGroup() as tg:
                tasks = []
                for item in shopping_list:
                    tasks.append(tg.create_task(service.search(item.name)))

        return [t.result()[0] for t in tasks]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search results: {e}")


####################
# GroceryStore
####################
@app.post("/grocery/generate_session", tags=[Tags.Grocery])
async def grocery_generate_session(
    params: SessionParams = Depends(validate_session_params),
) -> uuid.UUID:
    """Generates a cached Grocery Chain session."""

    try:
        return await grocery_chain_cacher.generate_session(
            params.grocery_chain,
            session_request_adapter.validate_python(
                {
                    "session_type": params.session_type,
                    "username": params.username,
                    "password": params.password,
                }
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Unable to login: {e}")


@app.get("/grocery/stores", tags=[Tags.Grocery])
async def grocery_stores(
    grocery_chain_session_id: uuid.UUID,
) -> List[GroceryStore]:
    """Return a list of  grocery chain's stores."""
    try:
        async with GroceryStoreService(
            grocery_chain_cacher.get_session(grocery_chain_session_id)
        ) as service:
            return await service.stores()

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list stores for grocery chain: {e}"
        )


@app.post("/grocery/select_store", tags=[Tags.Grocery])
async def grocery_select_store(
    grocery_chain_session_id: uuid.UUID, grocery_store_id: Annotated[str, Field()]
) -> bool:
    """Select a grocery store."""
    try:
        async with GroceryStoreService(
            grocery_chain_cacher.get_session(grocery_chain_session_id)
        ) as service:
            await service.select_store(grocery_store_id)
            return True
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to select a grocery store: {e}"
        )


@app.post("/grocery/add_item_to_cart", tags=[Tags.Grocery])
async def grocery_add_item_to_cart(
    item_id: Annotated[str, Form()],
    amount: Annotated[int, Form()],
    grocery_chain_session_id: Annotated[uuid.UUID, Form()],
) -> bool:
    """Adds a number of items to a grocery store."""

    try:
        log.info(f"Adding {amount} of {item_id}...")

        async with GroceryStoreService(
            grocery_chain_cacher.get_session(grocery_chain_session_id)
        ) as service:
            await service.add_to_cart(item_id, amount)

        return True
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to add item to grocery store cart: {e}"
        )


@app.get("/grocery/search", tags=[Tags.Grocery])
async def grocery_search(
    product_name: str,
    grocery_chain_session_id: uuid.UUID,
    category: Optional[Category] = None,
) -> List[PossibleProductResponse]:
    """Searching the grocery store for the specified items."""

    try:
        log.info(f"Searching grocery store for {product_name}...")

        async with GroceryStoreService(
            grocery_chain_cacher.get_session(grocery_chain_session_id)
        ) as service:
            return await service.search(product_name, category)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to search grocery store: {e}"
        )
