with open('financial_chatbot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the csv_files section with pagination
old_section = """for m in month_folders:
                # Get CSV files in this month folder
                csv_files = service.files().list(
                    q=f"'{m['id']}' in parents and name contains '_flat.csv' and trashed=false",
                    fields="files(name)",
                    pageSize=100
                ).execute().get('files', [])
                
                if csv_files:
                    if year not in folders_with_data:
                        folders_with_data[year] = []
                    folders_with_data[year].append(m['name'])
                    
                    # Store project info (just file names, no data)
                    for csv_file in csv_files:
                        code, name = extract_project_info(csv_file['name'])
                        if code:
                            project_list[csv_file['name']] = {'code': code, 'name': name, 'year': year, 'month': m['name']}"""

new_section = """for m in month_folders:
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
                    if year not in folders_with_data:
                        folders_with_data[year] = []
                    folders_with_data[year].append(m['name'])
                    
                    # Store project info (just file names, no data)
                    for csv_file in all_csv_files:
                        code, name = extract_project_info(csv_file['name'])
                        if code:
                            project_list[csv_file['name']] = {'code': code, 'name': name, 'year': year, 'month': m['name']}"""

if old_section in content:
    content = content.replace(old_section, new_section)
    with open('financial_chatbot.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Updated CSV file query with pagination')
else:
    print('Could not find old section to replace')
