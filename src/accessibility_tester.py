"""
Accessibility testing using axe-core via Playwright
"""

import json
import asyncio
from typing import List, Dict, Any
import logging

from playwright.async_api import Page

logger = logging.getLogger(__name__)


class AccessibilityTester:
    """Runs accessibility tests using axe-core"""
    
    def __init__(self, wcag_level: str = "AA", rules_to_skip: List[str] = None):
        """
        Initialize accessibility tester
        
        Args:
            wcag_level: WCAG compliance level (A, AA, AAA)
            rules_to_skip: List of axe rules to skip
        """
        self.wcag_level = wcag_level
        self.rules_to_skip = rules_to_skip or []
    
    async def run_test(self, page: Page, url: str) -> Dict[str, Any]:
        """
        Run accessibility test on a page
        
        Args:
            page: Playwright page object
            url: URL being tested
            
        Returns:
            Dictionary with test results
        """
        try:
            # Check if axe is already injected (performance optimization)
            axe_loaded = await page.evaluate("""() => typeof window.axe !== 'undefined'""")
            
            if not axe_loaded:
                # Inject axe-core
                await page.add_script_tag(url="https://unpkg.com/axe-core@4.8.2/axe.min.js")
                # Wait a bit for script to load
                await page.wait_for_timeout(500)
            
            # Run axe with timeout to prevent hanging
            results = await asyncio.wait_for(
                page.evaluate("""async () => {
                    return await axe.run({
                        runOnly: {
                            type: 'tag',
                            values: ['wcag2a', 'wcag2aa', 'wcag21aa']
                        }
                    });
                }"""),
                timeout=30.0  # 30 second timeout
            )
            
            violations = results.get('violations', [])
            passes = results.get('passes', [])
            incomplete = results.get('incomplete', [])
            
            # Format violations
            formatted_violations = []
            for violation in violations:
                formatted_violations.append({
                    'id': violation.get('id', ''),
                    'impact': violation.get('impact', ''),
                    'description': violation.get('description', ''),
                    'help': violation.get('help', ''),
                    'helpUrl': violation.get('helpUrl', ''),
                    'nodes': [
                        {
                            'html': node.get('html', ''),
                            'target': node.get('target', []),
                            'failureSummary': node.get('failureSummary', '')
                        }
                        for node in violation.get('nodes', [])
                    ]
                })
            
            return {
                'status': 'pass' if len(violations) == 0 else 'fail',
                'violations': formatted_violations,
                'violation_count': len(violations),
                'pass_count': len(passes),
                'incomplete_count': len(incomplete),
                'summary': f"Found {len(violations)} accessibility violations"
            }
            
        except Exception as e:
            logger.error(f"Error running accessibility test on {url}: {e}")
            return {
                'status': 'fail',
                'violations': [],
                'violation_count': 0,
                'error': str(e),
                'summary': f"Accessibility test failed: {str(e)}"
            }
    
    def _get_severity(self, impact: str) -> str:
        """Map axe impact to severity"""
        impact_map = {
            'critical': 'P1',
            'serious': 'P1',
            'moderate': 'P2',
            'minor': 'P3'
        }
        return impact_map.get(impact.lower(), 'P2')

