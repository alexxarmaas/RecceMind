"""Create pacenote feedback table.

Revision ID: 20260805_0001
Revises:
Create Date: 2026-08-05
"""

from alembic import op
import sqlalchemy as sa

revision = "20260805_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pacenote_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("radius", sa.Float(), nullable=False),
        sa.Column("heading_change", sa.Float(), nullable=False),
        sa.Column("length", sa.Float(), nullable=False),
        sa.Column("original_classification", sa.Integer(), nullable=False),
        sa.Column("user_classification", sa.Integer(), nullable=False),
        sa.Column("driver_id", sa.String(length=100), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pacenote_feedback_driver_id"), "pacenote_feedback", ["driver_id"])
    op.create_index(op.f("ix_pacenote_feedback_id"), "pacenote_feedback", ["id"])
    op.create_index(op.f("ix_pacenote_feedback_radius"), "pacenote_feedback", ["radius"])


def downgrade() -> None:
    op.drop_index(op.f("ix_pacenote_feedback_radius"), table_name="pacenote_feedback")
    op.drop_index(op.f("ix_pacenote_feedback_id"), table_name="pacenote_feedback")
    op.drop_index(op.f("ix_pacenote_feedback_driver_id"), table_name="pacenote_feedback")
    op.drop_table("pacenote_feedback")
