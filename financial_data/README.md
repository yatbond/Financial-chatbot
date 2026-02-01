# Financial Data Folder Structure

## Structure
```
financial_data/
├── 2025/
│   ├── 01/  (January)
│   │   ├── file1.xlsx
│   │   └── file1_flat.csv
│   ├── 02/  (February)
│   │   └── ...
│   ├── 03/  (March)
│   └── ...
└── financial_data_index.json
```

## Instructions

### Option 1: Download from Google Drive
1. Go to Google Drive /Ai Chatbot Knowledge Base/year/month
2. Download Excel files to `workspace/financial_data/year/month/`
3. Run the preprocessor:
   ```
   python financial_preprocessor.py
   ```

### Option 2: Sync with Google Drive (Advanced)
Use rclone or Google Drive desktop app to sync the folder.

### Running the Chatbot
```python
from financial_chatbot import initialize, query

# Initialize (auto-parses Excel files)
initialize()

# Query examples
query(Year=2025, Month=1, Sheet_Name='Projection')
query(Year=2025, Financial_Type='1st Working Budget B')
```
