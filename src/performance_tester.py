"""
Performance testing using Playwright performance APIs
"""

import json
from typing import Dict, Any, Optional
import logging

from playwright.async_api import Page

logger = logging.getLogger(__name__)


class PerformanceTester:
    """Runs performance tests and measures Core Web Vitals"""
    
    def __init__(self, thresholds: Dict[str, Any] = None):
        """
        Initialize performance tester
        
        Args:
            thresholds: Performance thresholds dictionary
        """
        self.thresholds = thresholds or {
            'page_load_time_ms': 3000,
            'lcp_threshold_ms': 2500,
            'cls_threshold': 0.1,
            'inp_threshold_ms': 200,
            'max_requests': 100,
            'max_payload_mb': 5
        }
    
    async def run_test(self, page: Page, url: str) -> Dict[str, Any]:
        """
        Run performance test on a page
        
        Args:
            page: Playwright page object
            url: URL being tested
            
        Returns:
            Dictionary with performance metrics
        """
        try:
            # Measure page load
            response = await page.goto(url, wait_until='networkidle')
            
            # Get load time using Performance API
            load_time = await page.evaluate("""() => {
                const timing = performance.timing;
                return timing.loadEventEnd - timing.navigationStart;
            }""")
            
            # Get Core Web Vitals
            vitals = await self._get_web_vitals(page)
            
            # Get network metrics
            network_metrics = await self._get_network_metrics(page)
            
            # Calculate total payload
            total_payload_mb = network_metrics.get('total_size', 0) / (1024 * 1024) if network_metrics.get('total_size', 0) > 0 else 0
            
            # Evaluate against thresholds
            results = {
                'page_load_time_ms': load_time,
                'lcp_ms': vitals.get('lcp', 0),
                'cls': vitals.get('cls', 0),
                'inp_ms': vitals.get('inp', 0),
                'request_count': network_metrics.get('request_count', 0),
                'total_payload_mb': total_payload_mb,
                'thresholds': self.thresholds,
                'violations': []
            }
            
            # Check thresholds
            if load_time > self.thresholds['page_load_time_ms']:
                results['violations'].append({
                    'metric': 'page_load_time',
                    'value': load_time,
                    'threshold': self.thresholds['page_load_time_ms'],
                    'severity': 'P1'
                })
            
            if vitals.get('lcp', 0) > self.thresholds['lcp_threshold_ms']:
                results['violations'].append({
                    'metric': 'lcp',
                    'value': vitals.get('lcp', 0),
                    'threshold': self.thresholds['lcp_threshold_ms'],
                    'severity': 'P1'
                })
            
            if vitals.get('cls', 0) > self.thresholds['cls_threshold']:
                results['violations'].append({
                    'metric': 'cls',
                    'value': vitals.get('cls', 0),
                    'threshold': self.thresholds['cls_threshold'],
                    'severity': 'P1'
                })
            
            if network_metrics.get('request_count', 0) > self.thresholds['max_requests']:
                results['violations'].append({
                    'metric': 'request_count',
                    'value': network_metrics.get('request_count', 0),
                    'threshold': self.thresholds['max_requests'],
                    'severity': 'P2'
                })
            
            if total_payload_mb > self.thresholds['max_payload_mb']:
                results['violations'].append({
                    'metric': 'total_payload',
                    'value': total_payload_mb,
                    'threshold': self.thresholds['max_payload_mb'],
                    'severity': 'P2'
                })
            
            results['status'] = 'pass' if len(results['violations']) == 0 else 'fail'
            results['summary'] = f"Page load: {load_time}ms, LCP: {vitals.get('lcp', 0)}ms, " \
                               f"CLS: {vitals.get('cls', 0)}, Requests: {network_metrics.get('request_count', 0)}"
            
            return results
            
        except Exception as e:
            logger.error(f"Error running performance test on {url}: {e}")
            return {
                'status': 'fail',
                'error': str(e),
                'summary': f"Performance test failed: {str(e)}"
            }
    
    async def _get_web_vitals(self, page: Page) -> Dict[str, float]:
        """Get Core Web Vitals using Performance API"""
        try:
            vitals = await page.evaluate("""() => {
                return new Promise((resolve) => {
                    const vitals = {};
                    
                    // LCP (Largest Contentful Paint)
                    new PerformanceObserver((list) => {
                        const entries = list.getEntries();
                        const lastEntry = entries[entries.length - 1];
                        vitals.lcp = lastEntry.renderTime || lastEntry.loadTime;
                    }).observe({entryTypes: ['largest-contentful-paint']});
                    
                    // CLS (Cumulative Layout Shift)
                    let clsValue = 0;
                    new PerformanceObserver((list) => {
                        for (const entry of list.getEntries()) {
                            if (!entry.hadRecentInput) {
                                clsValue += entry.value;
                            }
                        }
                        vitals.cls = clsValue;
                    }).observe({entryTypes: ['layout-shift']});
                    
                    // INP (Interaction to Next Paint) - simplified
                    setTimeout(() => {
                        vitals.inp = vitals.inp || 0;
                        resolve(vitals);
                    }, 2000);
                });
            }""")
            
            return vitals
        except Exception as e:
            logger.debug(f"Error getting web vitals: {e}")
            return {'lcp': 0, 'cls': 0, 'inp': 0}
    
    async def _get_network_metrics(self, page: Page) -> Dict[str, Any]:
        """Get network request metrics"""
        try:
            metrics = await page.evaluate("""() => {
                const resources = performance.getEntriesByType('resource');
                let totalSize = 0;
                resources.forEach(resource => {
                    if (resource.transferSize) {
                        totalSize += resource.transferSize;
                    }
                });
                return {
                    request_count: resources.length,
                    total_size: totalSize
                };
            }""")
            return metrics
        except Exception as e:
            logger.debug(f"Error getting network metrics: {e}")
            return {'request_count': 0, 'total_size': 0}

