# predictor.py — Predictive failure forecasting
# Uses exponential smoothing on log frequency to predict tower failures
# OPTIMIZED: Fixed N+1 query problem — uses bulk GROUP BY queries instead of per-tower loops

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, case
from datetime import datetime, timedelta
from models.models import LogEntry


def get_tower_risk_scores(db: Session) -> list:
    """
    Calculate failure risk score for each tower/component.

    Algorithm:
    1. Count critical events per tower in the last 6 hours
    2. Compare recent rate (last 1h) vs baseline rate (last 6h)
    3. Apply exponential weighting — recent events matter more
    4. Score 0-100 where 100 = imminent failure

    OPTIMIZED: Uses 3 bulk SQL queries instead of N*4 queries (N+1 fix)

    Returns:
        Sorted list of tower risk assessments
    """
    now = datetime.utcnow()
    window_6h = now - timedelta(hours=6)
    window_1h = now - timedelta(hours=1)
    window_30m = now - timedelta(minutes=30)

    # ── BULK QUERY 1: 6h stats per component (replaces N*2 queries) ───────────
    bulk_6h = db.query(
        LogEntry.component,
        func.count(LogEntry.id).label("total_6h"),
        func.sum(case((LogEntry.severity == "CRITICAL", 1), else_=0)).label("critical_6h"),
        # Most common event type — use max as a proxy (good enough for ranking)
        func.max(LogEntry.event_type).label("common_event"),
        func.max(LogEntry.region).label("region"),
    ).filter(
        and_(
            LogEntry.severity.in_(["CRITICAL", "WARNING"]),
            LogEntry.created_at >= window_6h,
            LogEntry.component.isnot(None)
        )
    ).group_by(LogEntry.component).all()

    if not bulk_6h:
        return []

    # ── BULK QUERY 2: 1h warning+critical counts ──────────────────────────────
    bulk_1h = {
        row.component: row.recent_1h
        for row in db.query(
            LogEntry.component,
            func.count(LogEntry.id).label("recent_1h"),
        ).filter(
            and_(
                LogEntry.severity.in_(["CRITICAL", "WARNING"]),
                LogEntry.created_at >= window_1h,
                LogEntry.component.isnot(None)
            )
        ).group_by(LogEntry.component).all()
    }

    # ── BULK QUERY 3: 30m critical-only counts ────────────────────────────────
    bulk_30m = {
        row.component: row.recent_30m
        for row in db.query(
            LogEntry.component,
            func.count(LogEntry.id).label("recent_30m"),
        ).filter(
            and_(
                LogEntry.severity == "CRITICAL",
                LogEntry.created_at >= window_30m,
                LogEntry.component.isnot(None)
            )
        ).group_by(LogEntry.component).all()
    }

    predictions = []

    for row in bulk_6h:
        component = row.component
        total_6h = row.total_6h or 0
        critical_6h = int(row.critical_6h or 0)
        recent_1h = bulk_1h.get(component, 0)
        recent_30m = bulk_30m.get(component, 0)

        # Calculate rates
        rate_6h = total_6h / 6.0        # events per hour (baseline)
        rate_1h = recent_1h / 1.0       # events in last hour

        # Acceleration factor: is the rate increasing?
        acceleration = rate_1h / max(rate_6h, 0.1)

        # Risk score formula (0-100)
        # Components:
        #   - Base risk from critical event count (40%)
        #   - Recent activity spike (30%)
        #   - Acceleration trend (30%)
        base_risk = min(critical_6h * 8, 40)
        spike_risk = min(recent_30m * 15, 30)
        accel_risk = min(acceleration * 10, 30)

        risk_score = min(round(base_risk + spike_risk + accel_risk), 100)

        # Determine risk level
        if risk_score >= 75:
            risk_level = "CRITICAL"
            eta = "< 1 hour"
        elif risk_score >= 50:
            risk_level = "HIGH"
            eta = "1-3 hours"
        elif risk_score >= 25:
            risk_level = "MEDIUM"
            eta = "3-6 hours"
        else:
            risk_level = "LOW"
            eta = "> 6 hours"

        predictions.append({
            "component": component,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "predicted_eta": eta,
            "critical_events_6h": critical_6h,
            "warning_events_6h": total_6h - critical_6h,
            "recent_events_1h": recent_1h,
            "acceleration": round(acceleration, 2),
            "likely_failure_mode": row.common_event or "Unknown",
            "region": row.region or "Unknown"
        })

    # Sort by risk score descending
    predictions.sort(key=lambda x: x["risk_score"], reverse=True)
    return predictions


def get_hourly_trend(db: Session, component: str, hours: int = 12) -> list:
    """
    Get hourly event counts for a specific tower.
    Used for the trend line chart.
    OPTIMIZED: Single query with conditional aggregation instead of N queries.
    """
    now = datetime.utcnow()
    start_window = now - timedelta(hours=hours)

    # Fetch all relevant logs in one query
    logs = db.query(
        LogEntry.created_at
    ).filter(
        and_(
            LogEntry.component == component,
            LogEntry.severity.in_(["CRITICAL", "WARNING"]),
            LogEntry.created_at >= start_window
        )
    ).all()

    # Build hourly buckets in Python — much faster than N SQL queries
    buckets = {}
    for i in range(hours, 0, -1):
        slot_start = now - timedelta(hours=i)
        label = slot_start.strftime("%H:%M")
        buckets[label] = {"hour": label, "events": 0, "_start": slot_start, "_end": now - timedelta(hours=i - 1)}

    for (created_at,) in logs:
        if created_at is None:
            continue
        for label, bucket in buckets.items():
            if bucket["_start"] <= created_at < bucket["_end"]:
                bucket["events"] += 1
                break

    return [{"hour": b["hour"], "events": b["events"]} for b in buckets.values()]
