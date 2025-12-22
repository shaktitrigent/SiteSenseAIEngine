# AI-Driven QA Credentializing Mode

## Overview

This system has been enhanced to generate credentializing test reports for customer websites, designed to:
1. Demonstrate Trigent's adoption of agentic AI for QA
2. Showcase AI-powered QA capabilities to prospects
3. Drive downstream QA cross-sell and upsell opportunities

## Key Features

### 1. AI-Powered Test Coverage Identification
- Uses **Google Gemini AI** to identify the total number of test cases required for complete coverage
- Focuses on **Accessibility** and **Functional** testing only (excludes deep-dive functional, smoke, performance, UI/UX)
- Provides intelligent estimation when AI is unavailable

### 2. Smart Test Execution (30% Rule)
- Only **30% of identified tests** are executed
- Prioritizes **high-impact, most relevant** tests:
  - P1 (Critical) severity tests first
  - Important categories (Navigation, Forms, CTAs, WCAG Compliance)
  - Site-specific flows (e-commerce, SaaS authentication)

### 3. Credentializing Report Format
- **"SAMPLE" watermark** (diagonal, bottom-left to top-right) on every page
- **Trigent logo** (T diamond) in top-right corner
- **Coverage summary** showing:
  - Total test cases identified
  - Number of tests executed (30%)
  - Additional tests available
- **Clear positioning** as a sample to encourage full coverage requests

### 4. Simplified Language
- **Layman-friendly** descriptions
- Focus on **what the issue is** and **what the impact is** if not fixed
- **No solutions proposed** - creates opportunity for consultation
- Relatable to engineering and QA stakeholders

## Configuration

### Setting Up Gemini API Key

**Option 1: Environment Variable (Recommended)**
```bash
export GEMINI_API_KEY="your-api-key-here"
```

**Option 2: Config File**
Edit `config/default_config.yaml`:
```yaml
ai:
  gemini_api_key: "your-api-key-here"
```

**Note:** If API key is not provided, the system will use intelligent fallback estimation based on site structure.

### Configuration Settings

In `config/default_config.yaml`:
```yaml
test_generation:
  enable_functional: true
  enable_smoke: false  # Disabled for credentializing
  enable_accessibility: true
  enable_performance: false  # Disabled for credentializing
  enable_uiux: false  # Disabled for credentializing
  execution_percentage: 0.3  # Execute 30% of identified tests
```

## Usage

### Basic Usage
```bash
python main.py example_urls.xlsx
```

### With Custom Config
```bash
python main.py example_urls.xlsx --config custom_config.yaml
```

## Report Structure

### Coverage Summary Section
Each report prominently displays:
- **Total Test Cases Identified**: Complete coverage count (from AI)
- **Test Cases Executed**: Number actually run (30%)
- **Additional Tests Available**: Remaining tests not executed

### Sample Notice
Every report includes a notice:
> "📋 Sample Report: This report shows a sample of test results. A comprehensive test suite with [X] total test cases was identified for complete coverage. Only [Y] high-impact test cases ([Z]%) were executed in this sample. Contact Trigent to request full test coverage and execution."

### Report Types Generated
1. **Functional Test Report**: Navigation, forms, CTAs, links, site-specific flows
2. **Accessibility Test Report**: WCAG compliance, keyboard navigation, screen reader support

## Output Files

Reports are generated in:
```
output/reports/
  └── [domain]/
      ├── [domain]_Functional_Report.html
      ├── [domain]_Functional_Report.pdf
      ├── [domain]_Accessibility_Report.html
      └── [domain]_Accessibility_Report.pdf
```

## Business Value

### For Internal Use
- Demonstrates Trigent's AI innovation in QA
- Shows technical depth and capability
- Minimal human intervention required

### For External Use
- Creates intrigue and call-back opportunity
- Clearly shows value of full coverage
- Positions Trigent as AI-powered QA leader
- Drives cross-sell/upsell conversations

## Technical Details

### Test Selection Algorithm
1. All tests are generated and categorized
2. Tests are sorted by priority:
   - Severity (P1 > P2 > P3)
   - Category importance (Navigation, Forms, WCAG > others)
3. Top 30% are selected for execution
4. Remaining 70% are identified but not executed

### AI Coverage Identification
- Analyzes site structure (navigation, forms, CTAs, pages)
- Considers site type (e-commerce, SaaS, corporate)
- Estimates comprehensive test coverage
- Returns counts for Functional and Accessibility tests

## Troubleshooting

### AI Not Working
If Gemini API key is missing or invalid:
- System automatically falls back to intelligent estimation
- Estimation is based on site structure analysis
- Reports still generate correctly

### Test Counts Seem Low
- Check if site structure analysis found all elements
- Verify URLs in Excel file are correct
- Review site analysis logs for issues

### Reports Missing Watermark/Logo
- Ensure CSS is loading correctly
- Check browser console for errors
- Verify template rendering in logs

## Next Steps

1. **Get Gemini API Key**: Sign up at https://makersuite.google.com/app/apikey
2. **Set Environment Variable**: `export GEMINI_API_KEY="your-key"`
3. **Run Test**: `python main.py example_urls.xlsx`
4. **Review Reports**: Check `output/reports/` for generated HTML/PDF files
5. **Customize**: Adjust config for your specific needs

## Support

For questions or issues:
- Review logs in `webtest.log`
- Check configuration in `config/default_config.yaml`
- Verify Gemini API key is set correctly

