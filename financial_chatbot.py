"""
Financial Chatbot - Streamlit Web App
Accesses Google Drive via API for financial data
DEBUG VERSION - Shows all files/folders found
"""
import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="Financial Chatbot", page_icon="📊")

# Initialize session state
if 'service' not in st.session_state:
    st.session_state.service = None
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'df' not in st.session_state:
    st.session_state.df = None
if 'debug_info' not in st.session_state:
    st.session_state.debug_info = ""

def get_drive_service():
    """Get Google Drive service."""
    if st.session_state.service is not None:
        return st.session_state.service
    
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        # Load credentials
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
        st.write(f"Error creating service: {e}")
        return None

def debug_list_all_files():
    """List all files - for debugging."""
    service = get_drive_service()
    if service is None:
        return "No service"
    
    debug = []
    
    # List ALL folders in root
    debug.append("=== Folders in My Drive root ===")
    results = service.files().list(
        q="mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)",
        pageSize=50
    ).execute()
    
    folders = results.get('files', [])
    for f in folders:
        debug.append(f"- {f['name']} ({f['id']})")
    
    # List files named similarly
    debug.append("\n=== Files with 'Financial' in name ===")
    results = service.files().list(
        q="name contains 'Financial' and trashed=false",
        fields="files(id, name)",
        pageSize=20
    ).execute()
    
    files = results.get('files', [])
    for f in files:
        debug.append(f"- {f['name']} ({f['id']})")
    
    # List files with 'Report' in name
    debug.append("\n=== Files with 'Report' in name ===")
    results = service.files().list(
        q="name contains 'Report' and trashed=false",
        fields="files(id, name)",
        pageSize=20
    ).execute()
    
    files = results.get('files', [])
    for f in files:
        debug.append(f"- {f['name']} ({f['id']})")
    
    return "\n".join(debug)

def find_and_load_data():
    """Find and load data."""
    service = get_drive_service()
    if service is None:
        return None, "No service"
    
    # Try multiple search approaches
    all_files = []
    
    # Approach 1: Search by name containing "Financial Report"
    for query_term in ["Financial Report", "Financial", "Report"]:
        results = service.files().list(
            q=f"name contains '{query_term}' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
            fields="files(id, name)",
            pageSize=50
        ).execute()
        
        files = results.get('files', [])
        for f in files:
            if f['id'] not in [x['id'] for x in all_files]:
                all_files.append(f)
    
    return all_files, len(all_files)

# Load credentials and test connection
service = get_drive_service()

st.title("📊 Financial Chatbot")

if service is None:
    st.error("Could not connect to Google Drive")
    st.info("Check Streamlit secrets for 'google_credentials'")
else:
    st.success("Connected to Google Drive ✓")

# Debug button
if st.button("Show Debug Info (What files are accessible?)"):
    with st.spinner("Fetching file list..."):
        debug_output = debug_list_all_files()
        st.session_state.debug_info = debug_output

# Show debug info if available
if st.session_state.debug_info:
    st.markdown("### 🔍 Debug Info")
    st.text(st.session_state.debug_info)

# Load data button
if st.button("Load Financial Data"):
    with st.spinner("Searching for files..."):
        files, count = find_and_load_data()
        
        if count == 0:
            st.error(f"No Excel files found! Files found: {count}")
            st.info("Try sharing a specific file with the service account email.")
        else:
            st.success(f"Found {count} files!")
            st.write("Files found:", [f['name'] for f in files])
            
            # Show first file ID for sharing check
            if files:
                st.code(f"First file ID: {files[0]['id']}")
                st.info(f"Service account email: financial-chatbot@chatbot-485614.iam.gserviceaccount.com")
                st.info("Make sure this email has access to the files!")

# Show debug info toggle
with st.expander("Service Account Info"):
    st.write("Email: financial-chatbot@chatbot-485614.iam.gserviceaccount.com")
    st.write("Permissions needed: Drive read access to shared folder")
