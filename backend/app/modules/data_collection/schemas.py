from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CollectionRequest(BaseModel):
    source: str = Field(min_length=1, max_length=100)


class CollectionResult(BaseModel):
    source: str
    fetched_at: datetime
    record_count: int
    records: list[dict[str, Any]]
