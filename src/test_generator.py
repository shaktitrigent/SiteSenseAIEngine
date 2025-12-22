"""
Test case generator based on site analysis
"""

from typing import List, Dict, Any, Tuple
import logging

from src.models import TestCase, TestType, Severity, CompanyData, SiteStructure
from src.ai_coverage_identifier import AICoverageIdentifier

logger = logging.getLogger(__name__)


class TestGenerator:
    """Generates test cases based on site analysis"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize test generator
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.enable_functional = self.config.get('test_generation', {}).get('enable_functional', True)
        self.enable_smoke = self.config.get('test_generation', {}).get('enable_smoke', True)
        self.enable_accessibility = self.config.get('test_generation', {}).get('enable_accessibility', True)
        self.enable_performance = self.config.get('test_generation', {}).get('enable_performance', True)
        self.enable_uiux = self.config.get('test_generation', {}).get('enable_uiux', True)
        
        # Initialize AI coverage identifier
        self.ai_coverage = AICoverageIdentifier(config)
        
        # Execution percentage (30% for credentializing reports)
        self.execution_percentage = self.config.get('test_generation', {}).get('execution_percentage', 0.3)
    
    def generate_tests(self, company: CompanyData, structure: SiteStructure) -> Tuple[List[TestCase], List[TestCase], Dict[str, int]]:
        """
        Generate test cases for a company based on site structure
        Uses AI to identify total coverage, then selects 30% for execution
        
        Args:
            company: CompanyData object
            structure: SiteStructure object from analysis
            
        Returns:
            Tuple of:
            - List of all TestCase objects (total identified)
            - List of TestCase objects to execute (30% high-impact)
            - Dictionary with total test counts by type
        """
        # Step 1: Identify total test coverage using AI
        total_counts = self.ai_coverage.identify_total_test_cases(company, structure)
        logger.info(f"AI identified total test coverage: {total_counts}")
        
        # Step 2: Generate all functional and accessibility tests (for credentializing)
        all_test_cases = []
        
        for url in company.urls:
            # Only generate Functional and Accessibility tests (as per requirements)
            if self.enable_functional:
                all_test_cases.extend(self._generate_functional_tests(url, company, structure))
            
            if self.enable_accessibility:
                all_test_cases.extend(self._generate_accessibility_tests(url, company))
        
        # Step 3: Select 30% high-impact tests for execution
        tests_to_execute = self._select_tests_for_execution(all_test_cases, total_counts)
        
        logger.info(f"Generated {len(all_test_cases)} total test cases for {company.domain}")
        logger.info(f"Selected {len(tests_to_execute)} tests ({len(tests_to_execute)/len(all_test_cases)*100:.1f}%) for execution")
        
        return all_test_cases, tests_to_execute, total_counts
    
    def _select_tests_for_execution(self, all_tests: List[TestCase], total_counts: Dict[str, int]) -> List[TestCase]:
        """
        Select 30% of tests for execution, prioritizing high-impact tests
        
        Args:
            all_tests: All generated test cases
            total_counts: Total test counts identified by AI
            
        Returns:
            List of test cases to execute (30% of total, high-impact)
        """
        # Separate by type
        functional_tests = [t for t in all_tests if t.test_type == TestType.FUNCTIONAL]
        accessibility_tests = [t for t in all_tests if t.test_type == TestType.ACCESSIBILITY]
        
        # Calculate how many to execute (30% of each type)
        functional_target = max(1, int(len(functional_tests) * self.execution_percentage))
        accessibility_target = max(1, int(len(accessibility_tests) * self.execution_percentage))
        
        # Prioritize: P1 > P2 > P3, then by category importance
        def test_priority(test: TestCase) -> tuple:
            # Priority: (severity_weight, category_importance)
            severity_weight = {'P1': 3, 'P2': 2, 'P3': 1}[test.severity.value]
            
            # Category importance (higher = more important)
            category_importance = {
                'Navigation': 10,
                'Form Validation': 9,
                'CTA': 9,
                'WCAG Compliance': 10,
                'Keyboard Navigation': 9,
                'Color Contrast': 8,
                'Images': 8,
                'E-commerce': 10,
                'Authentication': 10,
                'Links': 7,
                'Search': 7,
                'Form Labels': 8,
                'ARIA Attributes': 7,
                'Focus Indicators': 7,
            }.get(test.category, 5)
            
            return (-severity_weight, -category_importance)  # Negative for descending sort
        
        # Select functional tests
        functional_tests.sort(key=test_priority)
        selected_functional = functional_tests[:functional_target]
        
        # Select accessibility tests
        accessibility_tests.sort(key=test_priority)
        selected_accessibility = accessibility_tests[:accessibility_target]
        
        # Combine selected tests
        selected = selected_functional + selected_accessibility
        
        logger.info(f"Selected {len(selected_functional)} functional and {len(selected_accessibility)} accessibility tests for execution")
        
        return selected
    
    def _generate_smoke_tests(self, url: str, company: CompanyData) -> List[TestCase]:
        """Generate smoke tests - at least 10 comprehensive tests"""
        tests = [
            TestCase(
                test_id=f"SMOKE-001-{company.domain}",
                test_type=TestType.SMOKE,
                category="Availability",
                description=f"Verify {url} is accessible and returns HTTP 200 status code. This test ensures the website is online and responding to requests, which is critical for user access.",
                severity=Severity.P1,
                url=url
            ),
            TestCase(
                test_id=f"SMOKE-002-{company.domain}",
                test_type=TestType.SMOKE,
                category="Page Load",
                description=f"Verify {url} loads completely within acceptable time threshold (typically under 5 seconds). This test validates that the page renders fully without excessive delays that could impact user experience.",
                severity=Severity.P1,
                url=url
            ),
            TestCase(
                test_id=f"SMOKE-003-{company.domain}",
                test_type=TestType.SMOKE,
                category="Title",
                description=f"Verify {url} has a valid, non-empty page title element. The title should be descriptive and present in the HTML head section, as it's crucial for SEO and browser tab identification.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"SMOKE-004-{company.domain}",
                test_type=TestType.SMOKE,
                category="Meta Description",
                description=f"Verify {url} contains a meta description tag. Meta descriptions improve SEO and provide context in search engine results, enhancing click-through rates.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"SMOKE-005-{company.domain}",
                test_type=TestType.SMOKE,
                category="DOM Ready",
                description=f"Verify {url} DOM content is fully loaded and ready for interaction. This ensures JavaScript can execute properly and page elements are accessible.",
                severity=Severity.P1,
                url=url
            ),
            TestCase(
                test_id=f"SMOKE-006-{company.domain}",
                test_type=TestType.SMOKE,
                category="HTTPS",
                description=f"Verify {url} uses HTTPS protocol for secure communication. HTTPS is essential for data security, user trust, and SEO ranking.",
                severity=Severity.P1,
                url=url
            ),
            TestCase(
                test_id=f"SMOKE-007-{company.domain}",
                test_type=TestType.SMOKE,
                category="Favicon",
                description=f"Verify {url} has a favicon (site icon) configured. Favicons improve brand recognition and user experience in browser tabs and bookmarks.",
                severity=Severity.P3,
                url=url
            ),
            TestCase(
                test_id=f"SMOKE-008-{company.domain}",
                test_type=TestType.SMOKE,
                category="No Console Errors",
                description=f"Verify {url} loads without critical JavaScript console errors. Console errors can indicate broken functionality and degrade user experience.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"SMOKE-009-{company.domain}",
                test_type=TestType.SMOKE,
                category="Content Presence",
                description=f"Verify {url} contains visible text content. Empty or minimal content pages may indicate loading issues or poor user experience.",
                severity=Severity.P1,
                url=url
            ),
            TestCase(
                test_id=f"SMOKE-010-{company.domain}",
                test_type=TestType.SMOKE,
                category="Response Headers",
                description=f"Verify {url} returns appropriate HTTP response headers including content-type, cache-control, and security headers. Proper headers ensure correct rendering and security.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"SMOKE-011-{company.domain}",
                test_type=TestType.SMOKE,
                category="Mobile Viewport",
                description=f"Verify {url} includes proper viewport meta tag for mobile responsiveness. This ensures the site displays correctly on mobile devices.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"SMOKE-012-{company.domain}",
                test_type=TestType.SMOKE,
                category="Language Declaration",
                description=f"Verify {url} declares the page language using HTML lang attribute. Language declaration improves accessibility and SEO.",
                severity=Severity.P3,
                url=url
            )
        ]
        return tests
    
    def _generate_functional_tests(self, url: str, company: CompanyData, 
                                   structure: SiteStructure) -> List[TestCase]:
        """Generate functional tests based on site structure - at least 10 comprehensive tests"""
        tests = []
        
        # Navigation tests
        tests.append(TestCase(
            test_id=f"FUNC-001-{company.domain}",
            test_type=TestType.FUNCTIONAL,
            category="Navigation",
            description=f"Verify primary navigation menu items are present, visible, and clickable. Navigation is critical for user journey and site usability. This test validates that users can access main sections of the website.",
            severity=Severity.P1,
            url=url,
            metadata={'nav_items': structure.navigation_items[:5] if structure.navigation_items else []}
        ))
        
        tests.append(TestCase(
            test_id=f"FUNC-002-{company.domain}",
            test_type=TestType.FUNCTIONAL,
            category="Navigation",
            description=f"Verify navigation links redirect to correct pages without errors. Each navigation item should lead to its intended destination with proper HTTP status codes.",
            severity=Severity.P1,
            url=url
        ))
        
        tests.append(TestCase(
            test_id=f"FUNC-003-{company.domain}",
            test_type=TestType.FUNCTIONAL,
            category="Navigation",
            description=f"Verify navigation menu remains accessible and functional after page interactions. Navigation should maintain state and functionality during user interactions.",
            severity=Severity.P2,
            url=url
        ))
        
        # Form tests
        form_count = len(structure.forms) if structure.forms else 0
        for i in range(min(5, max(3, form_count + 2))):  # At least 3, up to 5 form tests
            tests.append(TestCase(
                test_id=f"FUNC-{100+i}-{company.domain}",
                test_type=TestType.FUNCTIONAL,
                category="Form Validation",
                description=f"Check if form {i+1} works correctly. If forms are broken, users cannot submit information, leading to lost leads or failed transactions.",
                severity=Severity.P2,
                url=url,
                metadata={'form': structure.forms[i] if i < form_count else None}
            ))
        
        # CTA tests
        cta_count = len(structure.ctas) if structure.ctas else 0
        for i in range(min(5, max(3, cta_count + 2))):  # At least 3, up to 5 CTA tests
            cta_text = structure.ctas[i]['text'] if i < cta_count else f"CTA {i+1}"
            tests.append(TestCase(
                test_id=f"FUNC-{200+i}-{company.domain}",
                test_type=TestType.FUNCTIONAL,
                category="CTA",
                description=f"Check if '{cta_text}' button works. If CTAs are broken, users cannot complete important actions like signing up or making purchases.",
                severity=Severity.P1 if i < cta_count and ('buy' in cta_text.lower() or 'checkout' in cta_text.lower() or 'sign up' in cta_text.lower()) else Severity.P2,
                url=url,
                metadata={'cta': structure.ctas[i] if i < cta_count else None}
            ))
        
        # Link validation
        tests.append(TestCase(
            test_id=f"FUNC-300-{company.domain}",
            test_type=TestType.FUNCTIONAL,
            category="Links",
            description=f"Verify all internal links on {url} are valid and return appropriate HTTP status codes. Broken internal links degrade user experience and SEO performance.",
            severity=Severity.P2,
            url=url
        ))
        
        tests.append(TestCase(
            test_id=f"FUNC-301-{company.domain}",
            test_type=TestType.FUNCTIONAL,
            category="Links",
            description=f"Verify external links on {url} are valid and open correctly. External links should be functional and lead to legitimate destinations without security warnings.",
            severity=Severity.P3,
            url=url
        ))
        
        tests.append(TestCase(
            test_id=f"FUNC-302-{company.domain}",
            test_type=TestType.FUNCTIONAL,
            category="Links",
            description=f"Verify all links have descriptive anchor text that clearly indicates their destination. Descriptive link text improves accessibility and user understanding.",
            severity=Severity.P2,
            url=url
        ))
        
        # Search functionality
        if structure.has_search:
            tests.append(TestCase(
                test_id=f"FUNC-400-{company.domain}",
                test_type=TestType.FUNCTIONAL,
                category="Search",
                description=f"Verify search functionality is accessible and returns relevant results. Search is a key feature for user navigation and content discovery on the website.",
                severity=Severity.P2,
                url=url
            ))
        else:
            tests.append(TestCase(
                test_id=f"FUNC-400-{company.domain}",
                test_type=TestType.FUNCTIONAL,
                category="Search",
                description=f"Verify if search functionality would benefit the site. For content-rich sites, search improves user experience and content discoverability.",
                severity=Severity.P3,
                url=url
            ))
        
        # Site-specific tests
        if structure.site_type == "e-commerce":
            tests.append(TestCase(
                test_id=f"FUNC-500-{company.domain}",
                test_type=TestType.FUNCTIONAL,
                category="E-commerce",
                description="Verify shopping cart functionality is accessible and functional. Users should be able to add items, view cart contents, and proceed to checkout without errors.",
                severity=Severity.P1,
                url=url
            ))
            tests.append(TestCase(
                test_id=f"FUNC-501-{company.domain}",
                test_type=TestType.FUNCTIONAL,
                category="E-commerce",
                description="Verify checkout process is accessible and secure. The checkout flow should be intuitive, secure, and handle payment processing correctly.",
                severity=Severity.P1,
                url=url
            ))
            tests.append(TestCase(
                test_id=f"FUNC-502-{company.domain}",
                test_type=TestType.FUNCTIONAL,
                category="E-commerce",
                description="Verify product pages display essential information including price, description, images, and availability. Product information is critical for purchase decisions.",
                severity=Severity.P1,
                url=url
            ))
        
        elif structure.site_type == "saas":
            tests.append(TestCase(
                test_id=f"FUNC-600-{company.domain}",
                test_type=TestType.FUNCTIONAL,
                category="Authentication",
                description="Verify login page is accessible and functional. Users should be able to authenticate securely to access their accounts and services.",
                severity=Severity.P1,
                url=url
            ))
            tests.append(TestCase(
                test_id=f"FUNC-601-{company.domain}",
                test_type=TestType.FUNCTIONAL,
                category="Authentication",
                description="Verify sign-up/registration process is functional. New users should be able to create accounts with proper validation and confirmation.",
                severity=Severity.P1,
                url=url
            ))
            tests.append(TestCase(
                test_id=f"FUNC-602-{company.domain}",
                test_type=TestType.FUNCTIONAL,
                category="Dashboard",
                description="Verify dashboard or main application interface is accessible after login. Users should have access to core features and functionality.",
                severity=Severity.P1,
                url=url
            ))
        
        else:
            # Generic corporate/marketing site tests
            tests.append(TestCase(
                test_id=f"FUNC-700-{company.domain}",
                test_type=TestType.FUNCTIONAL,
                category="Contact",
                description="Verify contact form or contact information is accessible. Users should be able to reach out to the company through provided contact methods.",
                severity=Severity.P2,
                url=url
            ))
            tests.append(TestCase(
                test_id=f"FUNC-701-{company.domain}",
                test_type=TestType.FUNCTIONAL,
                category="Content",
                description="Verify main content sections are present and readable. Key information about the company, services, or products should be clearly displayed.",
                severity=Severity.P1,
                url=url
            ))
        
        # Additional functional tests
        tests.append(TestCase(
            test_id=f"FUNC-800-{company.domain}",
            test_type=TestType.FUNCTIONAL,
            category="JavaScript",
            description=f"Verify JavaScript functionality works correctly on {url}. Interactive elements, animations, and dynamic content should function as expected without errors.",
            severity=Severity.P2,
            url=url
        ))
        
        tests.append(TestCase(
            test_id=f"FUNC-801-{company.domain}",
            test_type=TestType.FUNCTIONAL,
            category="Images",
            description=f"Verify images on {url} load correctly and display properly. Broken or missing images degrade user experience and site credibility.",
            severity=Severity.P2,
            url=url
        ))
        
        tests.append(TestCase(
            test_id=f"FUNC-802-{company.domain}",
            test_type=TestType.FUNCTIONAL,
            category="Error Handling",
            description=f"Verify error pages (404, 500, etc.) are properly handled with user-friendly messages. Good error handling improves user experience when issues occur.",
            severity=Severity.P2,
            url=url
        ))
        
        return tests
    
    def _generate_accessibility_tests(self, url: str, company: CompanyData) -> List[TestCase]:
        """Generate accessibility tests - at least 10 comprehensive tests"""
        return [
            TestCase(
                test_id=f"A11Y-001-{company.domain}",
                test_type=TestType.ACCESSIBILITY,
                category="WCAG Compliance",
                description=f"Check if the website meets accessibility standards. If accessibility is poor, people with disabilities cannot use the site, which may violate legal requirements and exclude potential customers.",
                severity=Severity.P1,
                url=url
            ),
            TestCase(
                test_id=f"A11Y-002-{company.domain}",
                test_type=TestType.ACCESSIBILITY,
                category="Images",
                description=f"Check if images have alt text. Without alt text, screen reader users cannot understand what images show, making the site unusable for visually impaired users.",
                severity=Severity.P1,
                url=url
            ),
            TestCase(
                test_id=f"A11Y-003-{company.domain}",
                test_type=TestType.ACCESSIBILITY,
                category="Keyboard Navigation",
                description=f"Verify keyboard navigation works throughout {url}. All interactive elements should be accessible via keyboard (Tab, Enter, Arrow keys). Users who cannot use a mouse rely on keyboard navigation for site interaction.",
                severity=Severity.P1,
                url=url
            ),
            TestCase(
                test_id=f"A11Y-004-{company.domain}",
                test_type=TestType.ACCESSIBILITY,
                category="Color Contrast",
                description=f"Verify text and background color contrast ratios meet WCAG AA standards (4.5:1 for normal text, 3:1 for large text) on {url}. Sufficient contrast ensures text is readable for users with visual impairments or color vision deficiencies.",
                severity=Severity.P1,
                url=url
            ),
            TestCase(
                test_id=f"A11Y-005-{company.domain}",
                test_type=TestType.ACCESSIBILITY,
                category="Headings",
                description=f"Verify heading hierarchy (h1, h2, h3, etc.) is properly structured and logical on {url}. Correct heading structure helps screen reader users navigate and understand page organization.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"A11Y-006-{company.domain}",
                test_type=TestType.ACCESSIBILITY,
                category="Form Labels",
                description=f"Verify all form inputs on {url} have associated labels. Proper labeling ensures screen reader users understand what information is required in each form field.",
                severity=Severity.P1,
                url=url
            ),
            TestCase(
                test_id=f"A11Y-007-{company.domain}",
                test_type=TestType.ACCESSIBILITY,
                category="ARIA Attributes",
                description=f"Verify ARIA (Accessible Rich Internet Applications) attributes are used correctly on {url} where needed. ARIA attributes enhance accessibility for dynamic content and complex widgets.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"A11Y-008-{company.domain}",
                test_type=TestType.ACCESSIBILITY,
                category="Focus Indicators",
                description=f"Verify all interactive elements have visible focus indicators on {url}. Clear focus indicators help keyboard users understand which element is currently active.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"A11Y-009-{company.domain}",
                test_type=TestType.ACCESSIBILITY,
                category="Link Purpose",
                description=f"Verify link text clearly indicates the link's purpose or destination on {url}. Descriptive link text helps all users, especially screen reader users who navigate by links, understand where links lead.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"A11Y-010-{company.domain}",
                test_type=TestType.ACCESSIBILITY,
                category="Language Declaration",
                description=f"Verify page language is declared using HTML lang attribute on {url}. Language declaration helps screen readers pronounce content correctly and improves overall accessibility.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"A11Y-011-{company.domain}",
                test_type=TestType.ACCESSIBILITY,
                category="Skip Links",
                description=f"Verify skip navigation links are present and functional on {url}. Skip links allow keyboard users to bypass repetitive navigation and jump to main content quickly.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"A11Y-012-{company.domain}",
                test_type=TestType.ACCESSIBILITY,
                category="Error Messages",
                description=f"Verify form error messages are clearly associated with form fields and provide actionable guidance on {url}. Accessible error messages help users understand and correct input errors.",
                severity=Severity.P2,
                url=url
            )
        ]
    
    def _generate_performance_tests(self, url: str, company: CompanyData) -> List[TestCase]:
        """Generate performance tests - at least 10 comprehensive tests"""
        return [
            TestCase(
                test_id=f"PERF-001-{company.domain}",
                test_type=TestType.PERFORMANCE,
                category="Page Load",
                description=f"Measure complete page load time for {url}, including all resources (HTML, CSS, JavaScript, images). Fast page load times are critical for user experience, SEO ranking, and conversion rates. Target: under 3 seconds.",
                severity=Severity.P1,
                url=url
            ),
            TestCase(
                test_id=f"PERF-002-{company.domain}",
                test_type=TestType.PERFORMANCE,
                category="Core Web Vitals - LCP",
                description=f"Measure Largest Contentful Paint (LCP) for {url}. LCP measures loading performance and represents when the largest content element becomes visible. Good LCP scores (under 2.5s) indicate fast perceived load time.",
                severity=Severity.P1,
                url=url
            ),
            TestCase(
                test_id=f"PERF-003-{company.domain}",
                test_type=TestType.PERFORMANCE,
                category="Core Web Vitals - CLS",
                description=f"Measure Cumulative Layout Shift (CLS) for {url}. CLS quantifies visual stability by measuring unexpected layout shifts during page load. Low CLS scores (under 0.1) ensure content doesn't shift unexpectedly, improving user experience.",
                severity=Severity.P1,
                url=url
            ),
            TestCase(
                test_id=f"PERF-004-{company.domain}",
                test_type=TestType.PERFORMANCE,
                category="Core Web Vitals - INP",
                description=f"Measure Interaction to Next Paint (INP) for {url}. INP assesses responsiveness by measuring the time from user interaction to visual feedback. Good INP scores (under 200ms) ensure responsive user interactions.",
                severity=Severity.P1,
                url=url
            ),
            TestCase(
                test_id=f"PERF-005-{company.domain}",
                test_type=TestType.PERFORMANCE,
                category="Network Requests",
                description=f"Analyze total number of network requests made by {url}. Excessive requests increase load time and server load. Optimizing request count improves performance and reduces bandwidth usage.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"PERF-006-{company.domain}",
                test_type=TestType.PERFORMANCE,
                category="Payload Size",
                description=f"Measure total page payload size (HTML, CSS, JS, images) for {url}. Large payloads slow down page loads, especially on mobile networks. Target: under 5MB total payload.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"PERF-007-{company.domain}",
                test_type=TestType.PERFORMANCE,
                category="Time to First Byte",
                description=f"Measure Time to First Byte (TTFB) for {url}. TTFB indicates server response time and network latency. Fast TTFB (under 600ms) ensures quick initial response and better user experience.",
                severity=Severity.P1,
                url=url
            ),
            TestCase(
                test_id=f"PERF-008-{company.domain}",
                test_type=TestType.PERFORMANCE,
                category="First Contentful Paint",
                description=f"Measure First Contentful Paint (FCP) for {url}. FCP measures when the first text or image is rendered, indicating perceived performance. Fast FCP (under 1.8s) improves user perception of site speed.",
                severity=Severity.P1,
                url=url
            ),
            TestCase(
                test_id=f"PERF-009-{company.domain}",
                test_type=TestType.PERFORMANCE,
                category="JavaScript Execution",
                description=f"Analyze JavaScript execution time and blocking scripts on {url}. Heavy or blocking JavaScript delays page interactivity. Optimized JS improves time to interactive and user experience.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"PERF-010-{company.domain}",
                test_type=TestType.PERFORMANCE,
                category="Image Optimization",
                description=f"Verify images on {url} are optimized (proper format, compression, sizing). Unoptimized images significantly impact load times. Modern formats (WebP, AVIF) and proper sizing reduce payload without quality loss.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"PERF-011-{company.domain}",
                test_type=TestType.PERFORMANCE,
                category="Caching",
                description=f"Verify appropriate caching headers are set for static resources on {url}. Proper caching reduces server load and improves repeat visit performance by serving cached content.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"PERF-012-{company.domain}",
                test_type=TestType.PERFORMANCE,
                category="Resource Compression",
                description=f"Verify text resources (HTML, CSS, JS) are compressed (gzip/brotli) on {url}. Compression reduces transfer size and improves load times, especially for text-based resources.",
                severity=Severity.P2,
                url=url
            )
        ]
    
    def _generate_uiux_tests(self, url: str, company: CompanyData) -> List[TestCase]:
        """Generate UI/UX tests - at least 10 comprehensive tests"""
        return [
            TestCase(
                test_id=f"UIUX-001-{company.domain}",
                test_type=TestType.UIUX,
                category="Layout",
                description=f"Check for layout and alignment issues on {url}, including overlapping elements, misaligned content, and inconsistent spacing. Proper layout ensures professional appearance and readability.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"UIUX-002-{company.domain}",
                test_type=TestType.UIUX,
                category="Responsive Design",
                description=f"Verify responsive design works correctly across multiple viewport sizes (desktop, tablet, mobile) on {url}. Responsive design ensures optimal user experience on all devices.",
                severity=Severity.P1,
                url=url
            ),
            TestCase(
                test_id=f"UIUX-003-{company.domain}",
                test_type=TestType.UIUX,
                category="Image Relevance",
                description=f"Check image relevance and appropriateness for {url}'s content and domain. Images should be contextually relevant and support the page's message and brand identity.",
                severity=Severity.P3,
                url=url
            ),
            TestCase(
                test_id=f"UIUX-004-{company.domain}",
                test_type=TestType.UIUX,
                category="Typography",
                description=f"Verify typography is consistent, readable, and properly sized on {url}. Good typography improves readability and user experience across all devices and user preferences.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"UIUX-005-{company.domain}",
                test_type=TestType.UIUX,
                category="Color Scheme",
                description=f"Verify color scheme is consistent and provides sufficient contrast on {url}. Consistent colors reinforce brand identity while ensuring readability and accessibility.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"UIUX-006-{company.domain}",
                test_type=TestType.UIUX,
                category="Button Design",
                description=f"Verify buttons and interactive elements are clearly identifiable and appropriately sized on {url}. Well-designed buttons improve usability and guide user actions effectively.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"UIUX-007-{company.domain}",
                test_type=TestType.UIUX,
                category="Content Hierarchy",
                description=f"Verify content hierarchy is clear with proper use of headings, spacing, and visual weight on {url}. Clear hierarchy guides users through content and improves comprehension.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"UIUX-008-{company.domain}",
                test_type=TestType.UIUX,
                category="White Space",
                description=f"Verify appropriate use of white space and padding on {url}. Adequate white space improves readability, reduces visual clutter, and creates a professional appearance.",
                severity=Severity.P3,
                url=url
            ),
            TestCase(
                test_id=f"UIUX-009-{company.domain}",
                test_type=TestType.UIUX,
                category="Mobile Usability",
                description=f"Verify mobile-specific usability features on {url}, including touch targets (minimum 44x44px), readable text without zooming, and mobile-friendly navigation. Mobile usability is critical as mobile traffic continues to grow.",
                severity=Severity.P1,
                url=url
            ),
            TestCase(
                test_id=f"UIUX-010-{company.domain}",
                test_type=TestType.UIUX,
                category="Visual Consistency",
                description=f"Verify visual consistency across {url}, including consistent styling, spacing, fonts, and component design. Consistency creates a cohesive user experience and reinforces brand identity.",
                severity=Severity.P2,
                url=url
            ),
            TestCase(
                test_id=f"UIUX-011-{company.domain}",
                test_type=TestType.UIUX,
                category="Loading States",
                description=f"Verify loading states and transitions are smooth and informative on {url}. Good loading indicators improve perceived performance and user experience during content loading.",
                severity=Severity.P3,
                url=url
            ),
            TestCase(
                test_id=f"UIUX-012-{company.domain}",
                test_type=TestType.UIUX,
                category="Content Readability",
                description=f"Verify content is readable with appropriate line length, line height, and paragraph spacing on {url}. Good readability ensures users can easily consume and understand content.",
                severity=Severity.P2,
                url=url
            )
        ]

