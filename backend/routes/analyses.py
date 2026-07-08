# analyses.py — Analysis and anomaly endpoints

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List
from datetime import datetime, date

from models.database import get_db
from models.models import LogEntry, Analysis, Anomaly
from models.schemas import AnalysisResponse, DashboardStats, AnomalyResponse

router = APIRouter(prefix="/api", tags=["analyses"])

@router.get("/analyses", response_model=List[AnalysisResponse])
async def get_all_analyses(db: Session = Depends(get_db)):
    """Get all past analysis sessions — shown in history page"""
    analyses = db.query(Analysis)\
                 .order_by(desc(Analysis.created_at))\
                 .all()
    return analyses

@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    """Get one specific analysis with all its anomalies"""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis

@router.get("/anomalies", response_model=List[AnomalyResponse])
async def get_anomalies(
    severity: str = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get all detected anomalies, optionally filtered by severity"""
    query = db.query(Anomaly)
    if severity:
        query = query.filter(Anomaly.severity == severity)
    anomalies = query.order_by(desc(Anomaly.detected_at)).limit(limit).all()
    return anomalies

@router.patch("/anomalies/{anomaly_id}/acknowledge")
async def acknowledge_anomaly(
    anomaly_id: int,
    db: Session = Depends(get_db)
):
    """Mark an anomaly as acknowledged by engineer"""
    anomaly = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")
    anomaly.acknowledged = True
    db.commit()
    return {"status": "acknowledged", "anomaly_id": anomaly_id}

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Get statistics for the main dashboard
    Shows: total logs today, severity counts, most affected tower
    """
    # Count logs by severity
    critical = db.query(LogEntry)\
                 .filter(LogEntry.severity == "CRITICAL")\
                 .count()
    warning = db.query(LogEntry)\
                .filter(LogEntry.severity == "WARNING")\
                .count()
    info = db.query(LogEntry)\
             .filter(LogEntry.severity == "INFO")\
             .count()

    # Find most affected tower
    most_affected = db.query(
        LogEntry.component,
        func.count(LogEntry.id).label("count")
    ).filter(
        LogEntry.severity == "CRITICAL"
    ).group_by(
        LogEntry.component
    ).order_by(
        desc("count")
    ).first()

    total_analyses = db.query(Analysis).count()

    return DashboardStats(
        total_logs_today=critical + warning + info,
        critical_count=critical,
        warning_count=warning,
        info_count=info,
        most_affected_tower=most_affected[0] if most_affected else None,
        total_analyses=total_analyses
    )