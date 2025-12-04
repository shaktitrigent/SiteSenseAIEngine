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
        Read URLs from Excel file and group by domain
        
        Args:
            excel_path: Path to Excel file
            
        Returns:
            List of CompanyData objects grouped by domain
        """
        try:
            df = pd.read_excel(excel_path)
            
            if self.url_column not in df.columns:
                raise ValueError(f"Column '{self.url_column}' not found in Excel file")
            
            # Extract URLs and normalize
            urls = df[self.url_column].dropna().unique().tolist()
            
            # Group by domain
            companies_dict: Dict[str, CompanyData] = {}
            
            for url in urls:
                if not isinstance(url, str) or not url.strip():
                    continue
                
                # Normalize URL
                url = url.strip()
                if not url.startswith(('http://', 'https://')):
                    url = f"https://{url}"
                
                # Extract domain
                parsed = urlparse(url)
                domain = parsed.netloc or parsed.path.split('/')[0]
                
                # Get company name
                if self.company_column and self.company_column in df.columns:
                    # Use explicit company column if available
                    company_row = df[df[self.url_column] == url]
                    if not company_row.empty:
                        company_name = str(company_row[self.company_column].iloc[0])
                    else:
                        company_name = self._sanitize_domain(domain)
                else:
                    # Infer from domain
                    company_name = self._sanitize_domain(domain)
                
                # Group by domain
                if domain not in companies_dict:
                    companies_dict[domain] = CompanyData(
                        company_name=company_name,
                        domain=domain,
                        urls=[]
                    )
                
                if url not in companies_dict[domain].urls:
                    companies_dict[domain].urls.append(url)
            
            companies = list(companies_dict.values())
            logger.info(f"Read {len(urls)} URLs, grouped into {len(companies)} companies")
            
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

