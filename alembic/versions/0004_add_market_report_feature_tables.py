"""Add generated market report artifact and schedule tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "0004_add_market_report_feature_tables"
down_revision = "0003_add_listing_performance_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_report_artifacts",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("report_type", sa.String(length=64), nullable=False),
        sa.Column("geography", sa.String(length=128), nullable=True),
        sa.Column(
            "geo_type",
            sa.Enum("METRO", "ZIP", "COUNTY", "NEIGHBORHOOD", "CITY", name="geotype"),
            nullable=True,
        ),
        sa.Column(
            "parameters",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column(
            "payload",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "market_report_schedules",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("geography", sa.String(length=128), nullable=False),
        sa.Column("frequency", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column(
            "metrics",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("market_report_schedules")
    op.drop_table("market_report_artifacts")
