# schemas.py — Pydantic schemas for API validation
# These define the shape of data coming in and going out

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# ─── Log Schemas ──────────────────────────────────────────

class LogEntryCreate(BaseModel):
    """Schema for receiving a log from simulator"""
    timestamp: str
    severity: str
    component: str
    region: Optional[str] = None
    event_type: Optional[str] = None
    metric: Optional[str] = None
    value: Optional[float] = None
    raw: str
    source: Optional[str] = "live"

class LogEntryResponse(BaseModel):
    """Schema for sending log data to frontend"""
    id: int
    timestamp: str
    severity: str
    component: str
    region: Optional[str]
    event_type: Optional[str]
    raw: str
    created_at: datetime

    class Config:
        from_attributes = True  # allows reading from SQLAlchemy models

# ─── Anomaly Schemas ───────────────────────────────────────

class AnomalyResponse(BaseModel):
    """Schema for anomaly data sent to frontend"""
    id: int
    severity: str
    component: str
    region: Optional[str]
    event_type: Optional[str]
    description: Optional[str]
    root_cause: Optional[str]
    suggested_action: Optional[str]
    acknowledged: bool
    detected_at: datetime

    class Config:
        from_attributes = True

# ─── Analysis Schemas ──────────────────────────────────────

class AnalysisResponse(BaseModel):
    """Schema for analysis session data"""
    id: int
    filename: Optional[str]
    source: str
    total_logs: int
    critical_count: int
    warning_count: int
    info_count: int
    summary: Optional[str]
    recommendations: Optional[str]
    status: str
    created_at: datetime
    anomalies: List[AnomalyResponse] = []

    class Config:
        from_attributes = True

# ─── Stats Schema ──────────────────────────────────────────

class DashboardStats(BaseModel):
    """Schema for dashboard statistics"""
    total_logs_today: int
    critical_count: int
    warning_count: int
    info_count: int
    most_affected_tower: Optional[str]
    total_analyses: int