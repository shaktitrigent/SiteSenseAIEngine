# AI-First Web Testing & Reporting System - Architecture

## Overview

This system provides end-to-end automated web testing with intelligent test generation, execution, and comprehensive reporting. It processes Excel files containing URLs, analyzes websites, generates appropriate tests, executes them, and produces detailed HTML reports.

## Tech Stack

- **Python 3.9+**: Core language
- **Playwright**: Browser automation (modern, fast, reliable)
- **Axe-core**: Accessibility testing (WCAG compliance)
- **Playwright Performance APIs**: Core Web Vitals and performance metrics
- **pandas + openpyxl**: Excel file reading
- **Jinja2**: HTML template rendering
- **Chart.js**: Interactive charts in HTML reports
- **PyYAML**: Configuration management
- **Pillow**: Image processing for UI/UX checks

## Architecture Components

### 1. Data Flow

```
Excel File (.xlsx)
    ↓
Excel Reader → Extract URLs → Group by Domain/Company
    ↓
Site Analyzer → Understand Site Nature & Structure
    ↓
Test Generator → Generate Test Cases (Functional, Smoke, Accessibility, Performance, UI/UX)
    ↓
Test Runner → Execute Tests (Browser, Accessibility Engine, Performance APIs)
    ↓
Results Storage → Save to JSON (per company)
    ↓
Report Generator → Generate 4 HTML Reports per Company
```

### 2. Module Structure

#### `excel_reader.py`
- Reads Excel files
- Extracts URLs from configurable column
- Groups URLs by domain/company
- Returns structured data for processing

#### `site_analyzer.py`
- Analyzes website structure (limited depth crawl)
- Identifies site type (e-commerce, SaaS, blog, etc.)
- Discovers navigation, forms, CTAs, key pages
- Provides context for test generation

#### `test_generator.py`
- Generates test cases based on site analysis
- Creates tests for: Functional, Smoke, Accessibility, Performance, UI/UX
- Assigns severity levels (P1, P2, P3)
- Returns structured test case objects

#### `test_runner.py`
- Orchestrates test execution
- Manages browser instances
- Coordinates with specialized testers
- Collects results and evidence

#### `browser_manager.py`
- Manages Playwright browser instances
- Handles page navigation and interactions
- Captures screenshots
- Provides browser context to other modules

#### `accessibility_tester.py`
- Integrates axe-core via Playwright
- Runs WCAG compliance checks
- Formats accessibility violations

#### `performance_tester.py`
- Measures page load times
- Captures Core Web Vitals (LCP, CLS, FID/INP)
- Tracks network requests and payload sizes
- Compares against thresholds

#### `uiux_tester.py`
- Checks layout and alignment issues
- Validates responsive design
- Analyzes image relevance
- Flags UI/UX problems

#### `results_storage.py`
- Defines JSON schema
- Writes test results to JSON files
- Organizes by company/domain
- Stores evidence paths

#### `report_generator.py`
- Generates HTML reports using Jinja2 templates
- Creates charts using Chart.js
- Formats data for PDF export
- Produces 4 report types per company

### 3. Configuration

- Centralized YAML configuration
- Environment variable support
- Runtime overrides via CLI
- Extensible for future features

### 4. Output Structure

```
output/
├── results/
│   ├── company1_results.json
│   └── company2_results.json
├── screenshots/
│   ├── company1/
│   └── company2/
└── reports/
    ├── Company1_Functional_Report.html
    ├── Company1_Smoke_Report.html
    ├── Company1_Accessibility_Report.html
    ├── Company1_Performance_Report.html
    └── ...
```

## Design Principles

1. **Separation of Concerns**: Each module has a single responsibility
2. **Extensibility**: Easy to add new test types or report formats
3. **Robustness**: Error handling, timeouts, retry logic
4. **Maintainability**: Clear naming, documentation, type hints
5. **Production-Ready**: Configuration-driven, scalable, well-structured

