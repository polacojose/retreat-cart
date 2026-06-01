from services.grocery import GroceryStore
import asyncio
import uuid
from typing import List

import httpx
from pydantic import SecretStr

from clients.clubplus import clubplus_authenticate
from clients.paknsave.models import PaknSaveProduct
from core import log
from models.product import PossibleProductResponse, ProductError


class _PaknSaveOAuth2Wrapper:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self.__auth_payload = {
            "fingerprintGuest": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
            "fingerprintUser": str(uuid.UUID),
        }
        self.__client = client if client else httpx.AsyncClient()
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
    __STORE_LIST_URL = "https://api-prod.paknsave.co.nz/v1/edge/store"

    def __init__(self):
        self.__store_id = None
        self.__sem = asyncio.Semaphore(1)

    async def authenticated_client(self, username: str, password: SecretStr):
        log.info("Logging into PaknSave...")
        self.__client = await _PaknSaveOAuth2Wrapper(
            await clubplus_authenticate(
                "https://www.paknsave.co.nz/auth/callback", username, password
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

    async def add_to_cart(self, id: str, amount: int):
        if self.__store_id is None:
            raise Exception("Store selection required.")
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
