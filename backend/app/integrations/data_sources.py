import json
import logging
from typing import Any, Protocol

import asyncio
import httpx


class DataSourceError(Exception):
    pass


class DataSource(Protocol):
    async def fetch(self) -> list[dict[str, Any]]: ...

class BaseDataSource:
    """Base class for data sources."""

    async def fetch(self) -> list[dict[str, Any]]:
        raise NotImplementedError("Subclasses must implement the fetch method.")


# booking
class BookingDataSource(BaseDataSource):
    """Fetch a configured Apify actor endpoint returning JSON records."""
    name = "booking"

    async def fetch(self) -> list[dict[str, Any]]:

        await asyncio.sleep(1)  # Simulate async operation
        logging.info("Fetching data from Apify actor: %s", self.name)
        records: list[dict[str, Any]] = [{"sample": "data"}]  # Placeholder for actual data fetching logic
        return records



registered_data_sources = {
    "booking": BookingDataSource
}
