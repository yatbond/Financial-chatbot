"""
Financial Chatbot - Streamlit Web App
Clean interface with project selection and Q&A chatbot
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
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'available_years' not in st.session_state:
    st.session_state.available_years = []
if 'available_months' not in st.session_state:
    st.session_state.available_months = []
if 'query_knowledge_base' not in st.session_state:
    st.session_state.query_knowledge_base = {}  # Maps query -> best match filters

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

def list_folders(service, parent_id=None):
    """List folders in Google Drive."""
    query = "mimeType='application/vnd.google-apps.folder'"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    results = service.files().list(
        q=query,
        fields="files(id, name)",
        pageSize=100
    ).execute()
    
    return results.get('files', [])

def get_folder_structure(service):
    """Get year/month folder structure from Google Drive."""
    folders = list_folders(service)
    
    # Find the root "Ai Chatbot Knowledge Base" folder
    root_folder = None
    for f in folders:
        if f['name'] == 'Ai Chatbot Knowledge Base':
            root_folder = f['id']
            break
    
    if not root_folder:
        return {}, []
    
    # List year folders
    year_folders = list_folders(service, root_folder)
    year_months = {}
    all_months = set()
    
    for year_folder in year_folders:
        try:
            year = year_folder['name']
            month_folders = list_folders(service, year_folder['id'])
            months = []
            for m in month_folders:
                months.append(m['name'])
                all_months.add(m['name'])
            year_months[year] = months
        except:
            continue
    
    return year_months, sorted(all_months)

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

def load_csv_files_for_period(service, selected_year, selected_month):
    """Load CSV files for selected year and month."""
    all_dfs = []
    projects = {}
    
    # Find the root folder
    folders = list_folders(service)
    root_folder = None
    for f in folders:
        if f['name'] == 'Ai Chatbot Knowledge Base':
            root_folder = f['id']
            break
    
    if not root_folder:
        return None, {}
    
    # Find year folder
    year_folders = list_folders(service, root_folder)
    year_folder_id = None
    for f in year_folders:
        if f['name'] == selected_year:
            year_folder_id = f['id']
            break
    
    if not year_folder_id:
        return None, {}
    
    # Find month folder
    month_folders = list_folders(service, year_folder_id)
    month_folder_id = None
    for f in month_folders:
        if f['name'] == selected_month:
            month_folder_id = f['id']
            break
    
    if not month_folder_id:
        return None, {}
    
    # Find CSV files in month folder
    csv_files = service.files().list(
        q=f"'{month_folder_id}' in parents and name contains '_flat.csv' and trashed=false",
        fields="files(id, name)",
        pageSize=100
    ).execute().get('files', [])
    
    for f in csv_files:
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
                df['_year'] = selected_year
                df['_month'] = selected_month
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
    
    # Filter by Item_Code = '3' (string) and Data_Type contains "Gross Profit"
    gp_filter = (project_df['Item_Code'] == '3') & \
                (project_df['Data_Type'].str.contains('Gross Profit', case=False, na=False))
    
    # Business Plan GP: Sheet_Name = Financial Status, Financial_Type contains "Business Plan"
    bp = project_df[(project_df['Sheet_Name'] == 'Financial Status') & 
                    (project_df['Financial_Type'].str.contains('Business Plan', case=False, na=False)) &
                    gp_filter]
    if not bp.empty:
        metrics['Business Plan GP'] = bp['Value'].sum()
    
    # Projected GP: Sheet_Name = Financial Status, Financial_Type contains "Projection"
    proj = project_df[(project_df['Sheet_Name'] == 'Financial Status') & 
                      (project_df['Financial_Type'].str.contains('Projection', case=False, na=False)) &
                      gp_filter]
    if not proj.empty:
        metrics['Projected GP'] = proj['Value'].sum()
    
    # WIP GP: Sheet_Name = Financial Status, Financial_Type contains "Audit Report"
    wip = project_df[(project_df['Sheet_Name'] == 'Financial Status') & 
                     (project_df['Financial_Type'].str.contains('Audit Report', case=False, na=False)) &
                     gp_filter]
    if not wip.empty:
        metrics['WIP GP'] = wip['Value'].sum()
    
    # Cash Flow: Sheet_Name = Financial Status, Financial_Type contains "Cash Flow"
    cf = project_df[(project_df['Sheet_Name'] == 'Financial Status') & 
                    (project_df['Financial_Type'].str.contains('Cash Flow', case=False, na=False)) &
                    gp_filter]
    if not cf.empty:
        metrics['Cash Flow'] = cf['Value'].sum()
    
    return metrics


def find_best_matches(df, search_text, project):
    """
    Find all possible matches for a query by combining Financial_Type and Data_Type.
    Returns list of matches sorted by relevance.
    """
    project_df = df[df['_project'] == project]
    search_lower = search_text.lower()
    search_words = search_lower.split()
    
    # Determine Item_Code based on query
    item_code = '3'
    if 'net profit' in search_lower or 'net loss' in search_lower:
        item_code = '7'
    elif 'after adjustment' in search_lower or 'adjusted' in search_lower:
        item_code = '5'
    
    # Filter by Item_Code first
    filtered_df = project_df[project_df['Item_Code'] == item_code]
    
    # Get unique combinations
    combinations = filtered_df.groupby(['Financial_Type', 'Data_Type']).agg({
        'Value': 'sum',
        'Month': 'first'
    }).reset_index()
    
    matches = []
    
    for _, row in combinations.iterrows():
        ft = str(row['Financial_Type']).lower()
        dt = str(row['Data_Type']).lower()
        value = row['Value']
        month = row['Month']
        
        score = 0
        
        for word in search_words:
            if len(word) < 2:
                continue
            
            # Check Financial_Type
            if word in ft:
                score += 10
            
            # Check Data_Type
            if word in dt:
                score += 10
            
            # Special bonuses for specific term matches
            # "projected" -> "projection" in Financial_Type
            if word == 'projected' and 'projection' in ft:
                score += 30
            
            # "budget" in Financial_Type
            if word == 'budget' and 'budget' in ft:
                score += 30
            
            # "audit" in Financial_Type
            if word == 'audit' and 'audit' in ft:
                score += 30
            
            # "business" in Financial_Type
            if word == 'business' and 'business' in ft:
                score += 30
            
            # "cash" in Financial_Type
            if word == 'cash' and 'cash' in ft:
                score += 30
        
        # Additional bonuses for key terms
        if 'projection' in search_lower and 'projection' in ft:
            score += 20
        if 'budget' in search_lower and 'budget' in ft:
            score += 20
        if 'audit' in search_lower and 'audit' in ft:
            score += 20
        if 'business plan' in search_lower and 'business plan' in ft:
            score += 20
        if 'cash flow' in search_lower and 'cash flow' in ft:
            score += 20
        
        if 'gross profit' in search_lower and 'gross profit' in dt:
            score += 20
        if 'net profit' in search_lower and 'net profit' in dt:
            score += 20
        if 'income' in search_lower and 'income' in dt:
            score += 20
        if 'cost' in search_lower and 'cost' in dt:
            score += 20
        
        if score > 0:
            matches.append({
                'Financial_Type': row['Financial_Type'],
                'Data_Type': row['Data_Type'],
                'Value': value,
                'Month': month,
                'Item_Code': item_code,
                'score': score
            })
    
    # Sort by score descending
    matches.sort(key=lambda x: x['score'], reverse=True)
    
    return matches


def answer_question(df, project, question, selected_filters=None):
    """Answer a user question about the project data."""
    project_df = df[df['_project'] == project]
    question_lower = question.lower()
    
    # Get latest month if not specified
    latest_month = project_df['Month'].max()
    target_month = latest_month
    
    # Check if user specified a month
    month_names = ['january', 'february', 'march', 'april', 'may', 'june',
                   'july', 'august', 'september', 'october', 'november', 'december']
    month_abbr = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    
    for i, m in enumerate(month_names):
        if m in question_lower:
            target_month = i + 1
            break
    else:
        for i, m in enumerate(month_abbr):
            if m in question_lower:
                target_month = i + 1
                break
    
    # Check for year specification
    year_match = re.search(r'202[0-9]', question)
    target_year = project_df['_year'].iloc[0] if year_match is None else int(year_match.group())
    
    # If user selected specific filters, use them
    if selected_filters:
        ft_match = selected_filters.get('Financial_Type')
        dt_match = selected_filters.get('Data_Type')
        item_code = selected_filters.get('Item_Code', '3')
    else:
        # Find best matches
        matches = find_best_matches(df, question, project)
        
        if not matches:
            return None, matches  # No matches found
        
        if len(matches) == 1:
            # Single match - use it
            ft_match = matches[0]['Financial_Type']
            dt_match = matches[0]['Data_Type']
            item_code = matches[0]['Item_Code']
        else:
            # Multiple matches - return them for user selection
            return None, matches
    
    # Apply filters to get data
    result_df = project_df[
        (project_df['Financial_Type'] == ft_match) &
        (project_df['Data_Type'] == dt_match) &
        (project_df['Item_Code'] == item_code) &
        (project_df['Month'] == target_month)
    ]
    
    if result_df.empty:
        return f"No data found for '{ft_match} - {dt_match}'", []
    
    total_value = result_df['Value'].sum()
    first_record = result_df.iloc[0]
    
    response = f"## ${total_value:,.0f} ('000)\n\n"
    response += f"**Year:** {first_record.get('_year', target_year)}\n"
    response += f"**Month:** {first_record['Month']}\n"
    response += f"**Sheet:** {first_record['Sheet_Name']}\n"
    response += f"**Financial Type:** {first_record['Financial_Type']}\n"
    response += f"**Item Code:** {first_record['Item_Code']}\n"
    response += f"**Data Type:** {first_record['Data_Type']}\n"
    response += f"\n*Records found: {len(result_df)}*"
    
    return response, []


# Load credentials
service = get_drive_service()

st.title("📊 Financial Chatbot")

if service is None:
    st.error("Could not connect to Google Drive")
    st.info("Check Streamlit secrets for 'google_credentials'")
else:
    st.success("Connected to Google Drive ✓")

# Get folder structure
if not st.session_state.available_years:
    with st.spinner("Loading folder structure..."):
        # First get the folder structure
        year_months, all_months = get_folder_structure(service)
        
        # Now check which folders actually have CSV files
        service = get_drive_service()
        folders = list_folders(service)
        
        # Find the root "Ai Chatbot Knowledge Base" folder
        root_folder = None
        for f in folders:
            if f['name'] == 'Ai Chatbot Knowledge Base':
                root_folder = f['id']
                break
        
        # Find year folders and check for CSV files
        year_folders = list_folders(service, root_folder)
        folders_with_data = {}
        
        for year_folder in year_folders:
            try:
                year = year_folder['name']
                month_folders = list_folders(service, year_folder['id'])
                
                for m in month_folders:
                    # Check if this month folder has CSV files
                    csv_files = service.files().list(
                        q=f"'{m['id']}' in parents and name contains '_flat.csv' and trashed=false",
                        fields="files(id)",
                        pageSize=1
                    ).execute()
                    
                    if csv_files.get('files'):  # Has CSV files
                        if year not in folders_with_data:
                            folders_with_data[year] = []
                        folders_with_data[year].append(m['name'])
            except:
                continue
        
        # Set available years (only those with data)
        st.session_state.available_years = sorted(folders_with_data.keys(), reverse=True)
        st.session_state.year_months = folders_with_data
        st.session_state.available_months = sorted(set(m for months in folders_with_data.values() for m in months))
        
        # Pre-select the latest year that has data
        if st.session_state.available_years:
            st.session_state.default_year = st.session_state.available_years[0]
            # Get the latest month that has data
            latest_months = st.session_state.year_months.get(st.session_state.default_year, [])
            if latest_months:
                sorted_months = sorted(latest_months, key=lambda x: int(x))
                st.session_state.default_month = sorted_months[-1]
            else:
                st.session_state.default_month = None
        else:
            st.session_state.default_year = None
            st.session_state.default_month = None

# Year and Month selectors
if st.session_state.available_years:
    st.markdown("### 📅 Select Period")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pre-select the latest year with data
        default_year_idx = 0
        if 'default_year' in st.session_state and st.session_state.default_year:
            try:
                default_year_idx = st.session_state.available_years.index(st.session_state.default_year)
            except:
                pass
        selected_year = st.selectbox("Year:", st.session_state.available_years, index=default_year_idx)
    
    with col2:
        # Only show months that have data for the selected year
        available_months = st.session_state.year_months.get(selected_year, [])
        
        # Sort months numerically for proper ordering
        sorted_months = sorted(available_months, key=lambda x: int(x))
        
        # Pre-select the latest month with data
        default_month_idx = len(sorted_months) - 1
        if 'default_month' in st.session_state and st.session_state.default_month:
            try:
                default_month_idx = sorted_months.index(st.session_state.default_month)
            except:
                pass
        selected_month = st.selectbox("Month:", sorted_months, index=default_month_idx)
    
    if st.button("Load Data"):
        with st.spinner(f"Loading data for {selected_month} {selected_year}..."):
            df, projects = load_csv_files_for_period(service, selected_year, selected_month)
            
            if df is not None and len(df) > 0:
                st.session_state.df = df
                st.session_state.data_loaded = True
                st.session_state.projects = projects
                st.session_state.selected_project = None
                st.session_state.chat_history = []
                st.session_state.current_year = selected_year
                st.session_state.current_month = selected_month
                st.success(f"✅ Loaded {len(projects)} projects with {len(df):,} records!")
                st.rerun()
            else:
                st.error("No data found for this period")

# Show project selector
if st.session_state.data_loaded and st.session_state.projects:
    projects = st.session_state.projects
    
    st.markdown(f"### 🏗️ Select Project ({st.session_state.current_month} {st.session_state.current_year})")
    
    project_options = ["-- Select a project --"] + sorted(projects.keys())
    selected = st.selectbox("Choose a project:", project_options)
    
    if selected != "-- Select a project --":
        st.session_state.selected_project = selected
    elif st.session_state.selected_project:
        selected = st.session_state.selected_project
    
    if st.session_state.selected_project:
        project = st.session_state.selected_project
        info = projects[project]
        
        st.info(f"**Project Code:** {info['code']}  \n**Project Name:** {info['name']}")
        
        # Get and show metrics
        metrics = get_project_metrics(st.session_state.df, project)
        
        if metrics:
            st.markdown("### 💰 Key Metrics ('000)")
            
            col1, col2, col3, col4 = st.columns(4)
            
            bgp = metrics.get('Business Plan GP', 0)
            pgp = metrics.get('Projected GP', 0)
            wgp = metrics.get('WIP GP', 0)
            cf = metrics.get('Cash Flow', 0)
            
            col1.metric("Business Plan GP", f"${bgp:,.0f}")
            col2.metric("Projected GP (bf adj)", f"${pgp:,.0f}")
            col3.metric("WIP GP (bf adj)", f"${wgp:,.0f}")
            col4.metric("Cash Flow", f"${cf:,.0f}")
        else:
            st.warning("No metrics available for this project")
        
        # Chatbot section
        st.markdown("### 💬 Ask about this Project ('000)")
        st.markdown("*Ask about financial data. I'll find the best match from Financial_Type or Data_Type.*")
        
        with st.form("chat_form"):
            user_question = st.text_input("Your question:", placeholder="e.g., What is the Gross Profit?")
            submitted = st.form_submit_button("Ask")
            
            if submitted and user_question:
                response, matches = answer_question(st.session_state.df, project, user_question)
                
                if response is None and matches:
                    # Multiple matches - show selection UI
                    st.session_state.pending_question = user_question
                    st.session_state.pending_matches = matches
                elif response:
                    st.session_state.chat_history.append({"q": user_question, "a": response})
                    st.session_state.pending_question = None
                    st.session_state.pending_matches = []
        
        # Show match selection if needed
        if hasattr(st.session_state, 'pending_question') and st.session_state.pending_matches:
            st.markdown("---")
            st.markdown(f"**Q:** {st.session_state.pending_question}")
            st.markdown("*Multiple matches found. Please select:*")
            
            for i, match in enumerate(st.session_state.pending_matches[:10]):  # Show top 10
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"• {match['Financial_Type']} → {match['Data_Type']}")
                with col2:
                    if st.button(f"Select", key=f"select_{i}"):
                        response, _ = answer_question(
                            st.session_state.df, 
                            project, 
                            st.session_state.pending_question,
                            selected_filters=match
                        )
                        if response:
                            st.session_state.chat_history.append({
                                "q": st.session_state.pending_question, 
                                "a": response
                            })
                            # Save to knowledge base
                            st.session_state.query_knowledge_base[st.session_state.pending_question] = match
                            st.session_state.pending_question = None
                            st.session_state.pending_matches = []
                            st.rerun()
            
            # Clear selection
            if st.button("Clear Selection"):
                st.session_state.pending_question = None
                st.session_state.pending_matches = []
                st.rerun()
        
        # Show chat history
        if st.session_state.chat_history:
            st.markdown("---")
            for i, chat in enumerate(st.session_state.chat_history):
                st.markdown(f"**Q:** {chat['q']}")
                st.markdown(chat['a'])
                st.markdown("---")
        
        if st.button("Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()
        
        with st.expander("📊 Project Data Summary", expanded=False):
            project_df = st.session_state.df[st.session_state.df['_project'] == project]
            st.write(f"Total records: {len(project_df)}")
            st.write(f"Sheets: {project_df['Sheet_Name'].unique().tolist()}")
            st.write(f"Financial Types: {project_df['Financial_Type'].unique().tolist()}")
        
        with st.expander("📋 Sample Data", expanded=False):
            st.dataframe(project_df.head(5))

# Clear button
if st.session_state.data_loaded:
    st.markdown("---")
    if st.button("🔄 Change Period"):
        st.session_state.data_loaded = False
        st.session_state.df = None
        st.session_state.projects = {}
        st.session_state.selected_project = None
        st.session_state.chat_history = []
        st.rerun()
