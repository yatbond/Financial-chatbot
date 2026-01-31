# Git & Vercel Deployment Guide

## 1. Initialize Git Repository

```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit: Financial Chatbot"
```

## 2. Create GitHub Repository

1. Go to [GitHub.com](https://github.com)
2. Click "+" > "New repository"
3. Name: `financial-chatbot`
4. Public or Private
5. Don't initialize with README
6. Click "Create repository"

## 3. Push to GitHub

```bash
git remote add origin https://github.com/YOUR_USERNAME/financial-chatbot.git
git branch -M main
git push -u origin main
```

## 4. Deploy to Vercel

### Option A: Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy
vercel
```

### Option B: Vercel Dashboard

1. Go to [Vercel.com](https://vercel.com)
2. Click "Add New..." > "Project"
3. Import from GitHub
4. Select `financial-chatbot` repository
5. Configure:
   - Framework Preset: `Streamlit` (or Other)
   - Build Command: `pip install -r requirements.txt`
   - Output Directory: `leave empty`
   - Install Command: `pip install pipenv &&6. Click "Deploy"

## 5. Environment pipenv install`
 Variables on Vercel

For Vercel deployment, you need to set environment variables:

1. Go to Vercel Dashboard > Your Project > Settings > Environment Variables
2. Add:
   - No sensitive env vars needed (credentials.json is file-based)

**Note:** For production, consider using environment variables instead of `credentials.json`:

```python
# In financial_chatbot.py, modify get_drive_service():
import os

CLIENT_SECRETS = os.environ.get('GOOGLE_CLIENT_SECRETS', 'credentials.json')
```

## 6. Important: Vercel Limitations

⚠️ **Streamlit on Vercel has limitations:**

- **Timeout limits:** Vercel's serverless functions timeout after ~10 seconds
- **No persistent processes:** Streamlit needs a running Python process
- **Not ideal for Streamlit**

**Better alternatives for Streamlit:**

| Platform | Free Tier | Notes |
|----------|-----------|-------|
| [Streamlit Community Cloud](https://share.streamlit.io) | ✅ | Native Streamlit hosting, easiest! |
| [Hugging Face Spaces](https://huggingface.co/spaces) | ✅ | Free GPU, great for ML apps |
| [Railway](https://railway.app) | ✅ $5 credit/month | Full Python server |
| [Render](https://render.com) | ✅ Free tier | Full server hosting |
| [Fly.io](https://fly.io) | ✅ | Edge computing |

**Recommendation:** Use **Streamlit Community Cloud** for this app - it's free, native, and perfect for Streamlit apps.

## 7. Quick Deploy to Streamlit Cloud (Recommended)

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub
4. Click "New app" > "From GitHub"
5. Select your repository
6. Set requirements file: `requirements.txt`
7. Click "Deploy!"

## Files to Commit

Required files:
- ✅ `financial_chatbot.py` - Main app
- ✅ `requirements.txt` - Dependencies
- ✅ `README.md` - Documentation
- ✅ `.gitignore` - Ignore patterns
- ❌ `credentials.json` - **NEVER commit** (add to .gitignore!)
- ❌ `token_drive.pickle` - **NEVER commit** (auto-generated)
- ❌ `financial_data_cache/` - **NEVER commit** (auto-generated)

## After First Deploy

```bash
# Make changes
git add .
git commit -m "Describe your changes"
git push
```

Vercel will auto-deploy on push!
