# Evaluation Framework

Comprehensive 300-query evaluation harness for benchmarking Compass RAG performance, accuracy, and citation correctness.

## Overview

The evaluation framework consists of:

1. **Test Queries** — 300 predefined queries covering different:
   - Variants (Cloud Native, Server-Based)
   - Categories (Installation, Configuration, Features, etc.)
   - Difficulty levels (Easy, Medium, Hard)

2. **Metrics Collection** — Tracks per-query:
   - Latency (response time)
   - Tool calls (number of tools executed)
   - Citations (count and correctness)
   - Keyword accuracy (expected keywords found in answer)
   - Answer quality (length, relevance)

3. **Report Generation** — Produces:
   - JSON report (machine-readable metrics)
   - CSV report (per-query detailed results)
   - HTML report (visual dashboard with charts)

## Usage

### Run Full Evaluation

```python
from compass.agent.agent import ReasoningAgent
from tests.evaluation import EvaluationHarness, EvaluationReporter, EVALUATION_QUERIES

# Initialize agent
agent = ReasoningAgent(...)

# Create harness
harness = EvaluationHarness(agent)

# Run all 300 queries
await harness.run_batch(EVALUATION_QUERIES, batch_size=10)

# Print summary
harness.print_summary()

# Generate reports
results = harness.get_results()
reporter = EvaluationReporter(results)
reporter.save_all_reports()
```

### Run Specific Variant

```python
from tests.evaluation import get_evaluation_queries_by_variant

# Get Cloud Native queries only
cn_queries = get_evaluation_queries_by_variant("CloudNative")
await harness.run_batch(cn_queries)
```

### Run by Difficulty

```python
from tests.evaluation import get_evaluation_queries_by_difficulty

# Get only hard queries
hard_queries = get_evaluation_queries_by_difficulty("hard")
await harness.run_batch(hard_queries)
```

### Run by Category

```python
from tests.evaluation import get_evaluation_queries_by_category

# Get installation queries
install_queries = get_evaluation_queries_by_category("Installation")
await harness.run_batch(install_queries)
```

## Query Structure

Each evaluation query includes:

```python
EvaluationQuery(
    id="cn-001",                    # Unique identifier
    query="How do I install...",    # Question to ask
    variant="CloudNative",          # Cloud Native or Server-Based
    expected_keywords=[...],        # Keywords expected in answer
    min_citations=1,                # Minimum citations required
    category="Installation",        # Query category
    difficulty="easy",              # Query difficulty level
)
```

## Metrics

### Per-Query Metrics

- **Latency** — Response time in milliseconds
- **Tool Calls** — Number of tools executed
- **Citations Count** — Number of citations in response
- **Keywords Found** — Count of expected keywords found
- **Answer Length** — Length of generated answer

### Aggregated Metrics

- **Success Rate** — % of queries meeting expectations
- **Average Latency** — Mean response time
- **Average Tool Calls** — Mean tools per query
- **Citation Coverage** — % of queries with sufficient citations
- **Keyword Accuracy** — % of expected keywords found across all queries

## Reports

### JSON Report

Machine-readable summary with:
- Overall success metrics
- Latency statistics
- Tool call averages
- Citation metrics
- Per-variant breakdown
- Per-category breakdown
- Per-difficulty breakdown

Example:
```json
{
  "timestamp": "2026-04-26T...",
  "summary": {
    "total_queries": 300,
    "successful": 285,
    "failed": 15,
    "success_rate": 95.0
  },
  "latency": {
    "average_ms": 2345.6,
    "min_ms": 150.2,
    "max_ms": 8900.1
  },
  ...
}
```

### CSV Report

Detailed per-query results with:
- Query ID and variant
- Success/failure status
- Latency, tool calls, citations
- Keyword accuracy
- Error messages for failed queries

### HTML Report

Visual dashboard with:
- Executive summary
- Performance metrics table
- Success rates by variant
- Success rates by category
- Success rates by difficulty
- Interactive charts (if viewed in browser)

## Evaluation Criteria

A query is considered **successful** if:

1. ✅ Agent executes without errors
2. ✅ Answer contains minimum required citations
3. ✅ Response time is reasonable (<10s)
4. ✅ At least one expected keyword found

## Success Rate Targets

- **Cloud Native Installation**: 95%+ (simple, well-documented)
- **Server-Based Configuration**: 90%+ (complex, many variations)
- **Cross-Variant Comparison**: 85%+ (requires multi-source analysis)
- **Hard Queries**: 70%+ (complex reasoning, ambiguous)

## Example Output

```
======================================================================
EVALUATION RESULTS SUMMARY
======================================================================

Total Queries: 300
Successful: 285
Failed: 15
Success Rate: 95.0%

Latency:
  Average: 2345.6ms
  Min: 150.2ms
  Max: 8900.1ms

Tool Calls:
  Total: 1425
  Average per query: 4.75

Citations:
  Total: 412
  Average per query: 1.37
  Queries meeting minimum: 298/300

Keyword Accuracy: 87.3%

Answer Length:
  Average: 1562 chars
  Min: 45
  Max: 9823

By Variant:
  CloudNative: 96.7%
  ServerBased: 93.3%

By Category:
  Installation: 98.0%
  Configuration: 94.0%
  Features: 92.0%
  Troubleshooting: 88.0%

By Difficulty:
  easy: 98.0%
  medium: 95.0%
  hard: 72.0%

======================================================================
```

## Performance Baseline

Expected performance on modern hardware:

| Metric | Target |
|--------|--------|
| Avg Latency | <3 seconds |
| Success Rate | >90% |
| Citations/Query | >1.0 |
| Keyword Accuracy | >85% |
| Tool Calls/Query | 3-6 |

## Integration with CI/CD

Add to GitHub Actions workflow:

```yaml
- name: Run Evaluation Harness
  run: |
    python -m pytest tests/evaluation/test_harness.py -v
    python scripts/run_full_evaluation.py
    
- name: Upload Reports
  uses: actions/upload-artifact@v3
  with:
    name: evaluation-reports
    path: evaluation_reports/
```

## Extending Queries

To add more evaluation queries:

1. Edit `tests/evaluation/test_queries.py`
2. Add new `EvaluationQuery` objects to `EVALUATION_QUERIES` list
3. Ensure IDs are unique
4. Run evaluation to validate new queries

## Troubleshooting

### High Failure Rate

- Check agent initialization
- Verify index tree is properly loaded
- Check variant isolation is working
- Review error logs in CSV report

### Slow Queries

- Profile tool execution
- Check search index performance
- Verify document parsing is efficient
- Monitor memory usage

### Missing Citations

- Check CitationExtractor is working
- Verify search results are being returned
- Ensure minimum citation requirements are reasonable

## Related Files

- `harness.py` — Main evaluation engine
- `metrics.py` — Metrics collection and aggregation
- `reporter.py` — Report generation
- `test_queries.py` — 300 evaluation queries
- `test_harness.py` — Unit tests for evaluation framework
