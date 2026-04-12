from pydantic import BaseModel, Field


class PaymentPreferenceCreate(BaseModel):
    title: str = "Produto ou Plano"
    quantity: int = Field(1, ge=1, le=999)
    unit_price: float = Field(..., gt=0, description="Valor unitário em BRL")
