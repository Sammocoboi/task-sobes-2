"""Initial demo data and activity history."""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("demo_options", sa.Column("kind", sa.String(30), primary_key=True), sa.Column("id", sa.Integer, primary_key=True), sa.Column("name", sa.String(255), nullable=False), sa.Column("state", sa.String(30), nullable=False, server_default="active"))
    op.create_table("demo_campaigns", sa.Column("id", sa.Integer, primary_key=True), sa.Column("name", sa.String(255), nullable=False), sa.Column("alias", sa.String(255), nullable=False), sa.Column("geo", sa.JSON, nullable=False), sa.Column("domain_id", sa.Integer, nullable=False), sa.Column("group_id", sa.Integer, nullable=False), sa.Column("traffic_source_id", sa.Integer, nullable=False), sa.Column("state", sa.String(30), nullable=False, server_default="active"), sa.Column("created_at", sa.DateTime, nullable=False))
    op.create_table("demo_streams", sa.Column("id", sa.Integer, primary_key=True), sa.Column("campaign_id", sa.Integer, sa.ForeignKey("demo_campaigns.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("type", sa.String(30), nullable=False), sa.Column("schema", sa.String(30), nullable=False), sa.Column("action_type", sa.String(50), nullable=False), sa.Column("action_payload", sa.String(2048), nullable=True), sa.Column("position", sa.Integer, nullable=False), sa.Column("filters", sa.JSON, nullable=False), sa.Column("offers", sa.JSON, nullable=False))
    op.create_table("activities", sa.Column("id", sa.Integer, primary_key=True), sa.Column("kind", sa.String(50), nullable=False), sa.Column("campaign_id", sa.Integer, nullable=False), sa.Column("summary", sa.String(500), nullable=False), sa.Column("created_at", sa.DateTime, nullable=False))


def downgrade() -> None:
    op.drop_table("activities")
    op.drop_table("demo_streams")
    op.drop_table("demo_campaigns")
    op.drop_table("demo_options")
