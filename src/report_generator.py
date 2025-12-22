"""
HTML report generator with charts and PDF conversion
"""

from pathlib import Path
from typing import List, Dict, Any
from jinja2 import Template
import logging
import asyncio
import os
from playwright.async_api import async_playwright

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
    
    def generate_reports(self, company_name: str, domain: str, results: List[TestResult],
                        total_test_counts: Dict[str, int] = None, total_identified_tests: int = None):
        """
        Generate all 4 HTML reports for a company and convert to PDF
        
        Args:
            company_name: Company name
            domain: Domain name
            results: List of TestResult objects (executed tests only)
            total_test_counts: Dictionary with total test counts by type (from AI)
            total_identified_tests: Total number of test cases identified
        """
        # Create domain-specific folder
        domain_folder = self._sanitize_domain(domain)
        domain_dir = self.output_dir / domain_folder
        domain_dir.mkdir(parents=True, exist_ok=True)
        
        # Filter results by type
        functional_results = [r for r in results if r.test_type == TestType.FUNCTIONAL]
        smoke_results = [r for r in results if r.test_type == TestType.SMOKE]
        accessibility_results = [r for r in results if r.test_type == TestType.ACCESSIBILITY]
        performance_results = [r for r in results if r.test_type == TestType.PERFORMANCE]
        
        html_files = []
        
        # Generate each report (only Functional and Accessibility per requirements)
        if functional_results:
            functional_total = total_test_counts.get('functional', len(functional_results)) if total_test_counts else len(functional_results)
            html_file = self._generate_report(
                company_name, domain, "Functional", functional_results, domain_dir,
                total_identified=functional_total, total_executed=len(functional_results)
            )
            if html_file:
                html_files.append(html_file)
        
        if accessibility_results:
            accessibility_total = total_test_counts.get('accessibility', len(accessibility_results)) if total_test_counts else len(accessibility_results)
            html_file = self._generate_report(
                company_name, domain, "Accessibility", accessibility_results, domain_dir,
                total_identified=accessibility_total, total_executed=len(accessibility_results)
            )
            if html_file:
                html_files.append(html_file)
        
        # Convert HTML files to PDF
        if html_files:
            try:
                # Try to get current event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is already running, we need to schedule it
                    # Create a new event loop in a thread
                    import threading
                    def run_in_thread():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        new_loop.run_until_complete(self._convert_html_to_pdf(html_files, domain_dir))
                        new_loop.close()
                    thread = threading.Thread(target=run_in_thread)
                    thread.start()
                    thread.join()
                else:
                    loop.run_until_complete(self._convert_html_to_pdf(html_files, domain_dir))
            except RuntimeError:
                # No event loop, create new one
                asyncio.run(self._convert_html_to_pdf(html_files, domain_dir))
    
    def _generate_report(self, company_name: str, domain: str, report_type: str, 
                        results: List[TestResult], domain_dir: Path,
                        total_identified: int = None, total_executed: int = None) -> Path:
        """
        Generate a single HTML report
        
        Args:
            company_name: Company name
            domain: Domain name
            report_type: Type of report (Functional, Accessibility, etc.)
            results: List of TestResult objects (executed tests)
            domain_dir: Directory for domain-specific reports
            total_identified: Total number of test cases identified
            total_executed: Total number of test cases executed
            
        Returns:
            Path to generated HTML file
        """
        # Calculate statistics
        stats = self._calculate_stats(results)
        
        # Add total identified vs executed info
        if total_identified is None:
            total_identified = len(results)
        if total_executed is None:
            total_executed = len(results)
        
        stats['total_identified'] = total_identified
        stats['total_executed'] = total_executed
        
        # Copy logo to report directory and get path
        logo_path = self._copy_logo_to_report_dir(domain_dir)
        
        # Prepare data for template
        template_data = {
            'company_name': company_name,
            'domain': domain,
            'report_type': report_type,
            'stats': stats,
            'results': results,
            'p1_failures': [r for r in results if r.severity.value == 'P1' and r.status.value == 'fail'],
            'logo_path': logo_path
        }
        
        # Render template
        html_content = self._render_template(template_data, report_type)
        
        # Save file with domain-based naming
        domain_safe = self._sanitize_domain(domain)
        filename = f"{domain_safe}_{report_type}_Report.html"
        filepath = domain_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Generated {report_type} report: {filepath}")
        return filepath
    
    def _sanitize_domain(self, domain: str) -> str:
        """
        Sanitize domain name for use in file/folder names
        
        Args:
            domain: Domain string
            
        Returns:
            Sanitized domain string safe for file system
        """
        # Replace invalid characters with underscores
        sanitized = domain.replace(':', '_').replace('/', '_').replace('\\', '_')
        sanitized = sanitized.replace(' ', '_').replace('.', '_')
        # Remove multiple consecutive underscores
        while '__' in sanitized:
            sanitized = sanitized.replace('__', '_')
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        return sanitized
    
    def _copy_logo_to_report_dir(self, report_dir: Path) -> str:
        """
        Copy logo to report directory and return base64 data URI
        
        Args:
            report_dir: Directory where report is saved
            
        Returns:
            Base64 data URI for logo image
        """
        import shutil
        import base64
        
        # Look for logo in assets directory
        project_root = Path(__file__).parent.parent
        assets_dir = project_root / "assets"
        logo_file = assets_dir / "trigent-logo.png"
        
        # Try alternative locations if primary not found
        if not logo_file.exists():
            alt_locations = [
                assets_dir / "trigent-logo.jpg",
                assets_dir / "logo.png",
                assets_dir / "logo.jpg",
            ]
            
            for alt_path in alt_locations:
                if alt_path.exists():
                    logo_file = alt_path
                    break
        
        # If logo found, embed as base64 data URI
        if logo_file.exists():
            try:
                # Copy logo to report directory
                dest_logo = report_dir / logo_file.name
                shutil.copy2(logo_file, dest_logo)
                
                # Create base64 data URI for embedding
                with open(logo_file, 'rb') as f:
                    logo_data = f.read()
                    logo_base64 = base64.b64encode(logo_data).decode('utf-8')
                    
                    # Determine MIME type
                    suffix = logo_file.suffix.lower()
                    if suffix == '.png':
                        mime_type = 'image/png'
                    elif suffix in ['.jpg', '.jpeg']:
                        mime_type = 'image/jpeg'
                    else:
                        mime_type = 'image/png'
                    
                    return f"data:{mime_type};base64,{logo_base64}"
                    
            except Exception as e:
                logger.error(f"Error loading logo: {e}")
                return ""
        else:
            logger.warning(f"Trigent logo not found at {assets_dir / 'trigent-logo.png'}")
            return ""
    
    async def _convert_html_to_pdf(self, html_files: List[Path], output_dir: Path):
        """
        Convert HTML files to PDF using Playwright
        
        Args:
            html_files: List of HTML file paths to convert
            output_dir: Directory to save PDF files
        """
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                for html_file in html_files:
                    try:
                        # Read HTML file
                        html_path = html_file.resolve()
                        
                        # Load HTML file
                        await page.goto(f"file://{html_path}")
                        await page.wait_for_load_state('networkidle')
                        
                        # Generate PDF filename
                        pdf_filename = html_file.stem + '.pdf'
                        pdf_path = output_dir / pdf_filename
                        
                        # Wait for watermark to be rendered
                        await page.wait_for_selector('.sample-watermark', state='attached', timeout=5000)
                        
                        # Generate PDF with background graphics enabled
                        await page.pdf(
                            path=str(pdf_path),
                            format='A4',
                            print_background=True,
                            prefer_css_page_size=False,
                            margin={
                                'top': '20mm',
                                'right': '15mm',
                                'bottom': '20mm',
                                'left': '15mm'
                            }
                        )
                        
                        logger.info(f"Generated PDF: {pdf_path}")
                        
                    except Exception as e:
                        logger.error(f"Error converting {html_file} to PDF: {e}")
                
                await browser.close()
                
        except Exception as e:
            logger.error(f"Error during PDF conversion: {e}")
    
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
            position: relative;
        }
        /* Sample Watermark - appears on all pages (clearly visible) */
        .sample-watermark {
            position: fixed;
            bottom: 30%;
            left: 8%;
            transform: rotate(45deg);
            transform-origin: bottom left;
            font-size: 180px;
            font-weight: 400;
            color: rgba(128, 128, 128, 0.25);
            z-index: 0;
            pointer-events: none;
            letter-spacing: 40px;
            white-space: nowrap;
            user-select: none;
            -webkit-user-select: none;
            font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif;
            text-transform: uppercase;
        }
        
        /* Also use pseudo-element for browser view */
        body::before {
            content: 'SAMPLE';
            position: fixed;
            bottom: 30%;
            left: 8%;
            transform: rotate(45deg);
            transform-origin: bottom left;
            font-size: 180px;
            font-weight: 400;
            color: rgba(128, 128, 128, 0.25);
            z-index: 0;
            pointer-events: none;
            letter-spacing: 40px;
            white-space: nowrap;
            user-select: none;
            font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif;
            text-transform: uppercase;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            position: relative;
            z-index: 1;
        }
        /* Trigent Logo */
        .trigent-logo {
            position: absolute;
            top: 15px;
            right: 15px;
            width: 50px;
            height: 50px;
            z-index: 10;
        }
        .trigent-logo img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            display: block;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 20px;
            padding-right: 60px; /* Space for logo */
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
        /* Coverage Summary Box */
        .coverage-summary {
            background: #fff3cd;
            border: 2px solid #ffc107;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
        }
        .coverage-summary h2 {
            color: #856404;
            margin-bottom: 15px;
            font-size: 20px;
        }
        .coverage-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .coverage-stat {
            background: white;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #ffc107;
        }
        .coverage-stat strong {
            display: block;
            font-size: 24px;
            color: #856404;
            margin-bottom: 5px;
        }
        .coverage-stat span {
            color: #666;
            font-size: 14px;
        }
        .sample-notice {
            background: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }
        .sample-notice strong {
            color: #1976D2;
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
            body { 
                background: white;
                position: relative;
            }
            .container { 
                box-shadow: none;
            }
            /* Ensure watermark appears clearly on all printed pages */
            .sample-watermark {
                position: fixed !important;
                bottom: 30% !important;
                left: 8% !important;
                transform: rotate(45deg) !important;
                transform-origin: bottom left !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                color: rgba(128, 128, 128, 0.30) !important;
                font-size: 180px !important;
                font-weight: 400 !important;
                display: block !important;
                visibility: visible !important;
                letter-spacing: 40px !important;
                text-transform: uppercase !important;
                opacity: 1 !important;
            }
            body::before {
                position: fixed !important;
                bottom: 30% !important;
                left: 8% !important;
                transform: rotate(45deg) !important;
                transform-origin: bottom left !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                color: rgba(128, 128, 128, 0.30) !important;
                font-size: 180px !important;
                font-weight: 400 !important;
                display: block !important;
                visibility: visible !important;
                letter-spacing: 40px !important;
                text-transform: uppercase !important;
                opacity: 1 !important;
            }
        }
        
    </style>
</head>
<body>
    <div class="sample-watermark">SAMPLE</div>
    <div class="container">
        <div class="trigent-logo">
            <img src="{{ logo_path }}" alt="Trigent Logo" />
        </div>
        <h1>{{ report_type }} Test Report</h1>
        
        <div class="sample-notice">
            <strong>📋 Sample Report:</strong> This report shows a sample of test results. 
            A comprehensive test suite with {{ stats.total_identified }} total test cases was identified for complete coverage. 
            Only {{ stats.total_executed }} high-impact test cases ({{ (stats.total_executed / stats.total_identified * 100) | round(1) }}%) were executed in this sample. 
            Contact Trigent to request full test coverage and execution.
        </div>
        
        <div class="coverage-summary">
            <h2>Test Coverage Summary</h2>
            <div class="coverage-stats">
                <div class="coverage-stat">
                    <strong>{{ stats.total_identified }}</strong>
                    <span>Total Test Cases Identified</span>
                </div>
                <div class="coverage-stat">
                    <strong>{{ stats.total_executed }}</strong>
                    <span>Test Cases Executed ({{ (stats.total_executed / stats.total_identified * 100) | round(1) }}%)</span>
                </div>
                <div class="coverage-stat">
                    <strong>{{ stats.total_identified - stats.total_executed }}</strong>
                    <span>Additional Tests Available</span>
                </div>
            </div>
        </div>
        
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
        
        <h2 style="margin-top: 30px;">Executed Test Results</h2>
        <p style="margin-bottom: 15px; color: #7f8c8d;">
            The following results are for the {{ stats.total_executed }} test cases executed in this sample. 
            Results show what issues were found and their potential impact if not addressed.
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

