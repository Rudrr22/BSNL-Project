# kpis.py — KPI endpoints: predictions, heatmap, call drops, KPI charts, NL2SQL
# Consolidates all new analytics endpoints

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, text, case
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta

from models.database import get_db
from models.models import LogEntry, Analysis, Anomaly

router = APIRouter(prefix="/api", tags=["kpis"])


# ═══════════════════════════════════════════════════════
# PREDICTIVE FAILURE SYSTEM
# ═══════════════════════════════════════════════════════

@router.get("/predictions")
async def get_predictions(db: Session = Depends(get_db)):
    """Get failure risk predictions for all towers"""
    from ml.predictor import get_tower_risk_scores
    predictions = get_tower_risk_scores(db)
    return {
        "predictions": predictions,
        "generated_at": datetime.utcnow().isoformat(),
        "model": "exponential_rate_analysis_v1"
    }


@router.get("/predictions/{component}/trend")
async def get_tower_trend(component: str, db: Session = Depends(get_db)):
    """Get hourly event trend for a specific tower"""
    from ml.predictor import get_hourly_trend
    trend = get_hourly_trend(db, component, hours=12)
    return {"component": component, "trend": trend}


# ═══════════════════════════════════════════════════════
# SIGNAL STRENGTH HEATMAP
# ═══════════════════════════════════════════════════════

# Real coordinates for BSNL regions
REGION_COORDS = {
    "Jaipur":   {"lat": 26.9124, "lng": 75.7873},
    "Delhi":    {"lat": 28.6139, "lng": 77.2090},
    "Mumbai":   {"lat": 19.0760, "lng": 72.8777},
    "Roorkee":  {"lat": 29.8543, "lng": 77.8880},
    "Lucknow":  {"lat": 26.8467, "lng": 80.9462},
}

@router.get("/heatmap")
async def get_heatmap_data(db: Session = Depends(get_db)):
    """
    Get signal strength data per region for geographic heatmap.
    Aggregates RSSI values and event counts.
    """
    regions = {}

    for region_name, coords in REGION_COORDS.items():
        # Average RSSI for this region
        avg_rssi = db.query(func.avg(LogEntry.value))\
            .filter(and_(
                LogEntry.region == region_name,
                LogEntry.metric == "RSSI"
            )).scalar()

        # Event counts by severity
        critical = db.query(func.count(LogEntry.id))\
            .filter(and_(
                LogEntry.region == region_name,
                LogEntry.severity == "CRITICAL"
            )).scalar() or 0

        warning = db.query(func.count(LogEntry.id))\
            .filter(and_(
                LogEntry.region == region_name,
                LogEntry.severity == "WARNING"
            )).scalar() or 0

        total = db.query(func.count(LogEntry.id))\
            .filter(LogEntry.region == region_name).scalar() or 0

        # Calculate health score (0-100, higher = healthier)
        if total > 0:
            health = max(0, 100 - (critical * 5) - (warning * 2))
        else:
            health = 50  # no data = neutral

        regions[region_name] = {
            **coords,
            "avg_rssi": round(avg_rssi, 1) if avg_rssi else None,
            "critical_count": critical,
            "warning_count": warning,
            "total_logs": total,
            "health_score": min(health, 100),
            "signal_quality": (
                "Good" if (avg_rssi and avg_rssi > -75) else
                "Fair" if (avg_rssi and avg_rssi > -85) else
                "Poor" if avg_rssi else "No data"
            )
        }

    return {"regions": regions}


# ═══════════════════════════════════════════════════════
# CALL DROP RATE ANALYZER
# ═══════════════════════════════════════════════════════

@router.get("/kpis/call-drops")
async def get_call_drop_rates(db: Session = Depends(get_db)):
    """
    Calculate call drop rate per tower.
    Formula: Handover_Failed / (Handover_Failed + Handover_Success) * 100
    TRAI threshold: 2%
    OPTIMIZED: Single bulk query using conditional aggregation (was N+1)
    """
    # Single bulk query — get failed, success, and region in one pass per component
    bulk = db.query(
        LogEntry.component,
        func.sum(case((LogEntry.event_type == "Handover_Failed", 1), else_=0)).label("failed"),
        func.sum(case((LogEntry.event_type == "Handover_Success", 1), else_=0)).label("success"),
        func.max(LogEntry.region).label("region"),
    ).filter(
        and_(
            LogEntry.component.isnot(None),
            LogEntry.event_type.in_(["Handover_Failed", "Handover_Success"])
        )
    ).group_by(LogEntry.component).all()

    rates = []
    for row in bulk:
        component = row.component
        failed = int(row.failed or 0)
        success = int(row.success or 0)
        total_handovers = failed + success
        drop_rate = (failed / total_handovers * 100) if total_handovers > 0 else 0

        rates.append({
            "component": component,
            "region": row.region or "Unknown",
            "handover_failed": failed,
            "handover_success": success,
            "total_handovers": total_handovers,
            "drop_rate_percent": round(drop_rate, 2),
            "trai_compliant": drop_rate <= 2.0,
            "status": (
                "Critical" if drop_rate > 5 else
                "Warning" if drop_rate > 2 else
                "Normal"
            )
        })

    rates.sort(key=lambda x: x["drop_rate_percent"], reverse=True)
    return {"call_drops": rates, "trai_threshold": 2.0}


# ═══════════════════════════════════════════════════════
# NETWORK KPI DASHBOARD
# ═══════════════════════════════════════════════════════

@router.get("/kpis/overview")
async def get_kpi_overview(db: Session = Depends(get_db)):
    """
    Comprehensive KPI data for the analytics dashboard.
    Includes severity trends, tower availability, latency by region.
    """
    now = datetime.utcnow()

    # Severity trend — hourly counts for last 12 hours
    severity_trend = []
    for i in range(12, 0, -1):
        start = now - timedelta(hours=i)
        end = now - timedelta(hours=i-1)

        critical = db.query(func.count(LogEntry.id))\
            .filter(and_(
                LogEntry.severity == "CRITICAL",
                LogEntry.created_at >= start,
                LogEntry.created_at < end
            )).scalar() or 0

        warning = db.query(func.count(LogEntry.id))\
            .filter(and_(
                LogEntry.severity == "WARNING",
                LogEntry.created_at >= start,
                LogEntry.created_at < end
            )).scalar() or 0

        info = db.query(func.count(LogEntry.id))\
            .filter(and_(
                LogEntry.severity == "INFO",
                LogEntry.created_at >= start,
                LogEntry.created_at < end
            )).scalar() or 0

        severity_trend.append({
            "hour": start.strftime("%H:%M"),
            "critical": critical,
            "warning": warning,
            "info": info
        })

    # Average latency by region
    latency_by_region = []
    for region_name in REGION_COORDS:
        avg_lat = db.query(func.avg(LogEntry.value))\
            .filter(and_(
                LogEntry.region == region_name,
                LogEntry.metric.in_(["Latency_ms"])
            )).scalar()

        latency_by_region.append({
            "region": region_name,
            "avg_latency_ms": round(avg_lat, 1) if avg_lat else 0
        })

    # Tower availability (based on Tower_Down events)
    tower_availability = []
    components = db.query(LogEntry.component).distinct().all()
    for (comp,) in components:
        if not comp:
            continue
        total = db.query(func.count(LogEntry.id))\
            .filter(LogEntry.component == comp).scalar() or 0
        down_events = db.query(func.count(LogEntry.id))\
            .filter(and_(
                LogEntry.component == comp,
                LogEntry.event_type == "Tower_Down"
            )).scalar() or 0

        availability = max(0, 100 - (down_events / max(total, 1) * 100))
        tower_availability.append({
            "component": comp,
            "availability_percent": round(availability, 1),
            "down_events": down_events,
            "total_events": total
        })

    tower_availability.sort(key=lambda x: x["availability_percent"])

    return {
        "severity_trend": severity_trend,
        "latency_by_region": latency_by_region,
        "tower_availability": tower_availability
    }


# ═══════════════════════════════════════════════════════
# NETWORK TOPOLOGY DATA
# ═══════════════════════════════════════════════════════

@router.get("/topology")
async def get_topology_data(db: Session = Depends(get_db)):
    """
    Get network topology data for the force-directed graph.
    Returns nodes (towers, routers, regions) and edges.
    """
    components = db.query(
        LogEntry.component,
        LogEntry.region,
        func.count(LogEntry.id).label('total')
    ).group_by(LogEntry.component, LogEntry.region).all()

    # Step 1: Map each component to its primary region based on highest activity
    comp_region_map = {}
    for comp, region, total in components:
        if not comp:
            continue
        if comp not in comp_region_map or total > comp_region_map[comp]['total']:
            comp_region_map[comp] = {'region': region, 'total': total}

    nodes = {}
    edges = []

    # Step 2: Build node structures and primary region edges
    for comp, data in comp_region_map.items():
        region = data['region']
        total = data['total']

        # Determine node type
        if comp.startswith("BTS"):
            node_type = "tower"
        elif "Router" in comp:
            node_type = "router"
        else:
            node_type = "device"

        # Determine health
        crit_count = db.query(func.count(LogEntry.id))\
            .filter(and_(
                LogEntry.component == comp,
                LogEntry.severity == "CRITICAL"
            )).scalar() or 0

        warn_count = db.query(func.count(LogEntry.id))\
            .filter(and_(
                LogEntry.component == comp,
                LogEntry.severity == "WARNING"
            )).scalar() or 0

        if crit_count > 5:
            health = "critical"
        elif crit_count > 0 or warn_count > 5:
            health = "warning"
        else:
            health = "healthy"

        nodes[comp] = {
            "id": comp,
            "label": comp,
            "type": node_type,
            "health": health,
            "region": region,
            "critical_count": crit_count,
            "warning_count": warn_count,
            "total_events": total
        }

        # Add region node and draw physical links
        if region:
            region_id = f"region_{region}"
            if region_id not in nodes:
                nodes[region_id] = {
                    "id": region_id,
                    "label": region,
                    "type": "region",
                    "health": "healthy",
                    "critical_count": 0,
                    "warning_count": 0,
                    "total_events": 0
                }
            edges.append({
                "from": comp,
                "to": region_id,
                "strength": min(total / 10, 5) if total else 1
            })

    # Step 3: Connect routers to towers within the SAME region to establish logical routing paths
    routers = [n for n in nodes.values() if n["type"] == "router"]
    towers = [n for n in nodes.values() if n["type"] == "tower"]
    for router in routers:
        for tower in towers:
            if router["region"] == tower["region"]:
                edges.append({
                    "from": router["id"],
                    "to": tower["id"],
                    "strength": 1
                })

    return {
        "nodes": list(nodes.values()),
        "edges": edges
    }


# ═══════════════════════════════════════════════════════
# NATURAL LANGUAGE TO SQL
# ═══════════════════════════════════════════════════════

class NL2SQLRequest(BaseModel):
    question: str

@router.post("/nl2sql")
async def natural_language_to_sql(request: NL2SQLRequest, db: Session = Depends(get_db)):
    """
    Convert natural language question to SQL query, execute, and return results.
    Only SELECT queries allowed for safety.
    """
    from langchain_groq import ChatGroq
    from langchain.schema import HumanMessage, SystemMessage
    import os
    import json

    llm = ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",
        temperature=0,
        max_tokens=500
    )

    system_prompt = """You are a SQL query generator for a BSNL telecom network monitoring database.

The database has these tables:

TABLE: log_entries
- id (INTEGER, primary key)
- timestamp (VARCHAR) — log timestamp string
- severity (VARCHAR) — 'CRITICAL', 'WARNING', or 'INFO'
- component (VARCHAR) — tower/router name like 'BTS_042', 'Core_Router_7', 'Edge_Router_2'
- region (VARCHAR) — 'Jaipur', 'Delhi', 'Mumbai', 'Roorkee', 'Lucknow'
- event_type (VARCHAR) — 'Signal_Drop', 'Handover_Failed', 'Tower_Down', 'High_Latency', 'Packet_Loss', 'High_Load', 'Handover_Success', 'Tower_Online', 'Normal_Operation'
- metric (VARCHAR) — 'RSSI', 'Latency_ms', 'Loss_Percent', 'CPU_Percent', 'Uptime', 'Subscribers_Affected'
- value (FLOAT) — metric value
- raw (TEXT) — full raw log line
- source (VARCHAR) — 'live' or 'upload'
- created_at (TIMESTAMP)

TABLE: anomalies
- id (INTEGER, primary key)
- severity (VARCHAR)
- component (VARCHAR)
- region (VARCHAR)
- event_type (VARCHAR)
- description (TEXT)
- root_cause (TEXT)
- suggested_action (TEXT)
- acknowledged (BOOLEAN)
- detected_at (TIMESTAMP)

RULES:
1. Return ONLY a valid PostgreSQL SELECT query — nothing else
2. NEVER use DELETE, UPDATE, INSERT, DROP, ALTER, or any write operations
3. Always LIMIT results to 50 rows max
4. Use proper PostgreSQL syntax
5. Return only the raw SQL string, no markdown, no explanation"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Generate a SELECT query for: {request.question}")
        ])

        sql = response.content.strip()

        # Clean up markdown code blocks if present
        if "```sql" in sql:
            sql = sql.split("```sql")[1].split("```")[0].strip()
        elif "```" in sql:
            sql = sql.split("```")[1].split("```")[0].strip()

        # Security: only allow SELECT
        sql_upper = sql.upper().strip()
        if not sql_upper.startswith("SELECT"):
            return {"error": "Only SELECT queries are allowed", "sql": sql, "results": []}

        dangerous = ["DELETE", "DROP", "INSERT", "UPDATE", "ALTER", "TRUNCATE", "CREATE", "EXEC"]
        for word in dangerous:
            if word in sql_upper:
                return {"error": f"Blocked: {word} operations not allowed", "sql": sql, "results": []}

        # Ensure LIMIT exists
        if "LIMIT" not in sql_upper:
            sql = sql.rstrip(";") + " LIMIT 50;"

        # Execute
        result = db.execute(text(sql))
        columns = list(result.keys())
        rows = []
        for row in result.fetchall():
            row_dict = {}
            for i, col in enumerate(columns):
                val = row[i]
                if isinstance(val, datetime):
                    val = val.isoformat()
                row_dict[col] = val
            rows.append(row_dict)

        return {
            "sql": sql,
            "columns": columns,
            "results": rows,
            "row_count": len(rows)
        }

    except Exception as e:
        return {
            "error": str(e),
            "sql": sql if 'sql' in dir() else "",
            "results": []
        }


# ═══════════════════════════════════════════════════════
# PDF REPORT DOWNLOAD
# ═══════════════════════════════════════════════════════

@router.get("/analyses/{analysis_id}/pdf")
async def download_analysis_pdf(analysis_id: int, db: Session = Depends(get_db)):
    """Download a PDF report for a completed analysis"""
    from utils.pdf_generator import generate_analysis_pdf
    import io

    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    anomalies = db.query(Anomaly)\
        .filter(Anomaly.analysis_id == analysis_id)\
        .order_by(desc(Anomaly.detected_at)).all()

    # Generate PDF into buffer
    buffer = generate_analysis_pdf(analysis, anomalies)
    buffer.seek(0)
    pdf_bytes = buffer.read()
    pdf_size = len(pdf_bytes)

    filename = f"Teleguard_Report_{analysis_id}_{datetime.now().strftime('%Y%m%d')}.pdf"

    # Use a generator that yields the full bytes — avoids streaming issues
    def iterfile():
        yield pdf_bytes

    return StreamingResponse(
        iterfile(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(pdf_size),
            "Access-Control-Expose-Headers": "Content-Disposition, Content-Length",
        }
    )


# ═══════════════════════════════════════════════════════
# ANOMALY CORRELATION ENGINE
# ═══════════════════════════════════════════════════════

@router.get("/correlations")
async def get_anomaly_correlations(
    window_minutes: int = 10,
    db: Session = Depends(get_db)
):
    """
    Find correlated anomalies — events that happened close together
    and may represent cascading failures.
    """
    # Get recent anomalies
    anomalies = db.query(Anomaly)\
        .order_by(desc(Anomaly.detected_at))\
        .limit(100).all()

    if not anomalies:
        return {"correlations": [], "message": "No anomalies to correlate"}

    # Group anomalies by time proximity
    correlations = []
    used = set()

    for i, a1 in enumerate(anomalies):
        if i in used or not a1.detected_at:
            continue

        group = [a1]
        for j, a2 in enumerate(anomalies):
            if j in used or j == i or not a2.detected_at:
                continue
            time_diff = abs((a1.detected_at - a2.detected_at).total_seconds())
            if time_diff <= window_minutes * 60:
                group.append(a2)
                used.add(j)

        if len(group) >= 2:
            used.add(i)
            # Determine correlation type
            regions = set(a.region for a in group if a.region)
            components = set(a.component for a in group if a.component)

            if len(regions) == 1 and len(components) > 1:
                corr_type = "Regional Cascade"
                description = f"Multiple components failed in {list(regions)[0]} within {window_minutes} minutes"
            elif len(components) == 1:
                corr_type = "Repeated Failure"
                description = f"{list(components)[0]} experienced {len(group)} failures within {window_minutes} minutes"
            else:
                corr_type = "Cross-Region Correlation"
                description = f"Failures across {', '.join(regions)} may indicate backbone issue"

            correlations.append({
                "type": corr_type,
                "description": description,
                "severity": max((a.severity or "INFO") for a in group),
                "affected_components": list(components),
                "affected_regions": list(regions),
                "event_count": len(group),
                "time_window_minutes": window_minutes,
                "events": [
                    {
                        "component": a.component,
                        "severity": a.severity,
                        "event_type": a.event_type,
                        "description": a.description,
                        "detected_at": a.detected_at.isoformat() if a.detected_at else None
                    }
                    for a in group
                ]
            })

    correlations.sort(key=lambda x: x["event_count"], reverse=True)
    return {"correlations": correlations}


# ═══════════════════════════════════════════════════════
# STREAMING CHAT (SSE)
# ═══════════════════════════════════════════════════════

class StreamChatRequest(BaseModel):
    question: str
    filter_severity: Optional[str] = None

@router.post("/chat/stream")
async def stream_chat_response(request: StreamChatRequest):
    """
    Server-Sent Events endpoint for streaming chat responses.
    Streams the AI response token by token.
    """
    import asyncio
    from langchain_groq import ChatGroq
    from langchain.schema import HumanMessage, SystemMessage
    from rag.embeddings import search_logs
    import os
    import json

    # Retrieve context from ChromaDB
    try:
        retrieved = search_logs(
            query=request.question,
            n_results=5,
            filter_severity=request.filter_severity
        )
    except Exception:
        retrieved = []

    if not retrieved:
        context = "No log data available in the database yet."
    else:
        context = "\n\n".join([
            f"[Severity: {r['metadata'].get('severity', 'Unknown')}] "
            f"[Tower: {r['metadata'].get('component', 'Unknown')}]\n"
            f"{r['text']}"
            for r in retrieved
        ])

    system_prompt = """You are Teleguard, an expert network analyst for BSNL telecom network.
Analyze network logs and answer questions about anomalies, tower performance, and network issues.
Only answer based on the provided log context. Be specific with tower names and values."""

    prompt = f"""Based on these BSNL network logs:

{context}

QUESTION: {request.question}

Analyze the logs and answer the question. Be specific."""

    async def generate():
        try:
            llm = ChatGroq(
                api_key=os.getenv("GROQ_API_KEY"),
                model="llama-3.3-70b-versatile",
                temperature=0,
                max_tokens=1000,
                streaming=True
            )

            # Stream tokens
            async for chunk in llm.astream([
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt)
            ]):
                if chunk.content:
                    yield f"data: {json.dumps({'token': chunk.content})}\n\n"

            # Send completion signal
            yield f"data: {json.dumps({'done': True, 'context_used': len(retrieved)})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
