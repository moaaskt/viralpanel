"""initial schema

Revision ID: 001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None

TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "source_videos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("url", sa.String(512), nullable=False, unique=True),
        sa.Column("author", sa.String(128)),
        sa.Column("metrics", sa.JSON()),
        sa.Column("score", sa.Float()),
        sa.Column("collected_at", TS, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
    )
    op.create_index("ix_source_videos_score", "source_videos", ["score"])
    op.create_index("ix_source_videos_status", "source_videos", ["status"])
    op.create_table(
        "scripts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_video_id", sa.String(36), sa.ForeignKey("source_videos.id"), nullable=False),
        sa.Column("transcription", sa.Text()),
        sa.Column("script_text", sa.Text()),
        sa.Column("hook", sa.Text()),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", TS, nullable=False),
    )
    op.create_index("ix_scripts_source_video_id", "scripts", ["source_video_id"])
    op.create_table(
        "assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("script_id", sa.String(36), sa.ForeignKey("scripts.id"), nullable=False),
        sa.Column("asset_type", sa.String(32), nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("duration_seconds", sa.Float()),
        sa.Column("created_at", TS, nullable=False),
    )
    op.create_index("ix_assets_script_id", "assets", ["script_id"])
    op.create_table(
        "publications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("scheduled_for", TS),
        sa.Column("published_at", TS),
        sa.Column("url", sa.String(512)),
        sa.Column("status", sa.String(32), nullable=False),
    )
    op.create_index("ix_publications_asset_id", "publications", ["asset_id"])
    op.create_index("ix_publications_status", "publications", ["status"])
    op.create_table(
        "runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("started_at", TS, nullable=False),
        sa.Column("stage", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("duration_seconds", sa.Float()),
        sa.Column("run_metadata", sa.JSON()),
    )
    op.create_index("ix_runs_status", "runs", ["status"])


def downgrade() -> None:
    for t in ("runs", "publications", "assets", "scripts", "source_videos"):
        op.drop_table(t)