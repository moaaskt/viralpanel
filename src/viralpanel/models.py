import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from viralpanel.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SourceVideo(Base):
    __tablename__ = "source_videos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    platform: Mapped[str] = mapped_column(String(32), default="tiktok")
    url: Mapped[str] = mapped_column(String(512), unique=True)
    author: Mapped[str | None] = mapped_column(String(128))
    metrics: Mapped[dict | None] = mapped_column(JSON)
    score: Mapped[float | None] = mapped_column(Float, index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)

    scripts: Mapped[list["Script"]] = relationship(back_populates="source_video")


class Script(Base):
    __tablename__ = "scripts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_video_id: Mapped[str] = mapped_column(ForeignKey("source_videos.id"), index=True)
    transcription: Mapped[str | None] = mapped_column(Text)
    script_text: Mapped[str | None] = mapped_column(Text)
    hook: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    source_video: Mapped["SourceVideo"] = relationship(back_populates="scripts")
    assets: Mapped[list["Asset"]] = relationship(back_populates="script")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    script_id: Mapped[str] = mapped_column(ForeignKey("scripts.id"), index=True)
    asset_type: Mapped[str] = mapped_column(String(32))
    file_path: Mapped[str] = mapped_column(String(512))
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    script: Mapped["Script"] = relationship(back_populates="assets")
    publications: Mapped[list["Publication"]] = relationship(back_populates="asset")


class Publication(Base):
    __tablename__ = "publications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    platform: Mapped[str] = mapped_column(String(32))
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    url: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)

    asset: Mapped["Asset"] = relationship(back_populates="publications")


class PipelineRun(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    stage: Mapped[str] = mapped_column(String(64), default="init")
    status: Mapped[str] = mapped_column(String(16), default="running", index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    run_metadata: Mapped[dict | None] = mapped_column(JSON)
