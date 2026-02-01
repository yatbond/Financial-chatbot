"""
Financial Chatbot - Streamlit Web App
Accesses Google Drive via API for financial data
"""
import streamlit as st
import pandas as pd
import json
from io import BytesIO

st.set_page_config(page_title="Financial Chatbot", page_icon="📊")

# Initialize session state
if 'service' not in st.session_state:
    st.session_state.service = None
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'df' not in st.session_state:
    st.session_state.df = None
if 'loaded_files' not in st.session_state:
    st.session_state.loaded_files = []

def get_drive_service():
    """Get Google Drive service."""
    if st.session_state.service is not None:
        return st.session_state.service
    
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        creds = None
        if 'google_credentials' in st.secrets:
            creds = st.secrets['google_credentials']
            if isinstance(creds, str):
                creds = json.loads(creds)
        
        if creds is None:
            return None
        
        credentials = service_account.Credentials.from_service_account_info(
            creds, 
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        st.session_state.service = build('drive', 'v3', credentials=credentials)
        return st.session_state.service
    except Exception as e:
        st.write(f"Error: {e}")
        return None

def find_and_load_data():
    """Find and load data."""
    service = get_drive_service()
    if service is None:
        return None, "No service"
    
    # Search for Excel files (.xlsx) - NOT Google Sheets
    all_files = []
    
    # Search by name containing "Financial Report" and ending with .xlsx
    results = service.files().list(
        q="name contains 'Financial Report' and name endsWith '.xlsx' and trashed=false",
        fields="files(id, name)",
        pageSize=50
    ).execute()
    
    files = results.get('files', [])
    for f in files:
        all_files.append(f)
    
    return all_files, len(all_files)

def load_excel_from_gdrive(file_id, file_name):
    """Load a single Excel file from Google Drive."""
    service = get_drive_service()
    if service is None:
        return None
    
    # Export as Excel format
    request = service.files().export_media(
        fileId=file_id,
        mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    content = request.execute()
    
    # Parse all sheets
    excel_file = pd.ExcelFile(BytesIO(content))
    all_sheets = {}
    
    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        df['_source_file'] = file_name
        df['_source_sheet'] = sheet_name
        all_sheets[sheet_name] = df
    
    return all_sheets

# Load credentials and test connection
service = get_drive_service()

st.title("📊 Financial Chatbot")

if service is None:
    st.error("Could not connect to Google Drive")
    st.info("Check Streamlit secrets for 'google_credentials'")
else:
    st.success("Connected to Google Drive ✓")

# Load data button
if st.button("Load Financial Data"):
    with st.spinner("Searching for files..."):
        files, count = find_and_load_data()
        
        if count == 0:
            st.error("No Excel files found!")
        else:
            st.success(f"Found {count} Excel files!")
            
            all_dfs = []
            
            with st.spinner(f"Loading {count} files..."):
                progress_bar = st.progress(0)
                
                for i, f in enumerate(files):
                    try:
                        sheets = load_excel_from_gdrive(f['id'], f['name'])
                        for sheet_name, df in sheets.items():
                            df['_source_file'] = f['name']
                            df['_source_sheet'] = sheet_name
                            all_dfs.append(df)
                        
                        st.session_state.loaded_files.append(f['name'])
                    except Exception as e:
                        st.write(f"Error loading {f['name']}: {e}")
                    
                    progress_bar.progress((i + 1) / count)
            
            if all_dfs:
                combined = pd.concat(all_dfs, ignore_index=True)
                st.session_state.df = combined
                st.session_state.data_loaded = True
                st.success(f"Loaded {len(combined)} records from {len(files)} files!")
                st.rerun()
            else:
                st.error("No data could be parsed")

# Show loaded data
if st.session_state.data_loaded and st.session_state.df is not None:
    df = st.session_state.df
    st.success(f"Data loaded: {len(df)} records from {len(st.session_state.loaded_files)} files")
    
    # Show files loaded
    st.markdown("### 📁 Files Loaded")
    for f in st.session_state.loaded_files:
        st.write(f"✓ {f}")
    
    # Show summary
    st.markdown("### 📈 Data Summary")
    
    # Try to show useful columns
    for col in ['_source_sheet', 'Year', 'Month', 'Sheet_Name']:
        if col in df.columns:
            unique_vals = df[col].unique()
            if len(unique_vals) <= 20:
                st.write(f"{col}: {list(unique_vals)}")
    
    # Show sample
    with st.expander("Sample Data", expanded=False):
        st.dataframe(df.head(10))
    
    # Download button
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "Download Data as CSV",
        csv,
        "financial_data.csv",
        "text/csv",
        key='download-csv'
    )

# Show loaded files
if st.session_state.loaded_files:
    with st.expander("Loaded Files"):
        for f in st.session_state.loaded_files:
            st.write(f"✓ {f}")

# Clear data button
if st.session_state.data_loaded:
    if st.button("Clear Data"):
        st.session_state.data_loaded = False
        st.session_state.df = None
        st.session_state.loaded_files = []
        st.rerun()
