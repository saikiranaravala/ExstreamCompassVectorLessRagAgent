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

#### Completed in M1

##### ✅ HTML Parser using selectolax + readability-lxml (2026-04-26)
- Created `src/compass/indexer/html_parser.py`:
  - `ParsedHTML` dataclass for structured results (title, url, content, text, html)
  - `HTMLParser.parse_file()` — parse HTML files from disk
  - `HTMLParser.parse_string()` — parse HTML from string
  - Readability-lxml for content extraction (title, summary)
  - Selectolax for text extraction and cleanup (removes scripts/styles)
  - Error handling with logging
- Created comprehensive tests in `tests/test_html_parser.py`:
  - Simple HTML parsing, script/style removal, complex structures, edge cases

##### ✅ PDF Text Extraction using pypdf + pdfplumber (2026-04-26)
- Created `src/compass/indexer/pdf_parser.py`:
  - `ParsedPDF` dataclass (title, url, text, pages, metadata)
  - `PDFParser.parse_file()` — parse PDF files from disk
  - `PDFParser.parse_bytes()` — parse PDF from bytes
  - Primary extraction via pdfplumber (better accuracy)
  - Fallback to pypdf if pdfplumber fails
  - Metadata extraction (title, author, subject, creator, producer)
  - Error handling with graceful fallbacks
- Created comprehensive tests in `tests/test_pdf_parser.py`:
  - Minimal PDF parsing, metadata extraction, error handling
  - Edge cases (empty, invalid, corrupted PDFs)

##### ✅ PDF Table Extraction Logic (2026-04-26)
- Created `src/compass/indexer/pdf_tables.py`:
  - `ExtractedTable` dataclass (page_num, table_num, rows, bbox)
  - Format conversion: to_dict(), to_markdown(), to_json()
  - `PDFTableExtractor.extract_from_bytes()` — extract all tables from PDF
  - `PDFTableExtractor.extract_from_file()` — extract from file path
  - Markdown output with page annotations
  - JSON output for structured data
  - Table counting utility
  - Robust error handling for malformed PDFs
- Created comprehensive tests in `tests/test_pdf_tables.py`:
  - Table dataclass conversions, edge cases
  - Empty/invalid PDF handling
  - Multiple tables per page
  - Special characters and None value handling

##### ✅ OCR Fallback for Scanned Content (2026-04-26)
- Created `src/compass/indexer/ocr.py`:
  - `OCRProcessor` class for text extraction using pytesseract
  - Tesseract availability detection
  - Image preprocessing: mode conversion, resizing, contrast enhancement
  - Text extraction from image and image bytes
  - Text density detection (distinguish scanned vs blank pages)
  - `PDFPageOCR` for PDF-specific OCR operations
  - OCR recommendation logic (should_use_ocr)
  - Graceful fallback when Tesseract unavailable
- Created comprehensive tests in `tests/test_ocr.py`:
  - Tesseract availability check
  - Image preprocessing (conversion, scaling, contrast)
  - Text extraction with/without preprocessing
  - Text density detection for various image types
  - OCR recommendation logic with custom thresholds

##### ✅ BM25 Lexical Search Index (2026-04-26)
- Created `src/compass/indexer/search.py`:
  - `BM25Index` class using tantivy for full-text search
  - `SearchResult` dataclass (doc_id, title, path, score, content_preview)
  - Schema creation with tokenized fields (title, content) and stored fields
  - Index initialization and persistence
  - `add_document()` — add single document to index
  - `batch_add_documents()` — bulk indexing with error resilience
  - `search()` — query with BM25 scoring and result limit
  - `delete_document()` — remove document by ID
  - `get_document_count()` — total document count
  - `clear_index()` — remove all documents
  - Content preview generation (first 200 chars)
- Created comprehensive tests in `tests/test_search.py`:
  - Index initialization and persistence
  - Single/batch document addition
  - Search with scoring and limits
  - Content preview truncation
  - Document deletion and counting

##### ✅ Atomic Write Mechanism (2026-04-26)
- Created `src/compass/indexer/atomic.py`:
  - `AtomicWriter` class for atomic file operations
  - `write_json()` — atomic JSON write with optional validation
  - `write_text()` — atomic text write with optional validation
  - `write_file()` — generic atomic write using tmp-then-rename pattern
  - Temp file created in same directory (same filesystem for atomic rename)
  - Parent directory creation with mkdir -p semantics
  - Optional validation function for consistency checks
  - Automatic cleanup of temp files on failure
  - `read_with_fallback()` — read with primary/fallback file support
  - `AtomicDirectory` class for directory operations
  - `atomic_replace_dir()` — atomic directory replacement with backup
- Created comprehensive tests in `tests/test_atomic.py`:
  - JSON/text write operations
  - Validation pass/fail scenarios
  - Overwrite of existing files
  - Complex nested JSON structures
  - Fallback file reading
  - Directory creation and replacement

##### ✅ Index Tree Generation (2026-04-26)
- Created `src/compass/indexer/index_tree.py`:
  - `IndexNode` dataclass (name, path, type, summary, children, doc_count)
  - Serialization: to_dict() and from_dict() for JSON persistence
  - `IndexTreeBuilder` for recursive tree construction
  - `build_tree()` — traverse docs folder and generate summaries
  - Integration with Claude Haiku 4.5 for folder summarization
  - Atomic write of final index tree JSON
  - `IndexTreeManager` for tree operations
  - `load_tree()` — load index from file
  - `find_node()` — search by name (recursive)
  - Document counting and tree printing utilities
- Created comprehensive tests in `tests/test_index_tree.py`:
  - Node creation and serialization roundtrips
  - Tree building and navigation
  - Document counting and node finding
  - File I/O and persistence

## M1: Indexer Implementation - ✅ COMPLETE

All Indexer tasks finished (7/7):
- ✅ HTML parser (selectolax + readability-lxml)
- ✅ PDF text extraction (pypdf + pdfplumber)
- ✅ PDF table extraction
- ✅ OCR fallback (pytesseract)
- ✅ BM25 lexical search (tantivy-py)
- ✅ Atomic write mechanism (tmp-then-rename)
- ✅ Index Tree generation (Claude Haiku 4.5 summarization)

## M1: Reasoning Agent - In Progress

### Completed

##### ✅ LangGraph Agent Scaffold (2026-04-26)
- Created `src/compass/agent/state.py`:
  - `AgentToolCall` dataclass for tool call tracking
  - `AgentState` extending LangGraph MessagesState
  - Fields: query, variant, tool_calls, budgets, final_answer, citations
- Created `src/compass/agent/agent.py`:
  - `ReasoningAgent` class with LangGraph workflow
  - Graph nodes: process_query, plan_tools, execute_tools, generate_answer, finalize
  - Conditional routing based on budget availability
  - Claude Opus 4.7 integration for answer generation
  - Budget enforcement (20 tool calls, 8 file reads per query)
  - `query()` method for end-to-end processing
- Created comprehensive tests in `tests/test_agent.py`:
  - State management and tool call tracking
  - Agent initialization with custom budgets
  - Graph node testing (process, plan, execute, generate, finalize)
  - Budget enforcement and variant validation
  - End-to-end query processing

##### ✅ 5 Core Tools (2026-04-26)
- Created `src/compass/agent/core_tools.py`:
  - `ToolResult` dataclass for consistent tool output
  - `ListNodeTool` — navigate index tree structure
  - `ReadHTMLTool` — parse and extract HTML documents
  - `ReadPDFTool` — extract content from PDF documents
  - `LexicalSearchTool` — full-text search via BM25 index
  - `CompareVariantsTool` — compare CloudNative vs ServerBased docs
  - `ToolRegistry` — centralized tool management and execution
  - Tool initialization with index tree, search index, docs root
- Created comprehensive tests in `tests/test_core_tools.py`:
  - Individual tool testing with mocks
  - Tool result validation
  - Registry management and tool discovery
  - Error handling and invalid arguments

##### ✅ Variant Isolation Logic (2026-04-26)
- Created `src/compass/agent/variant_isolation.py`:
  - `VariantConfig` dataclass for variant definitions
  - `VariantIsolationManager` for boundary enforcement
  - Predefined variants: CloudNative, ServerBased, OTDS_DirectoryServices
  - Path validation: `is_path_in_variant()` checks if path belongs to variant
  - Path enforcement: `enforce_variant_path()` restricts access
  - Search result filtering: `filter_search_results()` removes cross-variant docs
  - Variant root resolution: `get_variant_root()` for file access
  - `VariantEnforcer` for tool-level enforcement
  - Tool call validation: prevents cross-variant tool execution
  - Tool output filtering: removes cross-variant results
  - Answer validation: detects forbidden terms in responses
- Created comprehensive tests in `tests/test_variant_isolation.py`:
  - Variant validation and configuration retrieval
  - Path checking in variant boundaries
  - Path enforcement and result filtering
  - Tool execution enforcement
  - Output filtering and answer validation

## M1: Reasoning Agent - ✅ COMPLETE

All Reasoning Agent tasks finished (4/4):
- ✅ LangGraph agent scaffold
- ✅ 5 core tools (list_node, read_html, read_pdf, lexical_search, compare_variants)
- ✅ Variant isolation logic (CloudNative vs. ServerBased)
- ✅ Budget enforcement built into agent state tracking

## M2: Orchestration Service - In Progress

### Completed

##### ✅ Session Management (2026-04-26)
- Created `src/compass/services/session.py`:
  - `SessionBudget` dataclass for per-session budgets
  - Budget enforcement: `has_tool_calls_remaining()`, `has_file_reads_remaining()`
  - Budget tracking: `increment_tool_calls()`, `increment_file_reads()`
  - `QueryRecord` dataclass for recording queries within session
  - `Session` dataclass with queries, budget, metadata
  - Session serialization: `to_dict()` and `from_dict()`
  - `SessionManager` for complete session lifecycle
  - Session CRUD: create, get, update, delete, list
  - Persistence: save/load sessions to JSON files
  - Session cleanup: `cleanup_expired_sessions()` for old sessions
  - Statistics: `get_session_stats()` for query and budget analysis
- Created comprehensive tests in `tests/test_session.py`:
  - Budget tracking and enforcement
  - Query record management
  - Session creation and persistence
  - Session expiration cleanup
  - Statistics generation

##### ✅ Citation Verification (2026-04-26)
- Created `src/compass/services/citations.py`:
  - `Citation` dataclass for tracking source documents
  - Formatting: `to_dict()`, `to_markdown()`, `to_html()`
  - `VerifiedCitation` with verification status and method
  - `Answer` dataclass with citations and verification flag
  - `CitationExtractor` for extracting citations from tool outputs
  - Support for search results, HTML reads, PDF reads
  - `CitationVerifier` for citation validation
  - Document existence verification
  - Content match verification with similarity threshold
  - `CitationFormatter` for output formatting
  - Markdown and HTML citation formatting
  - Citation indexing by source document
- Created comprehensive tests in `tests/test_citations.py`:
  - Citation creation and formatting
  - Answer with citations
  - Citation extraction from tool outputs
  - Citation verification (existence, content match)
  - Citation formatting and indexing

##### ✅ Audit Logging (2026-04-26)
- Created `src/compass/services/audit.py`:
  - `AuditEventType` enum for all event categories
  - `AuditEvent` dataclass with serialization
  - `AuditLogger` for centralized logging
  - Event logging methods: log_session_*, log_query_*, log_tool_*, log_budget_*, log_variant_*
  - File-based logging with JSONL format (one event per line)
  - Event filtering: by session, user, event type
  - Audit trail methods: `get_session_audit_trail()`, `get_user_audit_trail()`
  - Statistics: `get_statistics()` for event analysis
  - Export: `export_logs()` for compliance exports
  - Severity levels: INFO, WARNING, ERROR
- Created comprehensive tests in `tests/test_audit.py`:
  - Event creation and serialization
  - Logging all event types
  - Event filtering and queries
  - Audit trail generation
  - Statistics collection
  - Log export

## M2: Orchestration Service - ✅ COMPLETE

All Orchestration Service tasks finished (3/3):
- ✅ Session management (create, persist, budget tracking)
- ✅ Citation verification (extraction, validation, formatting)
- ✅ Audit logging (comprehensive event tracking and export)

## M3: Vision Service - ✅ COMPLETE

### Completed

##### ✅ Diagram Interpretation & Figure Extraction (2026-04-26)
- Created `src/compass/services/vision.py`:
  - `Figure` dataclass for extracted figures (diagrams, charts, images, tables)
  - `VisionAnalysis` dataclass with interpretation results
  - `FigureExtractor` for extracting figures from files/directories
  - File format detection (PNG, JPG, GIF, WebP)
  - Figure type detection (diagram, chart, table, image)
  - `VisionInterpreter` using Claude Opus 4.7 vision
  - Base64 image encoding for API submission
  - Type-specific interpretation prompts
  - Object detection and insight extraction
  - `VisionCache` for persistent caching
  - Two-tier cache: memory + disk (JSON)
- Created comprehensive tests in `tests/test_vision.py`:
  - Figure extraction from files and directories
  - Type detection for different figure kinds
  - Vision interpretation with caching
  - Cache persistence across instances
  - Memory and disk cache operations

## M4: API Gateway & Auth - ✅ COMPLETE

### Completed

##### ✅ API Gateway with Authentication & Rate Limiting (2026-04-26)
- Created `src/compass/api/gateway.py`:
  - `RateLimitConfig` with per-minute and per-hour limits
  - `RateLimiter` for rate limiting enforcement
  - Request tracking with automatic cleanup
  - Per-user rate limit tracking
  - `AuthenticationManager` for user management
  - Token creation with expiry
  - Token revocation and validation
  - User registration and retrieval
  - `APIGateway` class for FastAPI integration
  - Middleware for request interception
  - Role-based access control (RBAC)
  - Rate limit response headers
  - Built-in routes: /login, /logout, /user/profile, /user/rate-limit
- Created comprehensive tests in `tests/test_gateway.py`:
  - Rate limiting enforcement
  - Token authentication and expiry
  - User registration and management
  - Role-based permissions
  - Complete authentication flows

##### ✅ Request Routing & Endpoint Management (2026-04-26)

- Created `src/compass/api/routes.py`:
  - `QueryRequest` and `QueryResponse` models
  - `APIRouter` class for request routing and endpoint management
  - Query endpoint: `/api/v1/query` (POST) with variant, session management, audit logging
  - Session endpoints: GET/DELETE `/api/v1/session/{session_id}`, GET `/api/v1/session/{session_id}/queries`
  - Admin endpoints: `/api/v1/health`, `/api/v1/stats`
  - `RequestHandler` with static methods for query, session, and admin request handling
  - Integration with authentication, rate limiting, audit logging, and session management
- Created comprehensive tests in `tests/test_gateway.py`:
  - API Gateway OIDC integration tests

##### ✅ SSO/OIDC Integration (2026-04-26)

- Created `src/compass/api/oidc.py`:
  - `OIDCConfig` dataclass for provider configuration
  - `OIDCUserInfo` dataclass for extracted user information
  - `OIDCProvider` class for provider interactions
  - Authorization URL generation with CSRF state
  - Token exchange (authorization code -> tokens)
  - User info extraction from OIDC provider
  - ID token verification (JWT validation)
  - `OIDCManager` for managing multiple providers
  - Auth state creation and verification (CSRF protection)
  - Callback handling with user info extraction
- Updated `src/compass/api/gateway.py`:
  - Added OIDC support to APIGateway constructor
  - `initialize_oidc()` async method for provider initialization
  - New endpoints: `/auth/{provider}`, `/auth/callback`, `/auth/success`
  - Middleware updated to exclude OIDC endpoints from auth
  - Redirect-based OIDC flow for seamless SSO
- Updated dependencies:
  - Added `authlib>=1.3.0` for OIDC support
  - Added `PyJWT>=2.8.0` for JWT token validation
- Created comprehensive tests in `tests/test_oidc.py`:
  - OIDC configuration and user info dataclasses
  - OIDC provider and manager functionality
  - Auth state management and CSRF protection
  - Token exchange simulation (mocked)
- Created documentation:
  - `docs/OIDC_SETUP.md` with setup guide for Azure AD, Okta, Google, and custom providers
  - Configuration examples for common OIDC providers
  - User flow documentation
  - Troubleshooting guide

## M5: Web UI - In Progress

### Completed

##### ✅ Frontend Framework Setup (2026-04-26)
- Created React 18 + TypeScript + Vite frontend in `frontend/` directory
- Configuration files:
  - `package.json` with React, React Router, Axios dependencies
  - `tsconfig.json` and `tsconfig.node.json` for TypeScript setup
  - `vite.config.ts` with dev server on port 3000 and `/api` proxy to backend
  - `index.html` entry point and `src/main.tsx` React bootstrapping
- Global styles:
  - `src/index.css` with CSS variables (colors, spacing) and dark mode support
  - Responsive design with `prefers-color-scheme` media queries
- API client layer:
  - `src/services/api.ts` with full TypeScript types and axios integration
  - Methods: login, logout, submitQuery, getSession, closeSession, getUserProfile, getRateLimit
  - Automatic token management in localStorage
  - 401 handling with redirect to login on token expiry

##### ✅ Variant Selector Component (2026-04-26)
- Created `src/components/VariantSelector.tsx`:
  - Displays Cloud Native and Server-Based documentation options
  - Button-style selector with description text
  - Callback for variant change
  - Responsive CSS Grid layout
- Styling: `src/components/VariantSelector.module.css`
  - Active state styling with primary color highlight
  - Hover effects and transitions
  - Dark mode support

##### ✅ Chat Interface Component (2026-04-26)
- Created `src/components/ChatInterface.tsx`:
  - Message display with role-based styling (user/assistant)
  - Input form with submit handling
  - Session management (create new or resume existing)
  - API integration for query submission
  - Real-time message streaming with loading state
  - Message history with timestamps
  - Click on assistant message to show citations/reasoning details
- Styling: `src/components/ChatInterface.module.css`
  - Two-column layout (messages + side panel)
  - Responsive (single column on mobile)
  - Message animations and loading indicators
  - Input form with disabled state during processing

##### ✅ Citations Panel Component (2026-04-26)
- Created `src/components/CitationsPanel.tsx`:
  - Displays list of citations from query response
  - Citation numbering with sequential badges
  - Shows: document title, file path, content preview
  - Truncates long content with `-webkit-line-clamp: 3`
- Styling: `src/components/CitationsPanel.module.css`
  - Scrollable list with numbered citations
  - Color-coded badges matching UI theme
  - Responsive spacing and typography

##### ✅ Reasoning Trail Component (2026-04-26)
- Created `src/components/ReasoningTrail.tsx`:
  - Collapsible section showing query metadata
  - Displays: variant, tool calls count, processing time, session ID
  - Processing steps (1-4): Query → Planning → Execution → Synthesis
  - Step descriptions and progress visualization
- Styling: `src/components/ReasoningTrail.module.css`
  - Expandable/collapsible header
  - Numbered step visualization
  - Color-coded info rows

##### ✅ Main App Component (2026-04-26)
- Created `src/App.tsx`:
  - Authentication flow: Login form if not authenticated, chat UI if logged in
  - User profile loading on mount
  - Session state management
  - Variant switching with session reset
  - Logout functionality
  - Error handling for authentication failures
- Login form component with email/password fields
- Loading state while checking authentication
- Styling: `src/App.module.css`
  - Header with branding and user section
  - Login container with gradient background
  - Responsive layout
  - Dark mode support

##### ✅ Frontend Configuration & Docs (2026-04-26)
- Created `frontend/.gitignore` for Node dependencies, build output, env files
- Created `frontend/README.md` with:
  - Setup and installation instructions
  - Development and build commands
  - Project structure overview
  - API integration documentation
  - Component descriptions
  - Browser support notes

## Remaining Work

### M5: Web UI - Pending Tasks

- [ ] Session persistence (save/load from backend)
- [ ] Message export/sharing
- [ ] Advanced filtering and search within chat history
- [ ] Keyboard shortcuts (Cmd/Ctrl+K for search, etc.)
- [ ] Error boundary components
- [ ] Loading skeleton screens
- [ ] Accessibility improvements (ARIA labels, keyboard nav)
- [ ] E2E tests (Cypress/Playwright)

### M6: Evaluation & Testing (Pending)

- [ ] 300-query evaluation harness (per PRD specification)
- [ ] Accuracy metrics (answer correctness, citation accuracy)
- [ ] Latency benchmarks (response time, tool call duration)
- [ ] Citation verification (correctness, completeness)
- [ ] Cross-variant boundary testing (ensure variant isolation)
- [ ] Edge case testing (malformed documents, OCR failures)

### M7: Deployment & Monitoring (Pending)

- [ ] Docker containerization (Dockerfile + docker-compose.yml)
- [ ] OpenTelemetry + Prometheus integration
- [ ] Grafana dashboards (query latency, error rates, cache hit rates)
- [ ] Production deployment configuration
- [ ] Monitoring and alerting setup

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
