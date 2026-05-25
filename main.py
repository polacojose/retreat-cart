import asyncio
import json
import logging

from fastapi import FastAPI, Request

from repos.retreat.client import RetreatManager
from repos.woolworths.client import WoolworthsAPI
from repos.woolworths.models import AvailabilityStatus, WoolWorthsProduct
from services.grocery import Grocery

log = logging.getLogger(__name__)


async def search(client: Grocery, search_string: str):
    products = await client.search(search_string)

    def product_value_cmp(p: WoolWorthsProduct):
        if p.size.cup_measure is not None:
            return p.size.cup_price / p.size.cup_measure.amount
        else:
            return p.size.cup_price

    # products = sorted(products, key=product_value_cmp)
    products = [
        p for p in products if p.availability_status != AvailabilityStatus.out_of_stock
    ]
    out_json = json.dumps([j.model_dump() for j in products][:5])

    # await client.add_to_cart("test", 1)
    print(out_json)


app = FastAPI()


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
    woolworths = WoolworthsAPI()
    await woolworths.login()
    await woolworths.add_items_to_cart(item_sku, number)
    await app.state.woolworths.close()
    return {}


@app.get("/search_results")
async def search_results():
    woolworths = WoolworthsAPI()
    await woolworths.login()
    log.info("Retrieving shopping list...")
    async with RetreatManager() as retreats_manager:
        retreats = await retreats_manager.get_retreats()
        shopping_list = await retreats_manager.get_shopping_list(retreats[0].id)

    log.info("Searching for items in grocery...")
    async with asyncio.TaskGroup() as tg:
        tasks = []
        for item in shopping_list:
            tasks.append(tg.create_task(woolworths.search(item.name)))

    for t in tasks:
        print(t.result()[0])

    await app.state.woolworths.close()


# Have an interactive top 10 selection with the ingredients list for each item
