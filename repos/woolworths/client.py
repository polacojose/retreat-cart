from pydantic import SecretStr
from services.shoppinglist import Product
from typing import List
from playwright.async_api import async_playwright
import asyncio

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

from repos.woolworths.models import WoolWorthsProduct


class WoolworthsAPI:
    __SEARCH_BASE = "https://www.woolworths.co.nz/api/v1/products?target=search&search={}&inStockProductsOnly=true"
    __LOGIN_URL = "https://www.woolworths.co.nz/api/v1/bff/initiate-oidc-signin?redirectUrl=https%3A%2F%2Fwww.woolworths.co.nz%2F"

    def __init__(self):
        self.__sem = asyncio.Semaphore(1)

    async def authenticate(self, username: str, password: SecretStr):
        print("Logging into Woolworths...")
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto(WoolworthsAPI.__LOGIN_URL)
            await page.locator("#username").fill(username)
            async with page.expect_navigation():
                await page.get_by_role("button", name="Continue").click()
                await page.wait_for_url("**/login/password**", timeout=5000)

            await page.locator("#password").fill(password.get_secret_value())
            async with page.expect_navigation():
                await page.get_by_role("button", name="Sign in").click()
                await page.wait_for_url("**www.woolworths.co.nz**", timeout=5000)

            playwright_cookies = await context.cookies()
            user_agent = await page.evaluate("navigator.userAgent")

            await browser.close()

        cookies = {cookie["name"]: cookie["value"] for cookie in playwright_cookies}

        headers = {
            "user-agent": user_agent,
            "x-requested-with": "OnlineShopping.WebApp",
        }

        self.__client = httpx.AsyncClient(cookies=cookies, headers=headers)
        print("Logged into Woolworths.")

    async def search(
        self, name_search: str, department_search: str | None = None
    ) -> List[Product]:

        async with httpx.AsyncClient() as client:
            async with self.__sem:
                items = (
                    await client.get(
                        url=WoolworthsAPI.__SEARCH_BASE.format(name_search),
                        headers={
                            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
                            "x-requested-with": "OnlineShopping.WebApp",
                        },
                        timeout=2,
                    )
                ).json()["products"]["items"]
                ww_products = [
                    WoolWorthsProduct.model_validate(p) for p in items if "unit" in p
                ]

                if department_search is not None:
                    ww_products = [
                        p
                        for p in ww_products
                        if True
                        in [
                            department_search.lower() in d.name.lower()
                            for d in p.departments
                        ]
                    ]

                products = [
                    product
                    for p in ww_products
                    if (product := p.to_product()) is not None
                ]

                return products

    async def add_to_cart(self, id: str, amount: int):
        """sku: 57303"""
        print(
            (
                await self.__client.post(
                    "https://www.woolworths.co.nz/api/v1/trolleys/my/items",
                    json={"sku": id, "quantity": amount, "pricingUnit": "Each"},
                )
            ).text
        )

    # exit method
    async def close(self):
        await self.__client.aclose()
