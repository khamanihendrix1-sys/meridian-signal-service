"""Create comp job table and link comps to jobs."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "0002_create_comp_job"
down_revision = "0001_create_core_models"
branch_labels = None
developer = None


def upgrade() -> None:
    op.create_table(
        "comp_jobs",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "subject_listing_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("PENDING", "RUNNING", "SUCCESS", "FAILED", name="compjobstatus"),
            nullable=False,
        ),
        sa.Column(
            "comp_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")
        ),
        sa.Column("error", sa.String(length=1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "comps",
        sa.Column(
            "job_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("comp_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_index("ix_comps_job_id", "comps", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_comps_job_id", table_name="comps")
    op.drop_column("comps", "job_id")
    op.drop_table("comp_jobs")
