"""
Financial Chatbot - Streamlit Web App
Accesses Google Drive via API for financial data
"""
import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="Financial Chatbot", page_icon="📊")

# Initialize session state
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'df' not in st.session_state:
    st.session_state.df = None
if 'creds' not in st.session_state:
    st.session_state.creds = None
if 'service' not in st.session_state:
    st.session_state.service = None

def get_drive_service():
    """Get Google Drive service."""
    if st.session_state.service is not None:
        return st.session_state.service
    
    if st.session_state.creds is None:
        return None
    
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        credentials = service_account.Credentials.from_service_account_info(
            st.session_state.creds, 
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        st.session_state.service = build('drive', 'v3', credentials=credentials)
        return st.session_state.service
    except:
        return None

def find_folder_id(folder_name):
    """Find folder ID by name."""
    service = get_drive_service()
    if service is None:
        return None
    
    results = service.files().list(
        q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)"
    ).execute()
    
    folders = results.get('files', [])
    if folders:
        return folders[0]['id']
    return None

def find_excel_files_in_folder(folder_id):
    """Find Excel files in a folder."""
    service = get_drive_service()
    if service is None:
        return []
    
    results = service.files().list(
        q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
        fields="files(id, name)"
    ).execute()
    
    return results.get('files', [])

def load_data_from_gdrive():
    """Load data using Google Drive API."""
    try:
        from io import BytesIO
        
        service = get_drive_service()
        if service is None:
            return None, "Could not connect to Google Drive"
        
        # Find the Knowledge Base folder
        folder_id = find_folder_id("Ai Chatbot Knowledge Base")
        if folder_id is None:
            return None, "Folder 'Ai Chatbot Knowledge Base' not found"
        
        st.session_state.folder_id = folder_id
        
        # Find Excel files in the folder
        # Search in folder and subfolders
        all_files = []
        
        def list_files_in_folder(parent_id, path=""):
            results = service.files().list(
                q=f"'{parent_id}' in parents and trashed=false",
                fields="files(id, name, mimeType)"
            ).execute()
            
            for f in results.get('files', []):
                if f['mimeType'] == 'application/vnd.google-apps.spreadsheet':
                    all_files.append({'id': f['id'], 'name': f['name']})
                elif f['mimeType'] == 'application/vnd.google-apps.folder':
                    list_files_in_folder(f['id'], f"{path}/{f['name']}")
        
        list_files_in_folder(folder_id)
        
        if not all_files:
            return None, f"No Excel files found in 'Ai Chatbot Knowledge Base' folder"
        
        st.write(f"Found {len(all_files)} Excel files")
        
        # Load first 3 files for testing
        all_dfs = []
        for f in all_files[:3]:
            st.write(f"Loading: {f['name']}")
            
            # Export as Excel
            request = service.files().export_media(
                fileId=f['id'],
                mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            content = request.execute()
            
            # Parse all sheets
            try:
                excel_file = pd.ExcelFile(BytesIO(content))
                for sheet_name in excel_file.sheet_names:
                    sheet_df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    sheet_df['_source_file'] = f['name']
                    sheet_df['_source_sheet'] = sheet_name
                    all_dfs.append(sheet_df)
            except Exception as e:
                st.write(f"Error parsing {f['name']}: {e}")
                continue
        
        if all_dfs:
            combined = pd.concat(all_dfs, ignore_index=True)
            return combined, "Success"
        
        return None, "No data could be parsed"
        
    except Exception as e:
        import traceback
        return None, f"Error: {str(e)}\n{traceback.format_exc()}"

# Load credentials from Streamlit secrets
if st.session_state.creds is None:
    try:
        if 'google_credentials' in st.secrets:
            creds = st.secrets['google_credentials']
            if isinstance(creds, str):
                st.session_state.creds = json.loads(creds)
            else:
                st.session_state.creds = creds
    except Exception as e:
        st.write(f"Error loading credentials: {e}")

st.title("📊 Financial Chatbot")

# Show credential status
if st.session_state.creds is None:
    st.warning("Google credentials not found in Streamlit secrets!")
    st.info("Please add 'google_credentials' to your Streamlit Cloud secrets.")
elif get_drive_service() is None:
    st.warning("Could not connect to Google Drive")
else:
    st.success("Connected to Google Drive ✓")

# Load data button
if not st.session_state.data_loaded:
    st.info("Click below to load financial data from Google Drive")
    if st.button("Load Data from Google Drive"):
        with st.spinner("Searching for files..."):
            df, msg = load_data_from_gdrive()
            if df is not None and len(df) > 0:
                st.session_state.df = df
                st.session_state.data_loaded = True
                st.success(f"Loaded {len(df)} records!")
                st.rerun()
            else:
                st.error(f"Error: {msg}")

# Show data if loaded
if st.session_state.data_loaded and st.session_state.df is not None:
    df = st.session_state.df
    st.success(f"Data loaded: {len(df)} records")
    
    # Show summary
    st.markdown("### 📈 Data Summary")
    if '_source_sheet' in df.columns:
        st.write(f"Available sheets: {df['_source_sheet'].unique().tolist()}")
    
    # Show sample
    with st.expander("Sample Data", expanded=True):
        st.dataframe(df.head(10))
    
    # Reload button
    if st.button("Reload Data"):
        st.session_state.data_loaded = False
        st.session_state.df = None
        st.rerun()

# Clear data button
if st.session_state.data_loaded:
    if st.button("Clear Data"):
        st.session_state.data_loaded = False
        st.session_state.df = None
        st.rerun()
