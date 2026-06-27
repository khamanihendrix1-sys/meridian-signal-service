"""Add listing performance indexes."""

from alembic import op

revision = "0003_add_listing_performance_indexes"
down_revision = "0002_create_comp_job"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_listings_status", "listings", ["status"])
    op.create_index("ix_listings_city", "listings", ["city"])
    op.create_index("ix_listings_zip", "listings", ["zip"])
    op.create_index("ix_listings_county", "listings", ["county"])
    op.create_index("ix_listings_list_price", "listings", ["list_price"])
    op.execute(
        "CREATE INDEX ix_listings_created_at_id_desc "
        "ON listings (created_at DESC, id DESC)"
    )


def downgrade() -> None:
    op.drop_index("ix_listings_created_at_id_desc", table_name="listings")
    op.drop_index("ix_listings_list_price", table_name="listings")
    op.drop_index("ix_listings_county", table_name="listings")
    op.drop_index("ix_listings_zip", table_name="listings")
    op.drop_index("ix_listings_city", table_name="listings")
    op.drop_index("ix_listings_status", table_name="listings")
