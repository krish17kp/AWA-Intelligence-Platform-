"""Add state and filters to coverage snapshots

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-06-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "coverage_snapshots",
        sa.Column("state_code", sa.String(length=2), nullable=True),
    )
    op.add_column(
        "coverage_snapshots",
        sa.Column("filters_json", sa.JSON(), nullable=True),
    )
    op.create_index(
        op.f("ix_coverage_snapshots_state_code"),
        "coverage_snapshots",
        ["state_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_coverage_snapshots_state_code"),
        table_name="coverage_snapshots",
    )
    op.drop_column("coverage_snapshots", "filters_json")
    op.drop_column("coverage_snapshots", "state_code")
