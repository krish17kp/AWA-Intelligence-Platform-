"""add canonical_key to source_document

Revision ID: a1b2c3d4e5f6
Revises: bdba9815b32a
Create Date: 2026-06-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'bdba9815b32a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'source_documents',
        sa.Column('canonical_key', sa.String(length=255), nullable=True)
    )
    op.create_index(
        op.f('ix_source_documents_canonical_key'),
        'source_documents',
        ['canonical_key'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_source_documents_canonical_key'),
        table_name='source_documents'
    )
    op.drop_column('source_documents', 'canonical_key')