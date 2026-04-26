"""Generate evaluation reports from results."""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from tests.evaluation.metrics import EvaluationResults


class EvaluationReporter:
    """Generate evaluation reports in various formats."""

    def __init__(self, results: EvaluationResults, output_dir: Optional[Path] = None):
        """Initialize reporter.

        Args:
            results: EvaluationResults to report
            output_dir: Directory for report output
        """
        self.results = results
        self.output_dir = output_dir or Path("evaluation_reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_json_report(self) -> str:
        """Generate JSON report.

        Returns:
            JSON string with results
        """
        data = {
            "timestamp": self.results.timestamp,
            "summary": {
                "total_queries": self.results.total_queries,
                "successful": self.results.successful_queries,
                "failed": self.results.failed_queries,
                "success_rate": (
                    self.results.successful_queries
                    / self.results.total_queries
                    * 100
                    if self.results.total_queries > 0
                    else 0
                ),
            },
            "latency": {
                "average_ms": self.results.avg_latency_ms,
                "min_ms": self.results.min_latency_ms,
                "max_ms": self.results.max_latency_ms,
            },
            "tool_calls": {
                "total": self.results.total_tool_calls,
                "average": self.results.avg_tool_calls,
            },
            "citations": {
                "total": self.results.total_citations,
                "average": self.results.avg_citations,
                "meeting_minimum": self.results.citations_meeting_minimum,
            },
            "keywords": {
                "accuracy_percent": self.results.keyword_accuracy,
            },
            "by_variant": self.results.results_by_variant,
            "by_category": self.results.results_by_category,
            "by_difficulty": self.results.results_by_difficulty,
        }

        return json.dumps(data, indent=2)

    def save_json_report(self) -> Path:
        """Save JSON report to file.

        Returns:
            Path to report file
        """
        report_file = (
            self.output_dir / f"evaluation_report_{datetime.now().isoformat()}.json"
        )
        report_file.write_text(self.generate_json_report())
        return report_file

    def generate_csv_report(self) -> str:
        """Generate CSV report with per-query results.

        Returns:
            CSV string with results
        """
        lines = [
            "query_id,variant,category,difficulty,success,latency_ms,tool_calls,"
            "citations,keywords_found,keywords_total,answer_length,error"
        ]

        for query in self.results.queries:
            line = (
                f"{query.query_id},{query.variant},{query.category},"
                f"{query.difficulty},{query.success},{query.latency_ms:.1f},"
                f"{query.tool_calls},{query.citations_count},"
                f"{query.keywords_found},{query.keywords_total},"
                f"{query.answer_length},\"{query.error or ''}\""
            )
            lines.append(line)

        return "\n".join(lines)

    def save_csv_report(self) -> Path:
        """Save CSV report to file.

        Returns:
            Path to report file
        """
        report_file = (
            self.output_dir
            / f"evaluation_results_{datetime.now().isoformat()}.csv"
        )
        report_file.write_text(self.generate_csv_report())
        return report_file

    def generate_html_report(self) -> str:
        """Generate HTML report.

        Returns:
            HTML string with results
        """
        success_rate = (
            self.results.successful_queries / self.results.total_queries * 100
            if self.results.total_queries > 0
            else 0
        )

        variant_rows = "".join(
            f"<tr><td>{v}</td><td>{s['successful']}/{s['total']}</td></tr>"
            for v, s in self.results.results_by_variant.items()
        )

        category_rows = "".join(
            f"<tr><td>{c}</td><td>{s['successful']}/{s['total']}</td></tr>"
            for c, s in self.results.results_by_category.items()
        )

        difficulty_rows = "".join(
            f"<tr><td>{d}</td><td>{s['successful']}/{s['total']}</td></tr>"
            for d, s in self.results.results_by_difficulty.items()
        )

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Compass Evaluation Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #3b82f6; color: white; }}
                .success {{ color: green; }}
                .failure {{ color: red; }}
                .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
                .metric-label {{ font-weight: bold; }}
                .metric-value {{ font-size: 1.2em; color: #3b82f6; }}
            </style>
        </head>
        <body>
            <h1>Compass RAG Evaluation Report</h1>
            <p>Generated: {self.results.timestamp}</p>

            <h2>Executive Summary</h2>
            <div class="metric">
                <div class="metric-label">Total Queries</div>
                <div class="metric-value">{self.results.total_queries}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Success Rate</div>
                <div class="metric-value {('success' if success_rate >= 90 else 'failure')}">
                    {success_rate:.1f}%
                </div>
            </div>
            <div class="metric">
                <div class="metric-label">Avg Latency</div>
                <div class="metric-value">{self.results.avg_latency_ms:.1f}ms</div>
            </div>

            <h2>Performance Metrics</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Average Latency</td>
                    <td>{self.results.avg_latency_ms:.1f}ms</td>
                </tr>
                <tr>
                    <td>Min Latency</td>
                    <td>{self.results.min_latency_ms:.1f}ms</td>
                </tr>
                <tr>
                    <td>Max Latency</td>
                    <td>{self.results.max_latency_ms:.1f}ms</td>
                </tr>
                <tr>
                    <td>Avg Tool Calls</td>
                    <td>{self.results.avg_tool_calls:.1f}</td>
                </tr>
                <tr>
                    <td>Avg Citations</td>
                    <td>{self.results.avg_citations:.1f}</td>
                </tr>
                <tr>
                    <td>Keyword Accuracy</td>
                    <td>{self.results.keyword_accuracy:.1f}%</td>
                </tr>
            </table>

            <h2>Results by Variant</h2>
            <table>
                <tr>
                    <th>Variant</th>
                    <th>Success Rate</th>
                </tr>
                {variant_rows}
            </table>

            <h2>Results by Category</h2>
            <table>
                <tr>
                    <th>Category</th>
                    <th>Success Rate</th>
                </tr>
                {category_rows}
            </table>

            <h2>Results by Difficulty</h2>
            <table>
                <tr>
                    <th>Difficulty</th>
                    <th>Success Rate</th>
                </tr>
                {difficulty_rows}
            </table>
        </body>
        </html>
        """
        return html

    def save_html_report(self) -> Path:
        """Save HTML report to file.

        Returns:
            Path to report file
        """
        report_file = (
            self.output_dir
            / f"evaluation_report_{datetime.now().isoformat()}.html"
        )
        report_file.write_text(self.generate_html_report())
        return report_file

    def save_all_reports(self) -> dict[str, Path]:
        """Save all report formats.

        Returns:
            Dictionary of report type to file path
        """
        return {
            "json": self.save_json_report(),
            "csv": self.save_csv_report(),
            "html": self.save_html_report(),
        }
