#!/usr/bin/env python3
"""
Main CLI entry point for AI-First Web Testing & Reporting System
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

from src.config_loader import ConfigLoader
from src.excel_reader import ExcelReader
from src.site_analyzer import SiteAnalyzer
from src.test_generator import TestGenerator
from src.test_runner import TestRunner
from src.results_storage import ResultsStorage
from src.report_generator import ReportGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('webtest.log')
    ]
)

logger = logging.getLogger(__name__)


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
        all_test_cases = {}
        
        for company in companies:
            structure = company_structures[company.domain]
            test_cases = test_generator.generate_tests(company, structure)
            all_test_cases[company.domain] = test_cases
            logger.info(f"Generated {len(test_cases)} test cases for {company.domain}")
        
        # Step 4: Execute tests
        logger.info(f"\n[4/6] Executing tests...")
        test_runner = TestRunner(config, base_output)
        all_results = {}
        
        try:
            # Start browser once for all companies (performance optimization)
            await test_runner.browser_manager.start()
            
            for company in companies:
                logger.info(f"Running tests for {company.domain}...")
                test_cases = all_test_cases[company.domain]
                results = await test_runner.run_tests(company, test_cases)
                all_results[company.domain] = results
                logger.info(f"Completed {len(results)} tests for {company.domain}")
        finally:
            # Stop browser after all companies are processed
            await test_runner.browser_manager.stop()
        
        # Step 5: Store results
        logger.info(f"\n[5/6] Storing results...")
        results_storage = ResultsStorage(results_dir)
        
        for company in companies:
            results = all_results[company.domain]
            results_storage.save_results(company.company_name, company.domain, results)
        
        # Step 6: Generate reports
        logger.info(f"\n[6/6] Generating HTML reports...")
        report_generator = ReportGenerator(reports_dir, config)
        
        for company in companies:
            results = all_results[company.domain]
            report_generator.generate_reports(company.company_name, company.domain, results)
            logger.info(f"Generated reports for {company.company_name}")
        
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

