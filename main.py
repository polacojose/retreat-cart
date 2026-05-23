import json
from typing import List
from product import Product, AvailabilityStatus
import httpx
import asyncio

SEARCH_BASE = "https://www.woolworths.co.nz/api/v1/products?target=search&search={}&inStockProductsOnly=true"
HEADERS = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "x-requested-with": "OnlineShopping.WebApp",
}


async def search(search_string: str, department: str | None = None) -> List[Product]:
    async with httpx.AsyncClient() as client:
        items = (
            await client.get(
                url=SEARCH_BASE.format(search_string), headers=HEADERS, timeout=2
            )
        ).json()["products"]["items"]
        products = [Product.model_validate(p) for p in items if "unit" in p][:20]

        if department is not None:
            products = [
                p
                for p in products
                if True in [department.lower() in d.name.lower() for d in p.departments]
            ]

        return products[:5]


async def main(search_string: str):
    products = await search(search_string, "veg")

    def product_value_cmp(p: Product):
        if p.size.cup_measure is not None:
            return p.size.cup_price / p.size.cup_measure.amount
        else:
            return p.size.cup_price

    products = sorted(products, key=product_value_cmp)
    products = [
        p for p in products if p.availability_status != AvailabilityStatus.out_of_stock
    ]
    out_json = json.dumps([j.model_dump() for j in products][:5])
    print(out_json)


asyncio.run(main("Courgette"))


# Have an interactive top 10 selection with the ingredients list for each item
