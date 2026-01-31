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
                    
                    # Check if service account
                    if creds_dict.get('type') == 'service_account':
                        from google.oauth2 import service_account
                        creds = service_account.Credentials.from_service_account_info(
                            creds_dict, scopes=SCOPES
                        )
                    else:
                        # Regular OAuth flow (needs browser - won't work on cloud)
                        import tempfile
                        creds_file = Path(tempfile.gettempdir()) / "credentials.json"
                        with open(creds_file, 'w') as f:
                            json_module.dump(creds_dict, f)
                        
                        flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
                        creds = flow.run_local_server(port=0)
                
                # Method 2: 'installed' or 'web' keys directly (OAuth)
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
            except Exception:
                # Fall back to local credentials.json file
                creds_file = Path(__file__).parent / "credentials.json"
                if not creds_file.exists():
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


def find_excel_files_in_month(service, month_folder_id):
    """Find Excel files in month folder AND all subfolders."""
    try:
        all_files = []
        
        # Find files directly in month folder
        query_direct = f"('{month_folder_id}' in parents)"
        results_direct = service.files().list(
            q=query_direct,
            fields="files(id, name, mimeType, modifiedTime)"
        ).execute()
        
        files_direct = results_direct.get('files', [])
        all_files.extend(files_direct)
        
        # Also find subfolders and search inside them
        query_folders = f"mimeType='application/vnd.google-apps.folder' and '{month_folder_id}' in parents"
        results_folders = service.files().list(
            q=query_folders,
            fields="files(id, name)"
        ).execute()
        
        subfolders = results_folders.get('files', [])
        subfolder_names = [s['name'] for s in subfolders]
        st.write(f"Debug - Found {len(subfolders)} subfolders: {subfolder_names}")
        
        # Search each subfolder
        for subfolder in subfolders:
            query_sub = f"'{subfolder['id']}' in parents"
            results_sub = service.files().list(
                q=query_sub,
                fields="files(id, name, mimeType, modifiedTime)"
            ).execute()
            all_files.extend(results_sub.get('files', []))
        
        # Filter for Excel files (xlsx or Google Sheets)
        excel_files = []
        for f in all_files:
            name = f.get('name', '').lower()
            mime = f.get('mimeType', '')
            if ('.xlsx' in name or '.xls' in name or 
                mime == 'application/vnd.google-apps.spreadsheet' or
                name.endswith('.xlsx') or name.endswith('.xls')):
                excel_files.append(f)
        
        st.write(f"Debug - Total files found: {len(all_files)}")
        
        # Show file names safely
        file_list = []
        for f in all_files:
            name = f.get('name', 'Unknown')
            file_list.append(name)
        st.write(f"Debug - Files: {file_list}")
        st.write(f"Debug - Excel files: {len(excel_files)}")
        
        return excel_files
    except HttpError as e:
        st.error(f"Error searching files: {e}")
        return []
    except HttpError as e:
        st.error(f"Error searching files: {e}")
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
            row_data = {
                'Item': item_str,
                'Trade': str(trade).strip(),
            }
            
            # Extract numeric columns dynamically
            for col_idx in range(2, len(df.columns)):
                col_header = str(df.iloc[7, col_idx]).strip() if pd.notna(df.iloc[7, col_idx]) else ''
                if col_header:
                    value = df.iloc[idx, col_idx]
                    if pd.notna(value):
                        try:
                            row_data[col_header] = float(value)
                        except (ValueError, TypeError):
                            row_data[col_header] = str(value)
                    else:
                        row_data[col_header] = 0.0
            
            data_rows.append(row_data)
        
        df_result = pd.DataFrame(data_rows)
        return df_result
    
    except Exception as e:
        st.error(f"Error parsing Financial Status: {e}")
        return pd.DataFrame()


def parse_monthly_sheet(excel_content, sheet_name):
    """Parse monthly sheet (Projection, Committed Cost, Accrual, Cash Flow)."""
    try:
        df = pd.read_excel(excel_content, sheet_name=sheet_name, header=None)
        
        # Data rows start from row 14
        data_rows = []
        for idx in range(14, len(df)):
            item_code = df.iloc[idx, 0]
            if pd.isna(item_code) or str(item_code).strip() == '':
                continue
            
            row_data = {'Item': str(item_code).strip()}
            
            # Extract columns based on standard structure
            col_mappings = {
                1: 'Trade',
                2: 'Original_Budget',
                3: 'Approved_PO',
                4: 'Pending_PO',
                5: 'Commitments',
                6: 'Forecast',
                7: 'Variance',
                8: 'April',
                9: 'May',
                10: 'June',
                11: 'July',
                12: 'August',
                13: 'September',
                14: 'October',
                15: 'November',
                16: 'December',
                17: 'January',
                18: 'February',
                19: 'March',
            }
            
            for col_idx, col_name in col_mappings.items():
                if col_idx < len(df.columns):
                    value = df.iloc[idx, col_idx]
                    if pd.notna(value):
                        try:
                            row_data[col_name] = float(value)
                        except (ValueError, TypeError):
                            row_data[col_name] = str(value)
                    else:
                        row_data[col_name] = 0.0
            
            data_rows.append(row_data)
        
        df_result = pd.DataFrame(data_rows)
        return df_result
    
    except Exception as e:
        st.error(f"Error parsing {sheet_name}: {e}")
        return pd.DataFrame()


def combine_all_data(all_data):
    """Combine data from multiple sheets into a single DataFrame."""
    all_dfs = []
    
    for sheet_name, df in all_data['sheets'].items():
        if not df.empty:
            df_copy = df.copy()
            df_copy['Source'] = sheet_name
            all_dfs.append(df_copy)
    
    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        # Consolidate duplicates by Item
        if 'Item' in combined.columns:
            combined = combined.groupby('Item').agg(lambda x: x.first_valid_index() if x.isna().all() else x.sum(min_count=1)).reset_index()
        return combined
    
    return pd.DataFrame()


def find_project_files(service, year_folder_id, month_folder_id):
    """Find Excel files in year and month folders."""
    # Find files in year folder
    year_files = find_excel_files_in_month(service, year_folder_id)
    
    # Find files in month folder  
    month_files = find_excel_files_in_month(service, month_folder_id)
    
    # Combine and deduplicate
    all_files = {}
    for f in year_files + month_files:
        all_files[f['id']] = f
    
    return list(all_files.values())


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
                return f"Gross Profit: ${gp['Projection'].sum():,.2f}"
    
    # Project overhead
    if 'overhead' in question or 'project overhead' in question:
        oh = df[df['Trade'].str.contains('Project Overhead', case=False, na=False)]
        if not oh.empty:
            if 'Projection' in oh.columns:
                return f"Project Overhead: ${oh['Projection'].sum():,.2f}"
    
    # Fee
    if 'fee' in question:
        fee = df[df['Trade'].str.contains('Fee', case=False, na=False)]
        if not fee.empty:
            if 'Projection' in fee.columns:
                return f"Fee: ${fee['Projection'].sum():,.2f}"
    
    # Bond
    if 'bond' in question:
        bond = df[df['Trade'].str.contains('Bond', case=False, na=False)]
        if not bond.empty:
            if 'Projection' in bond.columns:
                return f"Bond: ${bond['Projection'].sum():,.2f}"
    
    # Monthly breakdown
    if 'april' in question and 'cost' in question:
        if 'April' in df.columns:
            return f"April Cost: ${df['April'].sum():,.2f}"
    
    if 'may' in question and 'cost' in question:
        if 'May' in df.columns:
            return f"May Cost: ${df['May'].sum():,.2f}"
    
    # Default response
    return "I'm not sure about that. Try asking about: Total Budget, Gross Profit, Cost Breakdown, Project Overhead, Fee, Bond, or Monthly Costs."


def main():
    st.set_page_config(
        page_title="Financial Chatbot 📊",
        page_icon="📊",
        layout="centered"
    )

    # Dark blue theme
    st.markdown("""
    <style>
    .stApp {
        background-color: #0c1929;
    }
    .stTitle, .stMarkdown, .stCaption, .stText, p, h1, h2, h3, h4 {
        color: #e0e6ed !important;
    }
    .stSelectbox label, .stButton label {
        color: #e0e6ed !important;
    }
    div[data-testid="stMetricValue"] {
        color: #4fc3f7 !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #90caf9 !important;
    }
    .stSuccess, .stInfo {
        background-color: #1e3a5f !important;
        color: #e0e6ed !important;
    }
    .stError {
        background-color: #4a1515 !important;
        color: #ffcdd2 !important;
    }
    button {
        background-color: #1e4a7a !important;
        color: #e0e6ed !important;
        border: 1px solid #2d5a8a !important;
    }
    button:hover {
        background-color: #2d5a8a !important;
    }
    div[data-testid="stExpander"] {
        background-color: #152238 !important;
    }
    input {
        background-color: #1a2a3a !important;
        color: #e0e6ed !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'projects_cache' not in st.session_state:
        st.session_state.projects_cache = {}
    if 'selected_project' not in st.session_state:
        st.session_state.selected_project = None
    if 'drive_service' not in st.session_state:
        st.session_state.drive_service = None
    if 'root_folder_id' not in st.session_state:
        st.session_state.root_folder_id = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Header with Instructions button
    col_h1, col_h2 = st.columns([1, 0.1])
    with col_h1:
        st.title("📊 Financial Chatbot")
    with col_h2:
        with st.popover("❓"):
            st.markdown("""
            ### How to Use
            
            1. **Select Year & Month** from the dropdowns
            2. **Click "Find Files"** to search Google Drive
            3. **Select a project** from the list
            4. **Ask questions** about the financial data!
            
            ---
            
            ### Expected Folder Structure
            
            ```
            Google Drive/
            └── Ai Chatbot Knowledge Base/
                └── 2025/
                    ├── 01/
                    │   └── Project Alpha.xlsx
                    └── 02/
                        └── Project Beta.xlsx
            ```
            """)
    
    # Auto-connect to Google Drive on load
    if st.session_state.drive_service is None:
        with st.spinner("Connecting to Google Drive..."):
            service = get_drive_service()
            if service:
                st.session_state.drive_service = service
                st.success("Connected to Google Drive!")
            else:
                st.warning("Could not connect to Google Drive.")
                st.info("Check your secrets configuration in Streamlit Cloud settings.")
    
    # Check if root folder exists
    if not st.session_state.root_folder_id:
        st.warning(f"Root folder '{DRIVE_ROOT_FOLDER_NAME}' not found in Google Drive!")
        st.info("Please ensure you have shared the folder with the service account.")
        return
    
    # Selection Controls
    st.markdown("### 📁 Select Project")
    
    col1, col2 = st.columns(2)
    
    with col1:
        year = st.selectbox("Year", options=["2024", "2025", "2026"], index=1, key="year_select")
    
    with col2:
        months = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
        month_names = {
            "01": "January", "02": "February", "03": "March",
            "04": "April", "05": "May", "06": "June",
            "07": "July", "08": "August", "09": "September",
            "10": "October", "11": "November", "12": "December"
        }
        month = st.selectbox("Month", options=months, format_func=lambda x: month_names[x], key="month_select")
    
    # Auto-search when year or month changes
    search_key = f"{year}-{month}"
    
    if search_key != st.session_state.get('last_search'):
        st.session_state.last_search = search_key
        st.session_state.projects_found = []
        st.session_state.selected_project = None
        if 'project_data' in st.session_state:
            del st.session_state.project_data
        if 'project_meta' in st.session_state:
            del st.session_state.project_meta
        
        with st.spinner(f"Searching {month_names[month]} {year}..."):
            # Debug: Show root folder
            st.write(f"Debug - Root folder ID: {st.session_state.root_folder_id}")
            
            # Find year folder
            year_folder = list_folders(st.session_state.drive_service, st.session_state.root_folder_id, year)
            st.write(f"Debug - Year folder '{year}': {'Found' if year_folder else 'Not found'}")
            
            if year_folder:
                # Find month folder
                month_folder = list_folders(st.session_state.drive_service, year_folder[0]['id'], month)
                st.write(f"Debug - Month folder '{month}': {'Found' if month_folder else 'Not found'}")
                
                if month_folder:
                    # Find Excel files
                    excel_files = find_excel_files_in_month(st.session_state.drive_service, month_folder[0]['id'])
                    st.write(f"Debug - Excel files found: {len(excel_files)}")
                    
                    if excel_files:
                        st.write(f"Debug - Files: {[f['name'] for f in excel_files]}")
                    
                    # Parse each file to get project code and name
                    projects = []
                    for file in excel_files:
                        try:
                            from io import BytesIO
                            request = st.session_state.drive_service.files().get_media(fileId=file['id'])
                            file_content = request.execute()
                            excel_file = BytesIO(file_content)
                            df = pd.read_excel(excel_file, sheet_name='Financial Status', header=None, nrows=10)
                            
                            # Extract project code and name
                            project_code = str(df.iloc[2, 1]).strip() if pd.notna(df.iloc[2, 1]) else "Unknown"
                            project_name = str(df.iloc[3, 1]).strip() if pd.notna(df.iloc[3, 1]) else file['name'].replace('.xlsx', '')
                            
                            projects.append({
                                'file_id': file['id'],
                                'file_name': file['name'],
                                'code': project_code,
                                'name': project_name,
                                'year': year,
                                'month': month_names[month],
                                'month_folder_id': month_folder[0]['id']
                            })
                        except Exception as e:
                            # Fallback to filename
                            projects.append({
                                'file_id': file['id'],
                                'file_name': file['name'],
                                'code': "Unknown",
                                'name': file['name'].replace('.xlsx', ''),
                                'year': year,
                                'month': month_names[month],
                                'month_folder_id': month_folder[0]['id']
                            })
                    
                    st.session_state.projects_found = projects
                    
                    # Sort projects alphabetically by first word of name
                    st.session_state.projects_found.sort(key=lambda x: x['name'].split()[0].lower() if x['name'].split() else '')
                else:
                    st.session_state.projects_found = []
            else:
                st.session_state.projects_found = []
    
    # Display projects found
    if st.session_state.get('projects_found'):
        st.markdown(f"**Found {len(st.session_state.projects_found)} projects:**")
        
        # Get selected file_id safely
        selected = st.session_state.get('selected_project')
        selected_id = selected.get('file_id') if selected else None
        
        # Create cards for each project
        for i, proj in enumerate(st.session_state.projects_found):
            is_selected = (selected_id == proj['file_id'])
            
            if is_selected:
                st.markdown(f"""
                <div style="background-color: #1e4a7a; padding: 15px; border-radius: 10px; margin: 5px 0; border: 2px solid #4fc3f7;">
                    <strong style="color: #4fc3f7; font-size: 18px;">{proj['code']}</strong>
                    <span style="color: #e0e6ed; font-size: 16px;"> - {proj['name']}</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                if st.button(f"📁 {proj['code']} - {proj['name']}", key=f"project_{i}", use_container_width=True):
                    st.session_state.selected_project = proj
                    # Clear old project data
                    if 'project_data' in st.session_state:
                        del st.session_state.project_data
                    if 'project_meta' in st.session_state:
                        del st.session_state.project_meta
                    st.rerun()
    elif st.session_state.get('last_search') and not st.session_state.get('projects_found'):
        st.info(f"No projects found in {month_names[month]} {year}")
    
    # Show selected project data
    if st.session_state.selected_project:
        project = st.session_state.selected_project
        
        st.markdown("---")
        st.markdown(f"### 📄 {project['code']} - {project['name']}")
        st.caption(f"{project['month']} {project['year']}")
        
        # Load data if not already loaded
        if 'project_data' not in st.session_state:
            with st.spinner("Loading project data..."):
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
        
        # Display project data
        if 'project_data' in st.session_state and st.session_state.project_data is not None:
            df = st.session_state.project_data
            
            # Summary metrics
            m1, m2, m3, m4 = st.columns(4)
            if 'Budget_Revision' in df.columns:
                m1.metric("Budget", f"${df['Budget_Revision'].sum():,.0f}")
            if 'Projection' in df.columns:
                m2.metric("Projection", f"${df['Projection'].sum():,.0f}")
            if 'Commitments' in df.columns:
                m3.metric("Commitments", f"${df['Commitments'].sum():,.0f}")
            if 'Forecast' in df.columns:
                m4.metric("Forecast", f"${df['Forecast'].sum():,.0f}")
            
            # Quick action buttons
            st.markdown("#### 💬 Quick Questions")
            q1, q2, q3, q4 = st.columns(4)
            if q1.button("Total Budget"):
                if 'Budget_Revision' in df.columns:
                    st.success(f"Total Budget: ${df['Budget_Revision'].sum():,.2f}")
            if q2.button("Gross Profit"):
                gp = df[df['Trade'].str.contains('Gross Profit', case=False, na=False)]
                if not gp.empty and 'Projection' in gp.columns:
                    st.success(f"Gross Profit: ${gp['Projection'].sum():,.2f}")
            if q3.button("Project Overhead"):
                oh = df[df['Trade'].str.contains('Project Overhead', case=False, na=False)]
                if not oh.empty and 'Projection' in oh.columns:
                    st.success(f"Project Overhead: ${oh['Projection'].sum():,.2f}")
            if q4.button("Fee"):
                fee = df[df['Trade'].str.contains('Fee', case=False, na=False)]
                if not fee.empty and 'Projection' in fee.columns:
                    st.success(f"Fee: ${fee['Projection'].sum():,.2f}")
            
            # Chat input
            st.markdown("#### 💭 Ask a Question")
            user_question = st.text_input("Type your question...", placeholder="e.g., What is the total cost?")
            
            if user_question:
                answer = answer_question(df, user_question)
                st.markdown(f"**Answer:** {answer}")
            
            # Data toggle
            with st.expander("📊 View Raw Data"):
                st.dataframe(df, use_container_width=True)


if __name__ == "__main__":
    main()
