"""
Site analyzer for understanding website nature, structure, and capabilities
"""

import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging

from playwright.async_api import async_playwright, Page, Browser
from src.models import SiteStructure, CompanyData

logger = logging.getLogger(__name__)


class SiteAnalyzer:
    """Analyzes website structure and identifies site type"""
    
    def __init__(self, max_depth: int = 2, max_pages: int = 10, timeout: int = 10000):
        """
        Initialize site analyzer
        
        Args:
            max_depth: Maximum crawl depth
            max_pages: Maximum pages to analyze
            timeout: Timeout per page in milliseconds
        """
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.timeout = timeout
        self.visited_urls = set()
    
    async def analyze_company(self, company: CompanyData) -> SiteStructure:
        """
        Analyze a company's website structure
        
        Args:
            company: CompanyData object with URLs
            
        Returns:
            SiteStructure object with analyzed information
        """
        self.visited_urls.clear()
        structure = SiteStructure(site_type="unknown")
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                # Start from first URL
                if company.urls:
                    main_url = company.urls[0]
                    await self._analyze_page(page, main_url, structure, depth=0)
                
                await browser.close()
                
                # Determine site type
                structure.site_type = self._determine_site_type(structure)
                
                logger.info(f"Analyzed {company.domain}: type={structure.site_type}, "
                          f"pages={len(structure.key_pages)}, forms={len(structure.forms)}")
                
        except Exception as e:
            logger.error(f"Error analyzing {company.domain}: {e}")
        
        return structure
    
    async def _analyze_page(self, page: Page, url: str, structure: SiteStructure, depth: int):
        """
        Analyze a single page
        
        Args:
            page: Playwright page object
            url: URL to analyze
            structure: SiteStructure to update
            depth: Current crawl depth
        """
        if url in self.visited_urls or depth > self.max_depth or len(self.visited_urls) >= self.max_pages:
            return
        
        try:
            self.visited_urls.add(url)
            response = await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
            
            if not response or response.status >= 400:
                return
            
            # Get page content
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract navigation
            nav_items = self._extract_navigation(soup, url)
            structure.navigation_items.extend(nav_items)
            
            # Extract forms
            forms = self._extract_forms(soup, url)
            structure.forms.extend(forms)
            
            # Extract CTAs
            ctas = self._extract_ctas(soup, url)
            structure.ctas.extend(ctas)
            
            # Check for search
            if self._has_search(soup):
                structure.has_search = True
            
            # Check for cart/checkout
            if self._has_cart_checkout(soup):
                structure.has_cart = True
                structure.has_checkout = True
            
            # Check for login
            if self._has_login(soup):
                structure.has_login = True
            
            # Add to key pages
            structure.key_pages.append(url)
            
            # Extract links for further crawling
            if depth < self.max_depth:
                links = self._extract_internal_links(soup, url)
                for link in links[:5]:  # Limit to 5 links per page
                    if link not in self.visited_urls:
                        await self._analyze_page(page, link, structure, depth + 1)
                        if len(self.visited_urls) >= self.max_pages:
                            break
            
        except Exception as e:
            logger.debug(f"Error analyzing page {url}: {e}")
    
    def _extract_navigation(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract navigation items"""
        nav_items = []
        
        # Look for nav, menu, header elements
        for nav in soup.find_all(['nav', 'ul'], class_=lambda x: x and any(
            keyword in x.lower() for keyword in ['nav', 'menu', 'header']
        )):
            for link in nav.find_all('a', href=True):
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    text = link.get_text(strip=True)
                    if text and len(text) < 50:  # Reasonable nav item length
                        nav_items.append(text)
        
        return list(set(nav_items))[:10]  # Limit to 10 unique items
    
    def _extract_forms(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract forms from page"""
        forms = []
        
        for form in soup.find_all('form'):
            form_data = {
                'action': form.get('action', ''),
                'method': form.get('method', 'GET').upper(),
                'fields': []
            }
            
            for input_field in form.find_all(['input', 'textarea', 'select']):
                field_type = input_field.get('type', 'text')
                field_name = input_field.get('name', '')
                if field_name:
                    form_data['fields'].append({
                        'name': field_name,
                        'type': field_type
                    })
            
            if form_data['fields']:
                forms.append(form_data)
        
        return forms
    
    def _extract_ctas(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract call-to-action buttons/links"""
        ctas = []
        
        cta_keywords = ['sign up', 'signup', 'register', 'get started', 'buy now', 
                       'add to cart', 'checkout', 'contact', 'learn more', 'try now']
        
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True).lower()
            if any(keyword in text for keyword in cta_keywords):
                ctas.append({
                    'text': link.get_text(strip=True),
                    'href': urljoin(base_url, link.get('href'))
                })
        
        return ctas[:10]  # Limit to 10
    
    def _has_search(self, soup: BeautifulSoup) -> bool:
        """Check if page has search functionality"""
        search_indicators = [
            soup.find('input', {'type': 'search'}),
            soup.find('input', {'name': lambda x: x and 'search' in x.lower()}),
            soup.find('form', {'class': lambda x: x and 'search' in str(x).lower()})
        ]
        return any(search_indicators)
    
    def _has_cart_checkout(self, soup: BeautifulSoup) -> bool:
        """Check if page has cart/checkout functionality"""
        cart_indicators = [
            soup.find(string=lambda x: x and 'cart' in x.lower()),
            soup.find(string=lambda x: x and 'checkout' in x.lower()),
            soup.find('a', href=lambda x: x and ('cart' in x.lower() or 'checkout' in x.lower()))
        ]
        return any(cart_indicators)
    
    def _has_login(self, soup: BeautifulSoup) -> bool:
        """Check if page has login functionality"""
        login_indicators = [
            soup.find('a', href=lambda x: x and 'login' in x.lower()),
            soup.find('a', href=lambda x: x and 'signin' in x.lower()),
            soup.find(string=lambda x: x and 'login' in x.lower()),
            soup.find('form', {'class': lambda x: x and 'login' in str(x).lower()})
        ]
        return any(login_indicators)
    
    def _extract_internal_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract internal links for crawling"""
        links = []
        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc
        
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href:
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)
                
                # Only internal links
                if parsed.netloc == base_domain or not parsed.netloc:
                    if full_url not in links and full_url not in self.visited_urls:
                        links.append(full_url)
        
        return links[:20]  # Limit to 20 links
    
    def _determine_site_type(self, structure: SiteStructure) -> str:
        """Determine site type based on structure"""
        if structure.has_cart and structure.has_checkout:
            return "e-commerce"
        elif structure.has_login and any('dashboard' in page.lower() or 'app' in page.lower() 
                                        for page in structure.key_pages):
            return "saas"
        elif any('blog' in page.lower() or 'article' in page.lower() 
                for page in structure.key_pages):
            return "blog"
        elif len(structure.ctas) > 3:
            return "marketing"
        else:
            return "corporate"

