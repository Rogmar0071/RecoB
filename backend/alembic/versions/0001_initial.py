"""Initial migration: create folders, folder_messages, jobs, artifacts tables.

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # folders
    # -------------------------------------------------------------------------
    op.create_table(
        "folders",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("clip_object_key", sa.Text, nullable=True),
    )

    # -------------------------------------------------------------------------
    # folder_messages
    # -------------------------------------------------------------------------
    op.create_table(
        "folder_messages",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column(
            "folder_id",
            sa.Uuid,
            sa.ForeignKey("folders.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # -------------------------------------------------------------------------
    # jobs
    # -------------------------------------------------------------------------
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column(
            "folder_id",
            sa.Uuid,
            sa.ForeignKey("folders.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="queued"),
        sa.Column("progress", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rq_job_id", sa.Text, nullable=True),
    )

    # -------------------------------------------------------------------------
    # artifacts
    # -------------------------------------------------------------------------
    op.create_table(
        "artifacts",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column(
            "folder_id",
            sa.Uuid,
            sa.ForeignKey("folders.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("object_key", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("artifacts")
    op.drop_table("jobs")
    op.drop_table("folder_messages")
    op.drop_table("folders")
