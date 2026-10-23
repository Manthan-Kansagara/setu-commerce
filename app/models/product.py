from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    seller_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )