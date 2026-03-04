"""Pydantic models para P0-1 API."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CreateOrderRequest(BaseModel):
    """Request para POST /orders"""
    symbol: str = Field(..., description="Símbolo BUY/SELL")
    order_type: str = Field(..., description="'BUY' or 'SELL'")
    volume: float = Field(..., gt=0)
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    take_profit: float = Field(..., gt=0)
    ml_score: float = Field(..., ge=0, le=1)
    detector_spike: float = Field(default=0.0)
    trader_approval: bool = Field(default=False)


class OrderAuditTrailItem(BaseModel):
    """Item no audit trail."""
    state: str
    timestamp: datetime
    message: str
    metadata: Optional[dict] = None


class CreateOrderResponse(BaseModel):
    """Response do POST /orders"""
    order_id: str
    symbol: str
    order_type: str
    volume: float
    status: str  # "ENQUEUED"
    created_at: datetime
    audit_trail: List[OrderAuditTrailItem]
