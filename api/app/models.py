from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Tick(BaseModel):
    ts: datetime = Field(..., description="ISO8601 UTC")
    symbol: str
    timeframe: str
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: int | None = 0
    spread: float | None = None
    meta: Any | None = None


class TickBatch(BaseModel):
    items: list[Tick]
