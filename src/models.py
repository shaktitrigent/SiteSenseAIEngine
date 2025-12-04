"""
Data models for test cases and results
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TestType(str, Enum):
    """Test type enumeration"""
    FUNCTIONAL = "Functional"
    SMOKE = "Smoke"
    ACCESSIBILITY = "Accessibility"
    PERFORMANCE = "Performance"
    UIUX = "UIUX"


class TestStatus(str, Enum):
    """Test execution status"""
    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"


class Severity(str, Enum):
    """Test severity levels"""
    P1 = "P1"  # Critical
    P2 = "P2"  # Important
    P3 = "P3"  # Minor


@dataclass
class TestCase:
    """Represents a single test case"""
    test_id: str
    test_type: TestType
    category: str
    description: str
    severity: Severity
    url: str
    page: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Represents the result of a test execution"""
    test_id: str
    company_name: str
    domain: str
    url: str
    test_type: TestType
    category: str
    severity: Severity
    status: TestStatus
    summary: str
    detailed_description: str
    timestamp: datetime
    evidence: Dict[str, Any] = field(default_factory=dict)
    p1_failure_description: Optional[str] = None  # Only for P1 failures


@dataclass
class CompanyData:
    """Represents a company and its associated URLs"""
    company_name: str
    domain: str
    urls: List[str]
    site_type: Optional[str] = None
    structure: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SiteStructure:
    """Represents analyzed site structure"""
    site_type: str  # e-commerce, saas, blog, corporate, etc.
    navigation_items: List[str] = field(default_factory=list)
    forms: List[Dict[str, Any]] = field(default_factory=list)
    ctas: List[Dict[str, Any]] = field(default_factory=list)
    key_pages: List[str] = field(default_factory=list)
    has_search: bool = False
    has_cart: bool = False
    has_checkout: bool = False
    has_login: bool = False

