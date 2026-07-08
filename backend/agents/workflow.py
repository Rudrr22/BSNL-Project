# workflow.py
# The complete LangGraph multi-agent workflow
# Connects Parser → Detector → Reporter
# Handles conditional routing and state passing

from langgraph.graph import StateGraph, END
from .state import AnalysisState
from .parser_agent import parser_agent
from .detector_agent import detector_agent
from .report_agent import report_agent


# ── CONDITIONAL EDGE FUNCTIONS ─────────────────────────────

def route_after_parser(state: AnalysisState) -> str:
    """
    Decision after Parser Agent:
    
    If logs were parsed → go to Detector
    If nothing parsed  → skip to Reporter
    
    This prevents Detector from running on empty data
    """
    parsed = state.get("parsed_logs", [])
    if len(parsed) > 0:
        print(f"✅ SUPERVISOR: {len(parsed)} logs parsed → going to Detector")
        return "detector"
    else:
        print("⚠️ SUPERVISOR: No logs parsed → skipping to Reporter")
        return "reporter"


def route_after_detector(state: AnalysisState) -> str:
    """
    Decision after Detector Agent:
    Always go to Reporter.
    
    Could add logic here later:
    IF critical anomalies found → send alert THEN report
    IF no anomalies → generate clean bill of health report
    """
    anomalies = state.get("anomalies", [])
    print(f"✅ SUPERVISOR: {len(anomalies)} anomalies found → going to Reporter")
    return "reporter"


# ── BUILD THE GRAPH ────────────────────────────────────────

def create_workflow():
    """
    Creates the LangGraph workflow
    
    This defines HOW agents connect to each other
    Like drawing a flowchart in code
    """

    # Initialize graph with our state schema
    graph = StateGraph(AnalysisState)

    # Add agent nodes
    # format: graph.add_node("name", function)
    graph.add_node("parser", parser_agent)
    graph.add_node("detector", detector_agent)
    graph.add_node("reporter", report_agent)

    # Set starting point
    graph.set_entry_point("parser")

    # Add conditional edge after parser
    # Runs route_after_parser() to decide next node
    graph.add_conditional_edges(
        "parser",            # after this node
        route_after_parser,  # run this decision function
        {
            "detector": "detector",   # if returns "detector"
            "reporter": "reporter"    # if returns "reporter"
        }
    )

    # Add conditional edge after detector
    graph.add_conditional_edges(
        "detector",
        route_after_detector,
        {
            "reporter": "reporter"
        }
    )

    # After reporter → END
    graph.add_edge("reporter", END)

    # Compile graph — makes it executable
    workflow = graph.compile()
    print("✅ LangGraph workflow ready")
    return workflow


# Create workflow ONCE when backend starts
analysis_workflow = create_workflow()


# ── MAIN FUNCTION TO RUN ANALYSIS ─────────────────────────

async def run_analysis(
    logs: list,
    analysis_id: int,
    source: str = "upload"
) -> dict:
    """
    Runs the complete 3-agent analysis pipeline
    
    This is what gets called from the upload endpoint
    
    Args:
        logs: list of log dicts with "raw" field
        analysis_id: PostgreSQL ID for this analysis
        source: "upload" or "live"
    
    Returns:
        Complete analysis results dict
    """
    print(f"\n{'='*50}")
    print(f"🚀 STARTING MULTI-AGENT ANALYSIS")
    print(f"   Logs: {len(logs)}")
    print(f"   Analysis ID: {analysis_id}")
    print(f"   Source: {source}")
    print(f"{'='*50}")

    # Convert logs list to raw text
    raw_logs = "\n".join([
        log.get("raw", str(log))
        for log in logs
        if log.get("raw")
    ])

    # Build initial state
    initial_state: AnalysisState = {
        # Input
        "raw_logs": raw_logs,
        "log_count": len(logs),
        "source": source,
        "analysis_id": analysis_id,

        # Parser output (empty — will be filled)
        "parsed_logs": [],
        "critical_logs": [],
        "warning_logs": [],
        "towers_affected": [],

        # Detector output (empty — will be filled)
        "anomalies": [],
        "severity_summary": {},
        "most_affected_tower": "",
        "patterns_found": [],

        # Report output (empty — will be filled)
        "executive_summary": "",
        "detailed_findings": "",
        "recommendations": [],
        "final_report": "",

        # Tracking
        "current_step": "parser",
        "errors": [],
        "completed": False
    }

    # RUN THE WORKFLOW
    # LangGraph handles passing state between agents
    final_state = analysis_workflow.invoke(initial_state)

    print(f"\n{'='*50}")
    print(f"✅ MULTI-AGENT ANALYSIS COMPLETE")
    print(f"   Anomalies: {len(final_state.get('anomalies', []))}")
    print(f"   Most affected: {final_state.get('most_affected_tower')}")
    print(f"   Errors: {final_state.get('errors', [])}")
    print(f"{'='*50}\n")

    return {
        "analysis_id": analysis_id,
        "anomalies": final_state.get("anomalies", []),
        "severity_summary": final_state.get("severity_summary", {}),
        "most_affected_tower": final_state.get("most_affected_tower", ""),
        "patterns_found": final_state.get("patterns_found", []),
        "executive_summary": final_state.get("executive_summary", ""),
        "final_report": final_state.get("final_report", ""),
        "recommendations": final_state.get("recommendations", []),
        "towers_affected": final_state.get("towers_affected", []),
        "errors": final_state.get("errors", []),
        "completed": final_state.get("completed", False)
    }