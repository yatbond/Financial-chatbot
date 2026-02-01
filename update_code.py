# Read the file
with open('financial_chatbot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the section to replace
old_section = '''        # Display project data
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
            
            # Data Selection - Two rows of quick filters
            st.markdown("#### 📊 Quick Data Selection")
            
            # Initialize selection state
            if 'data_category' not in st.session_state:
                st.session_state.data_category = None
            if 'data_type' not in st.session_state:
                st.session_state.data_type = None
            
            # Row 1: Category Selection
            st.markdown("**Category:**")
            cat_cols = st.columns(6)
            categories = [
                ("Budget", "Budget_Revision"),
                ("Business Plan", "Business_Plan"),
                ("Audit Report (WIP)", "Audit_Report_WIP"),
                ("Projection", "Projection"),
                ("Committed Value", "Commitments"),
                ("Cash Flow", "Cash_Flow")
            ]
            for i, (cat_name, cat_key) in enumerate(categories):
                with cat_cols[i]:
                    if st.button(cat_name, key=f"cat_{i}", use_container_width=True):
                        st.session_state.data_category = cat_key
                        st.session_state.data_type = None  # Reset type when category changes
                        st.rerun()
            
            # Row 2: Type Selection
            st.markdown("**Type:**")
            type_cols = st.columns(6)
            types = [
                ("Gross Profit (bf adj)", "gp_bf"),
                ("Gross Profit (after)", "gp_after"),
                ("Total Income", "income"),
                ("Total Cost", "cost"),
                ("VO/CE", "vo_ce"),
                ("Claims", "claims")
            ]
            for i, (type_name, type_key) in enumerate(types):
                with type_cols[i]:
                    if st.button(type_name, key=f"type_{i}", use_container_width=True):
                        st.session_state.data_type = type_key
                        st.rerun()
            
            # Display selected data
            if st.session_state.data_category and st.session_state.data_type:
                cat_key = st.session_state.data_category
                type_key = st.session_state.data_type
                
                # Filter data based on type
                if type_key == "gp_bf":
                    filtered = df[df['Trade'].str.contains('Gross Profit', case=False, na=False)]
                elif type_key == "gp_after":
                    filtered = df[df['Trade'].str.contains('Gross Profit', case=False, na=False)]
                elif type_key == "income":
                    # Income items (usually category 1)
                    filtered = df[df['Item'].astype(str).str.match(r'^1(\\.|$)', na=False)]
                elif type_key == "cost":
                    # Cost items (usually category 2)
                    filtered = df[df['Item'].astype(str).str.match(r'^2(\\.|$)', na=False)]
                elif type_key == "vo_ce":
                    filtered = df[df['Trade'].str.contains('VO|Compensation|CE', case=False, na=False)]
                elif type_key == "claims":
                    filtered = df[df['Trade'].str.contains('Claim', case=False, na=False)]
                else:
                    filtered = df
                
                # Get category column
                if cat_key in filtered.columns:
                    total = filtered[cat_key].sum()
                    st.success(f"**Total {cat_key.replace('_', ' ')}:** ${total:,.2f}")
                    
                    # Show breakdown
                    if 'Trade' in filtered.columns:
                        st.markdown("**Breakdown:**")
                        st.dataframe(filtered[['Item', 'Trade', cat_key]].sort_values(by=cat_key, ascending=False), use_container_width=True)
                else:
                    st.warning(f"Column '{cat_key}' not found in data")
            
            # Chat input
            st.markdown("#### 💭 Ask a Question")
            user_question = st.text_input("Type your question...", placeholder="e.g., What is the total cost?")
            
            if user_question:
                answer = answer_question(df, user_question)
                st.markdown(f"**Answer:** {answer}")
            
            # Data toggle
            with st.expander("📊 View Raw Data"):
                st.dataframe(df, use_container_width=True)'''

new_section = '''        # Display project data
        if 'project_data' in st.session_state and st.session_state.project_data is not None:
            df = st.session_state.project_data
            
            # Load Financial Status sheet data for high-level summary
            try:
                from io import BytesIO
                request = st.session_state.drive_service.files().get_media(fileId=project['file_id'])
                file_content = request.execute()
                excel_file = BytesIO(file_content)
                
                # Parse Financial Status sheet
                df_financial = pd.read_excel(excel_file, sheet_name='Financial Status', header=None)
                
                # Extract the 3 key metrics from Financial Status
                # Row 9-11 contain the Gross Profit data
                gp_projection = 0
                gp_wip = 0
                gp_cash_flow = 0
                
                for idx in range(9, min(20, len(df_financial))):
                    item_name = str(df_financial.iloc[idx, 0]).strip() if pd.notna(df_financial.iloc[idx, 0]) else ""
                    if 'gross profit' in item_name.lower() and 'adjustment' not in item_name.lower():
                        # Get the values from columns B, D, F (1, 3, 5)
                        gp_projection = float(df_financial.iloc[idx, 1]) if pd.notna(df_financial.iloc[idx, 1]) else 0
                        gp_wip = float(df_financial.iloc[idx, 3]) if pd.notna(df_financial.iloc[idx, 3]) else 0
                        gp_cash_flow = float(df_financial.iloc[idx, 5]) if pd.notna(df_financial.iloc[idx, 5]) else 0
                        break
                
                # Show 3 high-level metrics from Financial Status
                s1, s2, s3 = st.columns(3)
                s1.metric("Projected Gross Profit (bf adj)", f"${gp_projection:,.0f}")
                s2.metric("WIP Gross Profit (bf adj)", f"${gp_wip:,.0f}")
                s3.metric("Cash Flow", f"${gp_cash_flow:,.0f}")
                
            except Exception as e:
                st.warning(f"Could not load Financial Status summary: {e}")
            
            # Data Selection - Two rows of quick filters
            st.markdown("#### 📊 Quick Data Selection")
            
            # Initialize selection state
            if 'data_category' not in st.session_state:
                st.session_state.data_category = None
            if 'data_type' not in st.session_state:
                st.session_state.data_type = None
            
            # Row 1: Category Selection
            st.markdown("**Category:**")
            cat_cols = st.columns(6)
            categories = [
                ("Budget", "Budget_Revision"),
                ("Business Plan", "Business_Plan"),
                ("Audit Report (WIP)", "Audit_Report_WIP"),
                ("Projection", "Projection"),
                ("Committed Value", "Commitments"),
                ("Cash Flow", "Cash_Flow")
            ]
            for i, (cat_name, cat_key) in enumerate(categories):
                with cat_cols[i]:
                    if st.button(cat_name, key=f"cat_{i}", use_container_width=True):
                        st.session_state.data_category = cat_key
                        st.session_state.data_type = None
                        st.rerun()
            
            # Row 2: Type Selection
            st.markdown("**Type:**")
            type_cols = st.columns(6)
            types = [
                ("Gross Profit (bf adj)", "gp_bf"),
                ("Gross Profit (after)", "gp_after"),
                ("Total Income", "income"),
                ("Total Cost", "cost"),
                ("VO/CE", "vo_ce"),
                ("Claims", "claims")
            ]
            for i, (type_name, type_key) in enumerate(types):
                with type_cols[i]:
                    if st.button(type_name, key=f"type_{i}", use_container_width=True):
                        st.session_state.data_type = type_key
                        st.rerun()
            
            # Display selected data from Financial Status sheet
            if st.session_state.data_category and st.session_state.data_type:
                cat_key = st.session_state.data_category
                type_key = st.session_state.data_type
                
                # Reload Financial Status sheet for breakdown
                try:
                    request = st.session_state.drive_service.files().get_media(fileId=project['file_id'])
                    file_content = request.execute()
                    excel_file = BytesIO(file_content)
                    df_status = pd.read_excel(excel_file, sheet_name='Financial Status', header=None)
                    
                    # Parse Financial Status data rows (starting from row 15)
                    data_rows = []
                    for idx in range(15, len(df_status)):
                        item_code = df_status.iloc[idx, 0]
                        if pd.isna(item_code) or str(item_code).strip() == '':
                            continue
                        
                        item_str = str(item_code).strip()
                        trade = df_status.iloc[idx, 1] if pd.notna(df_status.iloc[idx, 1]) else ''
                        
                        # Extract values from columns B, D, F (Projection, WIP, Cash Flow)
                        row_data = {
                            'Item': item_str,
                            'Trade': str(trade).strip(),
                            'Projection': float(df_status.iloc[idx, 1]) if pd.notna(df_status.iloc[idx, 1]) else 0,
                            'WIP': float(df_status.iloc[idx, 3]) if pd.notna(df_status.iloc[idx, 3]) else 0,
                            'Cash_Flow': float(df_status.iloc[idx, 5]) if pd.notna(df_status.iloc[idx, 5]) else 0
                        }
                        data_rows.append(row_data)
                    
                    df_filtered = pd.DataFrame(data_rows)
                    
                    # Filter based on type
                    if type_key == "gp_bf":
                        filtered = df_filtered[df_filtered['Trade'].str.contains('Gross Profit', case=False, na=False)]
                    elif type_key == "gp_after":
                        filtered = df_filtered[df_filtered['Trade'].str.contains('Gross Profit', case=False, na=False)]
                    elif type_key == "income":
                        filtered = df_filtered[df_filtered['Item'].astype(str).str.match(r'^1(\\.|$)', na=False)]
                    elif type_key == "cost":
                        filtered = df_filtered[df_filtered['Item'].astype(str).str.match(r'^2(\\.|$)', na=False)]
                    elif type_key == "vo_ce":
                        filtered = df_filtered[df_filtered['Trade'].str.contains('VO|Compensation|CE', case=False, na=False)]
                    elif type_key == "claims":
                        filtered = df_filtered[df_filtered['Trade'].str.contains('Claim', case=False, na=False)]
                    else:
                        filtered = df_filtered
                    
                    # Get total based on category
                    if cat_key == "Projection":
                        col_name = 'Projection'
                    elif cat_key == "Audit_Report_WIP":
                        col_name = 'WIP'
                    elif cat_key == "Cash_Flow":
                        col_name = 'Cash_Flow'
                    else:
                        col_name = 'Projection'
                    
                    if col_name in filtered.columns:
                        total = filtered[col_name].sum()
                        st.success(f"**Total:** ${total:,.2f}")
                        
                        # Show breakdown from Financial Status
                        st.markdown("**Breakdown (Financial Status):**")
                        display_cols = ['Item', 'Trade', col_name]
                        st.dataframe(filtered[display_cols].sort_values(by=col_name, ascending=False), use_container_width=True)
                    
                except Exception as e:
                    st.error(f"Error loading Financial Status data: {e}")
            
            # Data toggle
            with st.expander("📊 View Raw Data"):
                st.dataframe(df, use_container_width=True)'''

# Replace
new_content = content.replace(old_section, new_section)

# Write back
with open('financial_chatbot.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Done!')
