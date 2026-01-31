"""
Financial Chatbot Web App
Analyzes construction project financial data from Google Drive Excel files.

Folder Structure Expected:
- Year/
  - Month/
    - Project Name/
      - Excel files (.xlsx)

Features:
- Google Drive integration for file access
- Automatic CSV parsing and caching
- Interactive project selection
- Natural language financial queries
"""

import streamlit as st
import pandas as pd
import json
import os
import pickle
from pathlib import Path
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import re

# ============================================================================
# CONFIGURATION
# ============================================================================

# Google Drive folder name (root folder to search for Year/Month/Project structure)
DRIVE_ROOT_FOLDER_NAME = "Ai Chatbot Knowledge Base"  # Folder name to search for

# Local cache directory for parsed CSVs
CACHE_DIR = Path(__file__).parent / "financial_data_cache"
CACHE_DIR.mkdir(exist_ok=True)

# Token file for Google Drive authentication
TOKEN_FILE = "token_drive.pickle"

# CSV criteria file (reference)
CRITERIA_FILE = Path(__file__).parent / "CSV_Formatting_Criteria.md"

# ============================================================================
# GOOGLE DRIVE FUNCTIONS
# ============================================================================

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_root_folder(service):
    """Find the root folder by name."""
    try:
        query = f"mimeType='application/vnd.google-apps.folder' and name='{DRIVE_ROOT_FOLDER_NAME}'"
        results = service.files().list(
            q=query,
            fields="files(id, name)"
        ).execute()
        
        files = results.get('files', [])
        if files:
            return files[0]
        else:
            st.error(f"Folder '{DRIVE_ROOT_FOLDER_NAME}' not found in Google Drive!")
            return None
    except HttpError as e:
        st.error(f"Error finding root folder: {e}")
        return None


def get_drive_service():
    """Get authenticated Google Drive service."""
    creds = None
    
    # Load existing token
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    # If no credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Check for Streamlit Cloud secrets first
            try:
                # Method 1: google_credentials as a JSON string
                if 'google_credentials' in st.secrets:
                    import json as json_module
                    creds_json = st.secrets['google_credentials']
                    if isinstance(creds_json, str):
                        creds_dict = json_module.loads(creds_json)
                    else:
                        creds_dict = creds_json
                    
                    import tempfile
                    creds_file = Path(tempfile.gettempdir()) / "credentials.json"
                    with open(creds_file, 'w') as f:
                        json_module.dump(creds_dict, f)
                    
                    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Method 2: 'installed' or 'web' keys directly
                elif 'installed' in st.secrets or 'web' in st.secrets:
                    import json as json_module
                    creds_dict = {k: dict(v) if hasattr(v, 'keys') else v for k, v in st.secrets.items()}
                    creds_file = Path(tempfile.gettempdir()) / "credentials.json"
                    with open(creds_file, 'w') as f:
                        json_module.dump(creds_dict, f)
                    
                    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
                    creds = flow.run_local_server(port=0)
                else:
                    raise FileNotFoundError("No credentials in secrets")
            except Exception as secret_error:
                # Fall back to local credentials.json file
                creds_file = Path(__file__).parent / "credentials.json"
                if not creds_file.exists():
                    st.error("❌ Google Drive credentials not found!")
                    st.markdown("""
                    ### 📋 How to Set Up Google Drive Access:
                    
                    **For Streamlit Cloud:**
                    1. Go to your app Settings > Secrets
                    2. Add your Google credentials JSON
                    
                    **For Local Development:**
                    1. Download credentials.json from Google Cloud Console
                    2. Place in the same folder as this app
                    """)
                    st.download_button(
                        label="📥 Download Sample credentials.json Template",
                        data='{"installed":{"client_id":"YOUR_CLIENT_ID.apps.googleusercontent.com","client_secret":"YOUR_CLIENT_SECRET"}}',
                        file_name="credentials_template.json",
                        mime="application/json"
                    )
                    return None
                
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
                creds = flow.run_local_server(port=0)
        
        # Save token
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    try:
        service = build('drive', 'v3', credentials=creds)
        
        # Verify root folder exists
        root_folder = get_drive_root_folder(service)
        if root_folder:
            st.session_state.root_folder_id = root_folder['id']
            st.session_state.root_folder_name = root_folder['name']
        
        return service
    except Exception as e:
        st.error(f"Error building Drive service: {e}")
        return None


def list_folders(service, parent_id=None, folder_name=None):
    """List folders in Google Drive."""
    try:
        query = "mimeType='application/vnd.google-apps.folder'"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        if folder_name:
            query += f" and name='{folder_name}'"
        
        results = service.files().list(
            q=query,
            fields="files(id, name, modifiedTime)"
        ).execute()
        
        return results.get('files', [])
    except HttpError as e:
        st.error(f"Error listing folders: {e}")
        return []


def search_folders_recursive(service, path_parts, parent_id=None):
    """Recursively search for folder path."""
    if not path_parts:
        return parent_id
    
    folder_name = path_parts[0]
    folders = list_folders(service, parent_id, folder_name)
    
    if not folders:
        return None
    
    return search_folders_recursive(service, path_parts[1:], folders[0]['id'])


def find_excel_files_in_month(service, month_folder_id):
    """Find all Excel files directly in a month folder."""
    try:
        # Look for .xlsx files directly in this folder
        query = "name contains '.xlsx' and mimeType contains 'spreadsheet'"
        query += f" and '{month_folder_id}' in parents"
        
        results = service.files().list(
            q=query,
            fields="files(id, name, modifiedTime)"
        ).execute()
        
        return results.get('files', [])
    except HttpError as e:
        st.error(f"Error finding files: {e}")
        return []


def get_or_create_project_folder(service, month_folder_id, project_name):
    """Get project folder or create if not exists."""
    # Search for project folder
    query = f"mimeType='application/vnd.google-apps.folder' and name='{project_name}' and '{month_folder_id}' in parents"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    
    if results.get('files'):
        return results['files'][0]
    
    return None


def download_and_parse_excel(service, file_id, file_name, cache_dir):
    """Download Excel file, parse it, and save as CSV."""
    # Check cache first
    cache_file = cache_dir / f"{file_id}.csv"
    cache_meta = cache_dir / f"{file_id}_meta.json"
    
    # Get file modified time
    file_metadata = service.files().get(fileId=file_id, fields="modifiedTime").execute()
    modified_time = file_metadata.get('modifiedTime')
    
    # Check if cached version exists and is up to date
    if cache_file.exists() and cache_meta.exists():
        with open(cache_meta, 'r') as f:
            meta = json.load(f)
        if meta.get('modifiedTime') == modified_time:
            # Load and return cached data
            df = pd.read_csv(cache_file)
            return df, meta
    
    # Download and parse
    try:
        from io import BytesIO
        request = service.files().get_media(fileId=file_id)
        file_content = request.execute()
        
        # Parse Excel
        excel_file = BytesIO(file_content)
        xl = pd.ExcelFile(excel_file)
        
        all_data = {'sheets': {}, 'metadata': {}}
        
        # Parse Financial Status (simplified)
        if 'Financial Status' in xl.sheet_names:
            df_financial = parse_financial_status_sheet(excel_file)
            all_data['sheets']['Financial_Status'] = df_financial
        
        # Parse other sheets
        for sheet_name in ['Projection', 'Committed Cost', 'Accrual', 'Cash Flow']:
            if sheet_name in xl.sheet_names:
                df = parse_monthly_sheet(excel_file, sheet_name)
                all_data['sheets'][sheet_name.replace(' ', '_')] = df
        
        # Save to cache
        df_combined = combine_all_data(all_data)
        df_combined.to_csv(cache_file, index=False)
        
        # Save metadata
        meta = {
            'file_id': file_id,
            'file_name': file_name,
            'modifiedTime': modified_time,
            'sheet_count': len(all_data['sheets'])
        }
        with open(cache_meta, 'w') as f:
            json.dump(meta, f)
        
        return df_combined, meta
    
    except Exception as e:
        st.error(f"Error parsing {file_name}: {e}")
        return None, None


def parse_financial_status_sheet(excel_content):
    """Parse Financial Status sheet from Excel content."""
    try:
        df = pd.read_excel(excel_content, sheet_name='Financial Status', header=None)
        
        # Project info (simplified extraction)
        project_info = {
            'project_code': str(df.iloc[2, 1]).strip() if pd.notna(df.iloc[2, 1]) else '',
            'project_name': str(df.iloc[3, 1]).strip() if pd.notna(df.iloc[3, 1]) else '',
            'report_date': str(df.iloc[4, 1]).strip() if pd.notna(df.iloc[4, 1]) else '',
        }
        
        # Extract data rows (simplified columns)
        data_rows = []
        for idx in range(15, len(df)):
            item_code = df.iloc[idx, 0]
            if pd.isna(item_code) or str(item_code).strip() == '':
                continue
            
            item_str = str(item_code).strip()
            trade = df.iloc[idx, 1] if pd.notna(df.iloc[idx, 1]) else ''
            
            # Extract key columns
            budget_revision = df.iloc[idx, 5] if pd.notna(df.iloc[idx, 5]) else 0
            business_plan = df.iloc[idx, 6] if pd.notna(df.iloc[idx, 6]) else 0
            audit_report = df.iloc[idx, 7] if pd.notna(df.iloc[idx, 7]) else 0
            projection = df.iloc[idx, 9] if pd.notna(df.iloc[idx, 9]) else 0
            
            data_rows.append({
                'Item': item_str,
                'Trade': str(trade).strip() if trade else '',
                'Budget_Revision': float(pd.to_numeric(budget_revision, errors='coerce') or 0),
                'Business_Plan': float(pd.to_numeric(business_plan, errors='coerce') or 0),
                'Audit_Report_WIP': float(pd.to_numeric(audit_report, errors='coerce') or 0),
                'Projection': float(pd.to_numeric(projection, errors='coerce') or 0),
                'Source': 'Financial_Status'
            })
        
        return pd.DataFrame(data_rows)
    
    except Exception as e:
        st.error(f"Error parsing Financial Status: {e}")
        return pd.DataFrame()


def parse_monthly_sheet(excel_content, sheet_name):
    """Parse monthly data sheet (Projection, Committed Cost, Accrual, Cash Flow)."""
    try:
        df = pd.read_excel(excel_content, sheet_name=sheet_name, header=None)
        
        # Column names
        column_names = ['Item_Code', 'Trade', 'Bal_BF', 'Apr', 'May', 'Jun', 
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 
                        'Jan', 'Feb', 'Mar', 'Total']
        
        # Data starts at row 12
        data_start_row = 12
        data_df = df.iloc[data_start_row:].copy()
        data_df = data_df.reset_index(drop=True)
        
        # Assign column names
        if len(data_df.columns) >= 16:
            data_df.columns = column_names[:len(data_df.columns)]
        
        # Filter empty rows
        data_df = data_df[data_df['Item_Code'].notna()]
        
        # Clean Item_Code
        data_df['Item_Code'] = data_df['Item_Code'].apply(
            lambda x: str(x).strip() if pd.notna(x) else ''
        )
        
        # Convert numeric columns
        numeric_columns = column_names[2:]
        for col in numeric_columns:
            if col in data_df.columns:
                data_df[col] = pd.to_numeric(data_df[col], errors='coerce').fillna(0)
        
        # Clean Trade
        data_df['Trade'] = data_df['Trade'].apply(
            lambda x: str(x) if pd.notna(x) else ''
        )
        
        data_df['Source'] = sheet_name.replace(' ', '_')
        
        return data_df
    
    except Exception as e:
        st.error(f"Error parsing {sheet_name}: {e}")
        return pd.DataFrame()


def combine_all_data(all_data):
    """Combine all parsed data into a single DataFrame."""
    all_rows = []
    
    for sheet_name, df in all_data.get('sheets', {}).items():
        if not df.empty:
            # Rename columns to be consistent
            df_copy = df.copy()
            if 'Item_Code' in df_copy.columns:
                df_copy = df_copy.rename(columns={'Item_Code': 'Item'})
            all_rows.append(df_copy)
    
    if all_rows:
        combined = pd.concat(all_rows, ignore_index=True)
        return combined
    else:
        return pd.DataFrame()


# ============================================================================
# STREAMLIT APP
# ============================================================================

def main():
    st.set_page_config(
        page_title="Financial Chatbot 📊",
        page_icon="📊",
        layout="wide"
    )
    
    # Initialize session state
    if 'projects_cache' not in st.session_state:
        st.session_state.projects_cache = {}
    if 'selected_project' not in st.session_state:
        st.session_state.selected_project = None
    if 'drive_service' not in st.session_state:
        st.session_state.drive_service = None
    if 'root_folder_id' not in st.session_state:
        st.session_state.root_folder_id = None
    
    # Title
    st.title("📊 Financial Chatbot")
    st.caption("Analyze construction project financial data from Google Drive")
    
    # Display root folder name
    if st.session_state.root_folder_id:
        st.caption(f"📁 Root folder: {st.session_state.get('root_folder_name', DRIVE_ROOT_FOLDER_NAME)}")
    
    # Title
    st.title("📊 Financial Chatbot")
    st.caption("Analyze construction project financial data from Google Drive")
    
    # Sidebar - Project Selection
    st.sidebar.title("📁 Project Selection")
    
    # Initialize Google Drive
    if st.session_state.drive_service is None:
        if st.sidebar.button("🔗 Connect to Google Drive"):
            with st.spinner("Connecting to Google Drive..."):
                service = get_drive_service()
                if service:
                    st.session_state.drive_service = service
                    st.success("Connected to Google Drive!")
                else:
                    st.error("Failed to connect. Please check credentials.")
    
    # Project selection flow
    if st.session_state.drive_service:
        # Step 1: Select Year
        if not st.session_state.root_folder_id:
            st.error("Root folder not found. Please check your Google Drive.")
            return
            
        year = st.sidebar.selectbox(
            "📅 Select Year",
            options=["2024", "2025", "2026"],
            index=1 if "2025" in ["2024", "2025", "2026"] else 0
        )
        
        # Step 2: Select Month (numeric format: 01, 02, 03, etc.)
        months = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
        month = st.sidebar.selectbox("📆 Select Month (01-12)", options=months)
        
        # Month name mapping for display
        month_names = {
            "01": "January", "02": "February", "03": "March",
            "04": "April", "05": "May", "06": "June",
            "07": "July", "08": "August", "09": "September",
            "10": "October", "11": "November", "12": "December"
        }
        month_display = month_names.get(month, month)
        
        # Step 3: Find and list Excel files
        if st.sidebar.button("🔍 Find Files"):
            with st.spinner(f"Searching for files in {month_display} {year}..."):
                # Find year folder under root
                year_folder = list_folders(st.session_state.drive_service, st.session_state.root_folder_id, year)
                if not year_folder:
                    st.sidebar.error(f"Year folder '{year}' not found")
                    return
                
                # Find month folder (numeric)
                month_folder = list_folders(st.session_state.drive_service, year_folder[0]['id'], month)
                if not month_folder:
                    st.sidebar.error(f"Month folder '{month}' not found in {year}")
                    return
                
                # Find all Excel files directly in month folder
                excel_files = find_excel_files_in_month(st.session_state.drive_service, month_folder[0]['id'])
                
                if not excel_files:
                    st.sidebar.error(f"No Excel files found in {month_display} {year}")
                    return
                
                # Store in session state
                st.session_state.projects_cache = {
                    'year': year,
                    'month': month,
                    'month_folder_id': month_folder[0]['id'],
                    'files': [(f['id'], f['name']) for f in excel_files]
                }
                
                st.success(f"Found {len(excel_files)} Excel files!")
        
        # Display file list if available
        if 'files' in st.session_state.projects_cache:
            files = st.session_state.projects_cache['files']
            
            st.sidebar.markdown("---")
            st.sidebar.subheader(f"📄 Files in {month_display} {year}")
            
            # List files with numbers
            for i, (file_id, file_name) in enumerate(files, 1):
                if st.sidebar.button(f"{i}. {file_name}", key=f"file_{i}"):
                    st.session_state.selected_project = {
                        'name': file_name.replace('.xlsx', ''),
                        'file_id': file_id,
                        'file_name': file_name,
                        'year': st.session_state.projects_cache['year'],
                        'month': month_display,
                        'month_folder_id': st.session_state.projects_cache['month_folder_id']
                    }
            
            # Search input
            search_query = st.sidebar.text_input("🔍 Or search filename", "")
            if search_query:
                matching = [(fid, fname) for fid, fname in files if search_query.lower() in fname.lower()]
                if matching:
                    st.sidebar.markdown("**Matching files:**")
                    for fid, fname in matching[:5]:
                        idx = files.index((fid, fname)) + 1
                        st.sidebar.text(f"{idx}. {fname}")
                else:
                    st.sidebar.info("No matching projects found")
    
    # Main content area
    if st.session_state.selected_project:
        project = st.session_state.selected_project
        st.markdown("---")
        st.subheader(f"📁 {project['name']}")
        st.caption(f"{project['month']} {project['year']}")
        
        # Load project data
        if 'project_data' not in st.session_state:
            with st.spinner("Loading project data..."):
                # Download and parse the Excel file directly using file_id
                df, meta = download_and_parse_excel(
                    st.session_state.drive_service,
                    project['file_id'],
                    project['file_name'],
                    CACHE_DIR
                )
                if df is not None:
                    st.session_state.project_data = df
                    st.session_state.project_meta = meta
                else:
                    st.error("Failed to load file data")
        
        # Display data if loaded
        if 'project_data' in st.session_state and st.session_state.project_data is not None:
            df = st.session_state.project_data
            project = st.session_state.selected_project
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            if 'Budget_Revision' in df.columns:
                col1.metric("Budget Revision", f"${df['Budget_Revision'].sum():,.0f}")
            if 'Business_Plan' in df.columns:
                col2.metric("Business Plan", f"${df['Business_Plan'].sum():,.0f}")
            if 'Audit_Report_WIP' in df.columns:
                col3.metric("Audit Report WIP", f"${df['Audit_Report_WIP'].sum():,.0f}")
            if 'Projection' in df.columns:
                col4.metric("Projection", f"${df['Projection'].sum():,.0f}")
            
            # Quick questions
            st.markdown("### 💬 Ask about this project")
            
            q_col1, q_col2, q_col3, q_col4 = st.columns(4)
            questions = [
                ("Total Budget", "What is the total budget?"),
                ("Gross Profit", "What is the gross profit?"),
                ("Cost Breakdown", "Show cost breakdown by category"),
                ("Monthly Trend", "Show monthly trend")
            ]
            
            if q_col1.button("Total Budget"):
                if 'Budget_Revision' in df.columns:
                    total = df['Budget_Revision'].sum()
                    st.info(f"Total Budget Revision: ${total:,.2f}")
            
            if q_col2.button("Gross Profit"):
                # Find gross profit items
                gp = df[df['Trade'].str.contains('Gross Profit', case=False, na=False)]
                if not gp.empty:
                    st.write(gp[['Item', 'Trade', 'Budget_Revision', 'Projection']].to_string(index=False))
            
            if q_col3.button("Cost Breakdown"):
                # Find Cost items (category 2)
                cost_items = df[df['Item'].astype(str).str.match(r'^2(\.|$)', na=False)]
                if not cost_items.empty:
                    st.write(cost_items[['Item', 'Trade', 'Projection']].to_string(index=False))
            
            if q_col4.button("Monthly Trend"):
                # Show monthly columns
                monthly_cols = ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar']
                available_monthly = [c for c in monthly_cols if c in df.columns]
                if available_monthly:
                    monthly_totals = df[available_monthly].sum()
                    st.bar_chart(monthly_totals)
            
            # Chat input
            st.markdown("---")
            user_question = st.text_input("Ask a question about this project's financial data...")
            
            if user_question:
                # Simple question answering
                answer = answer_question(df, user_question)
                st.markdown(f"**Answer:** {answer}")
            
            # Data table toggle
            with st.expander("📊 View Raw Data"):
                st.dataframe(df, use_container_width=True)
    
    else:
        # Welcome message
        st.markdown("""
        ## Welcome to the Financial Chatbot! 🎉
        
        ### How to use:
        1. Click **"Connect to Google Drive"** in the sidebar
        2. Select **Year** and **Month**
        3. Click **"Find Projects"** to search your Google Drive
        4. Select a project by clicking its name
        5. Ask questions about the financial data!
        
        ### Expected Folder Structure:
        ```
        Google Drive/
        └── 2025/
            ├── January/
            │   ├── Project Alpha/
            │   │   └── Financial Report.xlsx
            │   └── Project Beta/
            │       └── Financial Report.xlsx
            └── February/
                └── ...
        ```
        """)


def answer_question(df: pd.DataFrame, question: str) -> str:
    """Answer a question about the financial data."""
    question = question.lower()
    
    # Total questions
    if 'total' in question and 'budget' in question:
        if 'Budget_Revision' in df.columns:
            return f"Total Budget Revision: ${df['Budget_Revision'].sum():,.2f}"
    
    if 'total' in question and 'business plan' in question:
        if 'Business_Plan' in df.columns:
            return f"Total Business Plan: ${df['Business_Plan'].sum():,.2f}"
    
    if 'total' in question and 'projection' in question:
        if 'Projection' in df.columns:
            return f"Total Projection: ${df['Projection'].sum():,.2f}"
    
    if 'total' in question and 'cost' in question:
        # Find Cost items
        cost_items = df[df['Item'].astype(str).str.match(r'^2(\.|$)', na=False)]
        if 'Projection' in cost_items.columns:
            return f"Total Cost (Projection): ${cost_items['Projection'].sum():,.2f}"
    
    # Gross profit
    if 'gross profit' in question:
        gp = df[df['Trade'].str.contains('Gross Profit', case=False, na=False)]
        if not gp.empty:
            if 'Projection' in gp.columns:
                return f"Gross Profit items found:\n" + \
                       gp[['Item', 'Trade', 'Projection']].to_string(index=False)
            else:
                return f"Gross Profit items: {len(gp)} items found"
    
    # Income
    if 'income' in question:
        income = df[df['Item'].astype(str).str.match(r'^1(\.|$)', na=False)]
        if 'Projection' in income.columns:
            return f"Total Income (Projection): ${income['Projection'].sum():,.2f}"
    
    # Default response
    return "I couldn't understand the question. Try asking about:\n" \
           "- Total budget\n" \
           "- Total business plan\n" \
           "- Total projection\n" \
           "- Gross profit\n" \
           "- Income breakdown"


if __name__ == "__main__":
    main()
# Build: 2026-01-31 16:13:53
