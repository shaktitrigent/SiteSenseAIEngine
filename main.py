#!/usr/bin/env python3
"""
Main CLI entry point for AI-First Web Testing & Reporting System
"""

import asyncio
import argparse
import logging
import sys
import io
from pathlib import Path
from typing import Dict, List, Any

from src.config_loader import ConfigLoader
from src.excel_reader import ExcelReader
from src.site_analyzer import SiteAnalyzer
from src.test_generator import TestGenerator
from src.test_runner import TestRunner
from src.results_storage import ResultsStorage
from src.report_generator import ReportGenerator
from src.models import CompanyData
import re

# Configure logging with UTF-8 encoding to handle Unicode characters
class UTF8StreamHandler(logging.StreamHandler):
    """StreamHandler that uses UTF-8 encoding for Windows compatibility"""
    def __init__(self, stream=None):
        if stream is None:
            stream = sys.stdout
        # Wrap stream with UTF-8 encoding for Windows
        if sys.platform == 'win32' and hasattr(stream, 'reconfigure'):
            try:
                stream.reconfigure(encoding='utf-8', errors='replace')
            except (AttributeError, ValueError):
                # Fallback if reconfigure fails
                pass
        super().__init__(stream)
    
    def emit(self, record):
        """Emit a record, handling Unicode encoding errors gracefully"""
        try:
            msg = self.format(record)
            stream = self.stream
            # Encode to UTF-8 and replace any problematic characters
            if sys.platform == 'win32':
                try:
                    stream.write(msg + self.terminator)
                except UnicodeEncodeError:
                    # Fallback: encode to UTF-8 and replace errors
                    stream.buffer.write((msg + self.terminator).encode('utf-8', errors='replace'))
                    stream.flush()
            else:
                stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        UTF8StreamHandler(sys.stdout),
        logging.FileHandler('webtest.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def is_playwright_browser_error(error: Exception) -> bool:
    """Check if error is related to missing Playwright browsers"""
    error_msg = str(error)
    error_type = type(error).__name__
    return ("Executable doesn't exist" in error_msg or 
            "playwright install" in error_msg.lower() or
            "BrowserType.launch" in error_msg or
            "Playwright browsers are not installed" in error_msg or
            (error_type == "RuntimeError" and "Playwright browsers" in error_msg))


def sanitize_error_message(error: Exception) -> str:
    """Remove Unicode box-drawing characters from error messages"""
    error_msg = str(error)
    # Remove Unicode box-drawing characters (╔, ║, ╚, ═, etc.)
    sanitized = re.sub(r'[╔╗╚╝║═╠╣╦╩╬]', '', error_msg)
    # Remove multiple consecutive newlines and whitespace
    sanitized = re.sub(r'\n\s*\n+', '\n', sanitized)
    # Remove the Playwright installation message block
    sanitized = re.sub(r'Looks like Playwright.*?Playwright Team', '', sanitized, flags=re.DOTALL)
    return sanitized.strip()


async def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description='AI-First Web Testing & Reporting System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py urls.xlsx
  python main.py urls.xlsx --config custom_config.yaml
  python main.py urls.xlsx --headless false
        """
    )
    
    parser.add_argument(
        'excel_file',
        type=str,
        help='Path to Excel file containing URLs'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to configuration YAML file (default: config/default_config.yaml)'
    )
    
    parser.add_argument(
        '--headless',
        type=str,
        default=None,
        help='Run browser in headless mode (true/false)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Base output directory (overrides config)'
    )
    
    parser.add_argument(
        '--parallel',
        type=int,
        default=None,
        help='Number of parallel instances to run (default: from config, max: 5). If URLs/companies < parallel, uses actual count.'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = ConfigLoader.load_config(args.config)
    
    # Apply CLI overrides
    if args.headless:
        config.setdefault('browser', {})['headless'] = args.headless.lower() == 'true'
    
    if args.output_dir:
        base_output = args.output_dir
    else:
        base_output = 'output'
    
    # Setup output directories
    output_config = config.get('output', {})
    results_dir = output_config.get('results_dir', f'{base_output}/results')
    screenshots_dir = output_config.get('screenshots_dir', f'{base_output}/screenshots')
    reports_dir = output_config.get('reports_dir', f'{base_output}/reports')
    
    logger.info("=" * 60)
    logger.info("AI-First Web Testing & Reporting System")
    logger.info("=" * 60)
    
    try:
        # Step 1: Read Excel file
        logger.info(f"\n[1/6] Reading Excel file: {args.excel_file}")
        excel_config = config.get('excel', {})
        reader = ExcelReader(
            url_column=excel_config.get('url_column', 'url'),
            company_column=excel_config.get('company_column')
        )
        companies = reader.read_urls(args.excel_file)
        logger.info(f"Found {len(companies)} companies with {sum(len(c.urls) for c in companies)} URLs")
        
        # Step 2: Analyze sites
        logger.info(f"\n[2/6] Analyzing websites...")
        analyzer_config = config.get('analysis', {})
        analyzer = SiteAnalyzer(
            max_depth=analyzer_config.get('max_depth', 2),
            max_pages=analyzer_config.get('max_pages', 10),
            timeout=analyzer_config.get('timeout', 10000)
        )
        
        company_structures = {}
        for company in companies:
            logger.info(f"Analyzing {company.domain}...")
            structure = await analyzer.analyze_company(company)
            company_structures[company.domain] = structure
            company.site_type = structure.site_type
            company.structure = {
                'navigation_items': structure.navigation_items,
                'forms': structure.forms,
                'ctas': structure.ctas,
                'key_pages': structure.key_pages,
                'has_search': structure.has_search,
                'has_cart': structure.has_cart,
                'has_checkout': structure.has_checkout,
                'has_login': structure.has_login
            }
        
        # Step 3: Generate tests
        logger.info(f"\n[3/6] Generating test cases...")
        test_generator = TestGenerator(config)
        all_test_cases = {}  # All identified test cases
        tests_to_execute = {}  # Tests selected for execution (30%)
        total_test_counts = {}  # AI-identified total counts
        
        for company in companies:
            structure = company_structures[company.domain]
            all_tests, execute_tests, counts = test_generator.generate_tests(company, structure)
            all_test_cases[company.domain] = all_tests
            tests_to_execute[company.domain] = execute_tests
            total_test_counts[company.domain] = counts
            logger.info(f"Generated {len(all_tests)} total test cases for {company.domain}")
            logger.info(f"Selected {len(execute_tests)} tests ({len(execute_tests)/len(all_tests)*100:.1f}%) for execution")
        
        # Step 4: Execute tests (with parallelism)
        logger.info(f"\n[4/6] Executing tests...")

        # Determine concurrency: CLI arg > config > default
        browser_config = config.get('browser', {})
        if args.parallel is not None:
            max_concurrency = max(1, min(args.parallel, 5))  # Cap at 5
        else:
            max_concurrency = max(1, int(browser_config.get('concurrency', 2)))
        
        # Limit concurrency to actual number of companies
        total_companies = len(companies)
        actual_concurrency = min(max_concurrency, total_companies)
        logger.info(f"Using parallel execution: requested={max_concurrency}, actual={actual_concurrency} (based on {total_companies} companies)")
        
        # Also set URL-level concurrency in config for parallel URL execution within companies
        # Use the same parallel setting, but limit to max 5
        browser_config['url_concurrency'] = min(max_concurrency, 5)

        all_results: Dict[str, List[Any]] = {}

        semaphore = asyncio.Semaphore(actual_concurrency)

        async def run_company_tests(company: CompanyData):
            """
            Run tests for a single company inside a bounded semaphore.
            Each company gets its own TestRunner / BrowserManager so that
            Playwright instances are isolated across parallel tasks.
            """
            async with semaphore:
                logger.info(f"Running tests for {company.domain}...")
                test_runner = TestRunner(config, base_output)
                test_cases = all_test_cases[company.domain]

                try:
                    # Start browser for this company
                    await test_runner.browser_manager.start()
                    # Execute only selected tests (30%) for this company
                    test_cases = tests_to_execute[company.domain]
                    results = await test_runner.run_tests(company, test_cases)
                    logger.info(f"Completed {len(results)} tests for {company.domain}")
                    return company.domain, results
                except Exception as e:
                    # Handle Playwright browser installation errors gracefully
                    if is_playwright_browser_error(e):
                        sanitized_msg = sanitize_error_message(e)
                        logger.error(f"Error running tests for {company.domain}: {sanitized_msg}")
                        logger.error("Please install Playwright browsers by running: playwright install chromium")
                    else:
                        logger.error(f"Error running tests for {company.domain}: {e}", exc_info=True)
                    return company.domain, []
                finally:
                    # Ensure browser is stopped for this company
                    try:
                        await test_runner.browser_manager.stop()
                    except Exception as stop_err:
                        logger.debug(f"Error stopping browser for {company.domain}: {stop_err}")

        # Launch tests for all companies in parallel with controlled concurrency
        company_tasks = [run_company_tests(company) for company in companies]
        results_per_company = await asyncio.gather(*company_tasks)

        for domain, results in results_per_company:
            all_results[domain] = results
        
        # Step 5: Store results
        logger.info(f"\n[5/6] Storing results...")
        results_storage = ResultsStorage(results_dir)
        
        for company in companies:
            results = all_results[company.domain]
            results_storage.save_results(company.company_name, company.domain, results)
        
        # Step 6: Generate reports
        logger.info(f"\n[6/6] Generating HTML reports and PDFs...")
        report_generator = ReportGenerator(reports_dir, config)
        
        for company in companies:
            results = all_results[company.domain]
            total_counts = total_test_counts[company.domain]
            all_tests = all_test_cases[company.domain]
            report_generator.generate_reports(
                company.company_name, 
                company.domain, 
                results,
                total_test_counts=total_counts,
                total_identified_tests=len(all_tests)
            )
            logger.info(f"Generated reports (HTML + PDF) for {company.company_name}")
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Execution Complete!")
        logger.info("=" * 60)
        logger.info(f"\nResults saved to: {results_dir}")
        logger.info(f"Reports saved to: {reports_dir}")
        logger.info(f"Screenshots saved to: {screenshots_dir}")
        
        for company in companies:
            results = all_results[company.domain]
            passed = sum(1 for r in results if r.status.value == 'pass')
            failed = sum(1 for r in results if r.status.value == 'fail')
            logger.info(f"\n{company.company_name} ({company.domain}):")
            logger.info(f"  Total: {len(results)}, Passed: {passed}, Failed: {failed}")
        
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

