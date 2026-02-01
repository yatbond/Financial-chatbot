"""
Google Drive API integration for Streamlit Cloud.
Provides access to G:/My Drive/Ai Chatbot Knowledge Base/ files.
"""

import os
import json
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Path to service account credentials (set via Streamlit secrets or environment variable)
SERVICE_ACCOUNT_INFO = None

# Try to load credentials from various sources
def load_credentials():
    """Load Google credentials from Streamlit secrets or environment."""
    global SERVICE_ACCOUNT_INFO
    
    # Check Streamlit secrets (for Streamlit Cloud)
    try:
        import streamlit as st
        if 'GOOGLE_SERVICE_ACCOUNT' in st.secrets:
            SERVICE_ACCOUNT_INFO = json.loads(st.secrets['GOOGLE_SERVICE_ACCOUNT'])
            return True
    except:
        pass
    
    # Check environment variable
    if os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON'):
        SERVICE_ACCOUNT_INFO = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_JSON'])
        return True
    
    # Check for local credentials file
    cred_path = 'google_service_account.json'
    if os.path.exists(cred_path):
        with open(cred_path, 'r') as f:
            SERVICE_ACCOUNT_INFO = json.load(f)
        return True
    
    return False


def get_drive_service():
    """Get Google Drive service instance."""
    if not load_credentials():
        raise Exception("Google Drive credentials not found. Please configure:")
        print("- Streamlit secrets: GOOGLE_SERVICE_ACCOUNT")
        print("- Environment variable: GOOGLE_SERVICE_ACCOUNT_JSON")
        print("- Local file: google_service_account.json")
    
    credentials = service_account.Credentials.from_service_account_info(
        SERVICE_ACCOUNT_INFO, scopes=SCOPES
    )
    
    return build('drive', 'v3', credentials=credentials)


def list_files_in_folder(folder_path):
    """
    List files in a Google Drive folder path.
    folder_path format: "Ai Chatbot Knowledge Base/2025/12"
    """
    try:
        service = get_drive_service()
        
        # Find folder ID by path
        folder_id = 'root'
        parts = folder_path.split('/')
        
        for part in parts:
            # Search for folder with this name
            results = service.files().list(
                q=f"name='{part}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields="files(id, name)"
            ).execute()
            
            folders = results.get('files', [])
            if folders:
                folder_id = folders[0]['id']
            else:
                raise Exception(f"Folder not found: {part}")
        
        # List files in the folder
        results = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
            fields="files(id, name, mimeType)"
        ).execute()
        
        return results.get('files', [])
    
    except Exception as e:
        print(f"Error listing files: {e}")
        return []


def download_file(file_id, destination_path):
    """Download a Google Sheet/Excel file to local path."""
    try:
        service = get_drive_service()
        
        # Get file metadata
        file = service.files().get(fileId=file_id).execute()
        
        # Download as Excel
        request = service.files().export_media(fileId=file_id, mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        
        with open(destination_path, 'wb') as f:
            f.write(request.execute())
        
        return True
    except Exception as e:
        print(f"Error downloading file: {e}")
        return False


def read_spreadsheet_as_dataframe(file_id):
    """
    Read a Google Sheet directly as DataFrame using pandas.
    Requires the sheet to be shared or accessible.
    """
    try:
        import pandas as pd
        
        # Use the export endpoint to get Excel format
        service = get_drive_service()
        request = service.files().export_media(
            fileId=file_id, 
            mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Download to memory and read with pandas
        from io import BytesIO
        content = request.execute()
        
        # Read all sheets
        excel_file = pd.ExcelFile(BytesIO(content))
        
        all_data = {}
        for sheet_name in excel_file.sheet_names:
            all_data[sheet_name] = pd.read_excel(excel_file, sheet_name=sheet_name)
        
        return all_data
    
    except Exception as e:
        print(f"Error reading spreadsheet: {e}")
        return {}


def find_excel_files_in_gdrive(folder_path="Ai Chatbot Knowledge Base"):
    """
    Find all Excel files in the Google Drive folder.
    Returns list of (file_id, file_name) tuples.
    """
    try:
        service = get_drive_service()
        
        # Find the base folder
        results = service.files().list(
            q=f"name='{folder_path}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name)"
        ).execute()
        
        folders = results.get('files', [])
        if not folders:
            print(f"Folder not found: {folder_path}")
            return []
        
        folder_id = folders[0]['id']
        
        # List all Excel files in folder and subfolders
        all_files = []
        
        def list_recursive(parent_id, path=""):
            results = service.files().list(
                q=f"'{parent_id}' in parents and trashed=false",
                fields="files(id, name, mimeType)"
            ).execute()
            
            for f in results.get('files', []):
                if f['mimeType'] == 'application/vnd.google-apps.spreadsheet':
                    all_files.append({
                        'id': f['id'],
                        'name': f['name'],
                        'path': f"{path}/{f['name']}" if path else f['name']
                    })
                elif f['mimeType'] == 'application/vnd.google-apps.folder':
                    list_recursive(f['id'], f"{path}/{f['name']}" if path else f['name'])
        
        list_recursive(folder_id)
        return all_files
    
    except Exception as e:
        print(f"Error searching files: {e}")
        return []


# Test function
if __name__ == "__main__":
    print("=== Google Drive API Test ===")
    
    if load_credentials():
        print("Credentials loaded successfully")
        
        # List files
        files = find_excel_files_in_gdrive("Ai Chatbot Knowledge Base")
        print(f"\nFound {len(files)} Excel files:")
        for f in files[:5]:
            print(f"  - {f['path']}")
    else:
        print("No credentials found. Please configure:")
        print("1. Create a service account in Google Cloud Console")
        print("2. Share the Drive folder with the service account email")
        print("3. Add credentials to Streamlit secrets or environment variable")
