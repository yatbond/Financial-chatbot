"""
Excel Chatbot - Robust Excel Parser for Construction Project Financial Data
Handles monthly time-series data from Projection, Committed Cost, Accrual, Cash Flow sheets.
"""

import pandas as pd
import json
from pathlib import Path


def parse_excel_file(file_path: str) -> dict:
    """
    Parse the construction project Excel file.
    
    Structure:
    - Each sheet (Projection, Committed Cost, Accrual, Cash Flow) has monthly data
    - Columns: Item, Trade, Bal B/F, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec, Jan, Feb, Mar, Total
    - Row 11 = column headers
    - Row 12 = category header (e.g., "Income", "Cost") - SKIP (no numeric values)
    - Row 13+ = actual data items with numeric values
    """
    file_path = Path(file_path)
    
    # Sheets to process
    sheets_to_process = ['Projection', 'Committed Cost', 'Accrual', 'Cash Flow']
    
    result = {
        'metadata': {},
        'sheets': {},
        'all_sheets': sheets_to_process
    }
    
    # Extract metadata from first sheet
    metadata_df = pd.read_excel(file_path, sheet_name=sheets_to_process[0], header=None)
    result['metadata'] = extract_metadata(metadata_df)
    
    # Parse each sheet
    for sheet_name in sheets_to_process:
        print(f"Processing sheet: {sheet_name}")
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
        
        # Parse using the correct structure (header at row 11, data at row 13+)
        cleaned_df = parse_monthly_sheet(df, sheet_name)
        result['sheets'][sheet_name] = cleaned_df
        
        print(f"  - Extracted {len(cleaned_df)} data rows")
    
    return result


def extract_metadata(df: pd.DataFrame) -> dict:
    """Extract project metadata from header rows."""
    metadata = {}
    
    for idx, row in df.iterrows():
        for col_idx, cell in enumerate(row):
            if pd.isna(cell):
                continue
            
            cell_str = str(cell).strip()
            
            if 'Project Code:' in cell_str:
                val = row.iloc[col_idx + 1] if col_idx + 1 < len(row) else None
                if pd.notna(val):
                    metadata['project_code'] = str(val).strip()
            
            elif 'Project Name:' in cell_str:
                val = row.iloc[col_idx + 1] if col_idx + 1 < len(row) else None
                if pd.notna(val):
                    metadata['project_name'] = str(val).strip()
            
            elif 'Report Date:' in cell_str:
                val = row.iloc[col_idx + 1] if col_idx + 1 < len(row) else None
                if pd.notna(val):
                    metadata['report_date'] = str(val).strip()
            
            elif 'Start Date:' in cell_str:
                val = row.iloc[col_idx + 1] if col_idx + 1 < len(row) else None
                if pd.notna(val):
                    metadata['start_date'] = str(val).strip()
            
            elif 'Complete Date:' in cell_str and 'Target' not in cell_str:
                val = row.iloc[col_idx + 1] if col_idx + 1 < len(row) else None
                if pd.notna(val):
                    metadata['complete_date'] = str(val).strip()
            
            elif 'Target Complete Date:' in cell_str:
                val = row.iloc[col_idx + 1] if col_idx + 1 < len(row) else None
                if pd.notna(val):
                    metadata['target_complete_date'] = str(val).strip()
    
    # Company name
    if pd.notna(df.iloc[0, 0]):
        metadata['company'] = str(df.iloc[0, 0]).strip()
    
    return metadata


def is_category_header(row_df: pd.DataFrame) -> bool:
    """
    Check if a row is a category header (like 'Income', 'Cost') rather than a data row.
    
    Category headers have:
    - Item_Code is a simple integer (1, 2, 3...) without decimals
    - Trade is a category name (not indented)
    - No numeric values in any column (all NaN or 0)
    
    Data rows have:
    - Item_Code with decimals (1.1, 1.2.1) OR indented name (starts with "-")
    - At least one numeric column has non-zero/non-NaN value
    """
    item_code = row_df['Item_Code']
    trade = row_df['Trade']
    
    # Skip if item code is empty
    if pd.isna(item_code) or str(item_code).strip() == '':
        return True
    
    item_str = str(item_code).strip()
    
    # If it has decimals, it's a data row
    if '.' in item_str:
        return False
    
    # If it doesn't start with a digit, it might be a sub-item (like "1.2.1" as string)
    if not item_str[0].isdigit():
        return False
    
    # It's a simple integer like "1", "2", "3" - check if it has values
    # Check if any numeric column has a non-zero, non-NaN value
    numeric_cols = ['Bal_BF', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Total']
    for col in numeric_cols:
        if col in row_df.index:
            val = row_df[col]
            if pd.notna(val) and val != 0:
                return False  # Has values, so it's a data row
    
    # No values found - it's a category header
    return True


def parse_monthly_sheet(df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    """
    Parse a monthly data sheet.
    
    Expected structure:
    - Row 11: Headers (Item, Trade, Bal B/F, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec, Jan, Feb, Mar, Total)
    - Row 12: Category header (e.g., "Income") - SKIP
    - Row 13+: Data rows
    """
    # Column names for monthly data
    column_names = ['Item_Code', 'Trade', 'Bal_BF', 'Apr', 'May', 'Jun', 
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 
                    'Jan', 'Feb', 'Mar', 'Total']
    
    # Data starts at row 12 (0-indexed) - includes category headers
    data_start_row = 12
    
    # Extract data rows
    data_df = df.iloc[data_start_row:].copy()
    data_df = data_df.reset_index(drop=True)
    
    # Assign column names
    if len(data_df.columns) >= 16:
        data_df.columns = column_names[:len(data_df.columns)]
    else:
        # Pad with empty columns if needed
        for i in range(len(data_df.columns), 16):
            data_df[i] = None
        data_df.columns = column_names
    
    # Filter out rows where Item_Code is empty
    data_df = data_df[data_df['Item_Code'].notna()]
    
    # Clean Item_Code
    data_df['Item_Code'] = data_df['Item_Code'].apply(
        lambda x: str(x).strip() if pd.notna(x) else ''
    )
    
    # Remove category headers (simple integer codes like "1", "2" with no values)
    # KEEP category headers per user request
    # data_df = data_df[~data_df.apply(is_category_header, axis=1)]
    
    # Reset index
    data_df = data_df.reset_index(drop=True)
    
    # Convert numeric columns to float, fill NaN with 0
    numeric_columns = column_names[2:]  # All columns except Item_Code and Trade
    for col in numeric_columns:
        if col in data_df.columns:
            data_df[col] = pd.to_numeric(data_df[col], errors='coerce').fillna(0)
    
    # Clean Trade column - keep original formatting (don't strip leading spaces for sub-items)
    data_df['Trade'] = data_df['Trade'].apply(
        lambda x: str(x) if pd.notna(x) else ''
    )
    
    return data_df


if __name__ == '__main__':
    excel_file = r'C:\Users\derri\.openclaw\media\inbound\file_5---f1932325-a544-44fe-a5d2-5235b24c1efb.xlsx'
    
    print("Parsing Excel file...")
    data = parse_excel_file(excel_file)
    
    # Save metadata to JSON
    metadata_file = r'C:\Users\derri\.openclaw\workspace\metadata.json'
    with open(metadata_file, 'w') as f:
        json.dump(data['metadata'], f, indent=2)
    print(f"Saved metadata to: {metadata_file}")
    
    # Save each sheet to CSV
    for sheet_name, df in data['sheets'].items():
        csv_name = sheet_name.replace(" ", "_")
        csv_path = rf'C:\Users\derri\.openclaw\workspace\{csv_name}.csv'
        df.to_csv(csv_path, index=False)
        print(f"Saved: {csv_path}")
    
    # Print summary
    print("\n=== Summary ===")
    print(f"Project: {data['metadata'].get('project_name', 'Unknown')}")
    print(f"Code: {data['metadata'].get('project_code', 'Unknown')}")
    print(f"Sheets: {list(data['sheets'].keys())}")
    for sheet_name, df in data['sheets'].items():
        print(f"  {sheet_name}: {len(df)} rows")
        # Show first 5 items
        print(f"    First items: {df['Trade'].head(5).tolist()}")
