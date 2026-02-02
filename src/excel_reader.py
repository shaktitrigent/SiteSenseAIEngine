"""
Excel file reader for extracting URLs and grouping by company/domain
"""

import pandas as pd
from typing import List, Dict
from urllib.parse import urlparse
import logging

from src.models import CompanyData

logger = logging.getLogger(__name__)


class ExcelReader:
    """Reads Excel files and extracts URLs grouped by company/domain"""
    
    def __init__(self, url_column: str = "url", company_column: str = None):
        """
        Initialize Excel reader
        
        Args:
            url_column: Name of the column containing URLs
            company_column: Optional explicit company column name
        """
        self.url_column = url_column
        self.company_column = company_column
    
    def read_urls(self, excel_path: str) -> List[CompanyData]:
        """
        Read URLs from Excel file and group by company name
        Excel format: First row has headers "CompanyName" and "URL"
        Data rows contain company name and URL pairs
        
        Args:
            excel_path: Path to Excel file
            
        Returns:
            List of CompanyData objects grouped by company name
        """
        try:
            # Read Excel file with headers
            df = pd.read_excel(excel_path)
            
            # Check for required columns
            required_columns = ['CompanyName', 'URL']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Excel file must have columns: {required_columns}. Missing: {missing_columns}")
            
            # Group by company name (not domain, since same company can have multiple URLs)
            companies_dict: Dict[str, CompanyData] = {}
            
            for idx, row in df.iterrows():
                # Skip empty rows
                if pd.isna(row['CompanyName']) or pd.isna(row['URL']):
                    continue
                
                company_name = str(row['CompanyName']).strip()
                url = str(row['URL']).strip()
                
                # Skip if empty
                if not company_name or not url:
                    continue
                
                # Normalize URL
                if not url.startswith(('http://', 'https://')):
                    url = f"https://{url}"
                
                # Extract domain from URL
                parsed = urlparse(url)
                domain = parsed.netloc or parsed.path.split('/')[0]
                
                # Group by company name (use company name as key)
                # If same company name appears multiple times, add URLs to same company
                if company_name not in companies_dict:
                    companies_dict[company_name] = CompanyData(
                        company_name=company_name,
                        domain=domain,  # Use first URL's domain as primary domain
                        urls=[]
                    )
                
                # Add URL if not already present
                if url not in companies_dict[company_name].urls:
                    companies_dict[company_name].urls.append(url)
            
            companies = list(companies_dict.values())
            total_urls = sum(len(c.urls) for c in companies)
            logger.info(f"Read {total_urls} URLs for {len(companies)} companies")
            
            return companies
            
        except Exception as e:
            logger.error(f"Error reading Excel file: {e}")
            raise
    
    @staticmethod
    def _sanitize_domain(domain: str) -> str:
        """
        Sanitize domain name to create a company name
        
        Args:
            domain: Domain string
            
        Returns:
            Sanitized company name
        """
        # Remove www. prefix
        domain = domain.replace('www.', '')
        
        # Remove port numbers
        if ':' in domain:
            domain = domain.split(':')[0]
        
        # Capitalize and clean
        parts = domain.split('.')
        company_name = parts[0].capitalize()
        
        return company_name

