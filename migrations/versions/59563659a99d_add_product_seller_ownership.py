"""add product seller ownership

Revision ID: 59563659a99d
Revises: 4238220b800b
Create Date: 2026-10-23 19:28:00.147446

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '59563659a99d'
down_revision: Union[str, Sequence[str], None] = '4238220b800b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("seller_id", sa.Integer(), nullable=True),
    )

    op.create_foreign_key(
        "fk_products_seller_id_users",
        "products",
        "users",
        ["seller_id"],
        ["id"],
    )

    op.create_index(
        "ix_products_seller_id",
        "products",
        ["seller_id"],
        unique=False,
    )

def downgrade() -> None:
    op.drop_index(
        "ix_products_seller_id",
        table_name="products",
    )
    op.drop_constraint(
        "fk_products_seller_id_users",
        "products",
        type_="foreignkey",
    )
    op.drop_column("products", "seller_id")