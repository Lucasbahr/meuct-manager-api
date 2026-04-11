from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


PaymentProvider = Literal["paypal", "mercado_pago"]
ProductSortField = Literal["name", "price", "created_at"]
SortDirection = Literal["asc", "desc"]


class ProductImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_url: str
    sort_order: int


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    gym_id: int
    name: str
    description: Optional[str] = None
    price: Decimal
    stock: Optional[int] = None
    track_stock: bool = True
    is_active: bool
    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None
    category_name: Optional[str] = None
    subcategory_name: Optional[str] = None
    images: List[ProductImageOut] = []


class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal = Field(gt=0)
    stock: int = Field(ge=0)
    track_stock: bool = True
    is_active: bool = True
    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None
    image_urls: List[str] = []


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = Field(default=None, gt=0)
    stock: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None
    image_urls: Optional[List[str]] = None


class CategoryCreate(BaseModel):
    name: str


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    gym_id: int
    name: str


class SubcategoryCreate(BaseModel):
    category_id: int
    name: str


class SubcategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    name: str


class PaymentConfigCreate(BaseModel):
    provider: PaymentProvider
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


class PaymentConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    gym_id: int
    provider: str
    client_id: Optional[str] = None
    has_client_secret: bool = False
    has_access_token: bool = False
    has_refresh_token: bool = False


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(ge=1)


class OrderCreate(BaseModel):
    items: List[OrderItemCreate]


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    price: Decimal


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    gym_id: int
    student_id: int
    total_amount: Decimal
    status: str
    payment_provider: Optional[str] = None
    external_checkout_id: Optional[str] = None
    created_at: Optional[str] = None
    items: List[OrderItemOut] = []


class CheckoutRequest(BaseModel):
    provider: PaymentProvider
    return_url: HttpUrl
    cancel_url: HttpUrl


class CheckoutResponse(BaseModel):
    provider: PaymentProvider
    redirect_url: str
    external_checkout_id: str
