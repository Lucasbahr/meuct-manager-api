from pydantic import BaseModel
from typing import Optional, Any


class ResponseBase(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
