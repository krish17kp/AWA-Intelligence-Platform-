"""Add ingestion_events, coverage_snapshots tables and new columns

Revision ID: d5e6f7a8b9c0
Revises: a1b2c3d4e5f6
Create Date: 2026-06-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ingestion_events table
    op.create_table(
        'ingestion_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=True),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['ingestion_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['source_documents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ingestion_events_run_id'), 'ingestion_events', ['run_id'], unique=False)
    op.create_index(op.f('ix_ingestion_events_document_id'), 'ingestion_events', ['document_id'], unique=False)
    op.create_index(op.f('ix_ingestion_events_event_type'), 'ingestion_events', ['event_type'], unique=False)

    # coverage_snapshots table
    op.create_table(
        'coverage_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('source_type', sa.String(length=100), nullable=True),
        sa.Column('date_range_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('date_range_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('records_found', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_preserved', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_extracted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duplicates_skipped', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_documents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='partial'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_coverage_snapshots_source'), 'coverage_snapshots', ['source'], unique=False)

    # Add columns to ingestion_runs
    op.add_column('ingestion_runs', sa.Column('run_type', sa.String(length=50), nullable=True, server_default='manual'))
    op.add_column('ingestion_runs', sa.Column('date_range_start', sa.DateTime(timezone=True), nullable=True))
    op.add_column('ingestion_runs', sa.Column('date_range_end', sa.DateTime(timezone=True), nullable=True))
    op.add_column('ingestion_runs', sa.Column('new_documents', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('ingestion_runs', sa.Column('duplicates_skipped', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('ingestion_runs', sa.Column('failed_documents', sa.Integer(), nullable=False, server_default='0'))

    # Add columns to source_documents
    op.add_column('source_documents', sa.Column('duplicate_of', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_source_documents_duplicate_of'), 'source_documents', ['duplicate_of'], unique=False)
    op.add_column('source_documents', sa.Column('extraction_status', sa.String(length=50), nullable=False, server_default='pending'))
    op.create_index(op.f('ix_source_documents_extraction_status'), 'source_documents', ['extraction_status'], unique=False)
    op.add_column('source_documents', sa.Column('extraction_method', sa.String(length=100), nullable=True))
    op.add_column('source_documents', sa.Column('text_storage_path', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove columns from source_documents
    op.drop_column('source_documents', 'text_storage_path')
    op.drop_column('source_documents', 'extraction_method')
    op.drop_index(op.f('ix_source_documents_extraction_status'), table_name='source_documents')
    op.drop_column('source_documents', 'extraction_status')
    op.drop_index(op.f('ix_source_documents_duplicate_of'), table_name='source_documents')
    op.drop_column('source_documents', 'duplicate_of')

    # Remove columns from ingestion_runs
    op.drop_column('ingestion_runs', 'failed_documents')
    op.drop_column('ingestion_runs', 'duplicates_skipped')
    op.drop_column('ingestion_runs', 'new_documents')
    op.drop_column('ingestion_runs', 'date_range_end')
    op.drop_column('ingestion_runs', 'date_range_start')
    op.drop_column('ingestion_runs', 'run_type')

    # Drop coverage_snapshots
    op.drop_index(op.f('ix_coverage_snapshots_source'), table_name='coverage_snapshots')
    op.drop_table('coverage_snapshots')

    # Drop ingestion_events
    op.drop_index(op.f('ix_ingestion_events_event_type'), table_name='ingestion_events')
    op.drop_index(op.f('ix_ingestion_events_document_id'), table_name='ingestion_events')
    op.drop_index(op.f('ix_ingestion_events_run_id'), table_name='ingestion_events')
    op.drop_table('ingestion_events')