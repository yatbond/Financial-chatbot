"""
Financial Chatbot - Streamlit Web App
Reads preprocessed CSV files from Google Drive
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

def find_csv_files():
    """Find preprocessed CSV files."""
    service = get_drive_service()
    if service is None:
        return [], "No service"
    
    # Search for _flat.csv files
    results = service.files().list(
        q="name contains '_flat.csv' and trashed=false",
        fields="files(id, name)",
        pageSize=50
    ).execute()
    
    files = results.get('files', [])
    return files, len(files)

def load_csv_from_gdrive(file_id):
    """Load a CSV file from Google Drive."""
    service = get_drive_service()
    if service is None:
        return None
    
    # Download as CSV
    request = service.files().get_media(fileId=file_id)
    content = request.execute()
    
    # Parse CSV
    from io import StringIO
    df = pd.read_csv(StringIO(content.decode('utf-8')))
    return df

# Load credentials and test connection
service = get_drive_service()

st.title("📊 Financial Chatbot")

if service is None:
    st.error("Could not connect to Google Drive")
    st.info("Check Streamlit secrets for 'google_credentials'")
else:
    st.success("Connected to Google Drive ✓")

# Load data button
if st.button("Load Financial Data from CSV"):
    with st.spinner("Searching for CSV files..."):
        files, count = find_csv_files()
        
        if count == 0:
            st.error("No CSV files found! Make sure _flat.csv files are in Google Drive.")
        else:
            st.success(f"Found {count} CSV files!")
            
            all_dfs = []
            
            with st.spinner(f"Loading {count} files..."):
                progress_bar = st.progress(0)
                
                for i, f in enumerate(files):
                    try:
                        df = load_csv_from_gdrive(f['id'])
                        df['_source_file'] = f['name']
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
                st.error("No data could be loaded")

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
    
    # Show columns
    st.write(f"Columns: {list(df.columns)}")
    
    # Show data by sheet
    if 'Sheet_Name' in df.columns:
        st.write(f"\nSheets: {df['Sheet_Name'].unique().tolist()}")
    
    # Show data by year/month
    if 'Year' in df.columns:
        st.write(f"Years: {sorted(df['Year'].unique())}")
    if 'Month' in df.columns:
        st.write(f"Months: {sorted(df['Month'].unique())}")
    
    # Calculate key metrics
    st.markdown("### 💰 Key Metrics")
    
    # Projected Gross Profit
    proj = df[df['Sheet_Name'] == 'Projection']
    if not proj.empty and 'Trade' in proj.columns:
        gp = proj[proj['Trade'].str.contains('Gross Profit', case=False, na=False)]
        if not gp.empty:
            st.metric("Projected Gross Profit", f"${gp['Value'].sum():,.2f}")
    
    # WIP Gross Profit
    wip = df[(df['Sheet_Name'] == 'Financial Status') & (df['Financial_Type'] == 'Audit Report (WIP) J')]
    if not wip.empty and 'Trade' in wip.columns:
        gp = wip[wip['Trade'].str.contains('Gross Profit', case=False, na=False)]
        if not gp.empty:
            st.metric("WIP Gross Profit", f"${gp['Value'].sum():,.2f}")
    
    # Cash Flow
    cf = df[df['Sheet_Name'] == 'Cash Flow']
    if not cf.empty and 'Trade' in cf.columns:
        gp = cf[cf['Trade'].str.contains('Gross Profit', case=False, na=False)]
        if not gp.empty:
            st.metric("Cash Flow", f"${gp['Value'].sum():,.2f}")
    
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

# Clear data button
if st.session_state.data_loaded:
    if st.button("Clear Data"):
        st.session_state.data_loaded = False
        st.session_state.df = None
        st.session_state.loaded_files = []
        st.rerun()
