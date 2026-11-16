"""Add evidence and scoring fields to screening_results

Revision ID: add_evidence_fields
Revises: 525a95dee632
Create Date: 2024-01-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_evidence_fields'
down_revision: Union[str, None] = '525a95dee632'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to screening_results table
    op.add_column('screening_results', sa.Column('skill_evidence', postgresql.JSONB(), nullable=True))
    op.add_column('screening_results', sa.Column('requirement_matches', postgresql.JSONB(), nullable=True))
    op.add_column('screening_results', sa.Column('required_skill_coverage', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('screening_results', sa.Column('preferred_skill_coverage', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('screening_results', sa.Column('scoring_strategy', postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    # Remove new columns from screening_results table
    op.drop_column('screening_results', 'scoring_strategy')
    op.drop_column('screening_results', 'preferred_skill_coverage')
    op.drop_column('screening_results', 'required_skill_coverage')
    op.drop_column('screening_results', 'requirement_matches')
    op.drop_column('screening_results', 'skill_evidence')
