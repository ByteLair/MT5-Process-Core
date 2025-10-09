from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

class Tick(BaseModel):
    ts: datetime = Field(..., description="ISO8601 UTC")
    symbol: str
    timeframe: str
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = 0
    spread: Optional[float] = None
    meta: Optional[Any] = None

class TickBatch(BaseModel):
    items: List[Tick]
