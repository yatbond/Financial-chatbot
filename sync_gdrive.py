"""
Sync financial data from Google Drive (G:) to local workspace.
"""

import os
import shutil
from financial_preprocessor import preprocess_folder, DEFAULT_DATA_ROOT, GDRIVE_SOURCE


def sync_from_gdrive(year=None, month=None, dry_run=True):
    """
    Copy Excel files from Google Drive to local workspace.
    
    Args:
        year: Year folder (e.g., 2025)
        month: Month folder (e.g., 12)
        dry_run: If True, just print what would be copied
    """
    gdrive_year_path = os.path.join(GDRIVE_SOURCE, str(year)) if year else None
    gdrive_month_path = os.path.join(gdrive_year_path, str(month).zfill(2)) if gdrive_year_path and month else None
    
    if gdrive_month_path and os.path.exists(gdrive_month_path):
        print(f"Source: {gdrive_month_path}")
    elif gdrive_year_path and os.path.exists(gdrive_year_path):
        print(f"Source: {gdrive_year_path}")
        print(f"Available months: {os.listdir(gdrive_year_path)}")
        return
    else:
        print(f"Source not found: {gdrive_month_path or gdrive_year_path}")
        return
    
    # Find Excel files
    excel_files = [f for f in os.listdir(gdrive_month_path) if f.endswith('.xlsx')]
    print(f"\nFound {len(excel_files)} Excel files:")
    for f in excel_files:
        print(f"  - {f}")
    
    if dry_run:
        print(f"\n[DRY RUN] Would copy {len(excel_files)} files to {DEFAULT_DATA_ROOT}")
        return
    
    # Create destination folder
    dest_folder = os.path.join(DEFAULT_DATA_ROOT, str(year), str(month).zfill(2))
    os.makedirs(dest_folder, exist_ok=True)
    
    # Copy files
    for f in excel_files:
        src = os.path.join(gdrive_month_path, f)
        dst = os.path.join(dest_folder, f)
        shutil.copy2(src, dst)
        print(f"Copied: {f}")
    
    print(f"\n[OK] Copied {len(excel_files)} files to {dest_folder}")
    
    # Run preprocessor
    print(f"\nRunning preprocessor...")
    preprocess_folder(DEFAULT_DATA_ROOT)
    
    return len(excel_files)


def sync_all_from_gdrive():
    """Sync all available data from Google Drive."""
    if not os.path.exists(GDRIVE_SOURCE):
        print(f"Google Drive path not found: {GDRIVE_SOURCE}")
        return
    
    # Find all years
    years = [d for d in os.listdir(GDRIVE_SOURCE) if d.isdigit()]
    print(f"Available years: {years}")
    
    total_files = 0
    for year in sorted(years):
        year_path = os.path.join(GDRIVE_SOURCE, year)
        months = [m for m in os.listdir(year_path) if m.isdigit()]
        
        for month in sorted(months):
            count = sync_from_gdrive(year=year, month=month, dry_run=False)
            if count:
                total_files += count
    
    print(f"\n=== TOTAL: {total_files} files synced ===")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # First arg = year, second = month
        year = sys.argv[1]
        month = sys.argv[2] if len(sys.argv) > 2 else '12'
        sync_from_gdrive(year=year, month=month, dry_run=False)
    else:
        # Sync all
        sync_all_from_gdrive()
