"""add stripe fields to users

Revision ID: 002_stripe_fields
Revises: 001_users
Create Date: 2025-04-08

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_stripe_fields"
down_revision: Union[str, None] = "001_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # These columns already exist from migration 001 but
    # we add indexes here for faster Stripe customer lookups
    op.create_index(
        "ix_users_stripe_customer_id",
        "users",
        ["stripe_customer_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_users_stripe_customer_id", table_name="users")
