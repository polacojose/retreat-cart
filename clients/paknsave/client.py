import asyncio
import uuid
from typing import List

import httpx
from playwright.async_api import async_playwright
from pydantic import SecretStr

from clients.paknsave.models import PaknSaveProduct
from core import log
from models.product import PossibleProductResponse, ProductError


class _PaknSaveOAuth2Wrapper:
    def __init__(self):
        self.__auth_payload = {
            "fingerprintGuest": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
            "fingerprintUser": str(uuid.UUID),
        }
        self.__client = httpx.AsyncClient()
        self.__auth_token = None

    async def authenticate(self) -> httpx.AsyncClient:
        response = await self.__client.post(
            "https://www.paknsave.co.nz/api/user/get-current-user",
            headers={
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
            },
            json=self.__auth_payload,
        )
        response.raise_for_status()

        data = response.json()

        self.__auth_token = data.get("access_token")

        self.__client.headers.update({"Authorization": f"Bearer {self.__auth_token}"})

        return self.__client


class PaknSaveClient:
    __SEARCH_BASE = "https://api-prod.paknsave.co.nz/v1/edge/search/paginated/products"
    __LOGIN_URL = "https://www.woolworths.co.nz/api/v1/bff/initiate-oidc-signin?redirectUrl=https%3A%2F%2Fwww.woolworths.co.nz%2F"

    def __init__(self):
        self.__sem = asyncio.Semaphore(1)

    async def authenticated_client(self, username: str, password: SecretStr):
        log.info("Logging into PaknSave...")
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto(PaknSaveClient.__LOGIN_URL)
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
        log.info("Logged into PaknSave.")

    async def public_client(self):
        self.__client = await _PaknSaveOAuth2Wrapper().authenticate()

    async def search(self, name_search: str) -> List[PossibleProductResponse]:
        async with self.__sem:
            items = (
                (
                    await self.__client.post(
                        url=PaknSaveClient.__SEARCH_BASE.format(name_search),
                        headers={
                            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
                        },
                        json={
                            "algoliaQuery": {
                                "query": name_search,
                            },
                            "storeId": "e1925ea7-01bc-4358-ae7c-c6502da5ab12",
                            "hitsPerPage": 50,
                            "page": 0,
                            "sortOrder": "NI_POPULARITY_ASC",
                        },
                        timeout=2,
                    )
                )
                .json()
                .get("products")
            )

            products = []

            for item in items:
                try:
                    ps_product = PaknSaveProduct.model_validate(item)
                    products.append(ps_product.to_product())
                except Exception as e:
                    products.append(
                        ProductError(
                            message=f"Unable to parse response: {item}",
                            exception_error_message=str(e),
                        )
                    )

            return products

    async def add_to_cart(self, id: str, amount: int):
        """sku: 57303"""
        log.info(
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
