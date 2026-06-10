"""initial schema

Creates all ATOShield tables from the SQLAlchemy metadata. Using create_all in
the initial revision keeps the ORM as the single source of truth for the schema;
subsequent revisions can use autogenerate for incremental changes.

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01 00:00:00
"""

from alembic import op  # noqa: F401

from app.db.models import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
