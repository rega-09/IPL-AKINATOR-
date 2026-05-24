# Render Deployment Guide — IPL Akinator Backend

## Step 1 — Create Render Account
Go to: https://render.com → Sign up with GitHub

## Step 2 — Create New Web Service
1. Dashboard → New → Web Service
2. Connect your GitHub account
3. Select your `ipl-akinator` repository
4. Click "Connect"

## Step 3 — Configure the Service

Fill in these settings:

| Setting | Value |
|---|---|
| Name | ipl-akinator-api |
| Root Directory | ipl_akinator |
| Runtime | Python 3 |
| Build Command | pip install -r requirements.txt |
| Start Command | uvicorn api.main:app --host 0.0.0.0 --port $PORT |
| Instance Type | Free |

## Step 4 — Set Environment Variables

In the "Environment" tab, add these key-value pairs:

| Key | Value |
|---|---|
| `GEMINI_API_KEY` | your_gemini_api_key |
| `FIREBASE_CREDENTIALS_JSON` | (paste entire contents of serviceAccountKey.json) |
| `ALLOWED_ORIGINS` | https://ipl-akinator.web.app (add after Firebase deploy) |
| `MAX_QUESTIONS` | 8 |
| `CONFIDENCE_THRESHOLD` | 0.80 |

### How to get FIREBASE_CREDENTIALS_JSON value:
Open your serviceAccountKey.json file, select ALL content, copy and paste
as the value for FIREBASE_CREDENTIALS_JSON.

## Step 5 — Deploy
Click "Create Web Service"
Render will:
1. Clone your repo
2. Run: pip install -r requirements.txt
3. Start: uvicorn api.main:app --host 0.0.0.0 --port $PORT
4. Health check: GET /health

## Step 6 — Verify Deployment
Your API will be live at:
  https://ipl-akinator-api.onrender.com

Test it:
  https://ipl-akinator-api.onrender.com/health
  https://ipl-akinator-api.onrender.com/docs

## Notes
- Free tier sleeps after 15 min of inactivity
- First request after sleep takes ~30 seconds (cold start)
- For hackathon demo: keep a browser tab open to prevent sleeping
- Or upgrade to $7/month "Starter" plan for always-on