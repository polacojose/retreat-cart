from models.grocery import AddToCartItem
import asyncio
from typing import List

import httpx
from playwright.async_api import async_playwright
from playwright_stealth.stealth import Stealth
from pydantic import SecretStr

from clients.woolworths.models import WoolworthsProduct
from core import log, USER_AGENT
from models.product import PossibleProductResponse, ProductError, ProductRequest


class WoolworthsClient:
    __SEARCH_BASE = "https://www.woolworths.co.nz/api/v1/products?target=search&search={}&inStockProductsOnly=true"
    __LOGIN_URL = "https://www.woolworths.co.nz/api/v1/bff/initiate-oidc-signin?redirectUrl=https%3A%2F%2Fwww.woolworths.co.nz%2F"

    def __init__(self):
        self.__sem = asyncio.Semaphore(4)

    async def authenticated_client(self, username: str, password: SecretStr):
        log.info("Logging into Woolworths...")
        async with Stealth().use_async(async_playwright()) as p:
            browser = await p.firefox.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto(WoolworthsClient.__LOGIN_URL)
            await page.locator("#username").fill(username)
            async with page.expect_navigation():
                await page.get_by_role("button", name="Continue").click()
                await page.wait_for_url("**/login/password**", timeout=10000)

            await page.locator("#password").fill(password.get_secret_value())
            async with page.expect_navigation():
                await page.get_by_role("button", name="Sign in").click()
                await page.wait_for_url("**www.woolworths.co.nz**", timeout=10000)

            playwright_cookies = await context.cookies()
            user_agent = await page.evaluate("navigator.userAgent")

            await browser.close()

        cookies = {cookie["name"]: cookie["value"] for cookie in playwright_cookies}

        headers = {
            "user-agent": user_agent,
            "x-requested-with": "OnlineShopping.WebApp",
        }

        self.__client = httpx.AsyncClient(cookies=cookies, headers=headers)
        log.info("Logged into Woolworths.")

    async def public_client(self):
        self.__client = httpx.AsyncClient(
            headers={
                "user-agent": USER_AGENT,
                "x-requested-with": "OnlineShopping.WebApp",
            }
        )
        log.info("Logged into Woolworths.")

    async def search(
        self, product_request: ProductRequest
    ) -> List[PossibleProductResponse]:
        async with self.__sem:
            response = await self.__client.get(
                url=WoolworthsClient.__SEARCH_BASE.format(product_request.name),
                headers={
                    "user-agent": USER_AGENT,
                    "x-requested-with": "OnlineShopping.WebApp",
                },
                timeout=2,
            )

            response.raise_for_status()

            items = response.json()["products"]["items"]

            products = []

            for item in items:
                if "unit" not in item:
                    continue

                try:
                    ww_product = WoolworthsProduct.model_validate(item)
                    products.append(ww_product.to_product())
                except Exception as e:
                    products.append(
                        ProductError(
                            message=f"Unable to parse response: {item}",
                            exception_error_message=str(e),
                        )
                    )

            return products

    async def add_to_cart(self, items: List[AddToCartItem]):
        """sku: 57303"""

        for item in items:
            log.info(
                (
                    await self.__client.post(
                        "https://www.woolworths.co.nz/api/v1/trolleys/my/items",
                        json={
                            "sku": item.id,
                            "quantity": item.amount,
                            "pricingUnit": "Each",
                        },
                    )
                ).text
            )

    # exit method
    async def close(self):
        await self.__client.aclose()
