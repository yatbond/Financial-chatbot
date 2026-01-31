"""
Simplified Financial Status Parser
Creates a clean CSV with project info and key financial figures.
"""

import pandas as pd
import json
from pathlib import Path


def parse_financial_status(file_path: str) -> dict:
    """
    Parse Financial Status sheet into simplified format.
    
    Structure:
    - Project Info: A1:C9
    - Data columns: A (item), B (trade), F (Budget Revision), G (Business Plan), 
                     H (Audit Report WIP), I (Projection)
    """
    file_path = Path(file_path)
    df = pd.read_excel(file_path, sheet_name='Financial Status', header=None)
    
    result = {
        'project_info': {},
        'data': []
    }
    
    # === Extract Project Info (A1:C9) ===
    project_info = {}
    
    # Row 0: Company name (A1)
    project_info['company'] = str(df.iloc[0, 0]).strip() if pd.notna(df.iloc[0, 0]) else ''
    
    # Row 2: Project Code (A2:C2)
    if pd.notna(df.iloc[2, 0]) and 'Project Code:' in str(df.iloc[2, 0]):
        project_info['project_code'] = str(df.iloc[2, 1]).strip() if pd.notna(df.iloc[2, 1]) else ''
    
    # Row 3: Project Name (A3:C3)
    if pd.notna(df.iloc[3, 0]) and 'Project Name:' in str(df.iloc[3, 0]):
        project_info['project_name'] = str(df.iloc[3, 1]).strip() if pd.notna(df.iloc[3, 1]) else ''
    
    # Row 4: Report Date (A4:C4)
    if pd.notna(df.iloc[4, 0]) and 'Report Date:' in str(df.iloc[4, 0]):
        report_date = str(df.iloc[4, 1]).strip() if pd.notna(df.iloc[4, 1]) else ''
        project_info['report_date'] = report_date
        # Extract month from report date for context
        project_info['report_month'] = report_date  # Use full date for reference
    
    # Row 5: Start Date (A5:C5)
    if pd.notna(df.iloc[5, 0]) and 'Start Date:' in str(df.iloc[5, 0]):
        project_info['start_date'] = str(df.iloc[5, 1]).strip() if pd.notna(df.iloc[5, 1]) else ''
    
    # Row 6: Complete Date (A6:C6)
    if pd.notna(df.iloc[6, 0]) and 'Complete Date:' in str(df.iloc[6, 0]):
        complete_val = str(df.iloc[6, 1]).strip() if pd.notna(df.iloc[6, 1]) else ''
        # Clean up - extract date (format: YYYY-MM-DD)
        import re
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', complete_val)
        project_info['complete_date'] = date_match.group(1) if date_match else complete_val.split('\n')[0].strip()
    
    # Row 7: Target Complete Date (A7:C7)
    if pd.notna(df.iloc[7, 0]) and 'Target Complete Date:' in str(df.iloc[7, 0]):
        target_val = str(df.iloc[7, 1]).strip() if pd.notna(df.iloc[7, 1]) else ''
        # Clean up - extract date (format: YYYY-MM-DD)
        import re
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', target_val)
        project_info['target_complete_date'] = date_match.group(1) if date_match else target_val.split('\n')[0].strip()
    
    result['project_info'] = project_info
    
    # === Extract Data ===
    # Column mapping (0-indexed):
    # 0 = Item (A)
    # 1 = Trade (B)
    # 5 = Budget Revision (D=B+C) - Revision as at
    # 6 = Business Plan (G)
    # 7 = Audit Report WIP (J)
    # 9 = Projection (I)
    
    data_rows = []
    
    # Data starts after headers (row 15+ based on earlier analysis)
    for idx in range(15, len(df)):
        item_code = df.iloc[idx, 0]
        trade = df.iloc[idx, 1]
        
        # Skip empty rows or non-item rows
        if pd.isna(item_code) or str(item_code).strip() == '':
            continue
        
        item_str = str(item_code).strip()
        
        # Extract numeric values
        budget_revision = df.iloc[idx, 5] if pd.notna(df.iloc[idx, 5]) else 0
        business_plan = df.iloc[idx, 6] if pd.notna(df.iloc[idx, 6]) else 0
        audit_report = df.iloc[idx, 7] if pd.notna(df.iloc[idx, 7]) else 0
        projection = df.iloc[idx, 9] if pd.notna(df.iloc[idx, 9]) else 0
        
        # Convert to numeric
        budget_revision = pd.to_numeric(budget_revision, errors='coerce')
        business_plan = pd.to_numeric(business_plan, errors='coerce')
        audit_report = pd.to_numeric(audit_report, errors='coerce')
        projection = pd.to_numeric(projection, errors='coerce')
        
        # Only include rows with at least some data
        if budget_revision == 0 and business_plan == 0 and audit_report == 0 and projection == 0:
            # Check if it's a category header (simple integer like "1", "2")
            if not '.' in item_str:
                # It's a category header - include it with zeros
                data_rows.append({
                    'Item': item_str,
                    'Trade': str(trade).strip() if pd.notna(trade) else '',
                    'Budget_Revision': 0,
                    'Business_Plan': 0,
                    'Audit_Report_WIP': 0,
                    'Projection': 0
                })
            continue
        
        data_rows.append({
            'Item': item_str,
            'Trade': str(trade).strip() if pd.notna(trade) else '',
            'Budget_Revision': round(budget_revision, 2) if pd.notna(budget_revision) else 0,
            'Business_Plan': round(business_plan, 2) if pd.notna(business_plan) else 0,
            'Audit_Report_WIP': round(audit_report, 2) if pd.notna(audit_report) else 0,
            'Projection': round(projection, 2) if pd.notna(projection) else 0
        })
    
    result['data'] = data_rows
    
    return result


def save_simplified_csv(data: dict, output_path: str):
    """Save simplified data to CSV."""
    # Create DataFrame from data
    df = pd.DataFrame(data['data'])
    
    # Reorder columns
    df = df[['Item', 'Trade', 'Budget_Revision', 'Business_Plan', 'Audit_Report_WIP', 'Projection']]
    
    # Save to CSV
    df.to_csv(output_path, index=False)
    print(f"Saved: {output_path}")
    
    return df


def save_project_info(data: dict, output_path: str):
    """Save project info to JSON."""
    with open(output_path, 'w') as f:
        json.dump(data['project_info'], f, indent=2)
    print(f"Saved: {output_path}")


if __name__ == '__main__':
    excel_file = r'C:\Users\derri\.openclaw\media\inbound\file_5---f1932325-a544-44fe-a5d2-5235b24c1efb.xlsx'
    output_csv = r'C:\Users\derri\.openclaw\workspace\Financial_Status_Simple.csv'
    output_json = r'C:\Users\derri\.openclaw\workspace\Financial_Status_ProjectInfo.json'
    
    print("Parsing Financial Status...")
    data = parse_financial_status(excel_file)
    
    # Save outputs
    save_project_info(data, output_json)
    df = save_simplified_csv(data, output_csv)
    
    # Print summary
    print("\n=== Project Info ===")
    for k, v in data['project_info'].items():
        print(f"{k}: {v}")
    
    print(f"\n=== Data: {len(df)} rows ===")
    print(df.head(20).to_string(index=False))
    
    print("\n=== Column Totals ===")
    for col in ['Budget_Revision', 'Business_Plan', 'Audit_Report_WIP', 'Projection']:
        print(f"{col}: {df[col].sum():,.2f}")
