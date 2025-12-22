"""
AI-driven test coverage identifier using Gemini
Identifies total number of test cases required for full coverage
"""

import logging
import os
from typing import Dict, Any, List
import google.generativeai as genai

from src.models import CompanyData, SiteStructure

logger = logging.getLogger(__name__)


class AICoverageIdentifier:
    """Uses Gemini AI to identify total test cases needed for full coverage"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize AI coverage identifier
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        api_key = os.getenv('GEMINI_API_KEY') or self.config.get('ai', {}).get('gemini_api_key')
        
        if not api_key:
            logger.warning("GEMINI_API_KEY not found. AI test coverage identification will be disabled.")
            self.enabled = False
            return
        
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            self.enabled = True
            logger.info("AI coverage identifier initialized with Gemini")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self.enabled = False
    
    def identify_total_test_cases(self, company: CompanyData, structure: SiteStructure) -> Dict[str, int]:
        """
        Use AI to identify total number of test cases needed for full coverage
        
        Args:
            company: CompanyData object
            structure: SiteStructure object from analysis
            
        Returns:
            Dictionary with test type as key and total count as value
            Format: {'functional': 50, 'accessibility': 25, 'total': 75}
        """
        if not self.enabled:
            # Fallback to estimated counts based on current generation logic
            return self._estimate_test_counts(company, structure)
        
        try:
            prompt = self._build_coverage_prompt(company, structure)
            response = self.model.generate_content(prompt)
            
            # Parse response to extract test counts
            counts = self._parse_ai_response(response.text)
            logger.info(f"AI identified total test cases: {counts}")
            return counts
            
        except Exception as e:
            logger.error(f"Error in AI coverage identification: {e}")
            # Fallback to estimated counts
            return self._estimate_test_counts(company, structure)
    
    def _build_coverage_prompt(self, company: CompanyData, structure: SiteStructure) -> str:
        """Build prompt for Gemini to identify test coverage"""
        
        site_info = f"""
Website Analysis:
- Domain: {company.domain}
- Site Type: {structure.site_type}
- URLs to test: {len(company.urls)}
- Has Navigation: {len(structure.navigation_items)} items
- Has Forms: {len(structure.forms)} forms
- Has CTAs: {len(structure.ctas)} CTAs
- Has Search: {structure.has_search}
- Has Login: {structure.has_login}
- Has Cart: {structure.has_cart}
- Has Checkout: {structure.has_checkout}
- Key Pages: {len(structure.key_pages)} pages
"""
        
        prompt = f"""You are a senior QA architect analyzing a website for comprehensive test coverage.

{site_info}

Task: Identify the TOTAL number of test cases required for complete coverage of this website.

Requirements:
1. Include ONLY Accessibility and Functional testing (exclude deep-dive functional testing)
2. Exclude: Smoke tests, Performance tests, UI/UX tests
3. Consider all URLs provided: {company.urls}
4. Consider all functional elements: navigation, forms, CTAs, site-specific flows
5. Consider all accessibility requirements: WCAG AA compliance, keyboard navigation, screen readers, etc.

Provide your response in this exact JSON format:
{{
    "functional": <number>,
    "accessibility": <number>,
    "total": <number>
}}

Be comprehensive but realistic. Think about:
- Each URL needs functional tests for navigation, forms, links, CTAs
- Each URL needs accessibility tests for WCAG compliance
- Site-specific flows (e-commerce checkout, SaaS login, etc.) need additional tests
- Multiple pages/URLs multiply the test count

Respond ONLY with valid JSON, no additional text."""
        
        return prompt
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, int]:
        """Parse AI response to extract test counts"""
        import json
        import re
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    'functional': int(data.get('functional', 0)),
                    'accessibility': int(data.get('accessibility', 0)),
                    'total': int(data.get('total', 0))
                }
        except Exception as e:
            logger.warning(f"Failed to parse AI response: {e}")
        
        # Fallback: try to extract numbers from text
        numbers = re.findall(r'\d+', response_text)
        if len(numbers) >= 2:
            functional = int(numbers[0])
            accessibility = int(numbers[1])
            return {
                'functional': functional,
                'accessibility': accessibility,
                'total': functional + accessibility
            }
        
        # Ultimate fallback
        return {'functional': 30, 'accessibility': 15, 'total': 45}
    
    def _estimate_test_counts(self, company: CompanyData, structure: SiteStructure) -> Dict[str, int]:
        """Fallback: Estimate test counts based on site structure"""
        url_count = len(company.urls)
        
        # Functional tests: base + per URL + per element
        functional_base = 10
        functional_per_url = 15
        functional_per_form = 3
        functional_per_cta = 2
        functional_site_specific = 5 if structure.site_type in ['e-commerce', 'saas'] else 2
        
        functional_total = (
            functional_base +
            (functional_per_url * url_count) +
            (functional_per_form * len(structure.forms)) +
            (functional_per_cta * len(structure.ctas)) +
            functional_site_specific
        )
        
        # Accessibility tests: base + per URL
        accessibility_base = 12
        accessibility_per_url = 8
        
        accessibility_total = accessibility_base + (accessibility_per_url * url_count)
        
        return {
            'functional': functional_total,
            'accessibility': accessibility_total,
            'total': functional_total + accessibility_total
        }

