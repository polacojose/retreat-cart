import asyncio
import logging

from fastapi import FastAPI

from repos.retreat.client import RetreatManager
from repos.woolworths.client import WoolworthsAPI
from services.grocery import GroceryStore

log = logging.getLogger(__name__)


app = FastAPI()


async def get_grocery() -> GroceryStore:
    return WoolworthsAPI()


async def get_auth_grocery() -> GroceryStore:
    woolworths = WoolworthsAPI()
    await woolworths.authenticate()
    return woolworths


@app.get("/retreats")
async def retreats():
    async with RetreatManager() as retreats_manager:
        retreats = await retreats_manager.get_retreats()
        return [r.model_dump() for r in retreats]


@app.get("/shopping_list")
async def shopping_list(retreat_id: int):
    log.info("Retrieving shopping list...")
    async with RetreatManager() as retreats_manager:
        return await retreats_manager.get_shopping_list(retreat_id)


@app.get("/add_item_to_cart")
async def add_item_to_cart(item_sku: str, number: int):
    log.info(f"Adding {number} of {item_sku}...")
    grocery_store = await get_auth_grocery()
    await grocery_store.add_to_cart(item_sku, number)
    await app.state.woolworths.close()
    return {}


@app.get("/search_results")
async def search_results(retreat_id: int):
    grocery_store = await get_grocery()
    log.info("Retrieving shopping list...")
    async with RetreatManager() as retreats_manager:
        shopping_list = await retreats_manager.get_shopping_list(retreat_id)

    log.info("Searching for items in grocery...")
    async with asyncio.TaskGroup() as tg:
        tasks = []
        for item in shopping_list:
            tasks.append(tg.create_task(grocery_store.search(item.name)))

    return [t.result()[0] for t in tasks]


@app.get("/grocery_search")
async def grocery_search(product_name: str):
    """Searching Woolworths for the specified items."""
    log.info(f"Searching grocery store for {product_name}...")
    grocery_store = await get_grocery()
    return await grocery_store.search(product_name)


# Have an interactive top 10 selection with the ingredients list for each item
