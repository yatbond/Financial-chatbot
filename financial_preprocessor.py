"""
Financial Data Preprocessor
Scans folders for Excel workbooks, converts to flat CSV format.
Stores metadata for chatbot quick-loading.

Supports both local G: drive and Google Drive API (for cloud deployment).
"""

import os
import json
import pandas as pd
from pathlib import Path
from excel_parser import parse_workbook

METADATA_FILE = "financial_data_index.json"

# Configuration
DEFAULT_DATA_ROOT = "G:/My Drive/Ai Chatbot Knowledge Base"
FALLBACK_GDRIVE_PATH = "Ai Chatbot Knowledge Base"  # For API access


def find_excel_files(root_folder):
    """Find all Excel files recursively."""
    excel_files = []
    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file.endswith(('.xlsx', '.xls')) and not file.startswith('~'):
                excel_files.append(os.path.join(root, file))
    return excel_files


def is_gdrive_available():
    """Check if G: drive is available."""
    return os.path.exists('G:/My Drive')


def get_data_source_path():
    """
    Get the data source path.
    Returns (path, source_type) where source_type is 'local' or 'api'.
    """
    # Check if G: drive is available (local machine)
    if is_gdrive_available():
        return DEFAULT_DATA_ROOT, 'local'
    
    # Try Google Drive API (for cloud deployment)
    try:
        from gdrive_api import load_credentials, find_excel_files_in_gdrive
        if load_credentials():
            files = find_excel_files_in_gdrive(FALLBACK_GDRIVE_PATH)
            if files:
                return FALLBACK_GDRIVE_PATH, 'api'
    except ImportError:
        pass
    
    # Fall back to local path anyway (might work on some setups)
    if os.path.exists(DEFAULT_DATA_ROOT):
        return DEFAULT_DATA_ROOT, 'local'
    
    return DEFAULT_DATA_ROOT, 'local'


def get_subfolder_name(excel_path):
    """Get the immediate parent folder name."""
    return os.path.basename(os.path.dirname(excel_path))


def preprocess_folder(root_folder, force=False):
    """
    Preprocess all Excel files in folder.
    Converts each to CSV and creates index.
    Returns list of data sources.
    """
    index = {
        "version": "1.0",
        "root_folder": root_folder,
        "sources": []
    }
    
    excel_files = find_excel_files(root_folder)
    
    for excel_path in excel_files:
        csv_path = excel_path.replace('.xlsx', '_flat.csv').replace('.xls', '_flat.csv')
        subfolder = get_subfolder_name(excel_path)
        
        # Check if already processed (skip unless force=True)
        if not force and os.path.exists(csv_path):
            # Load existing data to get metadata
            try:
                df = pd.read_csv(csv_path)
                year_range = f"{df['Year'].min()}-{df['Year'].max()}" if 'Year' in df.columns else "unknown"
                index["sources"].append({
                    "excel": excel_path,
                    "csv": csv_path,
                    "subfolder": subfolder,
                    "rows": len(df),
                    "year_range": year_range,
                    "sheets": df['Sheet_Name'].unique().tolist() if 'Sheet_Name' in df.columns else []
                })
                print(f"[OK] Already exists: {csv_path}")
                continue
            except Exception as e:
                print(f"[WARN] Error reading {csv_path}: {e}")
        
        # Process new file
        print(f"Processing: {excel_path}")
        try:
            df = parse_workbook(excel_path)
            df.to_csv(csv_path, index=False)
            
            index["sources"].append({
                "excel": excel_path,
                "csv": csv_path,
                "subfolder": subfolder,
                "rows": len(df),
                "year_range": f"{df['Year'].min()}-{df['Year'].max()}" if 'Year' in df.columns else "unknown",
                "sheets": df['Sheet_Name'].unique().tolist() if 'Sheet_Name' in df.columns else []
            })
            print(f"[OK] Saved: {csv_path} ({len(df)} rows)")
        except Exception as e:
            print(f"[ERR] Error processing {excel_path}: {e}")
    
    # Save index
    index_path = os.path.join(root_folder, METADATA_FILE)
    with open(index_path, 'w') as f:
        json.dump(index, f, indent=2)
    print(f"\n[OK] Index saved: {index_path}")
    
    return index


def load_all_data(root_folder):
    """
    Load all preprocessed CSV files.
    Returns combined DataFrame.
    """
    # Check if data folder exists
    if not os.path.exists(root_folder):
        print(f"[WARN] Data folder not found: {root_folder}")
        print("Returning empty dataset. Please configure the data path.")
        return pd.DataFrame()
    
    index_path = os.path.join(root_folder, METADATA_FILE)
    
    if not os.path.exists(index_path):
        print("No index found. Preprocessing...")
        preprocess_folder(root_folder)
    
    if not os.path.exists(index_path):
        print(f"[WARN] Index file not found: {index_path}")
        return pd.DataFrame()
    
    with open(index_path, 'r') as f:
        index = json.load(f)
    
    all_dfs = []
    for source in index["sources"]:
        if os.path.exists(source["csv"]):
            df = pd.read_csv(source["csv"])
            df["_source_file"] = source["excel"]
            df["_source_subfolder"] = source["subfolder"]
            all_dfs.append(df)
            print(f"Loaded: {source['csv']} ({len(df)} rows)")
    
    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        print(f"\nTotal: {len(combined)} rows from {len(all_dfs)} files")
        return combined
    else:
        return pd.DataFrame()


# Test preprocessor
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        root = sys.argv[1]
    else:
        # Default to financial_data folder
        root = DEFAULT_DATA_ROOT
    
    print(f"Preprocessing: {root}\n")
    index = preprocess_folder(root)
    
    print(f"\n=== INDEX ===")
    print(json.dumps(index, indent=2))
