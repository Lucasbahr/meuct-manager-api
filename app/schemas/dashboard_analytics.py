"""Schemas para GET /dashboard/analytics (painel da academia)."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class StudentAnalyticsBlock(BaseModel):
    total: int
    active: int
    inactive: int
    new_in_reference_month: int
    new_in_previous_month: int
    new_delta_vs_previous_month: int
    new_percent_change_vs_previous_month: Optional[float] = None


class RevenueMonthMetrics(BaseModel):
    total: float
    total_orders: Optional[int] = None
    paid_payments_count: Optional[int] = None


class RevenueChangeBlock(BaseModel):
    amount_delta: float
    percent_change: Optional[float] = None


class ProductsRevenueBlock(BaseModel):
    reference_month: RevenueMonthMetrics
    previous_month: RevenueMonthMetrics
    change_vs_previous_month: RevenueChangeBlock
    sales_by_day: List[dict] = Field(default_factory=list)


class MembershipsRevenueBlock(BaseModel):
    reference_month: RevenueMonthMetrics
    previous_month: RevenueMonthMetrics
    change_vs_previous_month: RevenueChangeBlock
    revenue_by_day: List[dict] = Field(default_factory=list)
    by_plan: List[dict] = Field(default_factory=list)


class CombinedRevenueBlock(BaseModel):
    reference_month_total: float
    previous_month_total: float
    change_vs_previous_month: RevenueChangeBlock


class RevenueAnalyticsBlock(BaseModel):
    products: ProductsRevenueBlock
    memberships: MembershipsRevenueBlock
    combined: CombinedRevenueBlock


class DashboardAnalyticsOut(BaseModel):
    gym_id: int
    timezone: str = "America/Sao_Paulo"
    reference_year: int
    reference_month: int
    reference_period_start_utc: str
    reference_period_end_exclusive_utc: str
    previous_period_start_utc: str
    previous_period_end_exclusive_utc: str
    students: StudentAnalyticsBlock
    revenue: RevenueAnalyticsBlock
