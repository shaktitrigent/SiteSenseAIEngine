"""
JSON results storage for test execution results
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import logging

from src.models import TestResult, TestType

logger = logging.getLogger(__name__)


class ResultsStorage:
    """Stores test results in JSON format"""
    
    def __init__(self, output_dir: str):
        """
        Initialize results storage
        
        Args:
            output_dir: Directory to store JSON results
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def save_results(self, company_name: str, domain: str, results: List[TestResult]):
        """
        Save test results to JSON file
        
        Args:
            company_name: Company name
            domain: Domain name
            results: List of TestResult objects
        """
        # Convert results to JSON-serializable format
        json_data = {
            'company_name': company_name,
            'domain': domain,
            'timestamp': datetime.now().isoformat(),
            'summary': self._generate_summary(results),
            'results': [self._result_to_dict(result) for result in results]
        }
        
        # Save to file
        filename = f"{company_name.replace(' ', '_')}_results.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(results)} results to {filepath}")
    
    def _result_to_dict(self, result: TestResult) -> Dict[str, Any]:
        """Convert TestResult to dictionary"""
        return {
            'test_id': result.test_id,
            'test_type': result.test_type.value,
            'category': result.category,
            'severity': result.severity.value,
            'status': result.status.value,
            'url': result.url,
            'summary': result.summary,
            'detailed_description': result.detailed_description,
            'timestamp': result.timestamp.isoformat(),
            'evidence': result.evidence,
            'p1_failure_description': result.p1_failure_description
        }
    
    def _generate_summary(self, results: List[TestResult]) -> Dict[str, Any]:
        """Generate summary statistics"""
        total = len(results)
        passed = sum(1 for r in results if r.status.value == 'pass')
        failed = sum(1 for r in results if r.status.value == 'fail')
        skipped = sum(1 for r in results if r.status.value == 'skipped')
        
        # Count by severity
        p1_failures = sum(1 for r in results if r.severity.value == 'P1' and r.status.value == 'fail')
        p2_failures = sum(1 for r in results if r.severity.value == 'P2' and r.status.value == 'fail')
        p3_failures = sum(1 for r in results if r.severity.value == 'P3' and r.status.value == 'fail')
        
        # Count by test type
        by_type = {}
        for test_type in TestType:
            type_results = [r for r in results if r.test_type == test_type]
            by_type[test_type.value] = {
                'total': len(type_results),
                'passed': sum(1 for r in type_results if r.status.value == 'pass'),
                'failed': sum(1 for r in type_results if r.status.value == 'fail'),
                'skipped': sum(1 for r in type_results if r.status.value == 'skipped')
            }
        
        return {
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'pass_rate': round((passed / total * 100) if total > 0 else 0, 2),
            'severity_breakdown': {
                'p1_failures': p1_failures,
                'p2_failures': p2_failures,
                'p3_failures': p3_failures
            },
            'by_test_type': by_type
        }
    
    def load_results(self, filepath: str) -> Dict[str, Any]:
        """
        Load results from JSON file
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            Dictionary with results data
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

