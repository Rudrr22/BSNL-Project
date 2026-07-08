from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from models.database import get_db
from models.models import LogEntry, Analysis, Anomaly
from models.schemas import LogEntryResponse

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.post("/upload")
async def upload_log_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a log file for AI analysis
    
    Flow:
    1. Read file
    2. Parse lines
    3. Save to PostgreSQL
    4. Trigger multi-agent analysis in background
    5. Return immediately (don't make user wait)
    """
    # Read file
    content = await file.read()
    text = content.decode("utf-8")
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Count severities
    critical = sum(1 for l in lines if "CRITICAL" in l)
    warning = sum(1 for l in lines if "WARNING" in l)
    info = len(lines) - critical - warning

    # Create analysis record
    analysis = Analysis(
        filename=file.filename,
        source="upload",
        status="processing",
        total_logs=len(lines),
        critical_count=critical,
        warning_count=warning,
        info_count=info
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Build logs list
    logs = [{"raw": line, "severity":
             "CRITICAL" if "CRITICAL" in line else
             "WARNING" if "WARNING" in line else "INFO"}
            for line in lines]

    # Start background analysis
    background_tasks.add_task(
        background_agent_analysis,
        logs=logs,
        analysis_id=analysis.id
    )

    return {
        "status": "processing",
        "analysis_id": analysis.id,
        "total_logs": len(lines),
        "critical": critical,
        "warning": warning,
        "info": info,
        "message": "🤖 AI Agents are analyzing your logs..."
    }


async def background_agent_analysis(logs: list, analysis_id: int):
    """
    Runs in background after upload
    
    1. Runs 3-agent LangGraph pipeline
    2. Saves anomalies to PostgreSQL
    3. Saves logs to ChromaDB for RAG
    4. Updates analysis status
    """
    from models.database import SessionLocal
    from models.models import Analysis, Anomaly
    from agents.workflow import run_analysis
    from rag.embeddings import embed_logs

    db = SessionLocal()
    try:
        print(f"\n🔄 Background analysis starting for ID: {analysis_id}")

        # Run multi-agent pipeline
        result = await run_analysis(
            logs=logs,
            analysis_id=analysis_id,
            source="upload"
        )

        # Save each anomaly to PostgreSQL
        for a in result.get("anomalies", []):
            anomaly = Anomaly(
                analysis_id=analysis_id,
                severity=a.get("severity", "WARNING"),
                component=a.get("component", "Unknown"),
                region=a.get("region", ""),
                event_type=a.get("event_type", ""),
                description=a.get("description", ""),
                root_cause=a.get("root_cause", ""),
                suggested_action=a.get("suggested_action", "")
            )
            db.add(anomaly)

        # Update analysis with report
        analysis = db.query(Analysis).filter(
            Analysis.id == analysis_id
        ).first()

        if analysis:
            analysis.summary = result.get("executive_summary", "")
            analysis.recommendations = "\n".join(
                result.get("recommendations", [])
            )
            analysis.status = "complete"
            db.commit()

        # Store logs in ChromaDB for RAG
        embed_logs(logs)
        print(f"✅ Background analysis complete for ID: {analysis_id}")

    except Exception as e:
        print(f"❌ Background analysis failed: {e}")
        import traceback
        traceback.print_exc()

        # Mark as failed
        analysis = db.query(Analysis).filter(
            Analysis.id == analysis_id
        ).first()
        if analysis:
            analysis.status = "failed"
            db.commit()
    finally:
        db.close()


@router.get("/recent", response_model=List[LogEntryResponse])
async def get_recent_logs(limit: int = 50, db: Session = Depends(get_db)):
    """Get most recent log entries"""
    logs = db.query(LogEntry)\
             .order_by(LogEntry.id.desc())\
             .limit(limit).all()
    return logs