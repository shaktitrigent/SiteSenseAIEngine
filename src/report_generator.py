"""
HTML report generator with charts
"""

from pathlib import Path
from typing import List, Dict, Any
from jinja2 import Template
import logging

from src.models import TestResult, TestType

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates HTML reports with charts"""
    
    def __init__(self, output_dir: str, config: Dict[str, Any] = None):
        """
        Initialize report generator
        
        Args:
            output_dir: Directory to save reports
            config: Configuration dictionary
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or {}
    
    def generate_reports(self, company_name: str, domain: str, results: List[TestResult]):
        """
        Generate all 4 HTML reports for a company
        
        Args:
            company_name: Company name
            domain: Domain name
            results: List of TestResult objects
        """
        # Filter results by type
        functional_results = [r for r in results if r.test_type == TestType.FUNCTIONAL]
        smoke_results = [r for r in results if r.test_type == TestType.SMOKE]
        accessibility_results = [r for r in results if r.test_type == TestType.ACCESSIBILITY]
        performance_results = [r for r in results if r.test_type == TestType.PERFORMANCE]
        
        # Generate each report
        if functional_results:
            self._generate_report(company_name, domain, "Functional", functional_results)
        
        if smoke_results:
            self._generate_report(company_name, domain, "Smoke", smoke_results)
        
        if accessibility_results:
            self._generate_report(company_name, domain, "Accessibility", accessibility_results)
        
        if performance_results:
            self._generate_report(company_name, domain, "Performance", performance_results)
    
    def _generate_report(self, company_name: str, domain: str, report_type: str, 
                        results: List[TestResult]):
        """Generate a single HTML report"""
        # Calculate statistics
        stats = self._calculate_stats(results)
        
        # Prepare data for template
        template_data = {
            'company_name': company_name,
            'domain': domain,
            'report_type': report_type,
            'stats': stats,
            'results': results,
            'p1_failures': [r for r in results if r.severity.value == 'P1' and r.status.value == 'fail']
        }
        
        # Render template
        html_content = self._render_template(template_data, report_type)
        
        # Save file
        filename = f"{company_name.replace(' ', '_')}_{report_type}_Report.html"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Generated {report_type} report: {filepath}")
    
    def _calculate_stats(self, results: List[TestResult]) -> Dict[str, Any]:
        """Calculate statistics for report"""
        from datetime import datetime
        
        total = len(results)
        passed = sum(1 for r in results if r.status.value == 'pass')
        failed = sum(1 for r in results if r.status.value == 'fail')
        skipped = sum(1 for r in results if r.status.value == 'skipped')
        
        # Severity breakdown
        p1_failures = sum(1 for r in results if r.severity.value == 'P1' and r.status.value == 'fail')
        p2_failures = sum(1 for r in results if r.severity.value == 'P2' and r.status.value == 'fail')
        p3_failures = sum(1 for r in results if r.severity.value == 'P3' and r.status.value == 'fail')
        
        return {
            'total': total,
            'executed': total - skipped,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'pass_rate': round((passed / total * 100) if total > 0 else 0, 1),
            'severity': {
                'p1': p1_failures,
                'p2': p2_failures,
                'p3': p3_failures
            },
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _render_template(self, data: Dict[str, Any], report_type: str) -> str:
        """Render HTML template"""
        template_str = self._get_template(report_type)
        template = Template(template_str)
        return template.render(**data)
    
    def _get_template(self, report_type: str) -> str:
        """Get HTML template for report type"""
        # Base template structure
        base_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ report_type }} Test Report - {{ company_name }}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        .header-info {
            background: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 30px;
        }
        .header-info p {
            margin: 5px 0;
        }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .summary-card {
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 20px;
            text-align: center;
        }
        .summary-card h3 {
            color: #7f8c8d;
            font-size: 14px;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        .summary-card .value {
            font-size: 32px;
            font-weight: bold;
            color: #2c3e50;
        }
        .summary-card.passed .value { color: #27ae60; }
        .summary-card.failed .value { color: #e74c3c; }
        .summary-card.skipped .value { color: #f39c12; }
        .chart-container {
            margin: 30px 0;
            padding: 20px;
            background: #fafafa;
            border-radius: 5px;
        }
        .chart-container canvas {
            max-height: 400px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
            vertical-align: top;
        }
        th {
            background: #34495e;
            color: white;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        tr:hover {
            background: #f5f5f5;
        }
        tbody tr:nth-child(even) {
            background: #fafafa;
        }
        tbody tr:nth-child(even):hover {
            background: #f0f0f0;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
        }
        .status-pass { background: #d4edda; color: #155724; }
        .status-fail { background: #f8d7da; color: #721c24; }
        .status-skipped { background: #fff3cd; color: #856404; }
        .severity-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
        }
        .severity-p1 { background: #e74c3c; color: white; }
        .severity-p2 { background: #f39c12; color: white; }
        .severity-p3 { background: #3498db; color: white; }
        .p1-failure {
            background: #ffe6e6;
            border-left: 4px solid #e74c3c;
            padding: 15px;
            margin: 10px 0;
            border-radius: 3px;
        }
        .p1-failure h4 {
            color: #e74c3c;
            margin-bottom: 10px;
        }
        @media print {
            body { background: white; }
            .container { box-shadow: none; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ report_type }} Test Report</h1>
        
        <div class="header-info">
            <p><strong>Company:</strong> {{ company_name }}</p>
            <p><strong>Domain:</strong> {{ domain }}</p>
            <p><strong>Report Generated:</strong> {{ stats.timestamp if stats.timestamp else 'N/A' }}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Total Tests</h3>
                <div class="value">{{ stats.total }}</div>
            </div>
            <div class="summary-card">
                <h3>Executed</h3>
                <div class="value">{{ stats.executed }}</div>
            </div>
            <div class="summary-card passed">
                <h3>Passed</h3>
                <div class="value">{{ stats.passed }}</div>
            </div>
            <div class="summary-card failed">
                <h3>Failed</h3>
                <div class="value">{{ stats.failed }}</div>
            </div>
            {% if stats.skipped > 0 %}
            <div class="summary-card skipped">
                <h3>Skipped</h3>
                <div class="value">{{ stats.skipped }}</div>
            </div>
            {% endif %}
        </div>
        
        <div class="chart-container">
            <canvas id="statusChart"></canvas>
        </div>
        
        <div class="chart-container">
            <canvas id="severityChart"></canvas>
        </div>
        
        {% if p1_failures %}
        <h2 style="margin-top: 30px; color: #e74c3c;">Critical (P1) Failures</h2>
        {% for failure in p1_failures %}
        <div class="p1-failure">
            <h4>Test ID: {{ failure.test_id }}</h4>
            <p><strong>URL:</strong> {{ failure.url }}</p>
            <p><strong>Description:</strong> {{ failure.detailed_description }}</p>
            {% if failure.p1_failure_description %}
            <p><strong>Impact & Remediation:</strong> {{ failure.p1_failure_description }}</p>
            {% endif %}
        </div>
        {% endfor %}
        {% endif %}
        
        <h2 style="margin-top: 30px;">Detailed Results</h2>
        <p style="margin-bottom: 15px; color: #7f8c8d;">
            This section provides comprehensive details for each test case executed, including test descriptions, execution status, severity levels, and detailed summaries of results.
        </p>
        <table>
            <thead>
                <tr>
                    <th style="width: 12%;">Test ID</th>
                    <th style="width: 15%;">Category</th>
                    <th style="width: 18%;">URL</th>
                    <th style="width: 30%;">Description</th>
                    <th style="width: 8%;">Status</th>
                    <th style="width: 8%;">Severity</th>
                    <th style="width: 30%;">Detailed Summary</th>
                </tr>
            </thead>
            <tbody>
                {% for result in results %}
                <tr>
                    <td><strong>{{ result.test_id }}</strong></td>
                    <td><em>{{ result.category }}</em></td>
                    <td><a href="{{ result.url }}" target="_blank" title="{{ result.url }}">{{ result.url[:40] }}{% if result.url|length > 40 %}...{% endif %}</a></td>
                    <td style="text-align: left; padding: 12px;">
                        <div style="line-height: 1.5;">
                            {{ result.detailed_description }}
                        </div>
                    </td>
                    <td>
                        <span class="status-badge status-{{ result.status.value }}">
                            {{ result.status.value|upper }}
                        </span>
                    </td>
                    <td>
                        <span class="severity-badge severity-{{ result.severity.value.lower() }}">
                            {{ result.severity.value }}
                        </span>
                    </td>
                    <td style="text-align: left; padding: 12px;">
                        <div style="line-height: 1.5; font-size: 13px;">
                            {{ result.summary }}
                            {% if result.evidence.screenshot %}
                            <br><small style="color: #7f8c8d;">Screenshot available in evidence</small>
                            {% endif %}
                        </div>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    
    <script>
        // Status distribution chart
        const statusCtx = document.getElementById('statusChart').getContext('2d');
        new Chart(statusCtx, {
            type: 'doughnut',
            data: {
                labels: ['Passed', 'Failed', 'Skipped'],
                datasets: [{
                    data: [{{ stats.passed }}, {{ stats.failed }}, {{ stats.skipped }}],
                    backgroundColor: ['#27ae60', '#e74c3c', '#f39c12']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Test Status Distribution'
                    }
                }
            }
        });
        
        // Severity breakdown chart
        const severityCtx = document.getElementById('severityChart').getContext('2d');
        new Chart(severityCtx, {
            type: 'bar',
            data: {
                labels: ['P1 Failures', 'P2 Failures', 'P3 Failures'],
                datasets: [{
                    label: 'Failures by Severity',
                    data: [{{ stats.severity.p1 }}, {{ stats.severity.p2 }}, {{ stats.severity.p3 }}],
                    backgroundColor: ['#e74c3c', '#f39c12', '#3498db']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Failures by Severity'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    </script>
</body>
</html>"""
        
        # Customize template based on report type
        if report_type == "Performance":
            # Add performance-specific table columns
            template_str = base_template.replace(
                '<th>Summary</th>',
                '<th>Metrics</th><th>Summary</th>'
            )
            template_str = template_str.replace(
                '<td>{{ result.summary }}</td>',
                '''<td>
                    {% if result.evidence.metrics %}
                    Load: {{ result.evidence.metrics.page_load_time_ms|round(0) }}ms,
                    LCP: {{ result.evidence.metrics.lcp_ms|round(0) }}ms,
                    CLS: {{ result.evidence.metrics.cls|round(2) }},
                    Requests: {{ result.evidence.metrics.request_count }}
                    {% else %}
                    N/A
                    {% endif %}
                </td>
                <td>{{ result.summary }}</td>'''
            )
            return template_str
        
        elif report_type == "Accessibility":
            # Add accessibility-specific table columns
            template_str = base_template.replace(
                '<th>Summary</th>',
                '<th>Violations</th><th>Summary</th>'
            )
            template_str = template_str.replace(
                '<td>{{ result.summary }}</td>',
                '''<td>
                    {% if result.evidence.violation_count %}
                    {{ result.evidence.violation_count }} violation(s)
                    {% else %}
                    0
                    {% endif %}
                </td>
                <td>{{ result.summary }}</td>'''
            )
            return template_str
        
        return base_template

