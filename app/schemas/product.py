
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)

class ProductResponse(BaseModel):
    id: int
    name: str
    description: str | None
    price: Decimal

    model_config = ConfigDict(from_attributes=True)
