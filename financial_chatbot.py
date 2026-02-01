"""
Financial Chatbot - Streamlit Web App
Reads preprocessed CSV files from Google Drive - NO PARSING NEEDED!
"""
import streamlit as st
import pandas as pd
import json
from io import StringIO

st.set_page_config(page_title="Financial Chatbot", page_icon="📊")

# Initialize session state
if 'service' not in st.session_state:
    st.session_state.service = None
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'df' not in st.session_state:
    st.session_state.df = None

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
        return None

def load_all_csv_files():
    """Download and combine all CSV files - FAST, NO PARSING!"""
    service = get_drive_service()
    if service is None:
        return None, "No service"
    
    # Find all _flat.csv files
    results = service.files().list(
        q="name contains '_flat.csv' and trashed=false",
        fields="files(id, name)",
        pageSize=100
    ).execute()
    
    files = results.get('files', [])
    if not files:
        return None, "No CSV files found"
    
    all_dfs = []
    file_list = []
    
    for f in files:
        try:
            # Download CSV directly
            request = service.files().get_media(fileId=f['id'])
            content = request.execute()
            
            # Read CSV directly - NO PARSING NEEDED!
            df = pd.read_csv(StringIO(content.decode('utf-8')))
            all_dfs.append(df)
            file_list.append(f['name'])
            
        except Exception as e:
            continue
    
    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        return combined, file_list
    
    return None, []

# Load credentials
service = get_drive_service()

st.title("📊 Financial Chatbot")

if service is None:
    st.error("Could not connect to Google Drive")
    st.info("Check Streamlit secrets for 'google_credentials'")
else:
    st.success("Connected to Google Drive ✓")

# Load button
if not st.session_state.data_loaded:
    if st.button("Load Financial Data"):
        with st.spinner("Downloading CSV files..."):
            df, file_list = load_all_csv_files()
            
            if df is not None and len(df) > 0:
                st.session_state.df = df
                st.session_state.data_loaded = True
                st.session_state.files = file_list
                st.success(f"✅ Loaded {len(df):,} records from {len(file_list)} files!")
                st.rerun()
            else:
                st.error("Could not load data")

# Show data
if st.session_state.data_loaded and st.session_state.df is not None:
    df = st.session_state.df
    
    st.success(f"📊 Data loaded: {len(df):,} records from {len(st.session_state.files)} files")
    
    # Show files
    with st.expander("📁 Source Files", expanded=False):
        for f in st.session_state.files:
            st.write(f"✓ {f}")
    
    # Key metrics
    st.markdown("### 💰 Key Metrics")
    
    col1, col2, col3 = st.columns(3)
    
    # Projected GP
    proj = df[df['Sheet_Name'] == 'Projection']
    if not proj.empty:
        gp = proj[proj['Trade'].str.contains('Gross Profit', case=False, na=False)]
        if not gp.empty:
            col1.metric("Projected GP", f"${gp['Value'].sum():,.0f}")
    
    # WIP GP
    wip = df[(df['Sheet_Name'] == 'Financial Status') & (df['Financial_Type'] == 'Audit Report (WIP) J')]
    if not wip.empty:
        gp = wip[wip['Trade'].str.contains('Gross Profit', case=False, na=False)]
        if not gp.empty:
            col2.metric("WIP GP", f"${gp['Value'].sum():,.0f}")
    
    # Cash Flow
    cf = df[df['Sheet_Name'] == 'Cash Flow']
    if not cf.empty:
        gp = cf[cf['Trade'].str.contains('Gross Profit', case=False, na=False)]
        if not gp.empty:
            col3.metric("Cash Flow", f"${gp['Value'].sum():,.0f}")
    
    # Summary
    st.markdown("### 📈 Summary")
    st.write(f"Sheets: {df['Sheet_Name'].unique().tolist()}")
    st.write(f"Years: {sorted(df['Year'].unique())}")
    st.write(f"Months: {sorted(df['Month'].unique())}")
    
    # Sample
    with st.expander("Sample Data", expanded=False):
        st.dataframe(df.head(5))
    
    # Download
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", csv, "data.csv", "text/csv")
    
    # Clear
    if st.button("Clear Data"):
        st.session_state.data_loaded = False
        st.session_state.df = None
        st.rerun()
