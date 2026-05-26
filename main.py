import uuid
from enum import Enum
import asyncio
import logging

from fastapi import FastAPI

from repos.retreat.client import RetreatManager
from services.grocery import GroceryStoreCacher, GroceryStoreType

log = logging.getLogger(__name__)


class Tags(str, Enum):
    Core = "Core"
    Retreat = "Retreat"
    Grocery = "Grocery Store"


grocery_store_cacher = GroceryStoreCacher()
app = FastAPI()


@app.get("/generate_session", tags=[Tags.Core])
async def generate_session(grocery_store_type: GroceryStoreType, username, password):
    """Generates a cached grocery_store session."""

    return await grocery_store_cacher.generate_session(
        grocery_store_type, username, password
    )


@app.get("/retreats", tags=[Tags.Retreat])
async def retreats():
    """Retrieves of list of Retreats from RetreatManager."""

    async with RetreatManager() as retreats_manager:
        retreats = await retreats_manager.get_retreats()
        return [r.model_dump() for r in retreats]


@app.get("/shopping_list", tags=[Tags.Retreat])
async def shopping_list(retreat_id: int):
    """Displays a retreat's shopping list."""

    log.info("Retrieving shopping list...")
    async with RetreatManager() as retreats_manager:
        return await retreats_manager.get_shopping_list(retreat_id)


@app.get("/add_item_to_cart", tags=[Tags.Grocery])
async def add_item_to_cart(item_id: str, amount: int, session_id: uuid.UUID):
    """Adds a number of items to a grocery store."""

    log.info(f"Adding {amount} of {item_id}...")
    grocery_store = await grocery_store_cacher.get_session(session_id)
    await grocery_store.add_to_cart(item_id, amount)
    return {}


@app.get("/grocery_search", tags=[Tags.Grocery])
async def grocery_search(product_name: str, session_id: uuid.UUID):
    """Searching the grocery store for the specified items."""

    log.info(f"Searching grocery store for {product_name}...")
    grocery_store = await grocery_store_cacher.get_session(session_id)
    return await grocery_store.search(product_name)


@app.get("/search_results")
async def search_results(retreat_id: int, session_id: uuid.UUID):
    """Responsible for pairing a retreat's shopping list with a grocery store's products"""

    grocery_store = await grocery_store_cacher.get_session(session_id)
    log.info("Retrieving shopping list...")
    async with RetreatManager() as retreats_manager:
        shopping_list = await retreats_manager.get_shopping_list(retreat_id)

    log.info("Searching for items in grocery...")
    async with asyncio.TaskGroup() as tg:
        tasks = []
        for item in shopping_list:
            tasks.append(tg.create_task(grocery_store.search(item.name)))

    return [t.result()[0] for t in tasks]
