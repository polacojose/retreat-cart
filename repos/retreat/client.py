import asyncio
import html
import re
from typing import List, Self

import httpx
from bs4 import BeautifulSoup
from pydantic_settings import BaseSettings, SettingsConfigDict

from repos.retreat.models import Retreat
from repos.retreat.models import RetreatProduct
from services.shoppinglist import Product


class RetreatConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="retreat_",
        extra="ignore",
    )
    email: str
    password: str


config = RetreatConfig()  # ty:ignore[missing-argument]


class RetreatManager:
    async def get_retreats(self) -> List[Retreat]:
        response = await self.__client.get(
            url="https://@retreatman.nztim.com/retreats",
            timeout=2,
        )

        matches = re.finditer(
            r"https://retreatman.nztim.com/retreats/([\d.]+)\">(.*?)<",
            response.text.strip(),
        )

        if not matches:
            raise ValueError("Could not parse list of retreats.")

        retreats = []
        for match in matches:
            id, name = match.groups()
            id = int(id)
            name = html.unescape(name)
            retreats.append(Retreat(id=id, name=name))

        return retreats

    async def get_shopping_list(self, retreat_id: int) -> List[Product]:

        shopping_response, category_response = await asyncio.gather(
            self.__client.get(
                url=f"https://retreatman.nztim.com/retreats/{retreat_id}/shopping",
                timeout=2,
            ),
            self.__client.get(
                url="https://retreatman.nztim.com/products",
                timeout=2,
            ),
        )

        soup = BeautifulSoup(category_response.text, features="html.parser")
        category_rows = {
            name.get_text().strip(): cat.get_text().strip()
            for r in soup.find_all("tr")[1:]
            if (cells := r.find_all("td")) and (name := cells[0]) and (cat := cells[1])
        }
        print(category_rows)

        soup = BeautifulSoup(shopping_response.text, features="html.parser")
        rows = [r for r in soup.find_all("tr") if len(r.findAll("td")) == 4]

        products = []
        for row in rows:
            cells = row.find_all("td")
            name = cells[0].get_text().strip()
            amount = cells[2].get_text().strip()
            products.append(
                RetreatProduct.model_validate(
                    {"name": name, "amount": amount, "category": category_rows[name]}
                ).to_product()
            )

        return products

    # entry method
    async def __aenter__(self) -> Self:
        self.__client = await httpx.AsyncClient().__aenter__()
        await self.__client.post(
            "https://retreatman.nztim.com/login",
            data={
                "_token": "4ocbxT3x3qJA85wm1IwdFCWjbXCJY8gLGkGcUYBK",
                "email": str(config.email),
                "password": str(config.password),
                "remember": 1,
            },
        )
        return self

    # exit method
    async def __aexit__(self, exc_type, exc, tb):
        await self.__client.__aexit__(exc_type, exc, tb)
