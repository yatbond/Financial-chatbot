"""
Excel Financial Data Parser
Converts Excel workbooks with merged headers into flat database-style tables.

Structure:
- Financial Status sheet: Year/Month from B5, Financial Type from merged column headers
- Other sheets: Sheet name = Financial Type, Column headings = Time periods

Output: Flat table with columns:
Year | Month | Sheet_Name | Financial_Type | Item_Code | Data_Type | Value
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import re
from io import BytesIO

# Month name to number mapping
MONTH_MAP = {
    'january': 1, 'jan': 1,
    'february': 2, 'feb': 2,
    'march': 3, 'mar': 3,
    'april': 4, 'apr': 4,
    'may': 5,
    'june': 6, 'jun': 6,
    'july': 7, 'jul': 7,
    'august': 8, 'aug': 8,
    'september': 9, 'sep': 9, 'sept': 9,
    'october': 10, 'oct': 10,
    'november': 11, 'nov': 11,
    'december': 12, 'dec': 12
}

# Patterns to ignore in financial type headers (formula indicators)
FORMULA_INDICATOR_PATTERNS = [
    r'^[A-Z]$',                          # Single letter: A, B, C
    r'^[A-Z]=[A-Z][+-]',                 # Formula like: D=B+C
    r'^E\d*=[A-Z]/[A-Z]',               # Ratio like: E1=E/D
    r'^ Balance .*',                     # Balance formulas
    r'^% of time.*',                     # Percentage formulas
]


def clean_text_value(val):
    """Remove '=' prefix from formula cells that show as text."""
    if pd.isna(val):
        return ""
    text = str(val).strip()
    # Remove leading '=' if present (Excel formula display)
    if text.startswith('='):
        text = text[1:]
    return text


def is_formula_indicator(text):
    """Check if text is a formula indicator that should be ignored."""
    if not text:
        return False
    text = str(text).strip()
    for pattern in FORMULA_INDICATOR_PATTERNS:
        if re.match(pattern, text):
            return True
    return False


def parse_date_to_year_month(date_val):
    """Extract Year and Month from various date formats."""
    if pd.isna(date_val):
        return None, None
    
    try:
        if isinstance(date_val, str):
            dt = pd.to_datetime(date_val)
        else:
            dt = pd.to_datetime(date_val)
        return dt.year, dt.month
    except:
        return None, None


def get_merged_header_value(df, row_idx, col_idx):
    """Get the actual value from a cell, handling NaN and merged cells."""
    val = df.iloc[row_idx, col_idx]
    if pd.notna(val):
        return str(val).strip()
    return ""


def parse_financial_status_sheet(xl, year=None, month=None):
    """
    Parse Financial Status sheet.
    Returns list of tuples: (year, month, "Financial Status", financial_type, item_code, data_type, value)
    """
    df = pd.read_excel(xl, sheet_name='Financial Status', header=None)
    rows = []
    
    # Extract Year/Month from Report Date (cell B5, which is row 4, col 1)
    if year is None or month is None:
        report_date = get_merged_header_value(df, 4, 1)  # B5
        year, month = parse_date_to_year_month(report_date)
    
    if year is None or month is None:
        print(f"Warning: Could not extract year/month from Financial Status")
        return []
    
    # Build financial type mapping from merged headers (rows 11-14)
    # Headers span multiple rows - need to trace vertically
    financial_types = {}
    
    for col_idx in range(2, df.shape[1]):
        # Trace vertically to build the full header name
        header_parts = []
        
        # Check rows 11-14 for header values in this column
        for row_idx in range(11, 15):
            if row_idx < len(df) and col_idx < df.shape[1]:
                val = df.iloc[row_idx, col_idx]
                if pd.notna(val) and str(val).strip():
                    val_str = str(val).strip()
                    # Skip formula indicators
                    if not is_formula_indicator(val_str):
                        header_parts.append(val_str)
        
        # Combine parts to create the full financial type
        if header_parts:
            combined = ' '.join(header_parts)
            if combined:
                financial_types[col_idx] = combined
    
    # Parse data rows (starting from row 15)
    for row_idx in range(15, len(df)):
        item_code = get_merged_header_value(df, row_idx, 0)  # Column A
        data_type = clean_text_value(df.iloc[row_idx, 1])  # Column B (was Trade, now Data_Type)
        
        # Skip empty rows or header rows
        if not item_code or item_code in ['Item', '(HK$']:
            continue
        
        # Parse numeric values for each financial type column
        for col_idx, fin_type in financial_types.items():
            if col_idx < df.shape[1]:
                val = df.iloc[row_idx, col_idx]
                try:
                    numeric_val = float(val) if pd.notna(val) else 0
                    # Only include non-zero values or structure rows
                    if numeric_val != 0 or '.' not in str(item_code):
                        rows.append((year, month, "Financial Status", fin_type, item_code, data_type, numeric_val))
                except (ValueError, TypeError):
                    pass
    
    return rows


def parse_time_column_header(header_val):
    """
    Parse time column header to extract month and year.
    Returns (month_number, year) or (month_number, None) if year not in header.
    """
    if pd.isna(header_val) or not header_val:
        return None, None
    
    header = str(header_val).strip().lower()
    
    # Check for month names
    for month_name, month_num in MONTH_MAP.items():
        if month_name in header:
            return month_num, None
    
    return None, None


def parse_other_sheet(xl, sheet_name, base_year=None):
    """
    Parse other sheets (Projection, Committed Cost, etc.)
    Sheet name = Financial Type
    Column headings = Time periods
    Returns list of tuples: (year, month, sheet_name, financial_type, item_code, data_type, value)
    """
    df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
    rows = []
    
    # Extract Year/Month from Report Date (cell B5, which is row 4, col 1)
    report_date = get_merged_header_value(df, 4, 1)  # B5
    year, month = parse_date_to_year_month(report_date)
    
    if year is None and base_year:
        year = base_year
    
    if year is None:
        print(f"Warning: Could not extract year from {sheet_name}")
        return []
    
    # Get time column headers (row 11)
    time_headers = [get_merged_header_value(df, 11, c) for c in range(df.shape[1])]
    
    # Build time column mapping: col_idx -> (month, year_if_specified)
    time_columns = {}
    for col_idx in range(2, df.shape[1]):  # Start from column C (index 2)
        header = time_headers[col_idx] if col_idx < len(time_headers) else ""
        if header:
            month, col_year = parse_time_column_header(header)
            if month:
                time_columns[col_idx] = (month, col_year if col_year else year)
    
    # Parse data rows (starting from row 12)
    for row_idx in range(12, len(df)):
        item_code = get_merged_header_value(df, row_idx, 0)  # Column A
        data_type = clean_text_value(df.iloc[row_idx, 1])  # Column B (was Trade, now Data_Type)
        
        # Skip empty rows or header rows
        if not item_code or item_code in ['Item', '(HK$']:
            continue
        
        # Get values for each time column
        for col_idx, (col_month, col_year) in time_columns.items():
            if col_idx < df.shape[1]:
                val = df.iloc[row_idx, col_idx]
                try:
                    numeric_val = float(val) if pd.notna(val) else 0
                    # Only include non-zero values or structure rows
                    if numeric_val != 0 or '.' not in str(item_code):
                        rows.append((col_year, col_month, sheet_name, sheet_name, item_code, data_type, numeric_val))
                except (ValueError, TypeError):
                    pass
    
    return rows


def parse_workbook(file_path):
    """
    Parse a complete Excel workbook and return flat data.
    Returns DataFrame with columns: Year, Month, Sheet_Name, Financial_Type, Item_Code, Data_Type, Value
    """
    all_rows = []
    
    xl = pd.ExcelFile(file_path)
    
    # Parse Financial Status first to get base year/month
    fs_rows = parse_financial_status_sheet(xl)
    all_rows.extend(fs_rows)
    
    # Get base year from Financial Status
    base_year = fs_rows[0][0] if fs_rows else None
    
    # Parse other sheets
    for sheet_name in xl.sheet_names:
        if sheet_name != 'Financial Status':
            other_rows = parse_other_sheet(xl, sheet_name, base_year)
            all_rows.extend(other_rows)
    
    # Create DataFrame
    if all_rows:
        df = pd.DataFrame(all_rows, columns=['Year', 'Month', 'Sheet_Name', 'Financial_Type', 'Item_Code', 'Data_Type', 'Value'])
        return df
    else:
        return pd.DataFrame(columns=['Year', 'Month', 'Sheet_Name', 'Financial_Type', 'Item_Code', 'Data_Type', 'Value'])


def parse_and_save(file_path, output_path=None):
    """
    Parse workbook and save to CSV.
    """
    df = parse_workbook(file_path)
    
    if output_path is None:
        output_path = file_path.replace('.xlsx', '_flat.csv')
    
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} rows to {output_path}")
    return df


# Test with the sample file
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "C:/Users/derri/.openclaw/media/inbound/file_13---f1726679-e4d8-439d-aaf1-292bcc355136.xlsx"
    
    df = parse_workbook(file_path)
    print(f"\nTotal rows: {len(df)}")
    print(f"\nColumns: {list(df.columns)}")
    print(f"\nSample data:")
    print(df.head(20).to_string())
    print(f"\nUnique Financial Types:")
    print(df['Financial_Type'].unique())
    print(f"\nUnique Sheets:")
    print(df['Sheet_Name'].unique())
