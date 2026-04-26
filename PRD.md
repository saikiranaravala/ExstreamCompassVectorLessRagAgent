# PRD: Vectorless RAG Agent for CCM Documentation ("Compass")

| Field | Value |
| --- | --- |
| Document version | 1.0 |
| Status | Draft for review |
| Author | Sai Kiran |
| Last updated | 2026-04-25 |
| Project codename | Compass |
| Target GA | Q4 2026 |

---

## 1. Executive summary

Compass is a **vectorless retrieval-augmented agent** built specifically for the CCM tool's product documentation. The corpus has a strong, deliberately curated structure: two product variants (**Cloud Native** and **Server**), each containing the same documentation expressed in two formats (**HTML** and **PDF**). That structure is not a nuisance to flatten — it is the most useful retrieval signal the system has, and Compass treats it that way.

Instead of building a vector index that throws the variant/format hierarchy away, Compass keeps the folder tree as the index, generates a hierarchical map of summaries on top of it, and uses an LLM agent to **navigate** that map at query time. The agent reasons about which variant the user is asking about, picks the format that gives the cleanest answer (HTML when both are available), and returns a grounded answer with deep links back to the exact section or page.

Three things make this design fit the CCM documentation problem in particular:

1. **Variant disambiguation is the first decision the agent makes.** "How do I configure SMTP?" means very different things in Cloud Native versus Server. The agent never silently merges them.
2. **HTML is the primary surface; PDF is the fallback.** When the same content exists in both, HTML wins because it has anchorable section IDs and survives parsing without losing structure.
3. **No vector store, no re-indexing pipeline, no chunking artifacts.** The docs change with each release; embedding-based RAG would lag the source of truth and obscure which version of which variant produced any given chunk.

---

## 2. Problem statement

CCM documentation is scattered across a deliberate but operationally awkward grid:

```
docs/
├── cloud-native/
│   ├── html/    (web-style docs, navigable, anchor-rich)
│   └── pdf/     (downloadable manuals, page-numbered, often verbose)
└── server/
    ├── html/
    └── pdf/
```

This produces five recurring failure modes for anyone trying to use the docs:

1. **Wrong-variant answers.** A search returns a Server-version article when the user is on Cloud Native. The user follows the instructions, hits a feature that doesn't exist, and loses an hour.
2. **Format duplication.** The same content exists in HTML and PDF. Standard search returns both as separate hits, ranked unpredictably.
3. **Lossy PDF extraction.** Code samples, configuration tables, and procedural steps come out of PDFs as run-on text, breaking the answer's usefulness.
4. **No cross-variant comparison.** "How does feature X differ between Cloud and Server?" requires reading both versions side-by-side. No tool does this.
5. **No conversational follow-up.** "What about for SSO?" after the previous question requires the user to re-search from scratch.

Compass exists to make the answer to a CCM documentation question be the **answer**, with the right variant, in the cleanest format, with citations the user can verify in one click.

---

## 3. Vision and goals

### 3.1 Vision

A CCM user — internal support engineer, integrator, or customer — opens Compass, picks (or implicitly indicates) their variant, and asks a question in plain English. Compass returns a synthesized answer scoped to that variant, drawn preferentially from the HTML docs but citing the PDF when only the PDF has it, with deep links to the precise anchor (HTML) or page (PDF). When the question is about both variants, Compass answers comparatively, clearly labeling which claim came from which variant.

### 3.2 Goals (priority order)

1. **Variant-correct answers.** The agent never confuses Cloud Native with Server. Cross-variant leakage is a Sev-1 defect class.
2. **Hierarchy-as-index.** The folder structure is the retrieval index. No vector database.
3. **Format-aware citations.** HTML citations carry section anchors; PDF citations carry page numbers and section headings.
4. **Cross-variant comparison as a first-class query type.** "What changed between Server and Cloud Native for X?" is a supported, primary use case.
5. **Faithful preservation of code, tables, and steps.** Code blocks stay code; numbered steps stay numbered; tables render as tables.
6. **Auditable reasoning.** Every answer ships with the agent's descent path: which variant, which format, which document, which section.

### 3.3 Non-goals (v1)

- Indexing source code or runtime artifacts; documentation only.
- Generating new documentation or fixing existing docs.
- Cross-product retrieval (Compass is scoped to one CCM product).
- Customer-facing UI in v1 (internal users first; external as a v2 decision).
- Voice interface (planned for v2; web/chat is sufficient for v1).
- Real-time documentation updates; refresh is scheduled and incremental.

---

## 4. Target users

### 4.1 Internal support engineer ("Priya")

Handles tier-2 and tier-3 tickets across both variants. Already knows which variant a customer is on (it's in the ticket). Cares about: speed, exact procedure, clear distinction between variants. Pain: "I keep landing on the Server doc when the customer is on Cloud Native."

### 4.2 Solutions engineer / integrator ("Marcus")

Helps customers integrate the CCM tool into their stack. Often working with Cloud Native; occasionally with Server. Cares about: API references, SDK examples, configuration schema, working code samples. Pain: "The PDF has the right answer but I can't copy the code block cleanly."

### 4.3 Documentation maintainer ("Lin")

Owns the docs themselves. Cares about: discovering coverage gaps, finding stale content, identifying drift between Cloud Native and Server docs. Pain: "I have no way to ask the corpus a question."

### 4.4 Power user / migration architect ("Devon")

Planning a migration from Server to Cloud Native. Lives in cross-variant comparison queries. Cares about: feature parity, behavioral differences, deprecation notices. Pain: "Side-by-side comparison is impossible without two browser windows and a lot of patience."

---

## 5. User stories

| # | As a... | I want to... | So that... |
| --- | --- | --- | --- |
| US-1 | Support engineer | ask a question scoped explicitly to Cloud Native | answers never reference Server-only behavior |
| US-2 | Solutions engineer | get an API reference answer with the code sample preserved | I can copy-paste into a working integration |
| US-3 | Migration architect | ask "how does X differ between Server and Cloud Native?" | I get a side-by-side answer with citations from both |
| US-4 | Any user | follow up with "what about for SAML?" | conversational context carries the variant from the prior turn |
| US-5 | Doc maintainer | ask "is this topic covered for both variants?" | I can find drift and gaps without reading the whole corpus |
| US-6 | Any user | click a citation and land on the exact section or page | I can verify before trusting the answer |
| US-7 | Any user | see the agent's reasoning trail | I trust answers I'd otherwise second-guess |
| US-8 | Operator | redeploy Compass against an updated docs drop | I don't rebuild the system every release |

---

## 6. The corpus

Compass indexes one root folder. The expected layout is:

```
docs_root/
├── cloud-native/
│   ├── html/
│   │   ├── getting-started/
│   │   │   ├── index.html
│   │   │   ├── installation.html
│   │   │   └── ...
│   │   ├── api-reference/
│   │   ├── configuration/
│   │   └── ...
│   └── pdf/
│       ├── admin-guide.pdf
│       ├── api-reference.pdf
│       ├── release-notes.pdf
│       └── ...
└── server/
    ├── html/
    │   └── ...
    └── pdf/
        └── ...
```

Two assumptions baked into the design:

1. **Variant is determined by the top-level folder.** `cloud-native/` and `server/` are the only two variant roots. Anything outside them is ignored.
2. **Format is determined by the second-level folder** (`html/` or `pdf/`). Mixed-format folders are not supported in v1.

Both are validated at index time; misplaced files produce a warning and are skipped.

---

## 7. Functional requirements

### 7.1 Variant handling (FR-V) — the central feature

This is the section that distinguishes Compass from a generic doc agent.

- **FR-V1.** Every query is processed under exactly one of three variant modes: `cloud-native`, `server`, or `compare`. There is no implicit default; the mode is always set, either by the user or by the agent.
- **FR-V2.** The UI provides an explicit variant selector (radio buttons or a toggle) that defaults to the user's last-used variant within the session.
- **FR-V3.** Before answering, the agent extracts variant cues from the query text (e.g., "on the cloud version", "in the server build", "k8s deployment"). If the extracted cue contradicts the UI selection, the agent surfaces the conflict in the response and asks the user to confirm — it does not silently override either signal.
- **FR-V4.** In `compare` mode, the agent runs descent against both variant subtrees independently, synthesizes a comparative answer, and labels every claim with its variant of origin.
- **FR-V5.** When operating in `cloud-native` or `server` mode, the agent must not read any file outside the corresponding variant subtree. This is enforced in the tool runtime, not just by prompt instruction.
- **FR-V6.** When the agent cannot find an answer within the selected variant but finds one in the other, it must not silently substitute. It must respond: "Not documented for [selected variant]; documented for [other variant] — would you like that answer?"
- **FR-V7.** Variant of every cited document is stamped on every citation in the response.

### 7.2 Format handling (FR-F)

- **FR-F1.** When the same logical content exists in both HTML and PDF within a variant, the agent prefers HTML because of cleaner structure and anchorable citations. Format preference is configurable.
- **FR-F2.** The agent may fall back to PDF when (a) HTML coverage is incomplete, (b) the PDF is the canonical/signed reference, or (c) the user explicitly requests "from the PDF".
- **FR-F3.** Citations carry their format type and the appropriate anchor: `{variant, format: html, file, section_id, heading}` or `{variant, format: pdf, file, page, section_heading}`.
- **FR-F4.** Code blocks, tables, and ordered/unordered lists are preserved in the answer payload as structured elements (not flattened to prose) regardless of source format.

### 7.3 Query and response (FR-Q)

- **FR-Q1.** Accept natural-language queries up to 2,000 characters.
- **FR-Q2.** Return a structured response: `{answer_markdown, citations[], reasoning_trail[], confidence, variant_used, mode}`.
- **FR-Q3.** Support multi-turn sessions. Variant selection persists across turns within a session unless explicitly changed.
- **FR-Q4.** When confidence is low or grounding is partial, the agent must say so explicitly and suggest a refined question — never fabricate to fill the gap.
- **FR-Q5.** The agent must refuse to answer when asked about content outside the configured corpus (e.g., third-party tools, general programming questions). Refusals are polite and explanatory.
- **FR-Q6.** Code samples in answers are returned as fenced code blocks with language hints when detectable.

### 7.4 Indexing (FR-I) — the hierarchical content map

Compass maintains an **Index Tree**: a JSON artifact mirroring the folder structure, with every node carrying an LLM-generated summary. There are no embeddings.

- **FR-I1.** The Index Tree has fixed top-level structure: `root → {cloud-native, server} → {html, pdf} → ...mirrors the folder tree`.
- **FR-I2.** Each file node stores: path, content hash, mtime, format, variant, summary, structural outline (headings/sections), and format-specific metadata (HTML anchors, PDF page count and TOC).
- **FR-I3.** Each folder node stores: path, an aggregated summary derived from its children, and a count of leaves by format/type.
- **FR-I4.** Summaries are length-bounded: ≤ 200 tokens for files, ≤ 400 tokens for folders. Generated by a cheap summarization-tier model during indexing.
- **FR-I5.** Indexing is incremental. On scheduled refresh, only files whose `(content_hash, mtime)` fingerprint changed are re-summarized; their ancestor folder summaries are then re-aggregated.
- **FR-I6.** Indexing is resumable; an interrupted run picks up where it stopped on next invocation.
- **FR-I7.** The Index Tree is written atomically (write to `.atlas/index.json.tmp`, fsync, rename) so concurrent queries never observe a partial state.
- **FR-I8.** Cold index of a typical CCM doc set (estimated 1–3k pages of HTML + 5–15 PDF manuals) completes in ≤ 20 minutes. Warm refresh (5% delta) completes in ≤ 90 seconds.

### 7.5 Retrieval — vectorless, agentic (FR-R)

The agent uses a small set of deterministic tools over the Index Tree and the filesystem.

- **FR-R1.** Tools available to the agent:
  - `list_node(path)` — return a node's summary plus its children's names and summaries.
  - `read_html(path, section_id?)` — return parsed HTML content (whole doc or one anchored section).
  - `read_pdf(path, page_range?)` — return extracted text for a page range, with structural cues preserved.
  - `lexical_search(scope_path, query)` — BM25 keyword search scoped to a subtree, returns ranked snippets with anchors. No vectors.
  - `compare_variants(query, topic_path)` — convenience wrapper that runs descent in both variants and stages results for synthesis.
- **FR-R2.** Hard descent budget: max **20 tool calls** per query, max **8 file reads** per query. Both configurable, both enforced in the tool runtime, never negotiable by the agent.
- **FR-R3.** Descent always begins at the root of the *selected* variant (or both, in compare mode). The agent cannot jump to an arbitrary path without justifying the jump in the trail (e.g., from a `lexical_search` result).
- **FR-R4.** Every tool call is recorded with: tool name, arguments, agent's stated reason, latency, success/failure, output token count.
- **FR-R5.** The agent terminates with either a grounded answer (≥ 1 citation) or an explicit "insufficient evidence" response. There is no in-between.
- **FR-R6.** Post-generation citation verifier: a deterministic check that every claim cited maps to a real anchor/page in the cited file, and that the cited file's variant matches the response's declared variant.

### 7.6 Format-specific parsing (FR-P)

Parsing quality directly determines answer quality. Both formats get dedicated treatment.

#### 7.6.1 HTML

- **FR-P1.** HTML is parsed with a structure-preserving extractor (`selectolax` or `lxml` + `readability`). Navigation, sidebars, headers, footers, and TOC widgets are stripped; main content is retained.
- **FR-P2.** Heading hierarchy (`h1`–`h6`) is preserved and serialized into a structural outline.
- **FR-P3.** Anchor IDs (`id="..."`) on headings and named sections are captured for deep linking.
- **FR-P4.** `<pre>`, `<code>`, `<table>`, `<ol>`, and `<ul>` blocks are preserved as structured elements with original markup intact for round-tripping.
- **FR-P5.** Internal links between HTML pages are recorded as edges in the Index Tree, enabling the agent to follow cross-references when relevant.

#### 7.6.2 PDF

- **FR-P6.** PDF text is extracted with `pypdf` for general text and `pdfplumber` for tables. Page boundaries are preserved as anchors.
- **FR-P7.** Heading detection is heuristic: font-size and weight cues plus matching against the PDF's TOC/bookmarks when present. Detected headings become structural outline entries with page numbers.
- **FR-P8.** Code blocks in PDFs are detected via monospace-font runs and preserved as `<pre>`-equivalent structured elements; if monospace detection is uncertain, the block is flagged in the response so the user knows to verify.
- **FR-P9.** Tables extracted by `pdfplumber` are stored as structured 2-D arrays; the agent receives them as Markdown tables.
- **FR-P10.** Image-only / scanned PDFs trigger OCR via Tesseract; OCR'd content is flagged in citations as "(OCR)" so the user knows fidelity is lower.
- **FR-P11.** Each PDF is indexed at page granularity for retrieval; the agent can request a single page or a contiguous range.

### 7.7 Configuration (FR-C)

Single source: `config.yml`.

```yaml
# config.yml — Compass

corpus:
  root: "/data/ccm-docs"
  variants:
    - id: "cloud-native"
      display_name: "Cloud Native"
      folder: "cloud-native"
    - id: "server"
      display_name: "Server"
      folder: "server"
  formats:
    - id: "html"
      folder: "html"
      preferred: true        # prefer HTML when both formats cover the same topic
    - id: "pdf"
      folder: "pdf"
      preferred: false

retrieval:
  max_tool_calls_per_query: 20
  max_files_read_per_query: 8
  default_mode: "ask"        # 'ask' | 'cloud-native' | 'server' — when no UI selection given

models:
  reasoning: "claude-opus-4-7"      # final synthesis + descent decisions
  summarization: "claude-haiku-4-5"  # cheap, used during indexing
  vision: "claude-opus-4-7"          # used for diagrams/figures inside docs

indexing:
  schedule_cron: "0 */6 * * *"     # every 6 hours
  full_rebuild_cron: "0 3 * * SUN"  # weekly full rebuild Sun 3am
  ocr_enabled: true

ui:
  enable_compare_mode: true
  default_variant_in_session: "cloud-native"
  show_reasoning_trail: true

security:
  audit_log_retention_days: 365
  pii_redaction: false        # CCM docs are not expected to contain PII; flip if otherwise
```

- **FR-C1.** All operational behavior is in `config.yml`. No code changes for redeployment.
- **FR-C2.** Adding a third variant in the future is a config change plus a folder; no code change.
- **FR-C3.** Config is validated on load; invalid config fails fast with a human-readable error message.

### 7.8 UI / interaction (FR-UI)

- **FR-UI1.** Web chat UI with three variant modes: Cloud Native, Server, Compare. Selector is always visible.
- **FR-UI2.** Each answer renders Markdown with preserved code blocks, tables, and ordered lists.
- **FR-UI3.** Citations appear as numbered footnotes; hovering shows variant + format + section/page; clicking opens the source at the anchor (HTML) or page (PDF).
- **FR-UI4.** A collapsible "How I got this" panel exposes the reasoning trail (folder choices → file reads → synthesis).
- **FR-UI5.** Compare mode renders the answer in a two-column layout (Cloud Native | Server) with a synthesis paragraph on top.
- **FR-UI6.** A "thumbs up / thumbs down + comment" affordance per answer feeds the eval harness.
- **FR-UI7.** Session history is local to the user; "clear session" wipes conversational memory and returns variant selection to default.

### 7.9 Security and access control (FR-S)

- **FR-S1.** Compass runs under a service account whose filesystem permissions are the upper bound of what it can ever read.
- **FR-S2.** Authentication via SSO/OIDC. Authorization is binary in v1 (allowed users vs. not); per-variant access control is a v2 candidate.
- **FR-S3.** All file content sent to LLM providers is wrapped in delimiter tags; the agent's system prompt explicitly treats content as untrusted data, not instructions (prompt-injection defense).
- **FR-S4.** Audit log records every query, tool call, and response with: timestamp, user, variant mode, files touched, token counts, model identifiers, response hash.
- **FR-S5.** Per-user and per-tenant rate limiting at the API gateway.
- **FR-S6.** Provider data-handling: zero-retention API tier where supported; documented per-provider in the runbook.

---

## 8. Non-functional requirements

| Category | Requirement |
| --- | --- |
| Latency p50 | ≤ 5 seconds for single-variant queries |
| Latency p95 | ≤ 12 seconds single-variant; ≤ 20 seconds in compare mode |
| Accuracy | ≥ 95% on the eval set (see §12) |
| Variant correctness | ≥ 99% (this is the highest-priority metric) |
| Citation precision | ≥ 95% — cited anchors actually contain the cited claim |
| Availability | 99.5% during business hours |
| Cost ceiling | ≤ $0.15 per single-variant query, ≤ $0.30 per compare-mode query (median) |
| Concurrency | 25 concurrent sessions without degradation in v1 |
| Index size | Up to 5,000 documents (HTML pages + PDFs) per deployment in v1 |
| Cold-start indexing | ≤ 20 minutes for a typical CCM doc set |
| Refresh lag | New/changed docs reflected in answers within 6 hours |
| Observability | Full OpenTelemetry tracing; cost and latency dashboards |

---

## 9. Why vectorless — for this corpus specifically

Vector RAG is the right tool when the corpus is unstructured, large, and frequently queried via fuzzy similarity. CCM documentation is the opposite case on every axis:

**Strong existing structure.** The variant/format split is meaningful. Embedding-based retrieval flattens it into a soup of similar-looking chunks, and you can no longer reliably tell whether a Cloud Native chunk or a Server chunk won the cosine-similarity coin flip. Compass keeps the structure as the index and reasons over it.

**Modest size.** A typical CCM product's docs are on the order of 1–5k HTML pages plus a dozen PDFs. The full Index Tree of summaries fits comfortably in an LLM's working context across descent steps. There is no point paying the operational cost of a vector store for this volume.

**Frequent regeneration.** Docs ship with releases. A vector pipeline lags every release by however long re-embedding takes. Compass reads files at query time, with summaries re-generated only when a file's hash changes. The freshest answer is always the live one.

**Citation precision matters.** Doc users verify before trusting. Vector chunks have ambiguous boundaries; a cited "chunk #4731" is not a section a user can navigate to. Compass cites HTML anchors and PDF page numbers — locations the user can see.

**Variant safety is non-negotiable.** A vector store with a "variant" filter applied post-hoc still has variant-mixed candidates ranked together; a bug in the filter, or a missed metadata tag on a chunk, leaks Server content into a Cloud Native answer. Compass cannot leak across variants because the agent literally never lists or reads files outside the selected subtree.

**Cross-variant comparison becomes natural.** In vector RAG, comparing variants means running two separate retrievals and somehow stitching them. In Compass, `compare` mode is a normal descent run twice, with synthesis at the end. The architecture supports the use case directly.

The trade-off Compass accepts in return: more LLM tokens per query (the agent reads summaries during descent), and a sub-linear scaling ceiling around 5–10k documents per deployment. Both are acceptable for this corpus and reconsidered for v2 if scale grows.

---

## 10. System architecture

### 10.1 Component diagram

```
                 +-----------------------+
                 |   Web Chat UI         |
                 |  (variant selector,   |
                 |   compare mode,       |
                 |   citations panel)    |
                 +-----------+-----------+
                             | HTTPS
                             v
                 +-----------------------+
                 |   API Gateway         |
                 |   (auth, rate limit)  |
                 +-----------+-----------+
                             |
                             v
        +--------------------+--------------------+
        |        Orchestration Service            |
        |  - session + variant mode mgmt          |
        |  - budget enforcement                   |
        |  - audit logging                        |
        |  - citation verifier                    |
        +-----+-----------+-----------+-----------+
              |           |           |
              v           v           v
        +---------+  +---------+  +---------+
        |Reasoning|  |  Tool   |  | Vision  |
        | Agent   |  | Runtime |  | Service |
        | (LLM)   |  |         |  |         |
        +---------+  +----+----+  +----+----+
                          |            |
                          v            v
                 +-----------------------+
                 |   Index Tree Store    |
                 |  (.atlas/index.json)  |
                 +-----------+-----------+
                             |
                             v
                 +-----------------------+
                 |  Source filesystem    |
                 |  (read-only mount)    |
                 |  cloud-native/{html,pdf}|
                 |  server/{html,pdf}    |
                 +-----------------------+

        +-----------------------------------------+
        |   Indexer (scheduled job)               |
        |   - traverses corpus root               |
        |   - parses HTML (selectolax)            |
        |   - parses PDF (pypdf + pdfplumber)     |
        |   - generates summaries (Haiku)         |
        |   - propagates folder summaries upward  |
        |   - atomic swap of index.json           |
        +-----------------------------------------+
```

### 10.2 Tech stack (proposed)

| Layer | Choice | Rationale |
| --- | --- | --- |
| Backend | Python 3.12, FastAPI | Async, fits agent workloads, ecosystem fit |
| Agent framework | LangGraph | Explicit graph control over descent and budget enforcement |
| LLM (reasoning) | Claude Opus 4.7 | Strong tool use, structured output, vision |
| LLM (summarization) | Claude Haiku 4.5 | Cheap, fast, good enough for summaries |
| HTML parsing | `selectolax` + `readability-lxml` | Fast, structure-preserving |
| PDF text | `pypdf` | Mature, reliable |
| PDF tables | `pdfplumber` | Best-in-class table extraction |
| OCR fallback | Tesseract via `pytesseract` | Standard for scanned PDFs |
| Lexical search | Tantivy (`tantivy-py`) | In-process BM25, no service to run |
| Index store | JSON on disk + SQLite for metadata | Simple, diffable, transactional |
| Telemetry | OpenTelemetry + Grafana | Standard |
| Deployment | Docker, single-tenant container | v1 is one corpus, one deployment |

---

## 11. Data model

### 11.1 Index Tree node — file (HTML)

```json
{
  "node_id": "ab12...",
  "type": "file",
  "variant": "cloud-native",
  "format": "html",
  "path": "/data/ccm-docs/cloud-native/html/configuration/smtp.html",
  "content_hash": "sha256:...",
  "mtime": "2026-04-22T10:11:00Z",
  "summary": "Describes SMTP relay configuration in Cloud Native, including TLS, OAuth2, and rate-limit settings.",
  "summary_model": "claude-haiku-4-5-20251001",
  "structural_outline": [
    {"heading": "Overview", "anchor": "overview", "level": 1},
    {"heading": "TLS configuration", "anchor": "tls-config", "level": 2},
    {"heading": "OAuth2 configuration", "anchor": "oauth2", "level": 2},
    {"heading": "Rate limits", "anchor": "rate-limits", "level": 2}
  ],
  "internal_links": ["../authentication/oauth2.html", "../monitoring/metrics.html"],
  "has_code_blocks": true,
  "has_tables": true
}
```

### 11.2 Index Tree node — file (PDF)

```json
{
  "node_id": "cd34...",
  "type": "file",
  "variant": "server",
  "format": "pdf",
  "path": "/data/ccm-docs/server/pdf/admin-guide.pdf",
  "content_hash": "sha256:...",
  "mtime": "2026-04-15T08:00:00Z",
  "page_count": 312,
  "summary": "Server admin guide covering installation, clustering, backup/restore, and monitoring.",
  "summary_model": "claude-haiku-4-5-20251001",
  "structural_outline": [
    {"heading": "Installation", "page": 12, "level": 1},
    {"heading": "Clustering", "page": 78, "level": 1},
    {"heading": "Backup and restore", "page": 154, "level": 1},
    {"heading": "Monitoring", "page": 220, "level": 1}
  ],
  "ocr_used": false,
  "has_tables": true
}
```

### 11.3 Audit record

```json
{
  "query_id": "q_20260425_...",
  "user_id": "sso:sai.kiran",
  "received_at": "2026-04-25T19:14:02Z",
  "query_text": "How do I configure SMTP with OAuth2?",
  "mode": "cloud-native",
  "variant_selected_via": "ui",
  "tool_calls": [
    {"tool": "list_node", "args": {"path": "/cloud-native/html"}, "duration_ms": 8},
    {"tool": "list_node", "args": {"path": "/cloud-native/html/configuration"}, "duration_ms": 7},
    {"tool": "read_html", "args": {"path": ".../smtp.html", "section_id": "oauth2"}, "duration_ms": 91}
  ],
  "files_cited": [
    {"path": ".../smtp.html", "variant": "cloud-native", "format": "html", "anchor": "oauth2"}
  ],
  "tokens_in": 14502,
  "tokens_out": 488,
  "cost_usd": 0.073,
  "latency_ms": 4210,
  "confidence": "high",
  "verifier_passed": true
}
```

---

## 12. Evaluation and success metrics

### 12.1 Eval harness

A held-out eval set of **300 queries** spanning every realistic shape:

| Category | Count | Purpose |
| --- | --- | --- |
| Cloud Native, single-fact | 60 | Bread-and-butter accuracy |
| Server, single-fact | 60 | Bread-and-butter accuracy |
| Cross-variant comparison | 50 | Compare-mode quality |
| Procedural ("how do I…") | 40 | Step preservation, ordered list integrity |
| API reference | 30 | Code block fidelity |
| Configuration / parameter | 30 | Table fidelity |
| Out-of-corpus (should refuse) | 30 | Refusal correctness |

| Metric | Target |
| --- | --- |
| Variant correctness (right product cited) | ≥ 99% |
| Answer accuracy | ≥ 95% |
| Citation precision (cited anchor contains cited claim) | ≥ 95% |
| Citation recall (vs. ground-truth sources) | ≥ 85% |
| Refusal correctness (out-of-corpus) | ≥ 98% |
| Hallucination rate | ≤ 1% |
| Code/table fidelity (human-judged) | ≥ 95% |
| Compare-mode synthesis quality (human-judged 1–5) | ≥ 4.0 |

### 12.2 Field metrics

- DAU per variant.
- Compare-mode usage rate (an interesting product signal).
- Deep-link clickthrough rate.
- Thumbs-up ratio per query category.
- Self-reported time saved per query.

### 12.3 Definition of success at GA

- Variant correctness ≥ 99% on eval; zero observed cross-variant leaks in pilot.
- Answer accuracy ≥ 95% on eval.
- p95 latency under 12s single-variant, 20s compare-mode.
- ≥ 60% of pilot users say Compass replaced their default doc-search workflow within 4 weeks.
- Zero security findings in penetration test.

---

## 13. Milestones and roadmap

| Phase | Window | Scope |
| --- | --- | --- |
| **M0 — Foundations** | May 2026 | Repo scaffolding, config schema, OIDC, audit log, single-variant prototype on a 100-doc subset |
| **M1 — Indexer v1** | Jun 2026 | HTML + PDF parsers, hierarchical tree builder, incremental refresh, atomic swap |
| **M2 — Agent v1** | Jul 2026 | LangGraph agent with five tools, descent budget, citation verifier, single-variant queries working end-to-end |
| **M3 — Variant features** | Aug 2026 | Compare mode, variant cue extraction from query, conflict surfacing UI, eval harness baseline (single-variant + compare) |
| **M4 — Format polish** | Sep 2026 | Code block / table fidelity work, OCR fallback for scanned PDFs, vision pass for diagrams in PDFs |
| **M5 — Hardening + pilot** | Oct 2026 | Prompt-injection defense, observability, load test, internal pilot with support team |
| **M6 — GA** | Q4 2026 | Runbooks, on-call, SLA |
| **v2 (post-GA)** | 2027 | Voice interface, customer-facing access, third-variant support, real-time refresh on doc-publish webhook |

---

## 14. Risks and mitigations

| # | Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| R-1 | Cross-variant leak: Server answer served when Cloud Native was selected | Med | **Critical** | Tool runtime enforces subtree restriction; citation verifier rechecks variant tag before response is returned; eval harness blocks releases below 99% variant correctness |
| R-2 | PDF code-block extraction mangles indentation / quotes | High | High | Monospace-font heuristic + uncertainty flag in response; offer raw page-image fallback for verification |
| R-3 | Same-content drift between HTML and PDF (doc team updated one, not the other) | Med | Med | Compass reports the drift in maintainer-mode queries; confidence band reflects when sources within a variant disagree |
| R-4 | Agent exceeds budget on compare-mode queries → cost spike | Med | Med | Per-mode budgets; compare mode gets ~2x single-variant budget but no more; circuit breaker at the daily-spend level |
| R-5 | Hallucinated citation (wrong anchor cited for a real claim) | Med | High | Post-generation verifier reads the cited anchor and confirms; failed verification triggers re-answer with stricter grounding |
| R-6 | Prompt injection embedded in a doc page | Low | High | All file content is delimiter-tagged; system prompt treats content as untrusted; tools cannot perform writes; provider-side filtering as defense in depth |
| R-7 | Scanned PDFs have low OCR fidelity | Med | Med | "(OCR)" tag on citations from OCR'd pages; lower confidence band; option to surface page image alongside text |
| R-8 | Folder layout drifts from spec (mixed-format folders, unexpected variants) | Med | Med | Indexer validates layout, warns and skips out-of-spec files; admin dashboard shows skipped files |
| R-9 | LLM provider outage | Low | High | Multi-provider abstraction with secondary configured (e.g., Azure OpenAI); failover documented in runbook |
| R-10 | Users over-trust answers, especially in compare mode where synthesis is harder | Med | High | Confidence band always shown; deep links emphasized; in-product copy nudges verification on procedural answers |

---

## 15. Open questions

1. **Compare mode default behavior on missing variant.** When a topic exists only in Cloud Native and the user asks a compare query, do we (a) say "Server: not documented" or (b) refuse compare and answer single-variant? Lean toward (a) for usefulness; needs UX validation.
2. **Drift reporting.** Should Compass actively surface HTML/PDF drift within a variant to maintainers, or stay silent unless asked? Affects scope of the maintainer persona.
3. **Format preference override per query.** Worth a UI toggle ("answer from PDF only") for users who need the canonical reference, or is a query-text cue enough?
4. **Per-variant access control.** Do we need to gate access to Server vs. Cloud Native independently? Likely yes for customer-facing v2; not required for internal v1.
5. **HTML cross-link traversal.** When an HTML page references another, should the agent automatically follow the link if relevant, or stay strictly within its descent budget? Lean toward "yes, but counts against budget."
6. **Diagrams in HTML.** HTML pages may embed `<img>` references to architecture diagrams. Treat them as first-class (vision pass at index time) or only on demand? Cost vs. discoverability trade-off.
7. **Eval set ownership.** Who authors and maintains the 300-query eval set, and on what cadence? This is the single biggest unstated dependency.

---

## 16. Appendix

### 16.1 Glossary

- **Variant.** Either `cloud-native` or `server`. The top-level partition of the corpus.
- **Format.** Either `html` or `pdf`. The second-level partition within a variant.
- **Compare mode.** A query mode where Compass runs descent against both variants and synthesizes a side-by-side answer.
- **Index Tree.** Hierarchical map of summaries that mirrors the on-disk folder structure. Compass's only retrieval index.
- **Descent.** The agent's tool-driven traversal of the Index Tree from root toward leaves.
- **Budget.** Hard-bounded count of tool calls and file reads per query.
- **Anchor.** Precise location within a document — HTML section ID or PDF page number.
- **Citation verifier.** Post-generation deterministic check that every citation maps to a real anchor whose content actually supports the cited claim.

### 16.2 Architectural decision records (to be authored)

- ADR-001: Why no vector database for the CCM doc corpus.
- ADR-002: HTML preferred over PDF when both formats cover the same topic.
- ADR-003: Variant determined by top-level folder; no metadata-based override.
- ADR-004: LangGraph for explicit descent control over a custom agent loop.
- ADR-005: JSON-on-disk Index Tree over a dedicated index service.

### 16.3 Out of scope, parked

- Voice-first desktop client.
- Customer-facing UI.
- A third variant (e.g., a future "Edge" deployment model) — supported by config but no UX work in v1.
- Documentation-generation features (writing or improving docs).
- Cross-product retrieval (other CCM tools, third-party integrations).

---

*End of document.*
