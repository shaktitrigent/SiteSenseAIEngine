"""
HTML report generator
"""

from pathlib import Path
from typing import List, Dict, Any
from jinja2 import Template
import logging
from datetime import datetime

from src.models import TestResult, TestType, Severity

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
        Generate a single consolidated HTML report combining Functional and Accessibility results
        
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
        accessibility_results = [r for r in results if r.test_type == TestType.ACCESSIBILITY]
        
        # Combine all results for consolidated report
        all_results = functional_results + accessibility_results
        
        if not all_results:
            logger.warning(f"No results to generate report for {domain}")
            return
        
        # Calculate totals
        functional_total = total_test_counts.get('functional', len(functional_results)) if total_test_counts else len(functional_results)
        accessibility_total = total_test_counts.get('accessibility', len(accessibility_results)) if total_test_counts else len(accessibility_results)
        total_identified = functional_total + accessibility_total
        total_executed = len(all_results)
        
        # Generate single consolidated report
        html_file = self._generate_consolidated_report(
            company_name, domain, functional_results, accessibility_results, 
            domain_dir, total_identified=total_identified, total_executed=total_executed
        )
    
    def _generate_consolidated_report(self, company_name: str, domain: str,
                                     functional_results: List[TestResult],
                                     accessibility_results: List[TestResult],
                                     domain_dir: Path,
                                     total_identified: int = None, total_executed: int = None) -> Path:
        """
        Generate a single consolidated report combining Functional and Accessibility results
        
        Args:
            company_name: Company name
            domain: Domain name
            functional_results: List of Functional TestResult objects
            accessibility_results: List of Accessibility TestResult objects
            domain_dir: Directory for domain-specific reports
            total_identified: Total number of test cases identified
            total_executed: Total number of test cases executed
            
        Returns:
            Path to generated HTML file
        """
        # Combine all results
        all_results = functional_results + accessibility_results
        
        # Calculate statistics for combined results
        stats = self._calculate_stats(all_results)
        stats['total_identified'] = total_identified or len(all_results)
        stats['total_executed'] = total_executed or len(all_results)
        
        # Copy logo to report directory and get path
        logo_path = self._copy_logo_to_report_dir(domain_dir)
        
        # Generate consolidated executive summary
        executive_summary = self._generate_consolidated_executive_summary(
            functional_results, accessibility_results, stats, total_identified, total_executed
        )
        
        # Get sales email from config
        sales_email = self.config.get('reporting', {}).get('sales_email', 'sales@trigent.com')
        
        # Calculate severity breakdown by category for table
        severity_by_category = self._calculate_severity_by_category(functional_results, accessibility_results)
        
        # Calculate Test Execution Summary by Severity table data
        execution_summary = self._calculate_execution_summary(functional_results, accessibility_results)
        
        # Order results: FAILED first, then PASSED
        all_results_ordered = sorted(all_results, key=lambda r: (r.status.value != 'fail', r.test_id))
        
        # Prepare template data
        template_data = {
            'company_name': company_name,
            'domain': domain,
            'stats': stats,
            'functional_results': functional_results,
            'accessibility_results': accessibility_results,
            'all_results': all_results_ordered,
            'logo_path': logo_path,
            'executive_summary': executive_summary,
            'sales_email': sales_email,
            'severity_by_category': severity_by_category,
            'execution_summary': execution_summary
        }
        
        # Render consolidated template
        html_content = self._render_consolidated_template(template_data)
        
        # Save file with new naming convention: <CompanyName>-Report-<YYYY-MM-DD>.html
        company_safe = self._sanitize_company_name(company_name)
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"{company_safe}-Report-{date_str}.html"
        filepath = domain_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Generated consolidated report: {filepath}")
        return filepath
    
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
        
        # Generate executive summary data
        executive_summary = self._generate_executive_summary(results, stats, report_type)
        
        # Group failures into patterns
        failure_patterns = self._group_failures_into_patterns(results)
        
        # Prepare data for template
        template_data = {
            'company_name': company_name,
            'domain': domain,
            'report_type': report_type,
            'stats': stats,
            'results': results,
            'p1_failures': [r for r in results if r.severity.value == 'P1' and r.status.value == 'fail'],
            'logo_path': logo_path,
            'executive_summary': executive_summary,
            'failure_patterns': failure_patterns,
            'additional_coverage': self._get_additional_coverage_areas(report_type)
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
    
    def _sanitize_company_name(self, company_name: str) -> str:
        """
        Sanitize company name for use in file names
        
        Args:
            company_name: Company name string
            
        Returns:
            Sanitized company name safe for file system
        """
        # Replace invalid characters with nothing or safe alternatives
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        sanitized = company_name
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '')
        # Replace spaces with nothing (for cleaner filenames)
        sanitized = sanitized.replace(' ', '')
        # Remove multiple consecutive spaces
        while '  ' in sanitized:
            sanitized = sanitized.replace('  ', ' ')
        return sanitized.strip()
    
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
    
    def _calculate_severity_by_category(self, functional_results: List[TestResult],
                                        accessibility_results: List[TestResult]) -> Dict[str, Dict[str, int]]:
        """
        Calculate severity breakdown by category (Functional vs Accessibility)
        
        Returns:
            Dictionary with structure:
            {
                'P1': {'total': N, 'functional': N, 'accessibility': N},
                'P2': {'total': N, 'functional': N, 'accessibility': N},
                'P3': {'total': N, 'functional': N, 'accessibility': N},
                'Passed': {'total': N, 'functional': N, 'accessibility': N}
            }
        """
        breakdown = {
            'P1': {'total': 0, 'functional': 0, 'accessibility': 0},
            'P2': {'total': 0, 'functional': 0, 'accessibility': 0},
            'P3': {'total': 0, 'functional': 0, 'accessibility': 0},
            'Passed': {'total': 0, 'functional': 0, 'accessibility': 0}
        }
        
        # Count functional results by severity
        for result in functional_results:
            if result.status.value == 'pass':
                breakdown['Passed']['total'] += 1
                breakdown['Passed']['functional'] += 1
            else:
                severity = result.severity.value
                if severity in breakdown:
                    breakdown[severity]['total'] += 1
                    breakdown[severity]['functional'] += 1
        
        # Count accessibility results by severity
        for result in accessibility_results:
            if result.status.value == 'pass':
                breakdown['Passed']['total'] += 1
                breakdown['Passed']['accessibility'] += 1
            else:
                severity = result.severity.value
                if severity in breakdown:
                    breakdown[severity]['total'] += 1
                    breakdown[severity]['accessibility'] += 1
        
        return breakdown
    
    def _calculate_execution_summary(self, functional_results: List[TestResult],
                                    accessibility_results: List[TestResult]) -> Dict[str, Dict[str, int]]:
        """
        Calculate Test Execution Summary by Severity table data
        
        Returns:
            Dictionary with structure:
            {
                'Curated Test Cases Executed': {'functional': N, 'accessibility': N, 'total': N},
                'Test Passed': {'functional': N, 'accessibility': N, 'total': N},
                'Test Failed': {'functional': N, 'accessibility': N, 'total': N},
                'Critical Failure': {'functional': N, 'accessibility': N, 'total': N},
                'Major Failure': {'functional': N, 'accessibility': N, 'total': N},
                'Minor Failure': {'functional': N, 'accessibility': N, 'total': N}
            }
        """
        summary = {
            'Curated Test Cases Executed': {'functional': 0, 'accessibility': 0, 'total': 0},
            'Test Passed': {'functional': 0, 'accessibility': 0, 'total': 0},
            'Test Failed': {'functional': 0, 'accessibility': 0, 'total': 0},
            'Critical Failure': {'functional': 0, 'accessibility': 0, 'total': 0},
            'Major Failure': {'functional': 0, 'accessibility': 0, 'total': 0},
            'Minor Failure': {'functional': 0, 'accessibility': 0, 'total': 0}
        }
        
        # Count functional results
        func_total = len(functional_results)
        func_passed = sum(1 for r in functional_results if r.status.value == 'pass')
        func_failed = sum(1 for r in functional_results if r.status.value == 'fail')
        func_p1 = sum(1 for r in functional_results if r.status.value == 'fail' and r.severity.value == 'P1')
        func_p2 = sum(1 for r in functional_results if r.status.value == 'fail' and r.severity.value == 'P2')
        func_p3 = sum(1 for r in functional_results if r.status.value == 'fail' and r.severity.value == 'P3')
        
        # Count accessibility results
        a11y_total = len(accessibility_results)
        a11y_passed = sum(1 for r in accessibility_results if r.status.value == 'pass')
        a11y_failed = sum(1 for r in accessibility_results if r.status.value == 'fail')
        a11y_p1 = sum(1 for r in accessibility_results if r.status.value == 'fail' and r.severity.value == 'P1')
        a11y_p2 = sum(1 for r in accessibility_results if r.status.value == 'fail' and r.severity.value == 'P2')
        a11y_p3 = sum(1 for r in accessibility_results if r.status.value == 'fail' and r.severity.value == 'P3')
        
        # Populate summary
        summary['Curated Test Cases Executed'] = {
            'functional': func_total,
            'accessibility': a11y_total,
            'total': func_total + a11y_total
        }
        summary['Test Passed'] = {
            'functional': func_passed,
            'accessibility': a11y_passed,
            'total': func_passed + a11y_passed
        }
        summary['Test Failed'] = {
            'functional': func_failed,
            'accessibility': a11y_failed,
            'total': func_failed + a11y_failed
        }
        summary['Critical Failure'] = {
            'functional': func_p1,
            'accessibility': a11y_p1,
            'total': func_p1 + a11y_p1
        }
        summary['Major Failure'] = {
            'functional': func_p2,
            'accessibility': a11y_p2,
            'total': func_p2 + a11y_p2
        }
        summary['Minor Failure'] = {
            'functional': func_p3,
            'accessibility': a11y_p3,
            'total': func_p3 + a11y_p3
        }
        
        return summary
    
    def _generate_consolidated_executive_summary(self, functional_results: List[TestResult],
                                                 accessibility_results: List[TestResult],
                                                 stats: Dict[str, Any],
                                                 total_identified: int, total_executed: int) -> Dict[str, Any]:
        """
        Generate consolidated executive summary combining Functional and Accessibility data
        
        Args:
            functional_results: List of Functional test results
            accessibility_results: List of Accessibility test results
            stats: Combined statistics dictionary
            total_identified: Total test cases identified
            total_executed: Total test cases executed
            
        Returns:
            Dictionary with consolidated executive summary data
        """
        p1_failures = stats['severity']['p1']
        p2_failures = stats['severity']['p2']
        total_failures = stats['failed']
        
        # Calculate failures by category
        accessibility_failures = sum(1 for r in accessibility_results if r.status.value == 'fail')
        functional_failures = sum(1 for r in functional_results if r.status.value == 'fail')
        
        # Calculate user impact level
        if p1_failures >= 3:
            user_impact = "High"
        elif p1_failures >= 1 or total_failures >= 5:
            user_impact = "Medium"
        else:
            user_impact = "Low"
        
        # Calculate overall risk level (combining functional and accessibility)
        if p1_failures >= 3:
            overall_risk = "High"
        elif p1_failures >= 1 or total_failures >= 5:
            overall_risk = "Medium"
        else:
            overall_risk = "Low"
        
        # Generate smart conditional messaging
        execution_message = self._generate_execution_message(
            total_executed, accessibility_failures, functional_failures
        )
        
        return {
            'critical_issues': p1_failures,
            'user_impact': user_impact,
            'overall_risk': overall_risk,
            'total_failures': total_failures,
            'accessibility_failures': accessibility_failures,
            'functional_failures': functional_failures,
            'execution_message': execution_message,
            'pass_rate': stats['pass_rate'],
            'total_identified': total_identified,
            'total_executed': total_executed
        }
    
    def _generate_execution_message(self, total_executed: int, 
                                   accessibility_failures: int, 
                                   functional_failures: int) -> str:
        """
        Generate smart conditional execution message based on failure patterns
        
        Args:
            total_executed: Total number of executed test cases
            accessibility_failures: Number of accessibility failures
            functional_failures: Number of functional failures
            
        Returns:
            Formatted message string
        """
        # Case 4: No failures (All Pass)
        if accessibility_failures == 0 and functional_failures == 0:
            return f"A total of <strong>{total_executed}</strong> high-priority test cases were identified and executed as part of this assessment. All executed test cases passed successfully. The Risk Dashboard below provides an at-a-glance view of the overall risk posture, followed by detailed pass/fail results for each executed test case across Functional and Accessibility categories."
        
        # Case 1: Both Functional and Accessibility failures exist
        if accessibility_failures > 0 and functional_failures > 0:
            return f"A total of <strong>{total_executed}</strong> high-priority test cases were identified and executed as part of this assessment. Of these, <strong>{accessibility_failures}</strong> accessibility and <strong>{functional_failures}</strong> functional test cases resulted in failures, while the remaining test cases passed successfully. The Risk Dashboard below provides an at-a-glance view of the overall risk posture, followed by detailed pass/fail results for each executed test case across Functional and Accessibility categories."
        
        # Case 2: ONLY Accessibility failures exist
        if accessibility_failures > 0 and functional_failures == 0:
            return f"A total of <strong>{total_executed}</strong> high-priority test cases were identified and executed as part of this assessment. Of these, <strong>{accessibility_failures}</strong> accessibility test cases resulted in failures. All functional tests passed successfully. The Risk Dashboard below provides an at-a-glance view of the overall risk posture, followed by detailed pass/fail results for each executed test case across Functional and Accessibility categories."
        
        # Case 3: ONLY Functional failures exist
        if functional_failures > 0 and accessibility_failures == 0:
            return f"A total of <strong>{total_executed}</strong> high-priority test cases were identified and executed as part of this assessment. Of these, <strong>{functional_failures}</strong> functional test cases resulted in failures. All accessibility tests passed successfully. The Risk Dashboard below provides an at-a-glance view of the overall risk posture, followed by detailed pass/fail results for each executed test case across Functional and Accessibility categories."
        
        # Fallback (should not reach here)
        return f"A total of <strong>{total_executed}</strong> high-priority test cases were identified and executed as part of this assessment. The Risk Dashboard below provides an at-a-glance view of the overall risk posture, followed by detailed pass/fail results for each executed test case across Functional and Accessibility categories."
    
    def _generate_executive_summary(self, results: List[TestResult], stats: Dict[str, Any], 
                                   report_type: str) -> Dict[str, Any]:
        """
        Generate executive summary data for the report
        
        Args:
            results: List of test results
            stats: Statistics dictionary
            report_type: Type of report
            
        Returns:
            Dictionary with executive summary data
        """
        p1_failures = stats['severity']['p1']
        p2_failures = stats['severity']['p2']
        total_failures = stats['failed']
        
        # Calculate user impact level
        if p1_failures >= 3:
            user_impact = "High"
        elif p1_failures >= 1 or total_failures >= 5:
            user_impact = "Medium"
        else:
            user_impact = "Low"
        
        # Calculate accessibility risk level (for accessibility reports)
        if report_type == "Accessibility":
            if p1_failures >= 2:
                accessibility_risk = "High"
            elif p1_failures >= 1 or total_failures >= 3:
                accessibility_risk = "Medium"
            else:
                accessibility_risk = "Low"
        else:
            accessibility_risk = "N/A"
        
        # Generate business impact description
        business_impact = self._generate_business_impact_description(results, stats, report_type)
        
        return {
            'critical_issues': p1_failures,
            'user_impact': user_impact,
            'accessibility_risk': accessibility_risk,
            'business_impact': business_impact,
            'total_failures': total_failures,
            'pass_rate': stats['pass_rate']
        }
    
    def _generate_business_impact_description(self, results: List[TestResult], 
                                              stats: Dict[str, Any], report_type: str) -> str:
        """Generate business impact description based on failures"""
        p1_failures = stats['severity']['p1']
        p2_failures = stats['severity']['p2']
        total_failures = stats['failed']
        
        impacts = []
        
        if report_type == "Accessibility":
            if p1_failures > 0:
                impacts.append("potential legal and compliance exposure under ADA and WCAG requirements")
                impacts.append("exclusion of users with disabilities from accessing your digital services")
            if total_failures > 0:
                impacts.append("reduced market reach and potential loss of customers who rely on assistive technologies")
        
        if report_type == "Functional":
            if p1_failures > 0:
                impacts.append("user frustration and potential abandonment of critical user journeys")
                impacts.append("direct impact on conversion rates and revenue")
            if p2_failures > 0:
                impacts.append("degraded user experience that may affect brand perception")
        
        if not impacts:
            return "The identified issues, while present, are contained and manageable with proper prioritization."
        
        return f"If these issues remain unresolved, they may result in: {', '.join(impacts)}. Early remediation reduces technical debt and prevents user experience degradation."
    
    def _group_failures_into_patterns(self, results: List[TestResult]) -> List[Dict[str, Any]]:
        """
        Group similar failures into patterns for executive presentation
        
        Args:
            results: List of test results
            
        Returns:
            List of failure pattern dictionaries
        """
        failed_results = [r for r in results if r.status.value == 'fail']
        
        if not failed_results:
            return []
        
        # Group by category and severity
        patterns = {}
        
        for result in failed_results:
            key = f"{result.category}_{result.severity.value}"
            
            if key not in patterns:
                patterns[key] = {
                    'issue_name': self._get_issue_name(result.category),
                    'category': result.category,
                    'severity': result.severity.value,
                    'affected_areas': [],
                    'count': 0,
                    'examples': [],
                    'business_impact': self._get_business_impact_for_category(result.category, result.severity),
                    'ai_insight': self._get_ai_insight(result.category, result)
                }
            
            patterns[key]['count'] += 1
            patterns[key]['affected_areas'].append(result.url)
            
            # Keep up to 2 examples
            if len(patterns[key]['examples']) < 2:
                patterns[key]['examples'].append({
                    'test_id': result.test_id,
                    'url': result.url,
                    'summary': result.summary
                })
        
        # Convert to list and sort by severity (P1 first), then count
        pattern_list = list(patterns.values())
        pattern_list.sort(key=lambda x: (x['severity'] == 'P1', -x['count']), reverse=True)
        
        # Deduplicate affected areas
        for pattern in pattern_list:
            pattern['affected_areas'] = list(set(pattern['affected_areas']))
            pattern['affected_count'] = len(pattern['affected_areas'])
        
        return pattern_list
    
    def _get_issue_name(self, category: str) -> str:
        """Get executive-friendly issue name from category"""
        name_map = {
            'WCAG Compliance': 'Accessibility Compliance Gaps',
            'Keyboard Navigation': 'Keyboard Accessibility Issues',
            'Color Contrast': 'Visual Accessibility Barriers',
            'Images': 'Image Accessibility Gaps',
            'Form Labels': 'Form Accessibility Issues',
            'Navigation': 'Navigation Functionality Issues',
            'Form Validation': 'Form Reliability Concerns',
            'CTA': 'Conversion Path Obstacles',
            'Links': 'Link Integrity Issues',
            'E-commerce': 'E-commerce Flow Disruptions',
            'Authentication': 'Authentication Flow Issues'
        }
        return name_map.get(category, category)
    
    def _get_business_impact_for_category(self, category: str, severity: Severity) -> str:
        """Get business impact description for a category"""
        impacts = {
            'WCAG Compliance': 'Non-compliance may result in legal exposure and exclusion of users with disabilities, impacting market reach and brand reputation.',
            'Keyboard Navigation': 'Users who cannot use a mouse are unable to navigate effectively, leading to abandonment and potential legal concerns.',
            'Color Contrast': 'Users with visual impairments cannot read content, creating barriers to information access and engagement.',
            'Images': 'Screen reader users cannot understand visual content, reducing content accessibility and user comprehension.',
            'Navigation': 'Users cannot find or access key pages, directly impacting conversion rates and user satisfaction.',
            'Form Validation': 'Users encounter errors without clear guidance, leading to form abandonment and lost conversions.',
            'CTA': 'Critical conversion points fail, directly impacting revenue and business objectives.',
            'Links': 'Broken or inaccessible links degrade user trust and navigation experience.',
            'E-commerce': 'Shopping and checkout flows break, directly impacting revenue and customer satisfaction.',
            'Authentication': 'Users cannot access their accounts or services, blocking core functionality.'
        }
        return impacts.get(category, 'This issue may impact user experience and business objectives.')
    
    def _get_ai_insight(self, category: str, result: TestResult) -> str:
        """Generate AI insight explaining why this looks systemic"""
        violation_count = result.evidence.get('violation_count', 0)
        if violation_count > 1:
            return f"This pattern appears across multiple elements ({violation_count} instances), suggesting a systemic design or implementation issue rather than isolated occurrences."
        else:
            return "This issue has been identified through AI-driven analysis of the site's accessibility and functional patterns. The pattern suggests a consistent implementation approach that may benefit from review."
    
    def _get_additional_coverage_areas(self, report_type: str) -> List[str]:
        """Get list of additional coverage areas for 'What We Didn't Test' section"""
        if report_type == "Accessibility":
            return [
                "Cross-browser accessibility compatibility (Chrome, Firefox, Safari, Edge)",
                "Screen reader behavior with NVDA, JAWS, and VoiceOver",
                "Keyboard-only navigation flows across all interactive elements",
                "Mobile accessibility on iOS and Android devices",
                "Dynamic content accessibility (SPA interactions, AJAX updates)",
                "Form error messaging accessibility",
                "Multi-language accessibility compliance"
            ]
        elif report_type == "Functional":
            return [
                "Cross-browser functional compatibility testing",
                "Mobile device-specific functionality",
                "User journey flows across multiple pages",
                "Integration with third-party services",
                "Error handling and edge cases",
                "Data validation and security testing",
                "Performance under load conditions"
            ]
        else:
            return [
                "Additional test scenarios identified by AI analysis",
                "Edge cases and boundary conditions",
                "Integration and dependency testing"
            ]
    
    def _render_consolidated_template(self, data: Dict[str, Any]) -> str:
        """Render consolidated HTML template"""
        template_str = self._get_consolidated_template()
        template = Template(template_str)
        return template.render(**data)
    
    def _render_template(self, data: Dict[str, Any], report_type: str) -> str:
        """Render HTML template"""
        template_str = self._get_template(report_type)
        template = Template(template_str)
        return template.render(**data)
    
    def _get_consolidated_template(self) -> str:
        """Get consolidated HTML template combining Functional and Accessibility"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Powered Website Quality Assessment - {{ company_name }}</title>
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
        /* Sample Watermark */
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
            color: #1a237e;
            font-size: 32px;
            margin-bottom: 30px;
            border-bottom: 4px solid #2196F3;
            padding-bottom: 15px;
            padding-right: 60px;
        }
        h2 {
            color: #2c3e50;
            font-size: 24px;
            margin-top: 40px;
            margin-bottom: 20px;
        }
        .executive-summary {
            background: #f5f5f5;
            border-left: 4px solid #2196F3;
            padding: 25px;
            margin-bottom: 30px;
            border-radius: 4px;
            font-size: 16px;
            line-height: 1.8;
        }
        .kpi-tiles {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin: 30px 0;
        }
        .kpi-tile {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .kpi-tile.critical {
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            background-color: #e74c3c !important; /* Fallback for PDF */
        }
        .kpi-tile.medium {
            background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
            background-color: #f39c12 !important; /* Fallback for PDF */
        }
        .kpi-tile.low {
            background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
            background-color: #27ae60 !important; /* Fallback for PDF */
        }
        .kpi-tile .icon {
            font-size: 32px;
            margin-bottom: 8px;
        }
        .kpi-tile .value {
            font-size: 32px;
            font-weight: bold;
            margin: 8px 0;
        }
        .kpi-tile .label {
            font-size: 14px;
            opacity: 0.95;
            font-weight: bold;
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
        /* Compliance Context */
        .compliance-note {
            background: #fff3e0;
            border-left: 4px solid #ff9800;
            padding: 20px;
            margin: 25px 0;
            border-radius: 4px;
        }
        .compliance-note h4 {
            color: #e65100;
            margin-bottom: 10px;
            font-size: 18px;
        }
        .compliance-note p {
            margin: 10px 0;
            line-height: 1.7;
        }
        /* Severity Summary Table */
        .severity-summary-section {
            margin: 30px 0;
        }
        .severity-summary-section h3 {
            color: #2c3e50;
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        .severity-summary-section p {
            color: #7f8c8d;
            font-size: 14px;
            margin-bottom: 15px;
            line-height: 1.6;
        }
        .severity-summary-table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            background: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .severity-summary-table thead {
            background: #f8f9fa;
        }
        .severity-summary-table th {
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #2c3e50;
            border-bottom: 2px solid #dee2e6;
            font-size: 14px;
        }
        .severity-summary-table th:not(:first-child) {
            text-align: center;
        }
        .severity-summary-table td {
            padding: 12px;
            text-align: center;
            border-bottom: 1px solid #e9ecef;
            font-size: 14px;
            color: #495057;
            vertical-align: middle;
        }
        .severity-summary-table td:first-child {
            text-align: left;
        }
        .severity-summary-table tbody tr:last-child td {
            border-bottom: none;
        }
        .severity-summary-table tbody tr:hover {
            background: #f8f9fa;
        }
        .severity-summary-table .severity-label {
            text-align: left;
            font-weight: 500;
        }
        .severity-summary-table .severity-critical {
            color: #e74c3c;
            font-weight: 600;
        }
        .severity-summary-table .severity-major {
            color: #f39c12;
            font-weight: 600;
        }
        .severity-summary-table .severity-minor {
            color: #3498db;
            font-weight: 600;
        }
        .severity-summary-table .severity-passed {
            color: #4caf50;
            font-weight: 600;
        }
        /* Test Case Card Layout (REAL TABLES) - PDF Compatible with Colspan Expansion */
        .test-results-container {
            margin-top: 20px;
            width: 100%;
        }
        table.test-case-card {
            width: 100%;
            border: 2px solid #d0d0d0;
            border-collapse: collapse;
            table-layout: fixed;
            background: #ffffff;
            margin: 0 0 25px 0;
            page-break-inside: avoid;
            break-inside: avoid;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }
        table.test-case-card col.col-label {
            width: 14%;
        }
        table.test-case-card col.col-value {
            width: 36%;
        }
        table.test-case-card td {
            border: 1px solid #e0e0e0;
            padding: 12px;
            font-size: 13px;
            line-height: 1.6;
            vertical-align: top;
            word-wrap: break-word;
        }
        /* Fixed row heights for uniform cards */
        table.test-case-card tr.header-row td {
            height: 44px;
            vertical-align: middle;
            background: #f0f0f0;
            font-weight: 600;
        }
        table.test-case-card tr.metadata-row td {
            height: 44px;
            vertical-align: middle;
        }
        table.test-case-card tr.scenario-row td,
        table.test-case-card tr.summary-row td {
            height: 96px;
        }
        /* Labels */
        .cell-label {
            background: #f8f9fa;
            font-weight: 600;
            color: #495057;
            white-space: nowrap;
        }
        .cell-section-title {
            background: #f5f5f5;
            font-weight: 600;
            color: #333;
            white-space: normal;
            word-break: break-word;
            hyphens: auto;
            width: 8%;
            min-width: 8%;
            max-width: 8%;
        }
        /* Full-width content cells (use colspan=3 in HTML) */
        .cell-section-content {
            overflow: hidden;
            width: 92%;
            word-wrap: break-word;
            word-break: break-word;
            overflow-wrap: anywhere;
        }
        .test-case-section-content-wrapper {
            display: block;
            height: 96px;
            max-height: 96px;
            overflow: hidden;
            word-break: normal;
            overflow-wrap: anywhere;
            font-size: 13px;
            line-height: 1.6;
        }
        .test-case-id {
            font-weight: bold;
            color: #2c3e50;
            font-size: 13px;
        }
        .test-case-url {
            word-break: break-all;
            font-size: 13px;
        }
        .test-case-url a {
            color: #2196F3;
            text-decoration: none;
        }
        .status-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 3px;
            font-size: 13px;
            font-weight: bold;
            text-transform: uppercase;
            color: white;
        }
        .status-pass { 
            background: #28a745; 
            color: white; 
        }
        .status-fail { 
            background: #dc3545; 
            color: white; 
        }
        .severity-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 13px;
            font-weight: bold;
        }
        .severity-p1 { background: #e74c3c; color: white; }
        .severity-p2 { background: #f39c12; color: white; }
        .severity-p3 { background: #3498db; color: white; }
        .cta-section {
            margin-top: 50px;
            text-align: center;
            padding: 30px;
            background: #f5f5f5;
            border-radius: 8px;
        }
        .cta-button {
            display: inline-block;
            background: #2196F3;
            color: white;
            padding: 15px 40px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: bold;
            font-size: 18px;
            margin-top: 20px;
        }
        .cta-button:hover {
            background: #1976D2;
        }
        @media print {
            /* Consolidated report test cards (real tables) */
            table.test-case-card {
                page-break-inside: avoid !important;
                break-inside: avoid !important;
                border: 2px solid #d0d0d0 !important;
                table-layout: fixed !important;
            }
            table.test-case-card tr.header-row td { height: 44px !important; }
            table.test-case-card tr.metadata-row td { height: 44px !important; }
            table.test-case-card tr.scenario-row td,
            table.test-case-card tr.summary-row td { height: 96px !important; }
            .test-case-section-content-wrapper {
                height: 96px !important;
                max-height: 96px !important;
                overflow: hidden !important;
            }
            body { 
                background: white;
                position: relative;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }
            .container { 
                box-shadow: none;
            }
            .kpi-tile {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }
            .kpi-tile.critical {
                background-color: #e74c3c !important;
                background: #e74c3c !important;
            }
            .kpi-tile.medium {
                background-color: #f39c12 !important;
                background: #f39c12 !important;
            }
            .kpi-tile.low {
                background-color: #27ae60 !important;
                background: #27ae60 !important;
            }
            .severity-summary-table {
                page-break-inside: avoid !important;
                break-inside: avoid !important;
            }
            .severity-summary-table th,
            .severity-summary-table td {
                border: 1px solid #e9ecef !important;
            }
            .severity-summary-table thead {
                background: #f8f9fa !important;
            }
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
        
        <h1>AI Powered Quality Assessment – {{ company_name }}</h1>
        
        <h2 style="margin-top: 20px; margin-bottom: 15px; color: #495057; font-size: 20px; font-weight: 600;">Executive Summary</h2>
        
        <div class="executive-summary">
            <p>This website has been analyzed using Trigent's AI-driven QA engine, designed to identify high-priority functional and accessibility issues that may impact user experience and regulatory compliance.</p>
            <p style="margin-top: 15px;"><strong>Assessment Overview:</strong> A comprehensive test suite comprising <strong>{{ executive_summary.total_identified }}</strong> total test cases was identified to ensure complete coverage. This report summarizes results from a curated subset of high-priority test cases executed, with a focus on user experience and accessibility compliance.</p>
            <p style="margin-top: 15px;">{{ executive_summary.execution_message|safe }}</p>
        </div>
        <div class="kpi-tiles">
            <div class="kpi-tile {% if executive_summary.critical_issues >= 1 %}critical{% else %}low{% endif %}">
                <div class="icon">🚨</div>
                <div class="value">{{ executive_summary.critical_issues }}</div>
                <div class="label">Critical Issues Found</div>
            </div>
            <div class="kpi-tile {% if executive_summary.user_impact == 'High' %}critical{% elif executive_summary.user_impact == 'Medium' %}medium{% else %}low{% endif %}">
                <div class="icon">👥</div>
                <div class="value">{{ executive_summary.user_impact }}</div>
                <div class="label">User Impact Level</div>
            </div>
            <div class="kpi-tile {% if executive_summary.overall_risk == 'High' %}critical{% elif executive_summary.overall_risk == 'Medium' %}medium{% else %}low{% endif %}">
                <div class="icon">⚖️</div>
                <div class="value">{{ executive_summary.overall_risk }}</div>
                <div class="label">Overall Risk Level</div>
            </div>
        </div>
        
        <div class="header-info">
            <p><strong>Company:</strong> {{ company_name }}</p>
            <p><strong>Domain:</strong> {{ domain }}</p>
            <p><strong>Assessment Date:</strong> {{ stats.timestamp if stats.timestamp else 'N/A' }}</p>
        </div>
        
        <div class="compliance-note">
            <h4>Compliance Context</h4>
            <p><strong>WCAG 2.1 Level AA Alignment:</strong> This assessment evaluates compliance with Web Content Accessibility Guidelines (WCAG) 2.1 Level AA standards, which are widely recognized as the benchmark for digital accessibility.</p>
        </div>
        
        <div class="severity-summary-section">
            <h3>Test Execution Summary by Severity</h3>
            <p>The table below provides a consolidated breakdown of executed test cases by severity level, including distribution across Functional and Accessibility test categories.</p>
            <table class="severity-summary-table">
                <thead>
                    <tr>
                        <th>Test Execution Summary</th>
                        <th>Functional</th>
                        <th>Accessibility</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="severity-label">Curated Test Cases Executed</td>
                        <td>{{ execution_summary['Curated Test Cases Executed'].functional }}</td>
                        <td>{{ execution_summary['Curated Test Cases Executed'].accessibility }}</td>
                        <td>{{ execution_summary['Curated Test Cases Executed'].total }}</td>
                    </tr>
                    <tr>
                        <td class="severity-label severity-passed">Test Passed</td>
                        <td>{{ execution_summary['Test Passed'].functional }}</td>
                        <td>{{ execution_summary['Test Passed'].accessibility }}</td>
                        <td>{{ execution_summary['Test Passed'].total }}</td>
                    </tr>
                    <tr>
                        <td class="severity-label severity-critical">Test Failed</td>
                        <td>{{ execution_summary['Test Failed'].functional }}</td>
                        <td>{{ execution_summary['Test Failed'].accessibility }}</td>
                        <td>{{ execution_summary['Test Failed'].total }}</td>
                    </tr>
                    <tr>
                        <td class="severity-label severity-critical">Critical Failure</td>
                        <td>{{ execution_summary['Critical Failure'].functional }}</td>
                        <td>{{ execution_summary['Critical Failure'].accessibility }}</td>
                        <td>{{ execution_summary['Critical Failure'].total }}</td>
                    </tr>
                    <tr>
                        <td class="severity-label severity-major">Major Failure</td>
                        <td>{{ execution_summary['Major Failure'].functional }}</td>
                        <td>{{ execution_summary['Major Failure'].accessibility }}</td>
                        <td>{{ execution_summary['Major Failure'].total }}</td>
                    </tr>
                    <tr>
                        <td class="severity-label severity-minor">Minor Failure</td>
                        <td>{{ execution_summary['Minor Failure'].functional }}</td>
                        <td>{{ execution_summary['Minor Failure'].accessibility }}</td>
                        <td>{{ execution_summary['Minor Failure'].total }}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <h2>Detailed Test Results</h2>
        <div class="test-results-container">
            {% for result in all_results %}
            <table class="test-case-card">
                <colgroup>
                    <col class="col-label" />
                    <col class="col-value" />
                    <col class="col-label" />
                    <col class="col-value" />
                </colgroup>
                <tr class="header-row">
                    <td class="cell-label">Test Case ID</td>
                    <td><span class="test-case-id">{{ result.test_id }}</span></td>
                    <td class="cell-label">Status</td>
                    <td>
                        <span class="status-badge status-{{ result.status.value }}">
                            {{ result.status.value|upper }}
                        </span>
                    </td>
                </tr>
                <tr class="metadata-row">
                    <td class="cell-label">URL</td>
                    <td>
                        <div class="test-case-url">
                            <a href="{{ result.url }}" target="_blank" title="{{ result.url }}">{{ result.url }}</a>
                        </div>
                    </td>
                    <td class="cell-label">Severity</td>
                    <td>
                        <span class="severity-badge severity-{{ result.severity.value.lower() }}">
                            {{ result.severity.value }}
                        </span>
                    </td>
                </tr>
                <tr class="scenario-row">
                    <td class="cell-section-title">Test Scenario</td>
                    <td class="cell-section-content" colspan="3">
                        <div class="test-case-section-content-wrapper">{{ result.detailed_description }}</div>
                    </td>
                </tr>
                <tr class="summary-row">
                    <td class="cell-section-title">Result Summary</td>
                    <td class="cell-section-content" colspan="3">
                        <div class="test-case-section-content-wrapper">{{ result.summary }}</div>
                    </td>
                </tr>
            </table>
            {% endfor %}
        </div>
        
        <div class="cta-section">
            <p style="font-size: 16px; margin-bottom: 15px;">For full assessment details and technical walkthrough, contact our sales team.</p>
            <a href="mailto:{{ sales_email }}?subject=Request for Full Quality Assessment Report - {{ company_name }}" class="cta-button">Contact Sales for Full Assessment</a>
        </div>
    </div>
</body>
</html>"""
    
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
            font-size: 13px;
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
        /* Executive Summary Styles */
        .executive-summary {
            page-break-after: always;
            margin-bottom: 50px;
        }
        .executive-summary h1 {
            font-size: 32px;
            color: #1a237e;
            margin-bottom: 30px;
            border-bottom: 4px solid #2196F3;
            padding-bottom: 15px;
        }
        .executive-advisory {
            background: #f5f5f5;
            border-left: 4px solid #2196F3;
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 4px;
            font-size: 16px;
            line-height: 1.8;
            color: #333;
        }
        .kpi-tiles {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin: 30px 0;
        }
        .kpi-tile {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .kpi-tile.critical {
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
        }
        .kpi-tile.medium {
            background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
        }
        .kpi-tile.low {
            background: linear-gradient(135deg, #27ae60 0%, #229954 100%);
        }
        .kpi-tile .icon {
            font-size: 32px;
            margin-bottom: 8px;
        }
        .kpi-tile .value {
            font-size: 32px;
            font-weight: bold;
            margin: 8px 0;
        }
        .kpi-tile .label {
            font-size: 14px;
            opacity: 0.95;
            font-weight: bold;
        }
        .business-impact {
            background: #fff9e6;
            border: 2px solid #ffc107;
            border-radius: 8px;
            padding: 25px;
            margin: 30px 0;
        }
        .business-impact h3 {
            color: #856404;
            margin-bottom: 15px;
            font-size: 20px;
        }
        .business-impact p {
            font-size: 16px;
            line-height: 1.8;
            color: #333;
        }
        /* Pattern-based Failure Section */
        .failure-patterns {
            margin: 40px 0;
        }
        .pattern-card {
            background: white;
            border: 1px solid #ddd;
            border-left: 5px solid #e74c3c;
            border-radius: 6px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .pattern-card.p2 {
            border-left-color: #f39c12;
        }
        .pattern-card.p3 {
            border-left-color: #3498db;
        }
        .pattern-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .pattern-header h3 {
            color: #2c3e50;
            font-size: 22px;
            margin: 0;
        }
        .pattern-meta {
            display: flex;
            gap: 15px;
            margin-top: 15px;
        }
        .pattern-meta-item {
            font-size: 14px;
            color: #666;
        }
        .pattern-meta-item strong {
            color: #333;
        }
        .ai-insight-box {
            background: #e8f4f8;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin-top: 15px;
            border-radius: 4px;
        }
        .ai-insight-box strong {
            color: #1976D2;
        }
        /* Premium Disclaimer */
        .premium-notice {
            background: #f0f7ff;
            border: 2px solid #2196F3;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
        }
        .premium-notice h3 {
            color: #1976D2;
            margin-bottom: 10px;
            font-size: 18px;
        }
        .premium-notice p {
            color: #333;
            line-height: 1.7;
            margin: 10px 0;
        }
        /* Compliance Context */
        .compliance-note {
            background: #fff3e0;
            border-left: 4px solid #ff9800;
            padding: 20px;
            margin: 25px 0;
            border-radius: 4px;
        }
        .compliance-note h4 {
            color: #e65100;
            margin-bottom: 10px;
        }
        /* Additional Coverage Section */
        .additional-coverage {
            background: #f5f5f5;
            border-radius: 8px;
            padding: 25px;
            margin: 30px 0;
        }
        .additional-coverage h3 {
            color: #2c3e50;
            margin-bottom: 15px;
        }
        .additional-coverage ul {
            list-style: none;
            padding: 0;
        }
        .additional-coverage li {
            padding: 10px 0;
            padding-left: 25px;
            position: relative;
            color: #555;
        }
        .additional-coverage li:before {
            content: "→";
            position: absolute;
            left: 0;
            color: #3498db;
            font-weight: bold;
        }
        /* Next Steps CTA */
        .next-steps {
            page-break-before: always;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 8px;
            margin-top: 50px;
            text-align: center;
        }
        .next-steps h2 {
            color: white;
            font-size: 32px;
            margin-bottom: 20px;
            border: none;
        }
        .next-steps-content {
            background: rgba(255,255,255,0.1);
            padding: 25px;
            border-radius: 6px;
            margin: 20px 0;
            text-align: left;
        }
        .next-steps-content h4 {
            color: white;
            margin-bottom: 15px;
        }
        .next-steps-content ul {
            list-style: none;
            padding: 0;
        }
        .next-steps-content li {
            padding: 8px 0;
            padding-left: 25px;
            position: relative;
        }
        .next-steps-content li:before {
            content: "✓";
            position: absolute;
            left: 0;
            color: #4caf50;
            font-weight: bold;
        }
        .cta-button {
            display: inline-block;
            background: white;
            color: #667eea;
            padding: 15px 40px;
            border-radius: 6px;
            text-decoration: none;
            font-weight: bold;
            font-size: 18px;
            margin-top: 20px;
            transition: transform 0.2s;
        }
        .cta-button:hover {
            transform: scale(1.05);
        }
        /* Severity Distribution */
        .severity-distribution {
            display: flex;
            gap: 15px;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        .severity-item {
            flex: 1;
            min-width: 150px;
            text-align: center;
            padding: 15px;
            border-radius: 6px;
            background: #f5f5f5;
        }
        .severity-item.critical {
            background: #ffe6e6;
            border: 2px solid #e74c3c;
        }
        .severity-item.major {
            background: #fff3e0;
            border: 2px solid #f39c12;
        }
        .severity-item.minor {
            background: #e3f2fd;
            border: 2px solid #3498db;
        }
        .severity-item .count {
            font-size: 36px;
            font-weight: bold;
            margin: 10px 0;
        }
        .severity-item.critical .count { color: #e74c3c; }
        .severity-item.major .count { color: #f39c12; }
        .severity-item.minor .count { color: #3498db; }
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
    <!-- PAGE 1: EXECUTIVE SUMMARY -->
    <div class="container executive-summary">
        <div class="trigent-logo">
            <img src="{{ logo_path }}" alt="Trigent Logo" />
        </div>
        <h1>AI-Powered Website Quality Assessment – Executive Summary</h1>
        
        <div class="executive-advisory">
            <p><strong>Assessment Overview:</strong> This website has been analyzed using Trigent's AI-driven QA engine, designed to surface high-risk functional and accessibility issues that may impact user experience, conversion rates, and regulatory compliance. Our analysis focuses on identifying patterns and systemic issues rather than isolated occurrences, providing actionable insights for strategic decision-making.</p>
        </div>
        
        <div class="kpi-tiles">
            <div class="kpi-tile {% if executive_summary.critical_issues >= 3 %}critical{% elif executive_summary.critical_issues >= 1 %}medium{% else %}low{% endif %}">
                <div class="icon">🚨</div>
                <div class="value">{{ executive_summary.critical_issues }}</div>
                <div class="label">Critical Issues Found</div>
            </div>
            <div class="kpi-tile {% if executive_summary.user_impact == 'High' %}critical{% elif executive_summary.user_impact == 'Medium' %}medium{% else %}low{% endif %}">
                <div class="icon">👥</div>
                <div class="value">{{ executive_summary.user_impact }}</div>
                <div class="label">Potential User Impact</div>
            </div>
            <div class="kpi-tile {% if executive_summary.accessibility_risk == 'High' %}critical{% elif executive_summary.accessibility_risk == 'Medium' %}medium{% else %}low{% endif %}">
                <div class="icon">⚖️</div>
                <div class="value">{{ executive_summary.accessibility_risk }}</div>
                <div class="label">Accessibility Risk Level</div>
            </div>
        </div>
        
        <div class="business-impact">
            <h3>Business Impact Assessment</h3>
            <p>{{ executive_summary.business_impact }}</p>
        </div>
        
        <div class="header-info">
            <p><strong>Company:</strong> {{ company_name }}</p>
            <p><strong>Domain:</strong> {{ domain }}</p>
            <p><strong>Assessment Date:</strong> {{ stats.timestamp if stats.timestamp else 'N/A' }}</p>
        </div>
    </div>
    
    <!-- MAIN REPORT CONTENT -->
    <div class="container">
        <div class="trigent-logo">
            <img src="{{ logo_path }}" alt="Trigent Logo" />
        </div>
        <h1>{{ report_type }} Quality Assessment</h1>
        
        <div class="premium-notice">
            <h3>Assessment Scope</h3>
            <p>This report represents a curated set of high-impact scenarios identified by our AI engine. The full assessment includes broader functional, accessibility, and compliance coverage across {{ stats.total_identified }} identified test scenarios. This analysis focuses on the {{ stats.total_executed }} most critical test cases to provide actionable insights efficiently.</p>
            <p><strong>Full Coverage Available:</strong> The complete assessment includes {{ stats.total_identified - stats.total_executed }} additional test scenarios covering cross-browser compatibility, mobile responsiveness, advanced accessibility flows, and performance under load conditions.</p>
        </div>
        
        {% if report_type == "Accessibility" %}
        <div class="compliance-note">
            <h4>Compliance Context</h4>
            <p><strong>WCAG 2.1 Level AA Alignment:</strong> This assessment evaluates compliance with Web Content Accessibility Guidelines (WCAG) 2.1 Level AA standards, which are widely recognized as the benchmark for digital accessibility.</p>
            <p><strong>Legal & Regulatory Relevance:</strong> In the United States, websites are subject to accessibility requirements under the Americans with Disabilities Act (ADA) and Section 508. Non-compliance may result in legal exposure, exclusion of users with disabilities, and reduced market reach. Organizations that prioritize accessibility demonstrate commitment to inclusive design and reduce compliance risk.</p>
        </div>
        {% endif %}
        
        <div class="severity-distribution">
            <div class="severity-item critical">
                <div class="icon">🔴</div>
                <div class="count">{{ stats.severity.p1 }}</div>
                <div class="label">Critical</div>
            </div>
            <div class="severity-item major">
                <div class="icon">🟠</div>
                <div class="count">{{ stats.severity.p2 }}</div>
                <div class="label">Major</div>
            </div>
            <div class="severity-item minor">
                <div class="icon">🟡</div>
                <div class="count">{{ stats.severity.p3 }}</div>
                <div class="label">Minor</div>
            </div>
            <div class="severity-item" style="background: #e8f5e9; border: 2px solid #4caf50;">
                <div class="icon">ℹ️</div>
                <div class="count" style="color: #4caf50;">{{ stats.passed }}</div>
                <div class="label">Passed</div>
            </div>
        </div>
        
        {% if failure_patterns %}
        <div class="failure-patterns">
            <h2 style="margin-top: 40px; color: #2c3e50;">Issue Patterns Identified</h2>
            <p style="margin-bottom: 20px; color: #666; font-size: 16px;">
                The following patterns represent systemic issues identified across the site. Addressing these patterns provides broader impact than fixing isolated occurrences.
            </p>
            
            {% for pattern in failure_patterns %}
            <div class="pattern-card p{{ pattern.severity[-1] }}">
                <div class="pattern-header">
                    <h3>{{ pattern.issue_name }}</h3>
                    <span class="severity-badge severity-{{ pattern.severity.lower() }}">{{ pattern.severity }}</span>
                </div>
                <p style="font-size: 16px; line-height: 1.7; margin: 15px 0; color: #333;"><strong>Why This Matters:</strong> {{ pattern.business_impact }}</p>
                
                <div class="pattern-meta">
                    <div class="pattern-meta-item">
                        <strong>Affected Areas:</strong> {{ pattern.affected_count }} page(s)
                    </div>
                    <div class="pattern-meta-item">
                        <strong>Occurrences:</strong> {{ pattern.count }} instance(s)
                    </div>
                </div>
                
                {% if pattern.examples %}
                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #eee;">
                    <strong style="color: #666;">Example Locations:</strong>
                    <ul style="margin-top: 10px; padding-left: 20px;">
                        {% for example in pattern.examples %}
                        <li style="margin: 5px 0; color: #555;">
                            <a href="{{ example.url }}" target="_blank" style="color: #2196F3;">{{ example.url }}</a>
                            <span style="color: #999; font-size: 13px;"> – {{ example.summary[:100] }}{% if example.summary|length > 100 %}...{% endif %}</span>
                        </li>
                        {% endfor %}
                    </ul>
                </div>
                {% endif %}
                
                <div class="ai-insight-box">
                    <strong>AI Insight:</strong> {{ pattern.ai_insight }}
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <div class="additional-coverage">
            <h3>Additional Coverage Areas</h3>
            <p style="margin-bottom: 15px; color: #666;">The comprehensive assessment includes analysis of the following areas:</p>
            <ul>
                {% for area in additional_coverage %}
                <li>{{ area }}</li>
                {% endfor %}
            </ul>
        </div>
        
        <h2 style="margin-top: 40px; color: #2c3e50;">Detailed Test Results</h2>
        <p style="margin-bottom: 15px; color: #7f8c8d; font-size: 15px;">
            Detailed results for the {{ stats.total_executed }} high-impact test cases executed in this assessment. Each result indicates the issue identified and its potential impact if not addressed.
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
        
        <!-- NEXT STEPS CALL TO ACTION -->
        <div class="next-steps">
            <h2>Next Steps</h2>
            <div class="next-steps-content">
                <h4>What Happens Next</h4>
                <ul>
                    <li>Findings are mapped to real user journeys to prioritize remediation based on business impact</li>
                    <li>Technical walkthrough sessions identify root causes and implementation approaches</li>
                    <li>Automation and AI reduce long-term QA costs through continuous monitoring</li>
                    <li>Full assessment reports provide comprehensive coverage across all identified scenarios</li>
                </ul>
            </div>
            <div style="margin-top: 30px;">
                <a href="#" class="cta-button" onclick="window.print(); return false;">Request Full Report & Technical Walkthrough</a>
            </div>
            <p style="margin-top: 20px; opacity: 0.9; font-size: 14px;">
                Contact Trigent to discuss findings, remediation strategies, and comprehensive QA coverage options.
            </p>
        </div>
    </div>
    
    <script>
        // Charts removed - replaced with executive-friendly severity distribution tiles
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

