---
name: ExstreamVectorLessRag Project Progress
description: Tracks key steps, project details, completed work, and pending tasks for the Compass RAG agent
type: project
---

# ExstreamVectorLessRag / Compass Project Progress Log

## Project Overview

**Project Name:** Compass  
**Purpose:** Vectorless Retrieval-Augmented Generation (RAG) agent for OpenText Exstream (Customer Communications Management) documentation  
**Key Innovation:** Folder hierarchy serves as retrieval index (no vector embeddings)  
**Target GA:** Q4 2026  
**Current Status:** Pre-implementation (planning phase)

## Project Details

**Tech Stack (Planned):**
- Backend: Python 3.11.9 + FastAPI
- Agent Framework: LangGraph
- LLM (reasoning): Deepseek v4 (via OpenRouter API)
- LLM (summarization): Deepseek v4 (via OpenRouter API)
- HTML parsing: selectolax + readability-lxml
- PDF handling: pypdf, pdfplumber
- OCR: Tesseract / pytesseract
- Lexical search: tantivy-py (BM25)
- Index store: .atlas/index.json (JSON) + SQLite metadata
- API Client: OpenRouter SDK (handles auth via OpenRouter key)

**Corpus Structure:**
- CloudNative: ~383 HTML files + 4 PDFs
- ServerBased: ~3,200 HTML files (4 subsystems) + 13 PDFs
- OTDS_DirectoryServices: 3 PDFs
- Total: ~3,583 HTML files + 29 PDFs

**Critical Divergence:** Actual corpus structure differs from PRD assumptions:
- Folder names use PascalCase (CloudNative, ServerBased) not kebab-case
- ServerBased HTML split into 4 subsystems using different authoring tools
- Third category (OTDS_DirectoryServices) not in PRD
- Some PDFs embedded in HTML trees

## Completed Steps

### 1. ✅ Created CLAUDE.md (2026-04-26)
- Documented project overview and vision
- Captured planned architecture (all 6 major components)
- Detailed tech stack and dependencies
- Flagged corpus structure divergence from PRD
- Added configuration schema reference (planned config.yml)
- Included development notes on key challenges (indexer complexity, variant isolation)

### 2. ✅ Analyzed Transcript Patterns for Permissions (2026-04-26)
- Scanned 13 recent transcript files across all projects
- Extracted tool call frequencies
- Found: all high-frequency read-only commands already auto-allowed by Claude Code
- Conclusion: No allowlist additions needed; permission system working optimally

### 3. ✅ Created Project-Local .claude Configuration (2026-04-26)
- Created `.claude/` folder in project root
- Generated `settings.json` with project-specific configuration:
  - Python 3.11.9
  - OpenRouter LLM provider (Deepseek v4)
  - Environment variables for OpenRouter API key
  - Project file paths
- Created `.claude/README.md` with setup instructions
- All settings isolated to project folder (not global)

### 4. ✅ Created .gitignore (2026-04-26)
- Added `docs/` folder to prevent large documentation corpus from being committed

### 5. ✅ Set up Python 3.11.9 Project Structure (2026-04-26)
- Created `pyproject.toml` with:
  - Python 3.11.9+ requirement
  - All planned dependencies with >= constraints (FastAPI, LangGraph, PDF tools, tantivy, OpenRouter SDK, etc.)
  - Dev dependencies (pytest, black, ruff, mypy)
  - Tool configurations (black, ruff, mypy, pytest)
- Created `requirements.txt` with flexible version constraints
- Project scaffold ready for development

### 6. ✅ Create FastAPI Project Scaffold (2026-04-26)
- Created directory structure:
  - `src/compass/` — main application package
  - `src/compass/agent/` — LangGraph agent module
  - `src/compass/indexer/` — indexing and parsing
  - `src/compass/services/` — orchestration services
  - `src/compass/api/` — API routes
- Created core files:
  - `src/compass/app.py` — FastAPI app with health check and root endpoints
  - `src/compass/main.py` — entry point for uvicorn
  - `src/compass/config.py` — settings management (pydantic)
  - Placeholder modules for agent tools, parser, and services

### 7. ✅ Set up CI/CD Pipeline (2026-04-26)
- Created GitHub Actions workflow (`.github/workflows/ci.yml`):
  - Python 3.11 matrix testing
  - Linting (ruff)
  - Format checking (black)
  - Type checking (mypy)
  - Unit tests with coverage (pytest)
  - Coverage reporting to codecov
- Created test infrastructure:
  - `tests/conftest.py` — pytest fixtures (FastAPI test client)
  - `tests/test_app.py` — basic endpoint tests
  - `pytest.ini` — pytest configuration
- Added configuration files:
  - `.env.example` — environment variables template
  - Updated `.gitignore` — comprehensive Python/project excludes

## M0: Foundations - ✅ COMPLETE

All M0 tasks completed:
- ✅ Initialize git repository (pre-existing)
- ✅ Set up Python 3.11.9 project structure
- ✅ Create FastAPI project scaffold
- ✅ Set up CI/CD pipeline

## Pending Steps

### 2. ⏳ M1: Indexer Implementation

### 2. ⏳ Indexer Implementation (M0/M1)
- [ ] HTML parser using selectolax + readability-lxml
- [ ] PDF text extraction (pypdf + pdfplumber)
- [ ] PDF table extraction logic
- [ ] OCR fallback for scanned content (pytesseract)
- [ ] BM25 lexical search index (tantivy-py)
- [ ] Index Tree generation (Claude Haiku 4.5 summarization)
- [ ] Atomic write mechanism (tmp-then-rename)

### 3. ⏳ Reasoning Agent (M1)
- [ ] LangGraph agent scaffold
- [ ] 5 core tools: list_node(), read_html(), read_pdf(), lexical_search(), compare_variants()
- [ ] Variant isolation logic (CloudNative vs. ServerBased enforcement)
- [ ] Budget enforcement (20 tool calls, 8 file reads per query)

### 4. ⏳ Orchestration Service (M2)
- [ ] Session management
- [ ] Citation verification
- [ ] Audit logging
- [ ] Budget tracking

### 5. ⏳ Vision Service (M2)
- [ ] Diagram interpretation (Claude Opus 4.7)
- [ ] Figure extraction & analysis

### 6. ⏳ API Gateway & Auth (M2)
- [ ] SSO/OIDC integration
- [ ] Rate limiting
- [ ] Request routing

### 7. ⏳ Web UI (M3)
- [ ] Variant selector component
- [ ] Chat interface
- [ ] Citations panel
- [ ] Reasoning trail visibility

### 8. ⏳ Evaluation & Testing (M4)
- [ ] 300-query evaluation harness (per PRD)
- [ ] Accuracy metrics
- [ ] Latency benchmarks
- [ ] Citation correctness validation

### 9. ⏳ Deployment & Monitoring (M4)
- [ ] Docker containerization
- [ ] OpenTelemetry + Grafana telemetry setup
- [ ] Production deployment

## Known Issues & Risks

1. **Indexer Complexity:** Must handle heterogeneous HTML/PDF formats + corpus structure misalignment with PRD
2. **Variant Isolation:** Critical security boundary; needs careful audit
3. **Corpus Layout Mismatch:** PRD assumes different folder structure; implementation must adapt to actual on-disk layout
4. **Config.yml Not Yet Created:** Will be created during M0; specifies parser tuning, budget constraints, indexing schedule

## Key Decisions

- **Vectorless approach:** Trades some semantic flexibility for determinism, auditability, and cost
- **Folder hierarchy as index:** Simple, transparent, doesn't require vector DB
- **LangGraph + Claude Opus 4.7:** Reasoning agent with deterministic tool use
- **Claude Haiku 4.5 for summarization:** Cost-optimized for high-volume folder processing
- **In-process BM25 (tantivy-py):** No external search dependency

## Links & References

- **PRD.md:** Full product requirements document (624 lines) with user stories, requirements, architecture diagram, roadmap, risk register
- **CLAUDE.md:** Developer guide for future Claude Code instances
