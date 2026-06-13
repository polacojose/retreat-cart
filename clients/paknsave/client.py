import re
from playwright.async_api import Page
from models.grocery import GroceryStore, AddToCartItem
import asyncio
import uuid
from typing import List

import httpx
from pydantic import SecretStr

from clients.clubplus import clubplus_authenticate
from clients.paknsave.models import PaknSaveProduct, PaknSaveDirectProduct
from core import log, USER_AGENT
from models.product import PossibleProductResponse, ProductError, SaleType


class _PaknSaveOAuth2Wrapper:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self.__auth_payload = {
            "fingerprintGuest": USER_AGENT,
            "fingerprintUser": str(uuid.UUID),
        }
        self.__client = client if client else httpx.AsyncClient()
        self.__auth_token = None

    async def authenticate(self) -> httpx.AsyncClient:
        response = await self.__client.post(
            "https://www.paknsave.co.nz/api/user/get-current-user",
            headers={
                "user-agent": USER_AGENT,
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
    __STORE_LIST_URL = "https://api-prod.paknsave.co.nz/v1/edge/store"

    def __init__(self):
        self.__store_id = None
        self.__sem = asyncio.Semaphore(1)

    async def authenticated_client(self, username: str, password: SecretStr):

        async def get_default_store(page: Page):
            default_data_content = (
                await page.locator("script#__NEXT_DATA__").inner_text()
            )[0:150]
            match = re.search(r'"id":"(.+?)"', default_data_content)
            if match:
                self.__store_id = match.group(1)

        log.info("Logging into PaknSave...")
        self.__client = await _PaknSaveOAuth2Wrapper(
            await clubplus_authenticate(
                "https://www.paknsave.co.nz/auth/callback",
                username,
                password,
                get_default_store,
            )
        ).authenticate()
        log.info("Logged into PaknSave.")

    async def public_client(self):
        self.__client = await _PaknSaveOAuth2Wrapper().authenticate()

    async def search(self, name_search: str) -> List[PossibleProductResponse]:
        async with self.__sem:
            if self.__store_id is None:
                raise Exception("Store selection required.")

            response = await self.__client.post(
                url=PaknSaveClient.__SEARCH_BASE.format(name_search),
                headers={
                    "user-agent": USER_AGENT,
                },
                json={
                    "algoliaQuery": {
                        "query": name_search,
                    },
                    "storeId": self.__store_id,
                    "hitsPerPage": 50,
                    "page": 0,
                    "sortOrder": "NI_POPULARITY_ASC",
                },
                timeout=2,
            )

            items = response.json().get("products")

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

    async def stores(self) -> List[GroceryStore]:
        async with self.__sem:
            response = await self.__client.get(
                url=PaknSaveClient.__STORE_LIST_URL,
                timeout=2,
            )
            response.raise_for_status()

            grocery_stores = []
            for ps_store in response.json()["stores"]:
                grocery_stores.append(
                    GroceryStore(
                        id=ps_store.get("id"),
                        name=ps_store.get("name"),
                        address=ps_store.get("address"),
                    )
                )

        return grocery_stores

    async def select_store(self, grocery_store_id: str):
        self.__store_id = grocery_store_id

    async def __get_product_by_id(self, product_id: str) -> PossibleProductResponse:
        if self.__store_id is None:
            raise Exception("Store selection required.")

        return PaknSaveDirectProduct.model_validate(
            (
                await self.__client.get(
                    f"https://api-prod.paknsave.co.nz/v1/edge/store/{self.__store_id}/product/{product_id}"
                )
            ).json()
        ).to_product()

    async def add_to_cart(self, items: List[AddToCartItem]):

        products_request = []
        for item in items:
            if self.__store_id is None:
                raise Exception("Store selection required.")

            product = await self.__get_product_by_id(item.id)
            if isinstance(product, ProductError):
                raise Exception("Invalid product id.")

            products_request.append(
                {
                    "productId": item.id,
                    "quantity": item.amount,
                    "sale_type": SaleType.Weight.value
                    if product.sale_type == SaleType.Both
                    else SaleType.Units.value,
                }
            )

        if len(products_request) > 0:
            request_data = {"products": products_request}

            response = await self.__client.post(
                "https://api-prod.paknsave.co.nz/v1/edge/cart",
                json=request_data,
            )
            response.raise_for_status()

    # exit method
    async def close(self):
        await self.__client.aclose()
