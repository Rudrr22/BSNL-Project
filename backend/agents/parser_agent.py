# parser_agent.py
# AGENT 1 — Reads raw messy logs
# Converts them to clean structured data
# Passes structured data to Detector Agent

from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from .state import AnalysisState
import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

# Using Groq — fastest LLM for parsing
# temperature=0 → always consistent output
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile",
    temperature=0,
    max_tokens=2000
)

PARSER_SYSTEM_PROMPT = """You are a BSNL network log parser.
Your ONLY job: convert raw log text to structured JSON.
Always return valid JSON. Nothing else. No explanations."""


def parser_agent(state: AnalysisState) -> AnalysisState:
    """
    PARSER AGENT
    
    Reads:  state["raw_logs"]     ← raw text
    Writes: state["parsed_logs"]  ← structured data
            state["critical_logs"] ← filtered critical
            state["warning_logs"]  ← filtered warnings
            state["towers_affected"] ← unique towers
    """
    print("\n🔍 PARSER AGENT: Starting...")

    raw_logs = state["raw_logs"]
    log_lines = [l for l in raw_logs.strip().split("\n") if l.strip()]

    # Only send first 80 lines to avoid token limit
    sample = "\n".join(log_lines[:80])

    prompt = f"""Parse these BSNL network logs into JSON.

RAW LOGS:
{sample}

Return ONLY this JSON structure:
{{
    "parsed_logs": [
        {{
            "timestamp": "2026-07-01 14:32:01",
            "severity": "CRITICAL",
            "component": "BTS_042",
            "event_type": "Signal_Drop",
            "metric": "RSSI",
            "value": -95,
            "region": "Jaipur",
            "raw": "full original log line"
        }}
    ],
    "summary": {{
        "total": 10,
        "critical": 3,
        "warning": 4,
        "info": 3,
        "towers": ["BTS_042", "Router_7"]
    }}
}}"""

    try:
        response = llm.invoke([
            SystemMessage(content=PARSER_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ])

        content = response.content.strip()

        # Remove markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        result = json.loads(content.strip())
        parsed_logs = result.get("parsed_logs", [])
        summary = result.get("summary", {})

        # Filter by severity
        critical = [l["raw"] for l in parsed_logs if l.get("severity") == "CRITICAL"]
        warning = [l["raw"] for l in parsed_logs if l.get("severity") == "WARNING"]
        towers = list(set([l.get("component", "") for l in parsed_logs if l.get("component")]))

        print(f"✅ PARSER DONE: {len(parsed_logs)} logs parsed")
        print(f"   🔴 Critical: {len(critical)}")
        print(f"   🟡 Warning:  {len(warning)}")
        print(f"   🗼 Towers:   {towers}")

        return {
            **state,
            "parsed_logs": parsed_logs,
            "critical_logs": critical,
            "warning_logs": warning,
            "towers_affected": towers,
            "current_step": "detector",
            "errors": state.get("errors", [])
        }

    except Exception as e:
        print(f"❌ PARSER ERROR: {e}")
        print("   Using fallback regex parser...")

        # Fallback — simple regex if LLM fails
        parsed_logs = fallback_parse(log_lines)
        return {
            **state,
            "parsed_logs": parsed_logs,
            "critical_logs": [l for l in log_lines if "CRITICAL" in l],
            "warning_logs": [l for l in log_lines if "WARNING" in l],
            "towers_affected": extract_towers(log_lines),
            "current_step": "detector",
            "errors": state.get("errors", []) + [f"Parser LLM failed: {e}"]
        }


def fallback_parse(lines: list) -> list:
    """
    Backup parser using regex
    Runs if Groq API fails or returns bad JSON
    Always works — no AI needed
    """
    parsed = []
    for line in lines:
        if not line.strip():
            continue

        # Determine severity
        if "CRITICAL" in line:
            severity = "CRITICAL"
        elif "WARNING" in line or "WARN" in line:
            severity = "WARNING"
        else:
            severity = "INFO"

        # Extract component with regex
        component = "Unknown"
        match = re.search(
            r'(BTS_\d+|Router_\w+|Switch_\w+|Edge_\w+|Core_\w+)',
            line
        )
        if match:
            component = match.group(1)

        # Extract region
        region = "Unknown"
        region_match = re.search(r'Region=(\w+)', line)
        if region_match:
            region = region_match.group(1)

        parsed.append({
            "timestamp": "",
            "severity": severity,
            "component": component,
            "event_type": "",
            "metric": "",
            "value": None,
            "region": region,
            "raw": line
        })

    return parsed


def extract_towers(lines: list) -> list:
    """Extract unique tower/component names"""
    towers = set()
    for line in lines:
        match = re.search(
            r'(BTS_\d+|Router_\w+|Switch_\w+|Edge_\w+|Core_\w+)',
            line
        )
        if match:
            towers.add(match.group(1))
    return list(towers)