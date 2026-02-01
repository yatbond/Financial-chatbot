"""
Financial Chatbot - Streamlit Web App
Clean interface with project selection
"""
import streamlit as st
import pandas as pd
import json
import re
from io import StringIO

st.set_page_config(page_title="Financial Chatbot", page_icon="📊")

# Initialize session state
if 'service' not in st.session_state:
    st.session_state.service = None
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'df' not in st.session_state:
    st.session_state.df = None
if 'projects' not in st.session_state:
    st.session_state.projects = {}
if 'selected_project' not in st.session_state:
    st.session_state.selected_project = None

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
    except:
        return None

def extract_project_info(filename):
    """
    Extract project code and name from filename.
    Example: "1014 PolyU Financial Report 2025-12_flat.csv" 
    → Code: "1014", Name: "PolyU"
    """
    # Remove _flat.csv suffix
    name = filename.replace('_flat.csv', '')
    
    # Extract project code (number at beginning)
    match = re.match(r'^(\d+)', name)
    if match:
        code = match.group(1)
        # Project name is the rest, remove "Financial Report" and date
        project_name = name[len(code):].strip()
        project_name = re.sub(r'\s*Financial\s*Report.*', '', project_name)
        project_name = project_name.strip()
        return code, project_name
    return None, name

def load_all_csv_files():
    """Download and combine all CSV files."""
    service = get_drive_service()
    if service is None:
        return None, {}
    
    # Find all _flat.csv files
    results = service.files().list(
        q="name contains '_flat.csv' and trashed=false",
        fields="files(id, name)",
        pageSize=100
    ).execute()
    
    files = results.get('files', [])
    if not files:
        return None, {}
    
    all_dfs = []
    projects = {}
    
    for f in files:
        try:
            # Download CSV directly
            request = service.files().get_media(fileId=f['id'])
            content = request.execute()
            
            # Read CSV
            df = pd.read_csv(StringIO(content.decode('utf-8')))
            
            # Extract project info
            code, project_name = extract_project_info(f['name'])
            
            if code:
                project_key = f"{code} - {project_name}"
                df['_project'] = project_key
                df['_source_file'] = f['name']
                all_dfs.append(df)
                projects[project_key] = {
                    'code': code,
                    'name': project_name,
                    'filename': f['name']
                }
            
        except Exception as e:
            continue
    
    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        return combined, projects
    
    return None, {}

def get_project_metrics(df, project):
    """Calculate key metrics for a project."""
    project_df = df[df['_project'] == project]
    
    if project_df.empty:
        return None
    
    metrics = {}
    
    # Get latest time period for this project
    if 'Month' in project_df.columns:
        latest_month = project_df['Month'].max()
    else:
        latest_month = None
    
    # Projected Gross Profit: Projection sheet, Gross Profit trades
    proj = project_df[project_df['Sheet_Name'] == 'Projection']
    if not proj.empty:
        if latest_month:
            proj = proj[proj['Month'] == latest_month]
        gp = proj[proj['Data_Type'].str.contains('Gross Profit', case=False, na=False)]
        if not gp.empty:
            metrics['Projected GP'] = gp['Value'].sum()
    
    # WIP Gross Profit: Audit Report (WIP) J, Gross Profit trades
    wip = project_df[(project_df['Sheet_Name'] == 'Financial Status') & 
                     (project_df['Financial_Type'] == 'Audit Report (WIP) J')]
    if not wip.empty:
        gp = wip[wip['Data_Type'].str.contains('Gross Profit', case=False, na=False)]
        if not gp.empty:
            metrics['WIP GP'] = gp['Value'].sum()
    
    # Cash Flow: Cash Flow sheet
    cf = project_df[project_df['Sheet_Name'] == 'Cash Flow']
    if not cf.empty:
        gp = cf[cf['Data_Type'].str.contains('Gross Profit', case=False, na=False)]
        if not gp.empty:
            metrics['Cash Flow'] = gp['Value'].sum()
    
    return metrics

# Load credentials
service = get_drive_service()

st.title("📊 Financial Chatbot")

if service is None:
    st.error("Could not connect to Google Drive")
    st.info("Check Streamlit secrets for 'google_credentials'")
else:
    st.success("Connected to Google Drive ✓")

# Load data
if not st.session_state.data_loaded:
    if st.button("Load All Projects"):
        with st.spinner("Loading projects..."):
            df, projects = load_all_csv_files()
            
            if df is not None and len(df) > 0:
                st.session_state.df = df
                st.session_state.data_loaded = True
                st.session_state.projects = projects
                st.session_state.selected_project = None
                st.success(f"✅ Loaded {len(projects)} projects with {len(df):,} records!")
                st.rerun()
            else:
                st.error("Could not load data")

# Show project selector
if st.session_state.data_loaded and st.session_state.projects:
    projects = st.session_state.projects
    
    st.markdown("### 🏗️ Select Project")
    
    # Create project options
    project_options = ["-- Select a project --"] + sorted(projects.keys())
    selected = st.selectbox("Choose a project:", project_options)
    
    # Update selected project
    if selected != "-- Select a project --":
        st.session_state.selected_project = selected
    elif st.session_state.selected_project:
        selected = st.session_state.selected_project
    
    # Show project info
    if st.session_state.selected_project:
        project = st.session_state.selected_project
        info = projects[project]
        
        st.info(f"**Project Code:** {info['code']}  \n**Project Name:** {info['name']}")
        
        # Get and show metrics
        metrics = get_project_metrics(st.session_state.df, project)
        
        if metrics:
            st.markdown("### 💰 Key Metrics")
            
            col1, col2, col3 = st.columns(3)
            
            pgp = metrics.get('Projected GP', 0)
            wgp = metrics.get('WIP GP', 0)
            cf = metrics.get('Cash Flow', 0)
            
            col1.metric("Projected GP (bf adj)", f"${pgp:,.0f}")
            col2.metric("WIP GP (bf adj)", f"${wgp:,.0f}")
            col3.metric("Cash Flow", f"${cf:,.0f}")
        else:
            st.warning("No metrics available for this project")
        
        # Show data summary
        project_df = st.session_state.df[st.session_state.df['_project'] == project]
        
        with st.expander("📊 Project Data Summary", expanded=False):
            st.write(f"Total records: {len(project_df)}")
            st.write(f"Sheets: {project_df['Sheet_Name'].unique().tolist()}")
            st.write(f"Months: {sorted(project_df['Month'].unique())}")
        
        # Show sample data
        with st.expander("📋 Sample Data", expanded=False):
            st.dataframe(project_df.head(5))

# Clear button
if st.session_state.data_loaded:
    st.markdown("---")
    if st.button("🔄 Reload All Projects"):
        st.session_state.data_loaded = False
        st.session_state.df = None
        st.session_state.projects = {}
        st.session_state.selected_project = None
        st.rerun()
