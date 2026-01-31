# Financial Chatbot

A web app for analyzing construction project financial data from Google Drive Excel files.

## Features

- 📊 Analyze financial data from Excel files
- 📁 Read files directly from Google Drive
- 💬 Natural language chatbot interface
- 📈 Quick financial summaries
- 🔒 Secure Google Drive authentication

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google Drive Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Enable **Google Drive API**
3. Create **OAuth 2.0 credentials** (Desktop app type)
4. Download the JSON file and rename to `credentials.json`
5. Place it in the project root directory

### 3. Run Locally

```bash
streamlit run financial_chatbot.py
```

## Google Drive Folder Structure

Expected structure in "Ai Chatbot Knowledge Base" folder:

```
Ai Chatbot Knowledge Base/
└── [Year]/
    └── [Month (01-12)]/
        ├── Financial Report 1.xlsx
        ├── Financial Report 2.xlsx
        └── ...
```

Example:
```
Ai Chatbot Knowledge Base/
├── 2025/
│   ├── 01/
│   │   ├── Project Alpha.xlsx
│   │   └── Project Beta.xlsx
│   ├── 02/
│   │   └── Project Gamma.xlsx
│   └── 03/
│       └── ...
└── 2026/
    └── 01/
        └── ...
```

## Deployment

### Vercel (Serverless)

Note: Streamlit runs as a Python server, not static files. For Vercel deployment:

1. Install Vercel CLI: `npm i -g vercel`
2. Create `vercel.json`:

```json
{
  "buildCommand": "pip install -r requirements.txt",
  "devCommand": "streamlit run financial_chatbot.py",
  "installCommand": "pip install pipenv && pipenv install",
  "framework": "streamlit"
}
```

3. Deploy: `vercel --prod`

**Important:** Vercel's serverless functions have timeout limits. For production use with large files, consider:

- [Streamlit Community Cloud](https://share.streamlit.io) - Free, native Streamlit hosting
- [Hugging Face Spaces](https://huggingface.co/spaces) - Free GPU hosting
- [Railway](https://railway.app) - Full Python server hosting
- [Render](https://render.com) - Full server hosting

## Files

- `financial_chatbot.py` - Main application
- `requirements.txt` - Python dependencies
- `credentials.json` - Google Drive OAuth credentials (you provide this)
- `vercel.json` - Vercel deployment config
- `.gitignore` - Git ignore rules
