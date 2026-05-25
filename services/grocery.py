from repos.woolworths.models import WoolWorthsProduct
from typing import Protocol, List


class Grocery(Protocol):
    async def search(
        self, name_search: str, department_search: str | None = None
    ) -> List[WoolWorthsProduct]: ...

    async def add_to_cart(self, sku: str, amount: int): ...
