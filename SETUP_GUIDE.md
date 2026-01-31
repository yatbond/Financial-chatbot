# Financial Chatbot Setup Guide

## Prerequisites

1. Python 3.9 or higher
2. Google account with access to Google Drive

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Set Up Google Drive Credentials

### Option A: Use Existing Credentials
If you already have Google Cloud credentials:
1. Download `credentials.json` from Google Cloud Console
2. Place it in the same directory as `financial_chatbot.py`

### Option B: Create New Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable Google Drive API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click "Enable"
4. Create OAuth credentials:
   - Navigate to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Desktop app"
   - Download the JSON file
5. Rename the downloaded file to `credentials.json`
6. Place it in the app directory

## Step 3: Run the App

```bash
streamlit run financial_chatbot.py
```

The app will open in your browser at `http://localhost:8501`

## Step 4: First Run Authentication

On first run, you'll need to:
1. Click "Connect to Google Drive" in the sidebar
2. A browser window will open for Google authentication
3. Sign in and grant access to Google Drive
4. Token will be saved for future runs

## Folder Structure Expected

Your Google Drive should have this structure:
```
Google Drive/
└── Ai Chatbot Knowledge Base/
    └── [Year]/
        └── [Month (01-12)]/
            └── *.xlsx (Financial Excel files)
```

Example:
```
Google Drive/
└── Ai Chatbot Knowledge Base/
    └── 2025/
        ├── 01/
        │   ├── Financial Report.xlsx
        │   └── Project Analysis.xlsx
        └── 02/
            └── Financial Report.xlsx
```

## Troubleshooting

### "credentials.json not found"
- Download credentials from Google Cloud Console
- Ensure file is in the same directory as the Python script

### "Failed to connect to Google Drive"
- Check that Google Drive API is enabled
- Verify credentials are valid
- Try deleting `token_drive.pickle` and re-authenticating

### "No projects found"
- Verify folder structure matches the expected format
- Check that Excel files are in the correct location
- Ensure folder names match exactly (Year/Month/Project)

## Files Created

- `financial_chatbot.py` - Main application
- `requirements.txt` - Python dependencies
- `credentials.json` - Google Drive credentials (you provide this)
- `token_drive.pickle` - Cached authentication token (auto-created)
- `financial_data_cache/` - Cached CSV files (auto-created)
