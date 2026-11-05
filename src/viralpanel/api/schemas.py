"""Pydantic schemas for the ViralPanel REST API matching SQLAlchemy models."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str
    timestamp: datetime


class StatsResponse(BaseModel):
    total_runs: int
    total_videos: int
    total_scripts: int
    total_publications: int
    successful_runs: int
    failed_runs: int
    publications_by_platform: Dict[str, int]


class PipelineRunSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    started_at: datetime
    stage: str
    status: str
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None
    run_metadata: Optional[Dict[str, Any]] = None


class SourceVideoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    platform: str
    url: str
    author: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    score: Optional[float] = None
    collected_at: datetime
    status: str


class ScriptSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_video_id: str
    transcription: Optional[str] = None
    script_text: Optional[str] = None
    hook: Optional[str] = None
    version: int
    created_at: datetime


class AssetSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    script_id: str
    asset_type: str
    file_path: str
    duration_seconds: Optional[float] = None
    created_at: datetime


class PublicationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str
    platform: str
    scheduled_for: Optional[datetime] = None
    published_at: Optional[datetime] = None
    url: Optional[str] = None
    status: str


class TriggerResponse(BaseModel):
    task_id: str
    message: str
