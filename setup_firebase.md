# Firebase Setup Guide — IPL Akinator
# ─────────────────────────────────────────────────────────────────────────────

## Step 1 — Create Firebase Project

1. Go to: https://console.firebase.google.com
2. Click "Add Project"
3. Name it: ipl-akinator
4. Disable Google Analytics (not needed)
5. Click "Create Project"

## Step 2 — Enable Firestore

1. In left sidebar → Build → Firestore Database
2. Click "Create Database"
3. Choose "Start in test mode" (for hackathon)
4. Select region: asia-south1 (Mumbai — lowest latency from India)
5. Click "Enable"

## Step 3 — Generate Service Account Key

1. In Firebase Console → Project Settings (gear icon)
2. Click "Service Accounts" tab
3. Click "Generate New Private Key"
4. Save the downloaded JSON file as:
   ipl_akinator/firebase/serviceAccountKey.json

   CRITICAL: Add this to .gitignore — never commit it.

## Step 4 — Install Firebase Admin SDK

```bash
pip install firebase-admin
```

Add to requirements.txt:
```
firebase-admin==6.5.0
```

## Step 5 — Update .env

Add to your .env file:
```
FIREBASE_CREDENTIALS=firebase/serviceAccountKey.json
```

## Firestore Collections We'll Create

sessions/          ← One document per completed game
  {session_id}/
    session_id, started_at, ended_at
    questions_asked, final_guess, correct_player
    correct (bool), history (array)

learning/          ← Aggregated failure patterns
  failures/
    {player_id}/
      player_name, miss_count, common_wrong_guesses
      questions_that_failed (array)

insights/          ← LLM-generated improvement notes
  {player_id}/
    player_name, insight_text, generated_at