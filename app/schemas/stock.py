from typing import Literal

from pydantic import BaseModel, Field

StockRemoveReason = Literal["manual", "loss", "adjustment", "cancel"]


class StockAddRequest(BaseModel):
    product_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)


class StockRemoveRequest(BaseModel):
    product_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1)
    reason: StockRemoveReason = "manual"
