# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Project Name:** Compass

**Purpose:** A vectorless Retrieval-Augmented Generation (RAG) agent designed to answer questions about OpenText Exstream (Customer Communications Management) product documentation.

**Key Architectural Insight:** The documentation folder hierarchy itself serves as the retrieval index — no vector embeddings. An LLM agent navigates an "Index Tree" (a JSON file of LLM-generated summaries mirroring the folder structure) using deterministic tools.

**Target GA:** Q4 2026

**Target Stack:**
- Backend: Python 3.11.9 + FastAPI
- Agent Framework: LangGraph
- LLM (reasoning): Deepseek v4 (via OpenRouter API)
- LLM (summarization): Deepseek v4 (via OpenRouter API)

## Repository Status

**Active development.** The system is partially implemented with working backend, frontend, and core agent framework. Current focus areas:
- Agent reasoning and tool orchestration (using Claude via Anthropic SDK, not Deepseek)
- Index tree generation and incremental indexing
- Citation verification and audit logging
- OIDC authentication and session management
- Observability and telemetry integration

**Note:** The PRD specifies Deepseek v4 for reasoning/summarization; implementation currently uses Claude. Evaluation on switching to cost-optimized model (Deepseek or similar) is planned post-MVP.

## Architecture Overview

### Two-Path Request Handling (Important)

There are currently **two distinct query paths** — understanding which is active prevents confusion:

**Path A — Active demo path (`src/compass/app.py`):**
- Routes `POST /api/v1/query`, `GET/DELETE /api/v1/session/{id}` are defined **inline in `app.py`**
- Uses `search_documentation()` (file-glob + keyword scoring against `docs/{variant}/HTML/`, returning top 3 results) and `generate_answer_from_docs()` to build answers without the LangGraph agent
- Allows unauthenticated access (demo mode); variant isolation is **not enforced** in this path

**Path B — Full agent path (`src/compass/api/routes.py` → `CompassRouter`):**
- `CompassRouter` wraps the LangGraph `ReasoningAgent`, `SessionManager`, and `AuditLogger`
- **Not currently registered with the app** — requires explicit `CompassRouter.register_with_app(app)` to activate
- Intended for production; falls back to a demo response if the agent fails

### Reasoning Agent (`src/compass/agent/`)
- **Framework:** LangGraph (`StateGraph`)
- **Model:** `claude-opus-4-7` (hard-coded in `agent.py` via Anthropic SDK — ignores the `REASONING_MODEL` env var, which is a Deepseek placeholder in `.env.example`)
- **Summarization model:** `claude-haiku-4-5-20251001` (used by `IndexTreeBuilder` in `indexer/index_tree.py` for generating `.atlas/index.json` summaries)
- **Tools (5)** registered via `ToolRegistry` in `core_tools.py` (note: `agent/tools.py` is an empty placeholder):
  - `list_node` — traverses `.atlas/index.json` hierarchy
  - `read_html` — parses HTML files via `indexer/html_parser.py`
  - `read_pdf` — extracts PDF content via `indexer/pdf_parser.py`
  - `lexical_search` — BM25 search via `indexer/search.py` (tantivy)
  - `compare_variants` — cross-variant topic comparison
- **All tools require their dependencies injected at construction** (`index_tree`, `search_index`, `docs_root`); they return errors if uninitialized (current stubs)
- **LangGraph DAG:**
  ```
  START → process_query → plan_tools ──(budget ok)──► execute_tools → generate_answer → finalize → END
                                      └─(budget exhausted)──────────────────────────────►
  ```
- `_plan_tools` and `_execute_tools` are currently stubs — tool dispatch is not yet wired to `ToolRegistry`
- **Budget constraints:** max 20 tool calls, max 8 file reads per query (tracked in `AgentState`)
- **Variant isolation:** Enforced at tool-runtime level via `variant_isolation.py` — queries restricted to CloudNative or ServerBased subtree; this is a **security boundary**

### Index Tree & Indexing (`src/compass/indexer/`)
- **Index structure:** `.atlas/index.json` — JSON file mirroring docs folder structure with LLM-generated summaries
- **Atomic writes:** tmp-then-rename pattern via `atomic.py`
- HTML parsing: `selectolax` + `readability-lxml` (`html_parser.py`)
- PDF text: `pypdf` (`pdf_parser.py`), tables: `pdfplumber` (`pdf_tables.py`)
- OCR fallback: Tesseract / `pytesseract` (`ocr.py`)
- Lexical search: `tantivy-py` BM25 in-process (`search.py`)
- **Known issue:** Corpus structure diverges from PRD (see Documentation Corpus Structure below). Index paths must match actual on-disk structure.

### Orchestration Services (`src/compass/services/`)
- `session.py` — per-user session state and chat history with budget tracking
- `citations.py` — maps agent-cited documents to actual files, tracks citation correctness (critical for evaluation metrics)
- `audit.py` — all tool calls and agent actions recorded to `.audit_logs/` (JSONL)
- `vision.py` — stub for diagram interpretation (planned)

### API Gateway (`src/compass/api/gateway.py`)
- `APIGateway` initializes `AuthenticationManager` (in-memory token store) and `RateLimiter` (60 req/min, 1000 req/hour per user)
- Middleware checks `Authorization: Bearer <token>`; falls back to `DemoUser` for `/api/v1/query` and `/api/v1/session` paths (unauthenticated demo access)
- OIDC flow: `GET /api/v1/auth/{provider}` → redirect → `GET /api/v1/auth/callback` → token creation
- `POST /api/v1/login` creates a token for any email/password (dev only)

### Frontend (`frontend/src/`)
- React + Vite (TypeScript) — variant selector, chat interface, citations panel, reasoning trail
- `services/api.ts` (`CompassAPI`) wraps axios; adds Bearer token automatically, redirects on 401
- Key components: `ChatInterface.tsx`, `CitationsPanel.tsx`, `ReasoningTrail.tsx`, `VariantSelector.tsx`
- **Ports:** Backend 8000, Frontend 5173 (dev) / 3000 (Docker)

## Documentation Corpus Structure

### Actual Layout (On-Disk)

```
docs/
├── CloudNative/
│   ├── HTML/  (~383 .htm files from MadCap Flare)
│   └── PDFs/  (4 PDF guides)
├── ServerBased/
│   ├── HTML/  (~3,200 .htm files across 4 subsystems)
│   │   ├── CommunicationsDesigner/      (MadCap Flare)
│   │   ├── ContentAuthor/               (MadCap Flare)
│   │   ├── DesignAndProduction/         (OpenText proprietary XML/XSLT, ~3,045 files)
│   │   └── Empower/                     (MadCap Flare)
│   └── PDFs/  (13 PDF guides, plus some embedded in HTML trees)
└── OTDS_DirectoryServices/
    └── PDFs/  (3 PDF guides for OpenText Directory Services)
```

**Total corpus:** ~3,583 HTML files, 29+ PDFs

### Divergence from PRD

The PRD specifies kebab-case flat paths (`cloud-native/html/`, `server/html/`) but the actual corpus uses:
- PascalCase folder names (`CloudNative`, `ServerBased`)
- ServerBased HTML split across **4 documentation subsystems** with different authoring tools, not a single flat `html/` folder
- DesignAndProduction uses OpenText's proprietary XML/XSLT (not MadCap Flare)
- A third top-level category `OTDS_DirectoryServices/` not covered in the PRD
- Some PDFs embedded **inside** HTML documentation trees

**Implementation note:** The indexer must handle this heterogeneous structure. Update `.atlas/` node paths to match actual on-disk structure.

## Development Commands

### Setup (One-Time)

```bash
python -m venv venv
# Windows PowerShell: venv\Scripts\Activate.ps1
# macOS/Linux: source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY
```

```bash
cd frontend && npm install && cd ..
```

### Running Locally

```bash
# Terminal 1 — Backend
python -m uvicorn compass.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev
# Browser: http://localhost:5173
```

### Running with Docker

```bash
docker-compose up -d
# Services: backend (8000), frontend (3000), PostgreSQL, Prometheus, Jaeger, Grafana (3001)

docker-compose ps
docker-compose logs -f backend
docker-compose down
```

### Testing

```bash
pytest                                        # All tests
pytest tests/test_agent.py                   # Specific file
pytest tests/test_agent.py::test_agent_workflow -v
pytest --cov=src --cov-report=html           # Coverage
pytest -m "not slow"                         # Skip slow tests
pytest -s tests/test_agent.py               # Live logging
```

Tests requiring API calls (agent, indexing) need `ANTHROPIC_API_KEY` in `.env`. Unit tests with mocks run without it.

**Evaluation framework** lives in `tests/evaluation/`: `harness.py`, `metrics.py`, `reporter.py`, `test_queries.py` — target 300-query dataset for accuracy, latency, citation correctness.

### Environment Variables

**Required:** `ANTHROPIC_API_KEY` — **not present in `.env.example`**; must be added manually after copying.

**Optional:** `OPENROUTER_API_KEY` (Deepseek evaluation), `DEBUG=true`, `LOG_LEVEL`

See `.env.example` for the full list. Note: `.env.example` specifies `REASONING_MODEL=deepseek-v4` and `SUMMARIZATION_MODEL=deepseek-v4`, but `agent.py` hard-codes `claude-opus-4-7` and does not read these vars.

### Code Quality

```bash
black src tests          # Format
ruff check src tests --fix  # Lint
mypy src                 # Type check
```

### Observability (Docker Only)

- **Prometheus:** `http://localhost:9090`
- **Jaeger UI:** `http://localhost:16686`
- **Grafana:** `http://localhost:3001` (admin/admin)
- **Audit logs:** `.audit_logs/*.jsonl`

## Debugging & Troubleshooting

**Backend fails to start:** Check `ANTHROPIC_API_KEY` is set; verify Python 3.11.9.

**Agent timeouts:** Agent enforces budget (20 tool calls, 8 file reads). Check `.audit_logs/` for action history.

**Indexing failures:** Indexer handles 4 different HTML authoring tools + PDFs. If a file fails, check `src/compass/indexer/html_parser.py` (note: `indexer/parser.py` is an empty stub). OCR fallback is in `ocr.py`.

**Variant isolation not enforced:** This is a security boundary. Audit tool calls via `.audit_logs/`.

```bash
# Enable debug logging
DEBUG=true python -m uvicorn compass.main:app --reload

# View audit logs
cat .audit_logs/*.jsonl | jq .
```

## Key Implementation Notes

**Activating the full agent path:** To switch from the demo keyword-search path to the full LangGraph agent, instantiate `CompassRouter` with a `ReasoningAgent`, `SessionManager`, and `AuditLogger`, then call `CompassRouter.register_with_app(app)` in `app.py`. The inline routes in `app.py` will need to be removed to avoid conflicts.

**Tool dependencies:** `ToolRegistry` (and its individual tools) require `index_tree`, `search_index`, and `docs_root` to be passed in. Without these, tools return error `ToolResult`s. The index must be built before the full agent path works.

**Citation verification** (`src/compass/services/citations.py`): Validates agent citations map to actual source files. Critical for trust and evaluation metrics.

**Budget enforcement:** `AgentState` (`src/compass/agent/state.py`) tracks `tool_calls_used` and `file_reads_used`. The `_should_execute_tools` conditional edge skips tool execution when budget is exhausted.

## Planned Work

- **Wire agent tools:** Connect `_plan_tools` / `_execute_tools` LangGraph nodes to `ToolRegistry` and real index/search
- **Activate CompassRouter:** Register full agent path, replacing the demo inline routes
- **Fix `.env.example`:** Add `ANTHROPIC_API_KEY`; align `REASONING_MODEL` with actual model used in `agent.py`
- **Model migration:** Evaluate cost-optimized models (Deepseek v4, Claude Haiku)
- **Incremental indexing:** Cron-driven delta updates to `.atlas/index.json`
- **Vision service:** Implement diagram interpretation stub in `vision.py`
- **Evaluation harness:** 300-query dataset for accuracy, latency, citation correctness
- **Configuration schema:** `config.yml` for variant selection, parser tuning, OCR thresholds, budget constraints (PRD §7.7)

## Reference Documentation

- **[PRD.md](PRD.md)** — Product requirements, milestones, risk register
- **[START_HERE.txt](START_HERE.txt)** — 5-minute local setup (no Docker)
- **[QUICKSTART.md](QUICKSTART.md)** — Docker setup
- **[INSTALLATION.md](INSTALLATION.md)** — Detailed setup
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** — Production deployment
- **[docs/OIDC_SETUP.md](docs/OIDC_SETUP.md)** — Authentication configuration
