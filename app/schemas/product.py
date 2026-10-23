
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    model_config = ConfigDict(extra="forbid")

class ProductResponse(BaseModel):
    id: int
    name: str
    description: str | None
    price: Decimal
    seller_id: int | None

    model_config = ConfigDict(extra="forbid")
    model_config = ConfigDict(from_attributes=True)


class ProductUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)

    model_config = ConfigDict(extra="forbid")



class ProductPatch(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
    )
    price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=2,
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_patch_fields(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        for field in ("name", "price"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")

        return self
