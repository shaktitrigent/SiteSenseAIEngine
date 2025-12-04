# AI-First Web Testing & Reporting System

An end-to-end automated web testing system that analyzes websites, generates intelligent test cases, executes comprehensive tests, and produces detailed HTML reports.

**Tested with:** [Trigent.com](https://trigent.com/) - Enterprise software solutions provider

## Features

- **Multi-Company Support**: Process multiple URLs from Excel, automatically grouped by domain/company
- **Intelligent Site Analysis**: Understands site structure, type (e-commerce, SaaS, blog, etc.), and key components
- **Automated Test Generation**: Generates Functional, Smoke, Accessibility, Performance, and UI/UX tests
- **Comprehensive Testing**:
  - **Functional Tests**: Navigation, forms, CTAs, links, site-specific flows
  - **Smoke Tests**: Basic availability, page load, title validation
  - **Accessibility Tests**: WCAG compliance using axe-core
  - **Performance Tests**: Core Web Vitals (LCP, CLS, INP), page load time, network metrics
  - **UI/UX Tests**: Layout issues, responsive design, image relevance
- **Detailed Reporting**: Four separate HTML reports per company with charts and metrics
- **PDF-Ready Reports**: Reports designed for easy PDF export
- **Structured JSON Storage**: All results stored in JSON for further analysis

## Quick Start (TL;DR)

### Option 1: Automated Setup (Recommended)

**Windows:**
```bash
setup.bat
```

**macOS/Linux:**
```bash
chmod +x setup.sh
./setup.sh
```

### Option 2: Manual Setup

```bash
# 1. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# or: source venv/bin/activate  # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 3. Create example Excel file (includes Trigent.com)
python setup_example.py

# 4. Run tests
python main.py example_urls.xlsx

# 5. View reports
# Open output/reports/Trigent_Functional_Report.html in browser
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

### Data Flow

```
Excel File → URL Extraction → Site Analysis → Test Generation → Test Execution → JSON Storage → HTML Reports
```

## Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager
- Git (optional, for cloning)

### Step-by-Step Setup

#### 1. Navigate to Project Directory

```bash
cd SiteSenseAIEngine
```

#### 2. Create Virtual Environment

**On Windows:**
```bash
python -m venv venv
```

**On macOS/Linux:**
```bash
python3 -m venv venv
```

#### 3. Activate Virtual Environment

**On Windows (PowerShell):**
```bash
.\venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```bash
venv\Scripts\activate.bat
```

**On macOS/Linux:**
```bash
source venv/bin/activate
```

You should see `(venv)` prefix in your terminal prompt when activated.

#### 4. Upgrade pip (Recommended)

```bash
python -m pip install --upgrade pip
```

#### 5. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- playwright
- pandas
- openpyxl
- pyyaml
- jinja2
- pillow
- beautifulsoup4
- lxml

#### 6. Install Playwright Browsers

```bash
playwright install chromium
```

**Note:** On Linux, you may need to install system dependencies:
```bash
playwright install --with-deps chromium
```

#### 7. Verify Installation

```bash
python -c "import playwright; import pandas; import yaml; print('All dependencies installed successfully!')"
```

### Deactivate Virtual Environment

When you're done working, deactivate the virtual environment:

```bash
deactivate
```

## Usage

### Quick Start with Example

#### 1. Create Example Excel File

First, create an example Excel file with test URLs:

```bash
python setup_example.py
```

This creates `example_urls.xlsx` with sample URLs including `https://trigent.com/`.

#### 2. Run the Application

Make sure your virtual environment is activated, then run:

```bash
python main.py example_urls.xlsx
```

#### 3. View Results

After execution completes, check the output:

- **JSON Results**: `output/results/Trigent_results.json`
- **HTML Reports**: `output/reports/Trigent_*_Report.html`
- **Screenshots**: `output/screenshots/trigent_com/`

Open the HTML reports in your browser to view detailed test results with charts.

### Complete Example Workflow

Here's a complete example using Trigent's website:

#### Step 1: Create Excel File with Trigent URL

Create a file named `trigent_test.xlsx` with the following content:

| url |
|-----|
| https://trigent.com/ |

Or use the setup script which includes this URL:

```bash
python setup_example.py
```

#### Step 2: Run Tests

```bash
# Make sure venv is activated
python main.py example_urls.xlsx
```

#### Step 3: Monitor Progress

You'll see output like:

```
[1/6] Reading Excel file: example_urls.xlsx
Found 1 companies with 1 URLs
[2/6] Analyzing websites...
Analyzing trigent.com...
[3/6] Generating test cases...
Generated 15 test cases for trigent.com
[4/6] Executing tests...
Running tests for trigent.com...
[5/6] Storing results...
[6/6] Generating HTML reports...
Generated reports for Trigent
```

#### Step 4: Review Reports

Open the generated HTML reports in your browser:

```bash
# Windows
start output\reports\Trigent_Functional_Report.html

# macOS
open output/reports/Trigent_Functional_Report.html

# Linux
xdg-open output/reports/Trigent_Functional_Report.html
```

### Advanced Usage

#### With Custom Configuration

```bash
python main.py example_urls.xlsx --config custom_config.yaml
```

#### Run in Non-Headless Mode (See Browser)

```bash
python main.py example_urls.xlsx --headless false
```

#### Custom Output Directory

```bash
python main.py example_urls.xlsx --output-dir my_output
```

### Command Line Options

- `excel_file`: Path to Excel file containing URLs (required)
- `--config`: Path to configuration YAML file (optional)
- `--headless`: Run browser in headless mode (true/false, optional, default: true)
- `--output-dir`: Base output directory (optional, overrides config)

### Excel File Format

The Excel file should contain at least one column with URLs. By default, the system looks for a column named `url`.

**Example Excel structure:**

| url |
|-----|
| https://trigent.com/ |
| https://trigent.com/about |
| https://example.com |

**Creating Your Own Excel File:**

1. Open Excel or Google Sheets
2. Create a column header named `url` (case-insensitive)
3. Add URLs (with or without http/https)
4. Save as `.xlsx` format
5. Use the file path when running the application

You can specify a custom column name in the configuration file.

## Configuration

Configuration is managed via YAML files. See `config/default_config.yaml` for all available options.

### Key Configuration Sections

- **Excel**: Column names for URL and company
- **Output**: Directories for results, screenshots, and reports
- **Browser**: Headless mode, timeout, viewport settings
- **Analysis**: Crawl depth, max pages, timeout
- **Test Generation**: Enable/disable test types
- **Performance**: Thresholds for metrics
- **Accessibility**: WCAG level, rules to skip
- **UI/UX**: Viewport sizes, layout tolerance

## Output Structure

```
output/
├── results/
│   ├── Company1_results.json
│   └── Company2_results.json
├── screenshots/
│   ├── company1_domain/
│   │   ├── TEST-001.png
│   │   └── TEST-002.png
│   └── company2_domain/
└── reports/
    ├── Company1_Functional_Report.html
    ├── Company1_Smoke_Report.html
    ├── Company1_Accessibility_Report.html
    ├── Company1_Performance_Report.html
    └── ...
```

## Report Types

### 1. Functional Test Report
- Navigation tests
- Form validation
- CTA functionality
- Link validation
- Site-specific flows (e-commerce, SaaS, etc.)

### 2. Smoke Test Report
- Page availability
- Page load time
- Title validation

### 3. Accessibility Report
- WCAG compliance violations
- Impact levels
- Remediation guidance
- Affected elements

### 4. Performance Report
- Page load time
- Core Web Vitals (LCP, CLS, INP)
- Network metrics (requests, payload size)
- Threshold comparisons

## JSON Results Schema

Results are stored in JSON with the following structure:

```json
{
  "company_name": "Example",
  "domain": "example.com",
  "timestamp": "2024-01-01T12:00:00",
  "summary": {
    "total_tests": 50,
    "passed": 45,
    "failed": 5,
    "skipped": 0,
    "pass_rate": 90.0,
    "severity_breakdown": {
      "p1_failures": 2,
      "p2_failures": 2,
      "p3_failures": 1
    }
  },
  "results": [
    {
      "test_id": "FUNC-001-example.com",
      "test_type": "Functional",
      "category": "Navigation",
      "severity": "P2",
      "status": "pass",
      "url": "https://example.com",
      "summary": "Found 10 navigation links",
      "detailed_description": "Verify navigation items are clickable",
      "timestamp": "2024-01-01T12:00:00",
      "evidence": {
        "screenshot": "screenshots/example_com/TEST-001.png"
      },
      "p1_failure_description": null
    }
  ]
}
```

## Severity Levels

- **P1 (Critical)**: Core functionality failures, major accessibility/performance blockers
- **P2 (Important)**: Non-blocking but important issues
- **P3 (Minor)**: Minor issues or suggestions

P1 failures include detailed impact and remediation descriptions.

## Extending the System

The system is designed for easy extension:

1. **Add New Test Types**: Extend `TestType` enum and add generation logic in `test_generator.py`
2. **Add New Testers**: Create new tester classes following the pattern in `accessibility_tester.py`
3. **Custom Reports**: Modify templates in `report_generator.py`
4. **Additional Metrics**: Extend performance tester or add new analysis modules

## Troubleshooting

### Virtual Environment Issues

**"python: command not found" (Linux/macOS)**
- Use `python3` instead of `python`
- Ensure Python 3.9+ is installed: `python3 --version`

**"Activate.ps1 cannot be loaded" (Windows PowerShell)**
- Run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- Or use Command Prompt instead of PowerShell

**Virtual environment not activating**
- Ensure you're in the project directory
- Check that `venv` folder exists
- Try creating venv again: `python -m venv venv --clear`

### Browser Installation Issues

**Playwright browsers fail to install:**
```bash
playwright install --with-deps chromium
```

**On Linux, if you get dependency errors:**
```bash
# Ubuntu/Debian
sudo apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2

# Then install Playwright
playwright install chromium
```

**Browser not found error:**
- Ensure Playwright is installed: `pip show playwright`
- Reinstall browsers: `playwright install chromium --force`

### Excel Reading Errors

**"Column 'url' not found"**
- Ensure the Excel file has a column header named `url` (case-insensitive)
- Check the file is saved as `.xlsx` format (not `.xls` or `.csv`)
- Verify the file is not corrupted

**"ModuleNotFoundError: No module named 'openpyxl'"**
- Activate your virtual environment
- Install dependencies: `pip install -r requirements.txt`

**Excel file is password protected:**
- Remove password protection from the Excel file
- Or create a new file without password

### Timeout Errors

**Page load timeout:**
- Increase timeout values in `config/default_config.yaml`:
```yaml
browser:
  timeout: 60000  # 60 seconds (default: 30000)
analysis:
  timeout: 20000  # 20 seconds (default: 10000)
```

**Network timeout:**
- Check your internet connection
- Some sites may block automated browsers
- Try running with `--headless false` to see what's happening

### Import Errors

**"ModuleNotFoundError" for any module:**
1. Ensure virtual environment is activated
2. Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
3. Verify installation: `pip list`

### Build/Compilation Errors (Windows)

**"ERROR: Unknown compiler" or "Failed to build pandas/numpy":**
This happens when packages try to build from source but no C compiler is found.

**Solution 1: Use pre-built wheels (Recommended)**
```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install packages individually to get wheels
pip install playwright
pip install pandas
pip install openpyxl
pip install pyyaml jinja2 pillow beautifulsoup4 lxml
```

**Solution 2: Install Visual Studio Build Tools**
1. Download and install [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. Select "Desktop development with C++" workload
3. Retry: `pip install -r requirements.txt`

**Solution 3: Use compatible Python version**
- Use Python 3.11 or 3.10 instead of 3.12
- These versions have better wheel availability for pandas

**Solution 4: Install from updated requirements**
The requirements.txt has been updated to use flexible versions that prefer wheels:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Permission Errors

**Cannot write to output directory:**
- Check file/folder permissions
- Try running with administrator/sudo privileges
- Or specify a different output directory: `--output-dir ./my_output`

### Performance Issues

**Tests running very slowly:**
- Reduce `max_pages` in config (default: 10)
- Reduce `max_depth` in config (default: 2)
- Increase `concurrency` in config (default: 2) if you have multiple URLs

**Out of memory errors:**
- Close other applications
- Reduce browser concurrency
- Process fewer URLs at a time

### Getting Help

1. Check the log file: `webtest.log`
2. Run with verbose output (check terminal)
3. Review error messages carefully
4. Ensure all prerequisites are met
5. Try with a simple test case first (single URL like `trigent_test.xlsx`)

## License

This project is provided as-is for demonstration and development purposes.

## Contributing

This is a production-ready starting point. To extend:

1. Add new test types in `src/test_generator.py`
2. Implement new testers following existing patterns
3. Extend report templates for new visualizations
4. Add configuration options as needed

## Support

For issues or questions, review the code comments and architecture documentation.

