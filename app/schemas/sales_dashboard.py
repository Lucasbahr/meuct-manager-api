from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SalesByDayRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: Optional[str] = None
    sales: float
    orders: int


class TopProductRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    name: str
    units_sold: int
    revenue: float


class GymSalesDashboardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    gym_id: int
    period_start: str
    period_end_exclusive: str
    total_sales: float
    total_orders: int
    average_ticket: float
    total_commission: float
    sales_by_day: List[SalesByDayRow] = Field(default_factory=list)
    top_products: List[TopProductRow] = Field(default_factory=list)


class TopAcademyRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    gym_id: int
    name: str
    gross_sales: float
    commission: float
    orders: int


class PlatformAdminDashboardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period_start: str
    period_end_exclusive: str
    total_revenue: float
    total_orders: int
    total_academies: int
    top_academies: List[TopAcademyRow] = Field(default_factory=list)
