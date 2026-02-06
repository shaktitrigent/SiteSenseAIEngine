"""
Helper script to create an example Excel file for testing
"""

import pandas as pd
from pathlib import Path

def create_example_excel():
    """Create an example Excel file with sample URLs including Trigent"""
    data = {
        'url': [
            'https://trigent.com/',
            'https://trigent.com/about',
            'https://example.com'
        ]
    }
    
    df = pd.DataFrame(data)
    output_path = Path('example_urls.xlsx')
    df.to_excel(output_path, index=False)
    print(f"✓ Created example Excel file: {output_path}")
    print(f"\nThe file contains {len(data['url'])} URLs including:")
    for url in data['url']:
        print(f"  - {url}")
    print(f"\nYou can now run:")
    print(f"  python main.py {output_path}")
    print(f"\nOr test with just Trigent:")
    print(f"  python main.py trigent_test.xlsx")

if __name__ == "__main__":
    try:
        create_example_excel()
    except Exception as e:
        print(f"Error creating example file: {e}")
        print("Make sure pandas and openpyxl are installed:")
        print("  pip install pandas openpyxl")

