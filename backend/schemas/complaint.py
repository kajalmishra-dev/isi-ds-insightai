from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


class ReadyResponse(BaseModel):
    status: str
    database: bool
    model: bool
    model_version: Optional[str] = None
    detail: Optional[str] = None


class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class PredictAlternative(BaseModel):
    category: str
    confidence: float


class PredictResponse(BaseModel):
    category: str
    confidence: float
    needs_review: bool
    model_version: str = "unknown"
    alternatives: list[PredictAlternative] = Field(default_factory=list)


class ComplaintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    category: Optional[str]
    confidence: Optional[float]
    needs_review: bool = False
    job_id: Optional[str] = None
    created_at: Optional[datetime]
    resolved_at: Optional[datetime]


class ReviewDecision(BaseModel):
    """Human triage: set ground-truth category and clear the review flag."""

    category: str = Field(..., min_length=1, max_length=64)


class ComplaintListResponse(BaseModel):
    items: list[ComplaintResponse]
    total: int
    page: int
    page_size: int
    total_pages: int = 0


class TopIssue(BaseModel):
    category: str
    count: int


class InsightItem(BaseModel):
    code: str
    text: str


class AnalyticsSummary(BaseModel):
    total_complaints: int
    resolved_count: int
    unresolved_count: int = 0
    needs_review_count: int
    category_distribution: dict[str, float]
    north_star_metric: float
    avg_confidence: float
    top_issues: list[TopIssue]
    resolution_rate: float = 0.0
    avg_resolution_hours: Optional[float] = None
    median_resolution_hours: Optional[float] = None
    low_confidence_rate: float = 0.0
    within_24h_count: int = 0
    category_avg_confidence: dict[str, float] = Field(default_factory=dict)
    insights: list[InsightItem] = Field(default_factory=list)


class UploadAccepted(BaseModel):
    job_id: str
    message: str
    status: str
    deduplicated: bool = False


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    status: str
    total_rows: int = 0
    processed_rows: int = 0
    skipped_rows: int = 0
    error_rows: int = 0
    error_message: Optional[str] = None
    quality_summary: Optional[str] = None
    content_hash: Optional[str] = None
    # source_path is stored server-side for retry only — never exposed to clients.
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    can_retry: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def progress_percentage(self) -> float:
        if self.status == "completed":
            return 100.0
        if self.status == "failed" and self.total_rows <= 0:
            return 0.0
        if self.total_rows <= 0:
            return 0.0 if self.status == "pending" else 5.0
        accounted = self.processed_rows + self.skipped_rows + self.error_rows
        return round(min(100.0, (accounted / self.total_rows) * 100.0), 1)


class ErrorResponse(BaseModel):
    detail: str
