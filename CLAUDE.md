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

This is **pre-implementation**. The repository currently contains:
- `PRD.md` — detailed Product Requirements Document (624 lines)
- `docs/` — raw OpenText Exstream documentation corpus

**No application code, tests, or build system exists yet.** Implementation is planned to start M0 (foundations) in May 2026.

## Planned Architecture

The system consists of several tightly integrated components:

### Reasoning Agent
- Framework: LangGraph
- Model: Deepseek v4 (via OpenRouter API) — cost-optimized reasoning
- Tools (5): `list_node()`, `read_html()`, `read_pdf()`, `lexical_search()`, `compare_variants()`
- Variant isolation: enforced at tool-runtime level (queries restricted to CloudNative or ServerBased subtree)
- Budget per query: max 20 tool calls, max 8 file reads

### Index Tree & Indexing
- **Index structure:** `.atlas/index.json` — a JSON file mirroring the documentation folder structure with LLM-generated summaries at each node
- **Summarization:** Deepseek v4 (via OpenRouter API) — cost-optimized for high-volume folder summarization
- **Atomic writes:** tmp-then-rename pattern to ensure consistency
- **Indexer:** Cron-driven incremental job
  - HTML parsing: `selectolax` + `readability-lxml`
  - PDF text extraction: `pypdf`
  - PDF tables: `pdfplumber`
  - OCR fallback (for scanned docs): Tesseract / `pytesseract`
  - Lexical search backend: `tantivy-py` (BM25, in-process, no external dependency)

### Orchestration Service
- Session management
- Budget enforcement (tool call & file read limits per query)
- Citation verification & tracking
- Audit logging (all tool calls recorded)

### Vision Service
- Model: Deepseek v4 (via OpenRouter API)
- Purpose: Interpret diagrams and figures in documentation
- Note: May need to evaluate if Deepseek v4 vision capabilities are sufficient; can fallback to alternative if needed

### API Gateway & Web UI
- Authentication: SSO/OIDC
- Rate limiting
- Frontend: Variant selector (Cloud Native vs. Server-Based), citations panel, reasoning trail visibility

## Documentation Corpus Structure

### Actual Layout (On-Disk)

The `docs/` folder contains three top-level categories:

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

The PRD specifies the planned corpus layout as:
```
docs_root/cloud-native/html/
docs_root/cloud-native/pdf/
docs_root/server/html/
docs_root/server/pdf/
```

**Actual divergence:**
- Folder names use PascalCase (`CloudNative`, `ServerBased`) not kebab-case (`cloud-native`, `server`)
- ServerBased HTML is split across **4 separate documentation subsystems** (CommunicationsDesigner, ContentAuthor, DesignAndProduction, Empower) using different authoring tools, not a single flat `html/` folder
- DesignAndProduction uses OpenText's proprietary XML/XSLT-based help system, not MadCap Flare like the others
- A third top-level category `OTDS_DirectoryServices/` (OpenText Directory Services) exists, not covered in the PRD
- Several PDFs are embedded **inside** HTML documentation trees, not only in separate `PDFs/` folders

**Implementation note:** The indexer must handle the complex ServerBased structure and the divergence between folder naming and the PRD's assumptions. Update `.atlas/` node paths to match actual on-disk structure.

## Key Files

- **[PRD.md](PRD.md)** — Full product requirements, user stories, functional requirements (9 categories), data models, evaluation strategy (300-query harness), 6-milestone roadmap, risk register, open questions, and planned configuration schema.

## Configuration (Planned)

The PRD (§7.7) specifies a planned `config.yml` with keys for:
- Variant selection (CloudNative vs. ServerBased)
- HTML/PDF tool configuration (parser tuning, OCR thresholds)
- Indexing schedule and parallelism
- Budget constraints (tool call limits, file read limits)
- Telemetry & logging settings

This file does not yet exist. It will be created during M0.

## Future Development Notes

- The indexer is the most complex component; it must robustly handle heterogeneous HTML/PDF formats and the misalignment between PRD-assumed and actual corpus structure.
- The variant isolation logic (enforcing CloudNative vs. ServerBased at the tool-runtime level) is a critical security boundary; audit carefully.
- Evaluation will use a 300-query harness to measure accuracy, latency, and citation correctness.
- OpenTelemetry + Grafana telemetry is planned for production monitoring.
