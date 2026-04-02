from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TextJobCreateRequest(BaseModel):
    clientRequestId: UUID
    prompt: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class JobStatusResponse(BaseModel):
    id: str
    type: str
    status: str
    clientRequestId: str
    remoteJobId: str | None
    assetId: str | None
    progress: float
    lastError: str | None
    outputAssets: list[str] = Field(default_factory=list)
    outputManifest: dict[str, Any] | None
    createdAt: datetime
    updatedAt: datetime


class JobCreateResponse(BaseModel):
    created: bool
    job: JobStatusResponse


class AssetImportResponse(BaseModel):
    assetId: str
    manifest: dict[str, Any]


class CancelJobResponse(BaseModel):
    job: JobStatusResponse


class ErrorPayloadDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any]
    request_id: str | None = None


class ErrorPayload(BaseModel):
    error: ErrorPayloadDetail
