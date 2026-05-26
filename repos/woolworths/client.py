from typing import List
from playwright.async_api import async_playwright
import asyncio

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict

from repos.woolworths.models import WoolWorthsProduct


class WoolworthsConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="woolworths_",
        extra="ignore",
    )
    username: str
    password: str


class WoolworthsAPI:
    __SEARCH_BASE = "https://www.woolworths.co.nz/api/v1/products?target=search&search={}&inStockProductsOnly=true"
    __LOGIN_URL = "https://www.woolworths.co.nz/api/v1/bff/initiate-oidc-signin?redirectUrl=https%3A%2F%2Fwww.woolworths.co.nz%2F"

    def __init__(self):
        self.__config = WoolworthsConfig()  # ty:ignore[missing-argument]
        self.__sem = asyncio.Semaphore(1)

    async def login(self):
        print("Logging into Woolworths...")
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto(WoolworthsAPI.__LOGIN_URL)
            await page.locator("#username").fill(self.__config.username)
            async with page.expect_navigation():
                await page.get_by_role("button", name="Continue").click()

            await page.locator("#password").fill(self.__config.password)
            async with page.expect_navigation():
                await page.get_by_role("button", name="Sign in").click()

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
        self, search_string: str, department: str | None = None
    ) -> List[WoolWorthsProduct]:

        async with httpx.AsyncClient() as client:
            async with self.__sem:
                items = (
                    await client.get(
                        url=WoolworthsAPI.__SEARCH_BASE.format(search_string),
                        headers={
                            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
                            "x-requested-with": "OnlineShopping.WebApp",
                        },
                        timeout=2,
                    )
                ).json()["products"]["items"]
                products = [
                    WoolWorthsProduct.model_validate(p) for p in items if "unit" in p
                ]

                if department is not None:
                    products = [
                        p
                        for p in products
                        if True
                        in [department.lower() in d.name.lower() for d in p.departments]
                    ]
                return products

    async def add_items_to_cart(self, sku: str, quantity: int):
        """sku: 57303"""
        print(
            (
                await self.__client.post(
                    "https://www.woolworths.co.nz/api/v1/trolleys/my/items",
                    json={"sku": sku, "quantity": quantity, "pricingUnit": "Each"},
                )
            ).text
        )

    # exit method
    async def close(self):
        await self.__client.aclose()
