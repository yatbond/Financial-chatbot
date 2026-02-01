"""
Financial Chatbot - Streamlit Web App
Fast loading: list projects first, load data only when selected
"""
import streamlit as st
import pandas as pd
import json
import re
import os
from io import StringIO

KB_FILE = 'chatbot_knowledge_base.json'

def load_knowledge_base():
    """Load knowledge base from file."""
    if os.path.exists(KB_FILE):
        try:
            with open(KB_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_knowledge_base(kb):
    """Save knowledge base to file."""
    with open(KB_FILE, 'w') as f:
        json.dump(kb, f, indent=2)

st.set_page_config(page_title="Financial Chatbot", page_icon="📊")

# Initialize session state
if 'service' not in st.session_state:
    st.session_state.service = None
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'df' not in st.session_state:
    st.session_state.df = None
if 'selected_project' not in st.session_state:
    st.session_state.selected_project = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'available_years' not in st.session_state:
    st.session_state.available_years = []
if 'available_months' not in st.session_state:
    st.session_state.available_months = []
if 'folders_with_data' not in st.session_state:
    st.session_state.folders_with_data = {}
if 'project_list' not in st.session_state:
    st.session_state.project_list = {}  # Just file names, no data
if 'query_knowledge_base' not in st.session_state:
    st.session_state.query_knowledge_base = load_knowledge_base()

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
            st.error("No 'google_credentials' found in secrets")
            return None

        credentials = service_account.Credentials.from_service_account_info(
            creds,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        st.session_state.service = build('drive', 'v3', credentials=credentials)
        return st.session_state.service
    except Exception as e:
        st.error(f"Failed to connect to Google Drive: {e}")
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

def extract_project_info(filename):
    """Extract project code and name from filename."""
    name = filename.replace('_flat.csv', '')
    match = re.match(r'^(\d+)', name)
    if match:
        code = match.group(1)
        project_name = name[len(code):].strip()
        project_name = re.sub(r'\s*Financial\s*Report.*', '', project_name)
        project_name = project_name.strip()
        return code, project_name
    return None, name

def load_folder_structure(service):
    """Load folder structure and list projects (fast - no data loading)."""
    print("=== FUNCTION load_folder_structure called ===")
    folders = list_folders(service)
    print(f"Root folders: {[f['name'] for f in folders]}")

    # Debug: Show all root folders on main page
    st.write(f"**Debug: Root folders found: {[f['name'] for f in folders]}**")

    # Find root folder
    root_folder = None
    for f in folders:
        if f['name'] == 'Ai Chatbot Knowledge Base':
            root_folder = f['id']
            break

    print(f"Root folder found: {root_folder}")
    st.write(f"**Debug: Root folder ID: {root_folder}**")

    if not root_folder:
        st.error("Root folder 'Ai Chatbot Knowledge Base' not found!")
        st.write("Your folder might have a different name. Check the debug output above.")
        return {}, {}
    
    # Find year folders
    year_folders = list_folders(service, root_folder)
    folders_with_data = {}
    project_list = {}  # filename -> (code, name)
    
    for year_folder in year_folders:
        try:
            year = year_folder['name']
            month_folders = list_folders(service, year_folder['id'])
            
            for m in month_folders:
                # Get CSV files in this month folder (with pagination)
                all_csv_files = []
                page_token = None

                while True:
                    csv_result = service.files().list(
                        query=f"'{m['id']}' in parents and name contains '_flat.csv' and trashed=false",
                        fields="files(name), nextPageToken",
                        pageSize=100,
                        pageToken=page_token
                    ).execute()

                    all_csv_files.extend(csv_result.get('files', []))
                    page_token = csv_result.get('nextPageToken')

                    if page_token is None:
                        break

                if all_csv_files:
                    st.write(f"**Found {len(all_csv_files)} files in {year}/{m['name']}**")
                    if year not in folders_with_data:
                        folders_with_data[year] = []
                    folders_with_data[year].append(m['name'])
                    
                    # Store project info (just file names, no data)
                    for csv_file in all_csv_files:
                        code, name = extract_project_info(csv_file['name'])
                        if code:
                            project_list[csv_file['name']] = {'code': code, 'name': name, 'year': year, 'month': m['name']}
        except Exception as e:
            st.error(f"Error processing {year}: {e}")
            continue

    st.write(f"**Debug: Total projects found: {len(project_list)}**")
    return folders_with_data, project_list

def load_project_data(service, filename, year, month):
    """Load a single CSV file (lazy loading when project selected)."""
    try:
        # Find the file ID
        folders = list_folders(service)
        root_folder = None
        for f in folders:
            if f['name'] == 'Ai Chatbot Knowledge Base':
                root_folder = f['id']
                break
        
        year_folders = list_folders(service, root_folder)
        year_folder_id = None
        for f in year_folders:
            if f['name'] == year:
                year_folder_id = f['id']
                break
        
        if not year_folder_id:
            return None
        
        month_folders = list_folders(service, year_folder_id)
        month_folder_id = None
        for f in month_folders:
            if f['name'] == month:
                month_folder_id = f['id']
                break
        
        if not month_folder_id:
            return None
        
        # Find the file
        file_result = service.files().list(
            q=f"'{month_folder_id}' in parents and name='{filename}' and trashed=false",
            fields="files(id, name)"
        ).execute().get('files', [])
        
        if not file_result:
            return None
        
        file_id = file_result[0]['id']
        
        # Download and parse
        request = service.files().get_media(fileId=file_id)
        content = request.execute()
        df = pd.read_csv(StringIO(content.decode('utf-8')))
        
        code, name = extract_project_info(filename)
        if code:
            df['_project'] = f"{code} - {name}"
        
        return df
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return None

def get_project_metrics(df, project):
    """Calculate key metrics for a project."""
    project_df = df[df['_project'] == project]
    if project_df.empty:
        return None
    
    metrics = {}
    gp_filter = (project_df['Item_Code'] == '3') & \
                (project_df['Data_Type'].str.contains('Gross Profit', case=False, na=False))
    
    bp = project_df[(project_df['Sheet_Name'] == 'Financial Status') & 
                    (project_df['Financial_Type'].str.contains('Business Plan', case=False, na=False)) &
                    gp_filter]
    if not bp.empty:
        metrics['Business Plan GP'] = bp['Value'].sum()
    
    proj = project_df[(project_df['Sheet_Name'] == 'Financial Status') & 
                      (project_df['Financial_Type'].str.contains('Projection', case=False, na=False)) &
                      gp_filter]
    if not proj.empty:
        metrics['Projected GP'] = proj['Value'].sum()
    
    wip = project_df[(project_df['Sheet_Name'] == 'Financial Status') & 
                     (project_df['Financial_Type'].str.contains('Audit Report', case=False, na=False)) &
                     gp_filter]
    if not wip.empty:
        metrics['WIP GP'] = wip['Value'].sum()
    
    cf = project_df[(project_df['Sheet_Name'] == 'Financial Status') & 
                    (project_df['Financial_Type'].str.contains('Cash Flow', case=False, na=False)) &
                    gp_filter]
    if not cf.empty:
        metrics['Cash Flow'] = cf['Value'].sum()
    
    return metrics

def find_best_matches(df, search_text, project):
    """Find best matches for a query."""
    project_df = df[df['_project'] == project]
    search_lower = search_text.lower()
    search_words = search_lower.split()
    
    target_item_code = None
    if 'net profit' in search_lower or 'net loss' in search_lower:
        target_item_code = '7'
    elif 'after adjustment' in search_lower or 'adjusted' in search_lower:
        target_item_code = '5'
    
    all_combinations = project_df.groupby(['Financial_Type', 'Data_Type', 'Item_Code']).agg({
        'Value': 'sum',
        'Month': 'first'
    }).reset_index()
    
    matches = []
    
    for _, row in all_combinations.iterrows():
        ft = str(row['Financial_Type']).lower()
        dt = str(row['Data_Type']).lower()
        value = row['Value']
        month = row['Month']
        item_code = row['Item_Code']
        
        score = 0
        matched_count = 0
        total_query_words = len([w for w in search_words if len(w) >= 2])
        
        for word in search_words:
            if len(word) < 2:
                continue
            if word in ft:
                score += 10
                matched_count += 1
            if word in dt:
                score += 10
                matched_count += 1
        
        if 'projected' in search_words and 'projection' in ft:
            score += 30
        if 'budget' in search_words and 'budget' in ft:
            score += 30
        if 'audit' in search_words and 'audit' in ft:
            score += 30
        if 'business' in search_words and 'business' in ft:
            score += 30
        if 'cash' in search_words and 'cash' in ft:
            score += 30
        
        if 'projection' in search_lower and 'projection' in ft:
            score += 20
        if 'budget' in search_lower and 'budget' in ft:
            score += 20
        if 'net profit' in search_lower and 'net profit' in dt:
            score += 20
        
        if target_item_code and item_code == target_item_code:
            score += 5
        
        # Knowledge base boost
        if st.session_state.query_knowledge_base:
            normalized_q = search_lower.strip()
            if normalized_q in st.session_state.query_knowledge_base:
                saved = st.session_state.query_knowledge_base[normalized_q]
                if (saved.get('Financial_Type') == row['Financial_Type'] and
                    saved.get('Data_Type') == row['Data_Type'] and
                    saved.get('Item_Code') == item_code):
                    score += 100
        
        if total_query_words > 0:
            words_found = sum(1 for w in search_words if len(w) >= 2 and (w in ft or w in dt))
            if words_found == total_query_words:
                score += 30
        
        if score > 0:
            matches.append({
                'Sheet_Name': 'Financial Status',
                'Financial_Type': row['Financial_Type'],
                'Data_Type': row['Data_Type'],
                'Value': value,
                'Month': month,
                'Item_Code': item_code,
                'score': score,
                'matched_count': matched_count
            })
    
    matches.sort(key=lambda x: (x['score'], x['matched_count']), reverse=True)
    return matches

def answer_question(df, project, question, selected_filters=None):
    """Answer a user question."""
    project_df = df[df['_project'] == project]
    question_lower = question.lower()
    
    latest_month = project_df['Month'].max()
    target_month = latest_month
    
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
    
    if selected_filters:
        ft_match = selected_filters.get('Financial_Type')
        dt_match = selected_filters.get('Data_Type')
        item_code = selected_filters.get('Item_Code', '3')
    else:
        matches = find_best_matches(df, question, project)
        if not matches:
            return None, matches
        if len(matches) == 1:
            ft_match = matches[0]['Financial_Type']
            dt_match = matches[0]['Data_Type']
            item_code = matches[0]['Item_Code']
        else:
            return None, matches
    
    result_df = project_df[
        (project_df['Financial_Type'] == ft_match) &
        (project_df['Data_Type'] == dt_match) &
        (project_df['Item_Code'] == item_code) &
        (project_df['Month'] == target_month)
    ]
    
    if result_df.empty:
        return f"No data found", []
    
    total_value = result_df['Value'].sum()
    first_record = result_df.iloc[0]
    
    response = f"## ${total_value:,.0f} ('000)\n\n"
    response += f"**Year:** {st.session_state.current_year}\n"
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

print("=== START OF APP ===")
print(f"service is None: {service is None}")

if service is None:
    st.error("Could not connect to Google Drive")
    st.info("Check Streamlit secrets for 'google_credentials'")
else:
    st.success("Connected to Google Drive ✓")
    print("=== About to load folder structure ===")

# Load folder structure (fast - no data)
if not st.session_state.available_years:
    print("=== Loading folder structure ===")
    with st.spinner("Loading folder structure..."):
        folders_with_data, project_list = load_folder_structure(service)
        st.session_state.folders_with_data = folders_with_data
        st.session_state.project_list = project_list
        st.session_state.available_years = sorted(folders_with_data.keys(), reverse=True)
        st.session_state.available_months = sorted(set(m for months in folders_with_data.values() for m in months))

        # Show debug info on main page
        st.write(f"**Debug: Folders with data: {folders_with_data}**")
        st.write(f"**Debug: Total projects found: {len(project_list)}**")

# Year and Month selectors
if st.session_state.available_years:
    st.markdown("### 📅 Select Period")
    
    col1, col2 = st.columns(2)
    
    with col1:
        default_year_idx = 0
        if 'default_year' in st.session_state and st.session_state.default_year:
            try:
                default_year_idx = st.session_state.available_years.index(st.session_state.default_year)
            except:
                pass
        selected_year = st.selectbox("Year:", st.session_state.available_years, index=default_year_idx)
    
    with col2:
        available_months = st.session_state.folders_with_data.get(selected_year, [])
        sorted_months = sorted(available_months, key=lambda x: int(x))
        default_month_idx = len(sorted_months) - 1
        if 'default_month' in st.session_state and st.session_state.default_month:
            try:
                default_month_idx = sorted_months.index(st.session_state.default_month)
            except:
                pass
        selected_month = st.selectbox("Month:", sorted_months, index=default_month_idx)
    
    st.session_state.current_year = selected_year
    st.session_state.current_month = selected_month
    
    # Debug: Show all loaded projects
    with st.expander(f"Debug: All loaded projects ({len(st.session_state.project_list)})", expanded=False):
        for f, info in st.session_state.project_list.items():
            st.write(f"{info['year']}/{info['month']}: {info['code']} - {info['name']}")
    
    # Show projects in this period (fast - just file names)
    projects_in_period = {}
    for filename, info in st.session_state.project_list.items():
        if info['year'] == selected_year and info['month'] == selected_month:
            projects_in_period[filename] = info
    
    st.markdown(f"### 🏗️ Projects in {selected_month}/{selected_year}")
    st.caption(f"Found {len(projects_in_period)} projects")
    
    # Debug: Show all projects in project_list
    with st.expander(f"Debug: All projects in period ({len(projects_in_period)})", expanded=False):
        for f, info in projects_in_period.items():
            st.write(f"{info['code']} - {info['name']}: {f}")
    
    if projects_in_period:
        
        # Sort by numeric code
        sorted_files = sorted(projects_in_period.keys(), 
                             key=lambda x: int(x.split(' ')[0]) if x.split(' ')[0].isdigit() else float('inf'))
        
        # Create project options
        project_options = ["-- Select a project --"] + [f"{projects_in_period[f]['code']} - {projects_in_period[f]['name']}" for f in sorted_files]
        selected_project = st.selectbox("Choose a project:", project_options)
        
        if selected_project != "-- Select a project --":
            # Find the selected file
            selected_file = None
            for f, info in projects_in_period.items():
                if f"{info['code']} - {info['name']}" == selected_project:
                    selected_file = f
                    break
            
            if selected_file and (not st.session_state.data_loaded or 
                                  (st.session_state.selected_file != selected_file)):
                # Load data for this project
                with st.spinner(f"Loading {selected_project}..."):
                    df = load_project_data(service, selected_file, selected_year, selected_month)
                    if df is not None:
                        st.session_state.df = df
                        st.session_state.data_loaded = True
                        st.session_state.selected_project = selected_project
                        st.session_state.selected_file = selected_file
                        st.session_state.chat_history = []
                        st.success(f"✅ Loaded {selected_project}")
                        st.rerun()
                    else:
                        st.error("Failed to load project data")
    else:
        st.info("No projects found in this period")

# Show project dashboard if data loaded
if st.session_state.data_loaded and st.session_state.df is not None:
    project = st.session_state.selected_project
    df = st.session_state.df
    
    st.info(f"**{project}**")
    
    # Get and show metrics
    metrics = get_project_metrics(df, project)
    
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
    
    # Chatbot
    st.markdown("### 💬 Ask about this Project ('000)")
    
    with st.form("chat_form"):
        user_question = st.text_input("Your question:", placeholder="e.g., What is the Net Profit?")
        submitted = st.form_submit_button("Ask")
        
        if submitted and user_question:
            response, matches = answer_question(df, project, user_question)
            
            if response is None and matches:
                st.session_state.pending_question = user_question
                st.session_state.pending_matches = matches
            elif response:
                st.session_state.chat_history.append({"q": user_question, "a": response})
                st.session_state.pending_question = None
                st.session_state.pending_matches = []
    
    # Match selection
    if hasattr(st.session_state, 'pending_question') and st.session_state.pending_matches:
        st.markdown("---")
        st.markdown(f"**Q:** {st.session_state.pending_question}")
        st.markdown("*Multiple matches found. Please select:*")
        
        for i, match in enumerate(st.session_state.pending_matches[:10]):
            col1, col2 = st.columns([4, 1])
            match_label = f"Financial Status → {match['Financial_Type']} → {match['Data_Type']} → Item:{match['Item_Code']} → {selected_year}/{match['Month']} → ${match['Value']:,.0f}"
            with col1:
                st.write(f"{i+1}. {match_label}")
            with col2:
                if st.button(f"Select", key=f"select_{i}"):
                    response, _ = answer_question(df, project, st.session_state.pending_question, selected_filters=match)
                    if response:
                        st.session_state.chat_history.append({
                            "q": st.session_state.pending_question, 
                            "a": response
                        })
                        normalized_q = st.session_state.pending_question.lower().strip()
                        st.session_state.query_knowledge_base[normalized_q] = match
                        save_knowledge_base(st.session_state.query_knowledge_base)
                        st.session_state.pending_question = None
                        st.session_state.pending_matches = []
                        st.rerun()
        
        if st.button("Clear Selection"):
            st.session_state.pending_question = None
            st.session_state.pending_matches = []
            st.rerun()
    
    # Chat history
    if st.session_state.chat_history:
        st.markdown("---")
        for chat in st.session_state.chat_history:
            st.markdown(f"**Q:** {chat['q']}")
            st.markdown(chat['a'])
            st.markdown("---")
    
    if st.button("Clear Chat"):
        st.session_state.chat_history = []
        st.rerun()
    
    if st.button("Reset Preferences"):
        st.session_state.query_knowledge_base = {}
        save_knowledge_base({})
        st.rerun()
    
    if st.button("Change Project"):
        st.session_state.data_loaded = False
        st.session_state.df = None
        st.session_state.selected_project = None
        st.session_state.selected_file = None
        st.session_state.chat_history = []
        st.rerun()
