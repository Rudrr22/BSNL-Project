# report_agent.py
# AGENT 3 — The writer
# Takes anomaly data → writes professional report
# Uses Gemini for better long-form writing quality

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from .state import AnalysisState
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Try Gemini first (better writing quality)
# Fall back to Groq if Gemini fails
try:
    primary_llm = ChatGoogleGenerativeAI(
        google_api_key=os.getenv("GEMINI_API_KEY"),
        model="gemini-2.5-flash",
        temperature=0.3,
        max_output_tokens=2000
    )
    USE_GEMINI = True
    print("✅ Report Agent using Gemini")
except Exception:
    USE_GEMINI = False
    print("⚠️ Gemini unavailable, Report Agent using Groq")

backup_llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile",
    temperature=0.3,
    max_tokens=2000
)

REPORTER_SYSTEM_PROMPT = """You are a senior BSNL network analyst.
Write professional network analysis reports for management.
Be specific with tower names, values, timestamps.
Use clear sections. Be actionable."""


def report_agent(state: AnalysisState) -> AnalysisState:
    """
    REPORT AGENT

    Reads:  state["anomalies"]          ← from Detector
            state["patterns_found"]     ← from Detector
            state["most_affected_tower"] ← from Detector
    Writes: state["executive_summary"]  ← brief overview
            state["final_report"]       ← full report
            state["recommendations"]    ← action items
            state["completed"]          ← marks done
    """
    print("\n📝 REPORT AGENT: Writing report...")

    anomalies = state.get("anomalies", [])
    patterns = state.get("patterns_found", [])
    most_affected = state.get("most_affected_tower", "Unknown")
    severity_summary = state.get("severity_summary", {})
    towers = state.get("towers_affected", [])
    log_count = state.get("log_count", 0)

    prompt = f"""Write a professional BSNL Network Analysis Report.

DATA:
- Total logs analyzed: {log_count}
- Most affected tower: {most_affected}
- Towers involved: {towers}
- Severity counts: {severity_summary}
- Patterns found: {patterns}

ANOMALIES DETECTED:
{json.dumps(anomalies, indent=2)}

Write this exact report structure:

## EXECUTIVE SUMMARY
(2-3 sentences. What happened, how bad, key tower.)

## CRITICAL FINDINGS
(Detail each anomaly. Tower name, values, impact.)

## PATTERN ANALYSIS
(What recurring issues were found?)

## ROOT CAUSE ANALYSIS
(Why did these issues occur?)

## RECOMMENDATIONS
(Numbered list. Priority: URGENT/HIGH/MEDIUM.
 Specific actions for each tower.)

Be professional. Use actual tower names and values."""

    try:
        # Try Gemini first
        llm = primary_llm if USE_GEMINI else backup_llm
        response = llm.invoke([
            SystemMessage(content=REPORTER_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ])
        report = response.content

    except Exception as e:
        print(f"⚠️ Primary LLM failed: {e}, trying backup...")
        try:
            response = backup_llm.invoke([
                SystemMessage(content=REPORTER_SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ])
            report = response.content
        except Exception as e2:
            print(f"❌ Both LLMs failed: {e2}")
            report = generate_fallback_report(anomalies, most_affected, severity_summary)

    # Extract executive summary (first paragraph after ## EXECUTIVE SUMMARY)
    executive_summary = extract_section(report, "EXECUTIVE SUMMARY")

    # Extract recommendations as list
    recommendations = extract_recommendations(report)

    print(f"✅ REPORT DONE!")
    print(f"   Summary: {executive_summary[:80]}...")
    print(f"   Recommendations: {len(recommendations)}")

    return {
        **state,
        "executive_summary": executive_summary,
        "detailed_findings": report,
        "recommendations": recommendations,
        "final_report": report,
        "current_step": "complete",
        "completed": True
    }


def extract_section(report: str, section_name: str) -> str:
    """Extract a specific section from the report"""
    lines = report.split('\n')
    in_section = False
    section_lines = []

    for line in lines:
        if section_name in line.upper():
            in_section = True
            continue
        if in_section:
            if line.startswith('##') or line.startswith('# '):
                break
            if line.strip():
                section_lines.append(line.strip())

    return ' '.join(section_lines[:3]) if section_lines else "Analysis complete."


def extract_recommendations(report: str) -> list:
    """Extract numbered recommendations from report"""
    lines = report.split('\n')
    recommendations = []
    in_recommendations = False

    for line in lines:
        if 'RECOMMENDATION' in line.upper():
            in_recommendations = True
            continue
        if in_recommendations:
            if line.startswith('##'):
                break
            stripped = line.strip()
            if stripped and (
                stripped[0].isdigit() or
                stripped.startswith('-') or
                stripped.startswith('•') or
                stripped.upper().startswith(('URGENT', 'HIGH', 'MEDIUM'))
            ):
                recommendations.append(stripped)

    return recommendations if recommendations else ["Review flagged components", "Schedule inspections"]


def generate_fallback_report(anomalies, most_affected, severity_summary) -> str:
    """Simple report if both LLMs fail"""
    lines = [
        "## EXECUTIVE SUMMARY",
        f"Network analysis detected {len(anomalies)} anomalies. "
        f"Most affected component: {most_affected}.",
        "",
        "## CRITICAL FINDINGS",
    ]
    for a in anomalies:
        lines.append(
            f"- [{a.get('severity')}] {a.get('component')}: "
            f"{a.get('description', 'Issue detected')}"
        )
    lines += [
        "",
        "## RECOMMENDATIONS",
        f"1. URGENT: Inspect {most_affected} immediately",
        "2. HIGH: Review all critical alerts",
        "3. MEDIUM: Schedule preventive maintenance"
    ]
    return '\n'.join(lines)