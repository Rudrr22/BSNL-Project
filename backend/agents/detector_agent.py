# detector_agent.py
# AGENT 2 — The intelligence layer
# Finds anomalies, patterns, root causes
# Uses parsed data from Parser Agent

from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from .state import AnalysisState
import os
import json
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile",
    temperature=0,
    max_tokens=2000
)

DETECTOR_SYSTEM_PROMPT = """You are an expert BSNL network anomaly detector.
You analyze structured log data to find anomalies and patterns.
You know telecom thresholds:
- RSSI below -85dBm = signal problem
- Packet loss above 5% = network issue
- CPU above 80% = overload
- Uptime = 0 = tower down
Always return valid JSON only."""


def detector_agent(state: AnalysisState) -> AnalysisState:
    """
    DETECTOR AGENT

    Reads:  state["parsed_logs"]        ← from Parser
    Writes: state["anomalies"]          ← detected issues
            state["severity_summary"]   ← counts
            state["most_affected_tower"] ← worst tower
            state["patterns_found"]     ← recurring issues
    """
    print("\n🔎 DETECTOR AGENT: Analyzing anomalies...")

    parsed_logs = state.get("parsed_logs", [])
    towers = state.get("towers_affected", [])
    critical_count = len(state.get("critical_logs", []))

    if not parsed_logs:
        print("⚠️ No parsed logs — skipping detection")
        return {
            **state,
            "anomalies": [],
            "severity_summary": {"CRITICAL": 0, "WARNING": 0, "INFO": 0},
            "most_affected_tower": "None",
            "patterns_found": [],
            "current_step": "reporter"
        }

    # Format for LLM — send max 50 entries
    log_data = json.dumps(parsed_logs[:50], indent=2)

    prompt = f"""Analyze these parsed BSNL network logs.
Find ALL anomalies and patterns.

PARSED LOGS:
{log_data}

TOWERS: {towers}
CRITICAL EVENTS: {critical_count}

Return ONLY this JSON:
{{
    "anomalies": [
        {{
            "severity": "CRITICAL",
            "component": "BTS_042",
            "region": "Jaipur",
            "event_type": "Signal_Drop",
            "description": "BTS_042 had repeated signal drops with RSSI=-95dBm, well below -85dBm threshold",
            "root_cause": "Likely antenna misalignment or hardware fault based on repeated pattern",
            "suggested_action": "Schedule immediate physical inspection of BTS_042 antenna and feeder cables",
            "occurrence_count": 3
        }}
    ],
    "severity_summary": {{
        "CRITICAL": 4,
        "WARNING": 3,
        "INFO": 5
    }},
    "most_affected_tower": "BTS_042",
    "patterns_found": [
        "BTS_042 shows 3 signal drops in 10 minutes — recurring hardware issue",
        "Jaipur region has highest concentration of critical events"
    ]
}}"""

    try:
        response = llm.invoke([
            SystemMessage(content=DETECTOR_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ])

        content = response.content.strip()

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        result = json.loads(content.strip())
        anomalies = result.get("anomalies", [])

        print(f"✅ DETECTOR DONE: Found {len(anomalies)} anomalies")
        for a in anomalies:
            print(f"   [{a.get('severity')}] {a.get('component')}: {a.get('event_type')}")

        return {
            **state,
            "anomalies": anomalies,
            "severity_summary": result.get("severity_summary", {}),
            "most_affected_tower": result.get("most_affected_tower", "Unknown"),
            "patterns_found": result.get("patterns_found", []),
            "current_step": "reporter"
        }

    except Exception as e:
        print(f"❌ DETECTOR ERROR: {e}")
        anomalies = fallback_detect(parsed_logs)
        return {
            **state,
            "anomalies": anomalies,
            "severity_summary": count_severities(parsed_logs),
            "most_affected_tower": find_most_affected(parsed_logs),
            "patterns_found": [],
            "current_step": "reporter",
            "errors": state.get("errors", []) + [f"Detector LLM failed: {e}"]
        }


def fallback_detect(parsed_logs: list) -> list:
    """Backup detection using simple rules"""
    anomalies = []
    component_counts = {}

    for log in parsed_logs:
        if log.get("severity") in ["CRITICAL", "WARNING"]:
            comp = log.get("component", "Unknown")
            component_counts[comp] = component_counts.get(comp, 0) + 1

            anomalies.append({
                "severity": log.get("severity"),
                "component": comp,
                "region": log.get("region", "Unknown"),
                "event_type": log.get("event_type", "Unknown"),
                "description": f"{comp} reported {log.get('event_type', 'an issue')}",
                "root_cause": "Manual investigation required",
                "suggested_action": f"Inspect {comp} and review recent changes",
                "occurrence_count": component_counts[comp]
            })

    return anomalies


def count_severities(parsed_logs: list) -> dict:
    counts = {"CRITICAL": 0, "WARNING": 0, "INFO": 0}
    for log in parsed_logs:
        sev = log.get("severity", "INFO")
        counts[sev] = counts.get(sev, 0) + 1
    return counts


def find_most_affected(parsed_logs: list) -> str:
    counts = {}
    for log in parsed_logs:
        if log.get("severity") == "CRITICAL":
            comp = log.get("component", "Unknown")
            counts[comp] = counts.get(comp, 0) + 1
    return max(counts, key=counts.get) if counts else "None"