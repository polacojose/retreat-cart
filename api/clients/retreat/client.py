from core import APP_CONFIG
from models.product import ProductRequest
import asyncio
import html
import re
from typing import List, Self

import httpx
from bs4 import BeautifulSoup

from clients.retreat.models import Retreat
from clients.retreat.models import RetreatProduct


class RetreatManagerClient:
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

    async def get_shopping_list(self, retreat_id: int) -> List[ProductRequest]:

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
                "email": str(APP_CONFIG.retreat_email),
                "password": str(APP_CONFIG.retreat_password),
                "remember": 1,
            },
        )
        return self

    # exit method
    async def __aexit__(self, exc_type, exc, tb):
        await self.__client.__aexit__(exc_type, exc, tb)
