"""
Financial Chatbot with Auto-Preprocessing
Automatically converts Excel files to CSV on first run.
Provides query functions for financial data.
"""

import os
import pandas as pd
from financial_preprocessor import preprocess_folder, load_all_data, METADATA_FILE, DEFAULT_DATA_ROOT, GDRIVE_SOURCE

# In-memory cache
_data_cache = None


def initialize(data_root=None, force_reprocess=False):
    """
    Initialize the chatbot.
    Preprocesses all Excel files if needed.
    """
    global _data_cache
    
    root = data_root or DEFAULT_DATA_ROOT
    
    print(f"Initializing Financial Chatbot...")
    print(f"Data root: {root}")
    print(f"Force reprocess: {force_reprocess}")
    
    if force_reprocess:
        print("\n[WARN] Repreprocessing all files...")
        preprocess_folder(root, force=True)
    
    print("\nLoading preprocessed data...")
    _data_cache = load_all_data(root)
    
    print(f"\n[OK] Financial Chatbot Ready!")
    print(f"  Total records: {len(_data_cache) if not _data_cache.empty else 0}")
    print(f"  Data index: {os.path.join(root, METADATA_FILE)}")
    
    return _data_cache


def get_data():
    """Get the loaded data frame."""
    global _data_cache
    if _data_cache is None or _data_cache.empty:
        initialize()
    return _data_cache


def query(**filters):
    """
    Query the financial data.
    
    Examples:
        query(Year=2025, Month=12)
        query(Sheet_Name='Projection', Item_Code='1.1')
        query(Financial_Type='1st Working Budget B', Trade='Income')
        query(Year=2025, Sheet_Name=['Projection', 'Committed Cost'])
    """
    df = get_data()
    if df.empty:
        return pd.DataFrame()
    
    result = df.copy()
    
    for key, value in filters.items():
        if key not in df.columns:
            continue
        
        if isinstance(value, list):
            result = result[result[key].isin(value)]
        else:
            result = result[result[key] == value]
    
    return result


def query_by_month(year, month):
    """Get all data for a specific month."""
    return query(Year=year, Month=month)


def query_by_sheet(sheet_name):
    """Get all data from a specific sheet."""
    return query(Sheet_Name=sheet_name)


def query_by_item(item_code):
    """Get all data for a specific item code."""
    return query(Item_Code=item_code)


def query_by_trade(trade_name):
    """Get all data for a specific trade."""
    return query(Trade=trade_name)


def summary_by_sheet():
    """Get summary statistics grouped by sheet."""
    df = get_data()
    if df.empty:
        return {}
    
    return df.groupby('Sheet_Name').agg({
        'Value': ['sum', 'mean', 'count']
    }).round(2)


def summary_by_month():
    """Get summary statistics grouped by month."""
    df = get_data()
    if df.empty:
        return {}
    
    return df.groupby('Month')['Value'].agg(['sum', 'count']).round(2)


def list_available_years():
    """List all available years in the data."""
    df = get_data()
    if 'Year' in df.columns:
        return sorted(df['Year'].unique().tolist())
    return []


def list_available_sheets():
    """List all available sheet names."""
    df = get_data()
    if 'Sheet_Name' in df.columns:
        return sorted(df['Sheet_Name'].unique().tolist())
    return []


def list_available_months():
    """List all available months."""
    df = get_data()
    if 'Month' in df.columns:
        return sorted(df['Month'].unique().tolist())
    return []


# Quick query helpers
def show_projection_by_month(item_code='1.1'):
    """Show projection values by month for an item."""
    proj = query(Sheet_Name='Projection', Item_Code=item_code)
    if proj.empty:
        return pd.DataFrame()
    return proj.pivot_table(index='Item_Code', columns='Month', values='Value', aggfunc='sum')


def show_financial_status_summary():
    """Show financial status summary."""
    fs = query(Sheet_Name='Financial Status')
    if fs.empty:
        return pd.DataFrame()
    return fs.pivot_table(index=['Item_Code', 'Trade'], columns='Financial_Type', values='Value')


def compare_budget_vs_actual():
    """Compare budget (Tender, 1st Working Budget) vs actual (Audit Report, Projection)."""
    budget_types = ['Tender A', '1st Working Budget B']
    actual_types = ['Audit Report (WIP) J', 'Projection as at I']
    
    df = query(Financial_Type=budget_types + actual_types)
    if df.empty:
        return pd.DataFrame()
    
    return df.pivot_table(
        index=['Item_Code', 'Trade'], 
        columns='Financial_Type', 
        values='Value',
        aggfunc='sum'
    )


# Summary metrics for dashboard
def get_projected_gross_profit():
    """
    Get Projected Gross Profit (before adjustment).
    Source: Projection sheet, Trade = Gross Profit (Item 3.0-4.3) or Gross Profit (Item 1.0-2.0)
    """
    # Query Projection sheet for Gross Profit items
    proj = query(Sheet_Name='Projection')
    if proj.empty:
        return 0.0
    
    # Filter for Gross Profit trades
    gp_trades = proj[proj['Trade'].str.contains('Gross Profit', case=False, na=False)]
    
    if gp_trades.empty:
        return 0.0
    
    # Sum all Gross Profit values from Projection
    return gp_trades['Value'].sum()


def get_wip_gross_profit():
    """
    Get WIP Gross Profit (before adjustment).
    Source: Financial Status sheet, Financial_Type = Audit Report (WIP) J, Trade = Gross Profit
    """
    # Query Audit Report (WIP) J for Gross Profit items
    wip = query(Sheet_Name='Financial Status', Financial_Type='Audit Report (WIP) J')
    if wip.empty:
        return 0.0
    
    # Filter for Gross Profit trades
    gp_trades = wip[wip['Trade'].str.contains('Gross Profit', case=False, na=False)]
    
    if gp_trades.empty:
        return 0.0
    
    # Sum all Gross Profit values from Audit Report (WIP)
    return gp_trades['Value'].sum()


def get_cash_flow():
    """
    Get Cash Flow amount (Gross Profit related).
    Source: Cash Flow sheet, Trade = Gross Profit
    """
    # Query Cash Flow sheet for Gross Profit items
    cf = query(Sheet_Name='Cash Flow')
    if cf.empty:
        return 0.0
    
    # Filter for Gross Profit trades
    gp_trades = cf[cf['Trade'].str.contains('Gross Profit', case=False, na=False)]
    
    if gp_trades.empty:
        return 0.0
    
    # Sum all Gross Profit values from Cash Flow
    return gp_trades['Value'].sum()


def get_financial_summary():
    """
    Get all three key financial metrics.
    Returns dict with Projected GP, WIP GP, and Cash Flow.
    """
    return {
        'projected_gross_profit': get_projected_gross_profit(),
        'wip_gross_profit': get_wip_gross_profit(),
        'cash_flow': get_cash_flow()
    }


# Initialize on import (optional - can be disabled if needed)
# initialize()


# Test module
if __name__ == "__main__":
    print("=== Financial Chatbot Test ===\n")
    
    # Initialize
    initialize(force_reprocess=False)
    
    print(f"\nAvailable years: {list_available_years()}")
    print(f"Available sheets: {list_available_sheets()}")
    print(f"Available months: {list_available_months()}")
    
    print(f"\n=== Projection by Month (Item 1.1) ===")
    print(show_projection_by_month('1.1'))
    
    print(f"\n=== Financial Status Summary ===")
    print(show_financial_status_summary().head(10))
