"""Create core application models."""

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "0001_create_core_models"
down_revision = None
branch_labels = None
developer = None


def upgrade() -> None:
    op.create_table(
        "listings",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("mls_number", sa.String(length=64), nullable=True),
        sa.Column("address", sa.String(length=256), nullable=False),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("zip", sa.String(length=5), nullable=False),
        sa.Column("zip4", sa.String(length=10), nullable=True),
        sa.Column("county", sa.String(length=128), nullable=True),
        sa.Column("geom", Geometry("POINT", srid=4326), nullable=True),
        sa.Column("property_type", sa.Enum("SFR", "CONDO", "TOWNHOUSE", "MULTIFAMILY", "LAND", name="propertytype"), nullable=False),
        sa.Column("beds", sa.Integer(), nullable=True),
        sa.Column("baths", sa.Numeric(4, 2), nullable=True),
        sa.Column("living_sqft", sa.Integer(), nullable=True),
        sa.Column("lot_sqft", sa.Integer(), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("list_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("sold_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("list_date", sa.Date(), nullable=False),
        sa.Column("sold_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Enum("ACTIVE", "PENDING", "SOLD", "EXPIRED", "WITHDRAWN", name="listingstatus"), nullable=False),
        sa.Column("days_on_market", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("photos", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("raw", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("source", "source_id", name="uq_listings_source_source_id"),
    )
    op.create_index("ix_listings_geom", "listings", ["geom"])

    op.create_table(
        "market_reports",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("geography", sa.String(length=128), nullable=False),
        sa.Column("geo_type", sa.Enum("METRO", "ZIP", "COUNTY", "NEIGHBORHOOD", "CITY", name="geotype"), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("median_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("mean_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("active_listings", sa.Integer(), nullable=False),
        sa.Column("sold_last_30d", sa.Integer(), nullable=False),
        sa.Column("avg_days_on_market", sa.Numeric(8, 2), nullable=False),
        sa.Column("months_of_inventory", sa.Numeric(8, 2), nullable=False),
        sa.Column("absorption_rate", sa.Numeric(8, 4), nullable=False),
        sa.Column("yoy_price_change", sa.Numeric(8, 4), nullable=False),
        sa.Column("mom_price_change", sa.Numeric(8, 4), nullable=False),
        sa.Column("list_to_sold_ratio", sa.Numeric(8, 4), nullable=False),
        sa.Column("raw_metrics", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "signal_definitions",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("category", sa.Enum("PRICE", "INVENTORY", "VELOCITY", "ABSORPTION", name="signalcategory"), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=False),
        sa.Column("refresh_frequency", sa.String(length=64), nullable=False),
        sa.Column("output_schema", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "signal_logs",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("signal_id", PG_UUID(as_uuid=True), sa.ForeignKey("signal_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("geography", sa.String(length=128), nullable=False),
        sa.Column("geo_type", sa.Enum("METRO", "ZIP", "COUNTY", "NEIGHBORHOOD", "CITY", name="geotype"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_value", sa.Float(), nullable=False),
        sa.Column("computed_output", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("fired", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "comps",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("subject_listing_id", PG_UUID(as_uuid=True), sa.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("comp_listing_id", PG_UUID(as_uuid=True), sa.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("distance_miles", sa.Float(), nullable=False),
        sa.Column("sold_date_delta_days", sa.Integer(), nullable=False),
        sa.Column("raw_similarity", sa.Float(), nullable=False),
        sa.Column("adjustments", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("adjusted_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("comps")
    op.drop_table("signal_logs")
    op.drop_table("signal_definitions")
    op.drop_table("market_reports")
    op.drop_index("ix_listings_geom", table_name="listings")
    op.drop_table("listings")
    op.execute("DROP TYPE IF EXISTS geotype")
    op.execute("DROP TYPE IF EXISTS propertytype")
    op.execute("DROP TYPE IF EXISTS listingstatus")
    op.execute("DROP TYPE IF EXISTS signalcategory")
