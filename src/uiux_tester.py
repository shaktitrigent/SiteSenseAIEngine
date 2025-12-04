"""
UI/UX testing for layout, alignment, and image relevance
"""

import re
from typing import List, Dict, Any, Tuple
from urllib.parse import urlparse
import logging

from playwright.async_api import Page
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class UIUXTester:
    """Runs UI/UX tests for layout and image relevance"""
    
    def __init__(self, viewport_sizes: List[Dict[str, int]] = None, 
                 layout_tolerance: int = 5, image_relevance_check: bool = True):
        """
        Initialize UI/UX tester
        
        Args:
            viewport_sizes: List of viewport sizes to test
            layout_tolerance: Pixel tolerance for alignment checks
            image_relevance_check: Enable image relevance checking
        """
        self.viewport_sizes = viewport_sizes or [
            {'width': 1920, 'height': 1080},
            {'width': 375, 'height': 667}
        ]
        self.layout_tolerance = layout_tolerance
        self.image_relevance_check = image_relevance_check
    
    async def run_test(self, page: Page, url: str) -> Dict[str, Any]:
        """
        Run UI/UX tests on a page
        
        Args:
            page: Playwright page object
            url: URL being tested
            
        Returns:
            Dictionary with UI/UX test results
        """
        results = {
            'layout_issues': [],
            'image_suggestions': [],
            'responsive_issues': []
        }
        
        try:
            # Test layout for each viewport
            for viewport in self.viewport_sizes:
                await page.set_viewport_size(viewport['width'], viewport['height'])
                await page.reload(wait_until='domcontentloaded')
                
                # Check layout issues
            layout_issues = await self._check_layout(page, viewport)
            results['layout_issues'].extend(layout_issues)
                
                # Check responsive issues
            responsive_issues = await self._check_responsive(page, viewport)
            results['responsive_issues'].extend(responsive_issues)
            
            # Check image relevance
            if self.image_relevance_check:
                image_suggestions = await self._check_image_relevance(page, url)
                results['image_suggestions'].extend(image_suggestions)
            
            # Determine status
            has_critical_issues = any(
                issue.get('severity') == 'P1' 
                for issue in results['layout_issues'] + results['responsive_issues']
            )
            
            results['status'] = 'fail' if has_critical_issues else 'pass'
            results['summary'] = f"Found {len(results['layout_issues'])} layout issues, " \
                               f"{len(results['responsive_issues'])} responsive issues, " \
                               f"{len(results['image_suggestions'])} image suggestions"
            
            return results
            
        except Exception as e:
            logger.error(f"Error running UI/UX test on {url}: {e}")
            return {
                'status': 'fail',
                'error': str(e),
                'summary': f"UI/UX test failed: {str(e)}"
            }
    
    async def _check_layout(self, page: Page, viewport: Dict[str, int]) -> List[Dict[str, Any]]:
        """Check for layout and alignment issues"""
        issues = []
        
        try:
            # Check for overlapping elements
            overlapping = await page.evaluate("""() => {
                const issues = [];
                const elements = document.querySelectorAll('*');
                const rects = Array.from(elements).map(el => {
                    const rect = el.getBoundingClientRect();
                    return {el, rect, zIndex: window.getComputedStyle(el).zIndex};
                });
                
                for (let i = 0; i < rects.length; i++) {
                    for (let j = i + 1; j < rects.length; j++) {
                        const r1 = rects[i].rect;
                        const r2 = rects[j].rect;
                        
                        if (r1.top < r2.bottom && r1.bottom > r2.top &&
                            r1.left < r2.right && r1.right > r2.left) {
                            const area = Math.min(r1.width, r2.width) * Math.min(r1.height, r2.height);
                            if (area > 100) { // Significant overlap
                                issues.push({
                                    type: 'overlap',
                                    element1: rects[i].el.tagName,
                                    element2: rects[j].el.tagName
                                });
                            }
                        }
                    }
                }
                return issues;
            }""")
            
            if overlapping:
                issues.append({
                    'type': 'overlapping_elements',
                    'severity': 'P2',
                    'description': f"Found {len(overlapping)} overlapping element pairs",
                    'viewport': viewport
                })
            
            # Check for clipped text
            clipped = await page.evaluate("""() => {
                const issues = [];
                const textElements = document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, span, div');
                textElements.forEach(el => {
                    const style = window.getComputedStyle(el);
                    if (style.overflow === 'hidden' && el.scrollHeight > el.clientHeight) {
                        issues.push({
                            type: 'clipped_text',
                            element: el.tagName
                        });
                    }
                });
                return issues;
            }""")
            
            if clipped:
                issues.append({
                    'type': 'clipped_text',
                    'severity': 'P2',
                    'description': f"Found {len(clipped)} elements with clipped text",
                    'viewport': viewport
                })
            
        except Exception as e:
            logger.debug(f"Error checking layout: {e}")
        
        return issues
    
    async def _check_responsive(self, page: Page, viewport: Dict[str, int]) -> List[Dict[str, Any]]:
        """Check for responsive design issues"""
        issues = []
        
        try:
            # Check for horizontal scroll
            has_horizontal_scroll = await page.evaluate("""() => {
                return document.documentElement.scrollWidth > document.documentElement.clientWidth;
            }""")
            
            if has_horizontal_scroll:
                issues.append({
                    'type': 'horizontal_scroll',
                    'severity': 'P1',
                    'description': f"Page has horizontal scroll at {viewport['width']}x{viewport['height']}",
                    'viewport': viewport
                })
            
            # Check for very small text on mobile
            if viewport['width'] < 768:
                small_text = await page.evaluate("""() => {
                    const textElements = document.querySelectorAll('p, span, div, a');
                    let count = 0;
                    textElements.forEach(el => {
                        const fontSize = parseFloat(window.getComputedStyle(el).fontSize);
                        if (fontSize < 12) {
                            count++;
                        }
                    });
                    return count;
                }""")
                
                if small_text > 5:
                    issues.append({
                        'type': 'small_text_mobile',
                        'severity': 'P2',
                        'description': f"Found {small_text} elements with very small text on mobile",
                        'viewport': viewport
                    })
        
        except Exception as e:
            logger.debug(f"Error checking responsive: {e}")
        
        return issues
    
    async def _check_image_relevance(self, page: Page, url: str) -> List[Dict[str, Any]]:
        """Check image relevance to domain/page context"""
        suggestions = []
        
        try:
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Get domain keywords
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '').split('.')[0]
            
            # Get page context
            title = soup.find('title')
            title_text = title.get_text() if title else ''
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            desc_text = meta_desc.get('content', '') if meta_desc else ''
            page_text = ' '.join(soup.get_text().split()[:50])  # First 50 words
            
            context_keywords = self._extract_keywords(title_text + ' ' + desc_text + ' ' + page_text)
            
            # Check images
            images = soup.find_all('img')
            for img in images[:10]:  # Limit to 10 images
                src = img.get('src', '')
                alt = img.get('alt', '')
                filename = src.split('/')[-1].lower() if src else ''
                
                # Check relevance
                is_relevant = self._is_image_relevant(src, alt, filename, domain, context_keywords)
                
                if not is_relevant:
                    suggestions.append({
                        'type': 'image_relevance',
                        'severity': 'P3',
                        'image_src': src,
                        'description': "Image appears unrelated to the site's domain or page context; consider updating to more domain-relevant imagery."
                    })
        
        except Exception as e:
            logger.debug(f"Error checking image relevance: {e}")
        
        return suggestions
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Simple keyword extraction
        words = re.findall(r'\b[a-z]{4,}\b', text.lower())
        # Filter common words
        stop_words = {'this', 'that', 'with', 'from', 'have', 'will', 'your', 'their', 'there'}
        keywords = [w for w in words if w not in stop_words]
        return list(set(keywords))[:20]  # Top 20 unique keywords
    
    def _is_image_relevant(self, src: str, alt: str, filename: str, domain: str, 
                          context_keywords: List[str]) -> bool:
        """Determine if image is relevant to domain/context"""
        # Check alt text
        if alt:
            alt_lower = alt.lower()
            if any(keyword in alt_lower for keyword in context_keywords[:5]):
                return True
        
        # Check filename
        if filename:
            if any(keyword in filename for keyword in context_keywords[:5]):
                return True
            if domain in filename:
                return True
        
        # Check for generic/placeholder images
        generic_patterns = ['placeholder', 'default', 'sample', 'test', 'dummy', 'logo']
        if any(pattern in src.lower() or pattern in filename for pattern in generic_patterns):
            return False
        
        # If no clear indicators, assume relevant (don't flag everything)
        return True

