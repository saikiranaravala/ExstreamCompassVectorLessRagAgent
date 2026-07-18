# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Project Name:** Compass

**Purpose:** A vectorless Retrieval-Augmented Generation (RAG) agent designed to answer questions about OpenText Exstream (Customer Communications Management) product documentation.

**Key Architectural Insight:** The documentation folder hierarchy itself serves as the retrieval index — no vector embeddings. An LLM agent navigates an "Index Tree" (a JSON file of LLM-generated summaries mirroring the folder structure) using deterministic tools.

**Target GA:** Q4 2026

**LLM Stack:** DeepSeek via OpenRouter (OpenAI-compatible client) for reasoning and demo-path answer generation — model/key read from `settings` (`REASONING_MODEL`, default `deepseek-v4`; `OPENROUTER_API_KEY`). Index-tree summarization still uses Claude `claude-haiku-4-5-20251001` via the Anthropic SDK (hard-coded in `indexer/index_tree.py`, needs `ANTHROPIC_API_KEY`).

## Repository Status

**Active development.** Backend (full-corpus retrieval + cited LLM answers), frontend, and agent
framework are working. Deployed to Render.com (free tier). Current focus:
- Activating `CompassRouter` (sessions/audit) and LLM-driven tool planning
- Index-tree summaries for hierarchical navigation; PDF corpus inclusion
- Evaluation harness (300-query dataset)

## Architecture Overview

### Retrieval Layer (`src/compass/retrieval/`) — the core of answering

The **single orchestration point** for answering queries, shared by the API routes and
the agent tools:

- `corpus.py` — `CorpusStore`: walks `docs/{variant}/HTML` recursively (ALL files, skipping
  viewer chrome dirs like `Skins/`), extracts title+text, caches to `.atlas/corpus_{variant}.json.gz`.
  First build takes minutes (~750 CloudNative / ~3,200 ServerBased docs); cached loads take seconds.
- `bm25.py` — `BM25Index`: pure-Python BM25 (no native deps) with weighted title field. Builds
  from the corpus cache in ~1-2s.
- `passages.py` — `best_passage()`: sliding-window extraction of the **query-relevant** span of
  each hit (not the first N chars of the file).
- `answer.py` — `generate_answer()`: structured, inline-cited markdown answer via DeepSeek/OpenRouter
  (system prompt demands direct answer → details/steps → `[n]` citations → gap disclosure).
  Extractive fallback when `OPENROUTER_API_KEY` is unset or the call fails.
- `service.py` — `QueryService`: thread-safe lazy per-variant index, `warmup()` (run in a
  background thread at app startup), `search()`, `query()` (returns answer, citations, trace).
- `textutil.py` — tokenizer + HTML text extraction (selectolax when installed, stdlib fallback).

Prebuild caches with `PYTHONPATH=src python scripts/build_index.py [--variant X] [--rebuild]`.
Caches live in `.atlas/` (gitignored).

### Two-Path Request Handling

**Path A — Active path (`src/compass/app.py`):**
- Routes `POST /api/v1/query`, `GET/DELETE /api/v1/session/{id}` are defined **inline in `app.py`**
  and delegate to the shared `QueryService`
- Endpoints are sync `def` on purpose (FastAPI threadpool) so index builds/LLM calls don't block
  the event loop; `@app.on_event("startup")` warms indexes in a background thread
- Response includes `answer` (markdown), `citations` (query-relevant passages), `tool_calls`,
  `model`, and `trace` (retrieval steps); allows unauthenticated access (demo mode)

**Path B — Full agent path (`src/compass/api/routes.py` → `CompassRouter`):**
- `CompassRouter` wraps the LangGraph `ReasoningAgent`, `SessionManager`, and `AuditLogger`
- **Not currently registered with the app** — requires explicit `CompassRouter.register_with_app(app)` to activate
- The agent is now functional when constructed with `ReasoningAgent(tools=ToolRegistry(service=query_service, docs_root=...))` — `_plan_tools`/`_execute_tools` dispatch real search-then-read plans with budget enforcement

### Reasoning Agent (`src/compass/agent/`)
- **Framework:** LangGraph (`StateGraph`)
- **Model:** DeepSeek via OpenRouter using the `openai` SDK (OpenRouter is OpenAI-compatible). `agent.py` reads `settings.reasoning_model` (default `deepseek-v4`), `settings.openrouter_api_key`, and `settings.openrouter_base_url` from `src/compass/config.py` (pydantic-settings, loads `.env`). The client is wrapped with LangSmith's `wrap_openai` when available.
- **Summarization model:** `claude-haiku-4-5-20251001` via Anthropic SDK — still **hard-coded** in `IndexTreeBuilder` (`indexer/index_tree.py`) for generating `.atlas/index.json` summaries; the `SUMMARIZATION_MODEL` setting (default `deepseek-v4`) is not read by it
- **Tools (5)** registered via `ToolRegistry` in `core_tools.py` (note: `agent/tools.py` is an empty placeholder):
  - `list_node` — lists real folders/files under `docs_root/{variant}` (variant-isolated)
  - `read_html` — reads `.htm`/`.html` via `retrieval/textutil.py`, enforces variant isolation
  - `read_pdf` — extracts PDF content via `indexer/pdf_parser.py`
  - `lexical_search` — BM25 search via `QueryService` (preferred) or a legacy index object
  - `compare_variants` — real cross-variant search when a `QueryService` is injected
- **Tools take their dependencies at construction** — `ToolRegistry(service=QueryService(), docs_root=...)`; without them, tools return explanatory error `ToolResult`s
- **LangGraph DAG:**
  ```
  START → process_query → plan_tools ──(budget ok)──► execute_tools → generate_answer → finalize → END
                                      └─(budget exhausted)──────────────────────────────►
  ```
- `_plan_tools` builds a search-then-read plan; `_execute_tools` dispatches it through the injected
  `ToolRegistry` (search → read top 3 hits), tracking budgets; `_generate_answer` reuses
  `retrieval/answer.py` for structured cited answers
- `AgentState` (`state.py`) is a **plain dataclass** — deliberately not LangGraph's `MessagesState`,
  which is a TypedDict in current versions and silently breaks attribute access
- **Budget constraints:** max 20 tool calls, max 8 file reads per query (tracked in `AgentState`)
- **Variant isolation:** Enforced in the tools (`read_html`, `list_node` refuse paths outside the
  variant subtree) and in `CorpusStore.get_document`; this is a **security boundary**

### Index Tree & Indexing (`src/compass/indexer/`)
- **Index structure:** `.atlas/index.json` — JSON file mirroring docs folder structure with LLM-generated summaries (planned; the active search index is `retrieval/bm25.py`)
- **Atomic writes:** tmp-then-rename pattern via `atomic.py`
- HTML parsing: `selectolax` + `readability-lxml` (`html_parser.py`; readability is best-effort — parse survives empty/odd docs)
- PDF text: `pypdf` (`pdf_parser.py`), tables: `pdfplumber` (`pdf_tables.py`)
- OCR fallback: Tesseract / `pytesseract` (`ocr.py`)
- `search.py` (tantivy BM25) is **legacy/unused** — tantivy imports lazily; the module raises at
  construction if tantivy is missing. Superseded by `retrieval/bm25.py`; kept for future scale-up.
- **Known issue:** Corpus structure diverges from PRD (see Documentation Corpus Structure below). Index paths must match actual on-disk structure.

### Guardrails (`src/compass/guardrails/`) — safety/quality boundary on every query

A layered boundary applied uniformly to **all personas** (legit roles and adversarial
actors) and wired into the shared `QueryService.query()` choke point, so both the API
path and the agent path are covered.

- `policy.py` — `Category` (in_scope, out_of_scope, prompt_injection, harmful, pii,
  malformed, rate_limited, low_confidence, ungrounded, leaked), `Decision`
  (ALLOW / SANITIZE / REFUSE / RATE_LIMIT), `GuardrailResult`, `GuardrailConfig`
  (thresholds from `settings`), and the documented persona × category matrix. User-facing
  refusal messages live here.
- `patterns.py` — precision-tuned regex banks (injection/jailbreak, harmful, off-topic,
  PII/secrets). Deliberately matches multi-word phrases, not single words, so
  "how do I **ignore** case in a filter" passes while "**ignore your previous
  instructions**" is refused. `redact_pii()` masks emails/SSNs/cards/keys/secrets.
- `input_guard.py` — pre-answer: validity (length/encoding/letters) → injection (REFUSE)
  → harmful (REFUSE) → off-topic (REFUSE) → PII (SANITIZE+redact).
- `output_guard.py` — post-answer: empty→disclaimer, system-prompt leak→replace,
  secret leak→redact, low retrieval confidence→ALLOW+flag disclaimer, missing citations→flag.
  Prefers to **repair** over hard-refuse so legit questions still get the best safe answer.
- `rate_limit.py` — `SlidingWindowRateLimiter` keyed by caller identity. Runs inside the
  pipeline so it covers the **unauthenticated demo path** too (the gateway's `RateLimiter`
  is bypassed there — see API Gateway note).
- `pipeline.py` — `GuardrailPipeline.check_request()` (rate limit + input) short-circuits
  answer generation on a block; `check_response()` validates/repairs the answer.

Flow in `QueryService.query(query, variant, identity)`: input guard → (blocked ⇒ refusal,
no retrieval/LLM) → retrieval → `generate_answer` (system prompt also hardened to treat
sources/query as data, never instructions) → output guard → response includes a
`guardrail: {input, output}` block. `app.py` maps a `rate_limit` decision to **HTTP 429**
and audits every decision. Config: `GUARDRAILS_ENABLED`, `MAX_QUERY_CHARS`,
`MIN_RETRIEVAL_SCORE`, `GUARDRAIL_RATE_PER_MINUTE/HOUR` in `config.py`.

### Orchestration Services (`src/compass/services/`)
- `session.py` — per-user session state and chat history with budget tracking
- `citations.py` — maps agent-cited documents to actual files, tracks citation correctness (critical for evaluation metrics)
- `audit.py` — all tool calls and agent actions recorded to `.audit_logs/` (JSONL); includes
  `GUARDRAIL_BLOCKED / GUARDRAIL_SANITIZED / GUARDRAIL_FLAGGED / RATE_LIMITED` event types
- `vision.py` — stub for diagram interpretation (planned)

### API Gateway (`src/compass/api/gateway.py`)
- `APIGateway` initializes `AuthenticationManager` (in-memory token store) and `RateLimiter` (60 req/min, 1000 req/hour per user)
- Middleware checks `Authorization: Bearer <token>`; falls back to `DemoUser` for `/api/v1/query` and `/api/v1/session` paths (unauthenticated demo access)
- **Note:** the gateway's `RateLimiter` is **not** invoked on the demo path (middleware early-returns with `DemoUser`). Rate limiting for that path is enforced by the guardrail pipeline's `SlidingWindowRateLimiter` inside `QueryService.query()` instead.
- **CORS:** `CORSMiddleware` uses `allow_origins=["*"]`, `allow_credentials=False` (Bearer tokens don't require credentials flag). Gateway middleware passes `OPTIONS` preflight requests straight through to `CORSMiddleware` before auth checks run — critical because Starlette runs `@app.middleware("http")` wrappers before `add_middleware` wrappers.
- OIDC flow: `GET /api/v1/auth/{provider}` → redirect → `GET /api/v1/auth/callback` → token creation
- `POST /api/v1/login` creates a token for any email/password (dev only)

### Frontend (`frontend/src/`)
- React + Vite (TypeScript) — chat interface, citations panel, reasoning trail
- App title: **Document Assistant** (renamed from "Compass RAG")
- `services/api.ts` (`CompassAPI`) wraps axios; adds Bearer token automatically, redirects on 401; base URL from `import.meta.env.VITE_API_URL` (baked at Vite build time) falling back to `/api/v1`
- **Variant selector** is embedded as a pill toggle inside the chat input bar (not a standalone page-level component); variant state + chat history are persisted in `localStorage` per-variant key (`compass_messages_{variant}`)
- Key components: `ChatInterface.tsx`, `CitationsPanel.tsx`, `ReasoningTrail.tsx`
- **Markdown answers:** assistant messages render through `utils/markdown.ts` — a minimal,
  HTML-escaping markdown renderer (headings, bold, code, lists, `[n]` citation superscripts)
- **Ports:** Backend 8000, Frontend 5173 (dev) / 3000 (Docker) / Render static site

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
# Edit .env: set OPENROUTER_API_KEY (LLM answers) and ANTHROPIC_API_KEY (index-tree summarization)
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

Tests requiring API calls need keys in `.env`: agent tests need `OPENROUTER_API_KEY`, indexing tests need `ANTHROPIC_API_KEY`. Unit tests with mocks run without them.

**Evaluation framework** lives in `tests/evaluation/`: `harness.py`, `metrics.py`, `reporter.py`, `test_queries.py` — target 300-query dataset for accuracy, latency, citation correctness.

### Environment Variables

All settings load through `src/compass/config.py` (pydantic-settings, `env_file=".env"`, case-insensitive).

- `OPENROUTER_API_KEY` — required for real LLM answers (agent and demo path). If unset, the app still starts and the demo path falls back to excerpt assembly.
- `ANTHROPIC_API_KEY` — required only for index-tree summarization (`IndexTreeBuilder`), read directly by the Anthropic SDK.
- `REASONING_MODEL` (default `deepseek-v4`), `OPENROUTER_BASE_URL` — read by `agent.py` and the demo path.
- `SUMMARIZATION_MODEL` — defined in `config.py` but **not** read by `index_tree.py`, which hard-codes `claude-haiku-4-5-20251001`.
- `LANGCHAIN_TRACING_V2` / `LANGCHAIN_API_KEY` / `LANGCHAIN_PROJECT` — opt-in LangSmith tracing (see Completed Work).
- `DEBUG=true` — debug logging.
- Guardrails: `GUARDRAILS_ENABLED` (default true), `MAX_QUERY_CHARS` (2000), `MIN_QUERY_CHARS` (3), `MIN_RETRIEVAL_SCORE` (1.5), `GUARDRAIL_RATE_PER_MINUTE` (30), `GUARDRAIL_RATE_PER_HOUR` (400).

See `.env.example` for the full annotated list.

### Render.com Deployment

See `render_deployment.md` for the complete step-by-step guide. Key points:
- Backend: Web Service, `pip install -r requirements-render.txt`, start cmd `PYTHONPATH=src uvicorn compass.main:app --host 0.0.0.0 --port $PORT`
- Frontend: Static Site, build `cd frontend && npm install && npm run build`, publish dir `./frontend/dist`
- Set `OPENROUTER_API_KEY` (and `ANTHROPIC_API_KEY` if indexing) in the backend's **Environment** tab
- Set `VITE_API_URL=https://<your-api>.onrender.com/api/v1` in the frontend's **Environment** tab **before** the first build — it is baked into the bundle at build time
- Free tier sleeps after 15 min idle; first cold-start request takes ~30–60 s

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

**Backend fails to start:** Verify Python 3.11.9 and that `pydantic-settings` is installed. API keys are not required at startup (settings default to empty strings) — missing `OPENROUTER_API_KEY` only degrades answers to excerpt assembly.

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

- **Activate CompassRouter:** Register full agent path (sessions/audit), replacing the inline routes
- **LLM-driven tool planning:** `_plan_tools` currently uses a fixed search-then-read plan; upgrade to model-chosen tool sequences (index-tree navigation)
- **Index tree summaries:** Generate `.atlas/index.json` LLM summaries for hierarchical navigation; `index_tree.py` still hard-codes Claude Haiku via Anthropic SDK — wire it to `settings.summarization_model`
- **PDF corpus:** Include `docs/{variant}/PDFs/` in the retrieval corpus (currently HTML-only)
- **Incremental indexing:** Cron-driven delta updates to the corpus caches
- **Vision service:** Implement diagram interpretation stub in `vision.py`
- **Evaluation harness:** 300-query dataset for accuracy, latency, citation correctness
- **Configuration schema:** `config.yml` for variant selection, parser tuning, OCR thresholds, budget constraints (PRD §7.7)

## Completed Work (recent)

- **Guardrails layer (`src/compass/guardrails/`):** input + output + rate-limit boundary on
  every query, applied uniformly across personas. Refuses prompt injection / harmful /
  malformed / off-topic; redacts PII/secrets; enforces per-identity rate limits (covers the
  demo path the gateway limiter misses); repairs ungrounded/low-confidence/leaked answers.
  System prompt hardened to treat sources+query as data. Wired into `QueryService.query()`,
  `app.py` (HTTP 429 + audit), the agent entrypoint, and surfaced in the UI as a footer badge.
  45 new tests (357 total green); verified end-to-end (injection refused with 0 LLM calls,
  PII redacted, legit query answered).

- **Retrieval overhaul (`src/compass/retrieval/`):** Replaced the first-100-files keyword demo search
  with full-corpus retrieval — `CorpusStore` (parse + gzip cache), pure-Python `BM25Index` with
  weighted titles, query-relevant `best_passage()` extraction, and structured cited answering.
  ~3,970 documents indexed vs ~100 before. `scripts/build_index.py` prebuilds caches.
- **Answer quality:** system prompt enforces direct answer → explanation/steps → inline `[n]`
  citations → explicit gap disclosure; `max_tokens=1600`, `temperature=0.2`; extractive fallback
  without an API key. Frontend renders the markdown properly (`frontend/src/utils/markdown.ts`).
- **Agent path functional:** `_plan_tools`/`_execute_tools` dispatch real plans through
  `ToolRegistry` with budget tracking; tools rewritten against the retrieval layer with variant
  isolation; `AgentState` converted to a plain dataclass (LangGraph `MessagesState` is a TypedDict
  now and broke attribute access).
- **Fixes:** `read_html` accepts `.htm` (the entire corpus); selectolax `select()` → `css()` API fix
  in `html_parser.py`; readability made best-effort; tantivy made an optional import; removed bogus
  `openrouter` package from requirements; added `selectolax` to `requirements-render.txt`; test
  suite green (312 passed, legacy tantivy suite skipped).

- **Render.com deployment:** Both API (Web Service) and UI (Static Site) deployed and working on free tier. See `render_deployment.md`.
- **CORS fix:** `allow_credentials=False` + OPTIONS preflight bypass at top of gateway middleware — resolves browser CORS errors for cross-origin Bearer-token requests.
- **UI — Document Assistant rename:** App title and login page updated from "Compass RAG" to "Document Assistant".
- **UI — per-query variant selector:** Variant toggle (Cloud Native / Server Based) embedded as pills inside the chat input bar; switching variant loads that variant's chat history from `localStorage`.
- **UI — chat history persistence:** Messages stored in `localStorage` per-variant; survives page refresh and variant switching.
- **TypeScript build fix:** Added `frontend/src/vite-env.d.ts` with `ImportMetaEnv` declaration to resolve `import.meta.env` type errors in Vite builds.
- **`.gitignore` / docs corpus:** Docs PDFs and `ServerBased/HTML/DesignAndProduction/` (160 MB) excluded from git; HTML docs committed to repo for Render.com search to work.
- **LangSmith tracing:** Opt-in distributed tracing via LangSmith. Set `LANGCHAIN_TRACING_V2=true` + `LANGCHAIN_API_KEY` to enable. Traces all LangGraph nodes, LLM calls (via `wrap_openai`), and tool invocations (via `@traceable`). `_bootstrap_langsmith()` in `app.py` sets env vars at module load time before any agent is constructed. Feature is off by default — Render.com demo works without a LangSmith key. Project name: `ExstreamDocumentAssistant`.
- **OpenRouter/DeepSeek migration (agent):** `ReasoningAgent` switched from Anthropic SDK to the `openai` client pointed at OpenRouter; model and key come from `settings` instead of being hard-coded. LangSmith wrapper swapped `wrap_anthropic` → `wrap_openai`.
- **Real LLM call in demo path:** `generate_answer_from_docs()` in `app.py` now calls DeepSeek via OpenRouter over the top-3 search excerpts (with LangSmith `@traceable`), falling back to excerpt assembly when `OPENROUTER_API_KEY` is unset or the call fails.

## Reference Documentation

- **[PRD.md](PRD.md)** — Product requirements, milestones, risk register
- **[render_deployment.md](render_deployment.md)** — Render.com step-by-step deployment guide
- **[START_HERE.txt](START_HERE.txt)** — 5-minute local setup (no Docker)
- **[QUICKSTART.md](QUICKSTART.md)** — Quick start (Render or Docker)
- **[INSTALLATION.md](INSTALLATION.md)** — Detailed local setup options
- **[SIMPLE_SETUP.md](SIMPLE_SETUP.md)** — Minimal local setup (Python + Node, no Docker)
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** — Production deployment (Docker, monitoring)
- **[docs/OIDC_SETUP.md](docs/OIDC_SETUP.md)** — Authentication configuration
