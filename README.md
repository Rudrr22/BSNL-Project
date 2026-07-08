# TeleGuard AI Pro 🛡️

> **Intelligent Telecom Network Monitor** — A production-grade AI platform for real-time BSNL network anomaly detection, predictive failure analysis, and RAG-powered log intelligence.

---

## 🚀 Tech Stack

![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat&logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?style=flat&logo=postgresql)
![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5-FF6B35?style=flat)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-7C3AED?style=flat)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker)

---

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       TELEGUARD AI PRO                          │
│                                                                 │
│  ┌──────────────┐    WebSocket     ┌──────────────────────────┐ │
│  │  React/Vite  │◄────────────────►│     FastAPI Backend      │ │
│  │  Frontend    │    REST/SSE      │                          │ │
│  │  (Port 3000) │◄────────────────►│  ┌────────────────────┐  │ │
│  └──────────────┘                  │  │  LangGraph Agents  │  │ │
│                                    │  │  Parser → Detector │  │ │
│  ┌──────────────┐    HTTP POST      │  │       → Reporter   │  │ │
│  │   Network    │─────────────────►│  └────────────────────┘  │ │
│  │  Simulator   │  /api/logs/ingest│                          │ │
│  └──────────────┘                  │  ┌──────────┐ ┌────────┐ │ │
│                                    │  │PostgreSQL│ │ChromaDB│ │ │
│                                    │  │(Logs,    │ │(Vector │ │ │
│                                    │  │Anomalies)│ │Embedds)│ │ │
│                                    │  └──────────┘ └────────┘ │ │
│                                    └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Pipeline Flow

```
Log Upload / Live Ingestion
         │
         ▼
  ┌─────────────┐
  │ Parser Agent │  → Extracts severity, component, region, metrics
  └──────┬──────┘
         │ (if logs parsed)
         ▼
  ┌───────────────┐
  │ Detector Agent │  → Identifies anomalies, patterns, root causes
  └──────┬────────┘
         │
         ▼
  ┌───────────────┐
  │ Report Agent  │  → Generates executive summary + recommendations
  └───────────────┘
         │
         ▼
  PostgreSQL + ChromaDB + PDF Report
```

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **Multi-Agent AI Pipeline** | LangGraph workflow with 3 specialized agents (Parser → Detector → Reporter) |
| 🔍 **RAG Chat** | Semantic search over logs using ChromaDB + sentence-transformers, streaming SSE responses |
| 🗣️ **Voice Interface** | Speech-to-Text input and Text-to-Speech responses in the AI chat |
| 🔮 **Predictive Failure Scoring** | Exponential rate analysis scoring each tower 0-100 for failure risk |
| 🗺️ **Network Topology** | Force-directed graph on India map with real-time health coloring + 12h trend sparklines |
| 📡 **Live WebSocket Feed** | Real-time log streaming from network simulator to dashboard |
| 🌡️ **Signal Heatmap** | RSSI-based coverage map with animated markers per region |
| 🔎 **NL → SQL Explorer** | Ask questions in English — LLM generates and executes safe SELECT queries |
| 📊 **KPI Analytics** | Severity trends, latency by region, TRAI compliance, tower availability |
| 📋 **Anomaly Correlation** | Detects cascade failures and cross-region correlated events |
| 📄 **PDF Report Download** | Branded PDF with severity breakdown, pie chart, anomaly table, and AI recommendations |
| ⬇️ **CSV Export** | One-click export of query results from the NL→SQL explorer |
| 🐳 **Docker Compose** | Single command spins up all 5 services: backend, frontend, postgres, chromadb, simulator |

---

## 🏃 Quick Start

### Prerequisites
- Docker & Docker Compose installed
- Groq API key (free at [console.groq.com](https://console.groq.com))

### 1. Clone and configure
```bash
git clone <repo-url>
cd BSNL-PROJECT

# Edit .env with your keys
cp .env.example .env
# Add your GROQ_API_KEY
```

### 2. Launch everything
```bash
docker compose up --build
```

This starts:
- **Frontend** → http://localhost:3000
- **Backend API** → http://localhost:8000
- **API Docs** → http://localhost:8000/docs
- **System Status** → http://localhost:8000/health/detailed
- **PostgreSQL** → localhost:5432
- **ChromaDB** → localhost:8001

### 3. Check it's running
```bash
curl http://localhost:8000/health
# → {"status": "healthy", "service": "TeleGuard AI Pro", "version": "2.0.0"}
```

---

## 📁 Project Structure

```
BSNL PROJECT/
├── backend/
│   ├── agents/              # LangGraph multi-agent pipeline
│   │   ├── parser_agent.py  # Log parsing + severity extraction
│   │   ├── detector_agent.py# Anomaly detection + pattern analysis
│   │   ├── report_agent.py  # AI report generation
│   │   ├── workflow.py      # LangGraph state machine
│   │   └── state.py         # Shared state schema
│   ├── ml/
│   │   └── predictor.py     # Failure risk scoring (optimized bulk queries)
│   ├── rag/
│   │   ├── embeddings.py    # ChromaDB embedding + search
│   │   └── rag_chain.py     # LangChain RAG pipeline
│   ├── models/
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   ├── schemas.py       # Pydantic request/response schemas
│   │   └── database.py      # PostgreSQL connection
│   ├── routes/
│   │   ├── logs.py          # Upload + ingestion endpoints
│   │   ├── analyses.py      # Analysis history + anomaly endpoints
│   │   ├── kpis.py          # KPI analytics, predictions, topology, NL2SQL
│   │   └── chat.py          # RAG chat + streaming SSE
│   ├── utils/
│   │   └── pdf_generator.py # ReportLab PDF generation
│   └── main.py              # FastAPI app, WebSocket, CORS
├── frontend/
│   └── src/
│       ├── pages/           # 8 pages: Dashboard, KPIs, Topology, Coverage,
│       │                    #           Upload, Chat, Explorer, History
│       ├── components/      # AnomalyCard, LogTicker, StatCard
│       └── utils/           # api.js, indiaMapData.js
├── simulator/
│   └── log_generator.py     # Realistic BSNL network event simulator
├── docker-compose.yml
└── .env
```

---

## 🔌 Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health/detailed` | Full system status (DB, ChromaDB, Groq, WebSocket) |
| `POST` | `/api/logs/upload` | Upload log file for multi-agent analysis |
| `POST` | `/api/logs/ingest` | Ingest single live log event + WebSocket broadcast |
| `GET` | `/api/predictions` | Failure risk scores for all towers |
| `GET` | `/api/predictions/{id}/trend` | 12-hour event trend for a tower |
| `GET` | `/api/kpis/overview` | Severity trends, latency by region, tower availability |
| `GET` | `/api/kpis/call-drops` | TRAI compliance — call drop rates per tower |
| `GET` | `/api/topology` | Force-directed graph nodes and edges |
| `GET` | `/api/heatmap` | Regional signal strength / health scores |
| `GET` | `/api/correlations` | Cascade failure correlation detection |
| `POST` | `/api/nl2sql` | Natural language → SQL query execution |
| `POST` | `/api/chat/stream` | Streaming SSE RAG chat response |
| `GET` | `/api/analyses/{id}/pdf` | Download branded PDF analysis report |
| `PATCH` | `/api/anomalies/{id}/acknowledge` | Mark anomaly as acknowledged |
| `WS` | `/ws/logs` | Real-time log streaming WebSocket |

---

## 🛠️ Development (Without Docker)

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev

# Simulator
cd simulator
python log_generator.py
```

---

## 🧪 Environment Variables

```env
# Required
GROQ_API_KEY=gsk_...          # Groq API key for LLaMA-3.3-70B

# Database (auto-configured in Docker)
DATABASE_URL=postgresql://postgres:teleguard123@postgres:5432/teleguard

# ChromaDB (auto-configured in Docker)
CHROMA_HOST=chromadb
CHROMA_PORT=8000
```

---

## 🏗️ Built With

- **FastAPI** — Async Python web framework with automatic OpenAPI docs
- **LangGraph** — Multi-agent state machine orchestration
- **LangChain + Groq** — LLM integration with LLaMA-3.3-70B
- **ChromaDB** — Local vector database for semantic search
- **sentence-transformers** — Local CPU-based text embeddings
- **PostgreSQL + SQLAlchemy** — Relational data with ORM
- **React 18 + Vite** — Fast frontend with React Router + TanStack Query
- **Recharts** — Responsive chart library
- **ReportLab** — Programmatic PDF generation
- **Docker Compose** — Multi-container orchestration

---

## 👤 Author

**Rudransh Bhatt**  
B.Tech Student | AI & Full-Stack Developer  
BSNL Network Monitoring Internship Project

---

*TeleGuard AI Pro — Powered by LangGraph multi-agent pipeline + RAG-enhanced network intelligence.*
