"""
Financial Chatbot - Streamlit Web App
Accesses Google Drive via API for financial data
"""
import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Financial Chatbot", page_icon="📊")

# Initialize session state
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'df' not in st.session_state:
    st.session_state.df = None
if 'creds' not in st.session_state:
    st.session_state.creds = None

def load_data_from_gdrive():
    """Load data using Google Drive API."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from io import BytesIO
        
        if st.session_state.creds is None:
            return None, "Google credentials not found in secrets"
        
        credentials = service_account.Credentials.from_service_account_info(
            st.session_state.creds, 
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        
        service = build('drive', 'v3', credentials=credentials)
        
        # Find Excel files with "Financial Report" in name
        results = service.files().list(
            q="name contains 'Financial Report' and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
            fields="files(id, name)"
        ).execute()
        
        files = results.get('files', [])
        if not files:
            return None, "No Excel files found in Google Drive"
        
        all_dfs = []
        for f in files[:3]:  # Limit to first 3 for testing
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
                continue
        
        if all_dfs:
            combined = pd.concat(all_dfs, ignore_index=True)
            return combined, "Success"
        
        return None, "No data parsed"
        
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
        pass

st.title("📊 Financial Chatbot")

# Show credential status
if st.session_state.creds is None:
    st.warning("Google credentials not found in Streamlit secrets!")
    st.info("Please add 'google_credentials' to your Streamlit Cloud secrets.")
else:
    st.success("Google credentials loaded")

# Load data button
if not st.session_state.data_loaded:
    st.info("Click below to load financial data from Google Drive")
    if st.button("Load Data from Google Drive"):
        with st.spinner("Loading data..."):
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
