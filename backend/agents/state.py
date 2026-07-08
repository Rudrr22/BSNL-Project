# state.py
# Shared memory between all 3 agents
# Like a whiteboard everyone reads and writes

from typing import TypedDict, List, Optional, Dict, Any

class AnalysisState(TypedDict):
    """
    This flows through ALL agents in order:
    
    Parser Agent    → reads raw_logs
                   → writes parsed_logs, critical_logs,
                      warning_logs, towers_affected
    
    Detector Agent  → reads parsed_logs
                   → writes anomalies, severity_summary,
                      most_affected_tower, patterns_found
    
    Report Agent    → reads anomalies, patterns_found
                   → writes executive_summary,
                      final_report, recommendations
    """

    # ── INPUT (set before workflow starts) ──────────
    raw_logs: str              # all raw log text
    log_count: int             # total log lines
    source: str                # "upload" or "live"
    analysis_id: int           # PostgreSQL analysis ID

    # ── PARSER AGENT OUTPUT ─────────────────────────
    parsed_logs: List[Dict[str, Any]]   # structured entries
    critical_logs: List[str]            # only CRITICAL lines
    warning_logs: List[str]             # only WARNING lines
    towers_affected: List[str]          # unique tower names

    # ── DETECTOR AGENT OUTPUT ───────────────────────
    anomalies: List[Dict[str, Any]]     # detected problems
    severity_summary: Dict[str, int]    # counts per severity
    most_affected_tower: str            # worst tower
    patterns_found: List[str]           # recurring issues

    # ── REPORT AGENT OUTPUT ─────────────────────────
    executive_summary: str              # brief overview
    detailed_findings: str             # full analysis
    recommendations: List[str]         # action items
    final_report: str                  # complete report

    # ── SUPERVISOR TRACKING ─────────────────────────
    current_step: str                  # which agent is running
    errors: List[str]                  # any errors caught
    completed: bool                    # is analysis done?