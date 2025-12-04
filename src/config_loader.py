"""
Configuration loader for YAML config files
"""

import yaml
from pathlib import Path
from typing import Dict, Any
import logging
import os

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Loads and manages configuration"""
    
    @staticmethod
    def load_config(config_path: str = None) -> Dict[str, Any]:
        """
        Load configuration from YAML file
        
        Args:
            config_path: Path to config file (defaults to config/default_config.yaml)
            
        Returns:
            Configuration dictionary
        """
        if config_path is None:
            # Try default location
            default_path = Path(__file__).parent.parent / "config" / "default_config.yaml"
            if default_path.exists():
                config_path = str(default_path)
            else:
                # Return minimal default config
                return ConfigLoader._get_default_config()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            # Override with environment variables
            config = ConfigLoader._apply_env_overrides(config)
            
            logger.info(f"Loaded configuration from {config_path}")
            return config
            
        except Exception as e:
            logger.warning(f"Error loading config from {config_path}: {e}. Using defaults.")
            return ConfigLoader._get_default_config()
    
    @staticmethod
    def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides"""
        # Browser settings
        if os.getenv('BROWSER_HEADLESS'):
            config.setdefault('browser', {})['headless'] = os.getenv('BROWSER_HEADLESS').lower() == 'true'
        
        if os.getenv('BROWSER_TIMEOUT'):
            config.setdefault('browser', {})['timeout'] = int(os.getenv('BROWSER_TIMEOUT'))
        
        # Output directories
        if os.getenv('OUTPUT_RESULTS_DIR'):
            config.setdefault('output', {})['results_dir'] = os.getenv('OUTPUT_RESULTS_DIR')
        
        if os.getenv('OUTPUT_REPORTS_DIR'):
            config.setdefault('output', {})['reports_dir'] = os.getenv('OUTPUT_REPORTS_DIR')
        
        return config
    
    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """Get minimal default configuration"""
        return {
            'excel': {
                'url_column': 'url'
            },
            'output': {
                'results_dir': 'output/results',
                'screenshots_dir': 'output/screenshots',
                'reports_dir': 'output/reports'
            },
            'browser': {
                'headless': True,
                'timeout': 30000,
                'viewport': {'width': 1920, 'height': 1080}
            },
            'test_generation': {
                'enable_functional': True,
                'enable_smoke': True,
                'enable_accessibility': True,
                'enable_performance': True,
                'enable_uiux': True
            },
            'performance': {
                'page_load_time_ms': 3000,
                'lcp_threshold_ms': 2500,
                'cls_threshold': 0.1,
                'inp_threshold_ms': 200,
                'max_requests': 100,
                'max_payload_mb': 5
            },
            'accessibility': {
                'wcag_level': 'AA'
            },
            'uiux': {
                'viewport_sizes': [
                    {'width': 1920, 'height': 1080},
                    {'width': 375, 'height': 667}
                ],
                'layout_tolerance': 5,
                'image_relevance_check': True
            }
        }

