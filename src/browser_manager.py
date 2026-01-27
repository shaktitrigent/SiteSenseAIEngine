"""
Browser management using Playwright
"""

import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
import logging

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages Playwright browser instances"""
    
    def __init__(self, headless: bool = True, timeout: int = 30000, 
                 viewport: Dict[str, int] = None):
        """
        Initialize browser manager
        
        Args:
            headless: Run browser in headless mode
            timeout: Default timeout in milliseconds
            viewport: Viewport dimensions {'width': int, 'height': int}
        """
        self.headless = headless
        self.timeout = timeout
        self.viewport = viewport or {'width': 1920, 'height': 1080}
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
    
    async def start(self):
        """Start browser instance"""
        try:
            if not self.playwright:
                self.playwright = await async_playwright().start()
            if not self.browser:
                self.browser = await self.playwright.chromium.launch(headless=self.headless)
            if not self.context:
                self.context = await self.browser.new_context(
                    viewport=self.viewport,
                    ignore_https_errors=True
                )
            else:
                # Test if context is still valid by trying to create a test page
                try:
                    test_page = await self.context.new_page()
                    await test_page.close()
                except Exception:
                    # Context is closed, create a new one
                    self.context = await self.browser.new_context(
                        viewport=self.viewport,
                        ignore_https_errors=True
                    )
        except Exception as e:
            error_msg = str(e)
            # Check if this is a Playwright browser installation issue
            if "Executable doesn't exist" in error_msg or "playwright install" in error_msg.lower():
                logger.error("Playwright browsers are not installed. Please run: playwright install")
                logger.error("You can install browsers by running: playwright install chromium")
                # Raise a cleaner exception without Unicode characters
                raise RuntimeError(
                    "Playwright browsers are not installed. "
                    "Please run: playwright install chromium"
                ) from None
            else:
                logger.error(f"Error starting browser: {error_msg}")
            # Reset and try again
            self.context = None
            self.browser = None
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            raise
    
    async def stop(self):
        """Stop browser instance"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def new_page(self) -> Page:
        """
        Create a new page
        
        Returns:
            Playwright Page object
        """
        if not self.context:
            await self.start()
        
        try:
            return await self.context.new_page()
        except Exception as e:
            logger.warning(f"Error creating page, restarting browser: {e}")
            # Context might be closed, restart browser
            self.context = None
            await self.start()
            return await self.context.new_page()
    
    async def take_screenshot(self, page: Page, filepath: str) -> str:
        """
        Take a screenshot of the current page
        
        Args:
            page: Playwright page object
            filepath: Path to save screenshot
            
        Returns:
            Path to saved screenshot
        """
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=filepath, full_page=True)
            return filepath
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return ""
    
    async def navigate(self, page: Page, url: str, wait_until: str = "networkidle") -> bool:
        """
        Navigate to a URL with retry logic and fallback strategies
        
        Args:
            page: Playwright page object
            url: URL to navigate to
            wait_until: Wait condition ('load', 'domcontentloaded', 'networkidle')
                       Default: 'networkidle' for complete page load
            
        Returns:
            True if navigation successful, False otherwise
        """
        max_retries = 2
        # Fallback strategies: try networkidle first, then load, then domcontentloaded
        wait_strategies = ['networkidle', 'load', 'domcontentloaded'] if wait_until == 'networkidle' else [wait_until]
        
        for attempt in range(max_retries):
            for strategy_idx, strategy in enumerate(wait_strategies):
                try:
                    # Use longer timeout for retries
                    timeout = self.timeout * (2 if attempt > 0 else 1)
                    
                    response = await page.goto(url, wait_until=strategy, timeout=timeout)
                    
                    # If we used a faster strategy but wanted networkidle, try to wait for it with shorter timeout
                    if strategy != 'networkidle' and wait_until == 'networkidle':
                        try:
                            await page.wait_for_load_state('networkidle', timeout=10000)
                        except:
                            pass  # Continue if timeout - page is still usable
                    
                    # Small additional wait for JavaScript to execute and page to stabilize
                    await page.wait_for_timeout(1000)
                    
                    if response is not None and response.status < 400:
                        if strategy != wait_until:
                            logger.debug(f"Navigation to {url} succeeded with fallback strategy: {strategy}")
                        return True
                    elif response and response.status >= 400:
                        logger.warning(f"Navigation to {url} returned status {response.status}")
                        return False
                        
                except Exception as e:
                    error_msg = str(e)
                    # If it's a timeout and we have more strategies, try next one
                    if "timeout" in error_msg.lower():
                        if strategy_idx < len(wait_strategies) - 1:
                            logger.debug(f"Timeout with {strategy} for {url}, trying next strategy...")
                            continue
                        elif attempt < max_retries - 1:
                            logger.warning(f"Navigation timeout (attempt {attempt + 1}/{max_retries}) for {url}, retrying...")
                            await asyncio.sleep(2)  # Brief delay before retry
                            break  # Break to retry outer loop
                        else:
                            # All strategies exhausted, try final fallback
                            logger.warning(f"Navigation timeout for {url} with all strategies, using 'load' as final fallback...")
                            try:
                                response = await page.goto(url, wait_until='load', timeout=self.timeout)
                                await page.wait_for_timeout(2000)  # Give page time to stabilize
                                if response and response.status < 400:
                                    return True
                            except Exception as fallback_error:
                                logger.error(f"Error navigating to {url} (all strategies failed): {fallback_error}")
                                return False
                    else:
                        # Non-timeout error - try next strategy or retry
                        if strategy_idx < len(wait_strategies) - 1:
                            logger.debug(f"Error with {strategy} for {url}: {error_msg}, trying next strategy...")
                            continue
                        elif attempt < max_retries - 1:
                            logger.warning(f"Navigation error (attempt {attempt + 1}/{max_retries}) for {url}, retrying...")
                            await asyncio.sleep(2)
                            break
                        else:
                            logger.error(f"Error navigating to {url}: {error_msg}")
                            return False
        
        return False

