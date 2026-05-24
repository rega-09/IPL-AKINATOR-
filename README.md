# 🏏 IPL Akinator — AI-Powered Player Guessing System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-green?style=flat-square&logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)
![Gemini](https://img.shields.io/badge/Gemini_AI-2.0_Flash-4285F4?style=flat-square&logo=google)
![Firebase](https://img.shields.io/badge/Firebase-Firestore-FFCA28?style=flat-square&logo=firebase)

**Think of any IPL cricketer. We'll identify them in ≤8 questions — using genuine AI reasoning.**

[Live Demo](#) · [API Docs](http://localhost:8000/docs) · [Video Walkthrough](#)

</div>

---

## 🎯 What Is This?

IPL Akinator is an AI-powered game that identifies any IPL cricketer (past or present, 2008–2024) through a sequence of intelligent yes/no questions — similar to the Akinator game, but built entirely on probabilistic AI reasoning instead of scripted decision trees.

The system narrows down a pool of **802 IPL players** using **Bayesian probability updates**, selects questions via **Shannon entropy and information gain**, and generates human-like questions and reasoning narration via **Google Gemini AI**.

---

## 🧠 How The AI Actually Works

This is not a chatbot wrapper. The intelligence is a three-layer reasoning engine:

### Layer 1 — Probabilistic Candidate Pool
Every player starts with equal probability `1/N`. After each answer, scores update using Bayes' theorem:

```
P(player | answer) ∝ P(answer | player) × P(player)
```

Players that fit the answer get multiplied by `0.95`. Players that don't get multiplied by `0.05`. This is applied across all 802 candidates simultaneously — no hard eliminations, no decision trees.

### Layer 2 — Entropy-Based Question Selection
The engine picks the next question by maximising **information gain**:

```
IG(Q) = H(current) − E[H(after asking Q)]
```

Where `H` is Shannon entropy in bits. The best question is always the one that splits the remaining candidate pool closest to 50/50 — maximising uncertainty reduction per question.

### Layer 3 — LLM Enhancement
Google Gemini rephrases mechanical questions into natural cricket-expert language and generates a Sherlock Holmes-style reasoning narration before the final guess.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| **802 IPL Players** | Complete dataset covering all seasons 2008–2024 |
| **Genuine Bayesian AI** | No hardcoded logic or decision trees — pure probabilistic reasoning |
| **≤8 Questions** | Entropy-based question selection minimises questions needed |
| **LLM Narration** | Gemini explains its reasoning before guessing |
| **Live AI Panel** | Real-time probability bars shift after every answer |
| **Learning System** | Wrong guesses stored in Firestore — system improves over time |
| **Graceful Degradation** | Game works even if Gemini API or Firebase is unavailable |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│              React + Vite (port 3000)                       │
│   StartScreen → GameScreen → GuessScreen → ResultScreen     │
│          Live AI Reasoning Panel (probability bars)         │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP (axios)
┌──────────────────────▼──────────────────────────────────────┐
│                      FASTAPI BACKEND                        │
│                     Python (port 8000)                      │
│  POST /game/start  →  POST /game/{id}/answer               │
│  POST /game/{id}/confirm  →  GET /game/{id}/state          │
└────────┬─────────────────┬──────────────────┬──────────────┘
         │                 │                  │
┌────────▼──────┐  ┌───────▼──────┐  ┌───────▼──────────────┐
│  PROBABILITY  │  │  LLM LAYER   │  │  FIREBASE FIRESTORE   │
│    ENGINE     │  │  (Gemini)    │  │  Learning System      │
│               │  │              │  │                       │
│ CandidatePool │  │ Question     │  │ sessions/             │
│ Bayesian      │  │ Rewriter     │  │ learning/             │
│ Updates       │  │ Confidence   │  │ insights/             │
│ Entropy / IG  │  │ Narrator     │  │                       │
└───────────────┘  └──────────────┘  └───────────────────────┘
         │
┌────────▼──────────────────────┐
│     PLAYER DATASET            │
│   802 players · players.json  │
│   48 curated + 754 from CSV   │
└───────────────────────────────┘
```

---

## 📁 Project Structure

```
ipl_akinator/               ← Backend (Python / FastAPI)
├── api/
│   ├── main.py             ← FastAPI app entry point
│   ├── routes.py           ← All 5 API endpoints
│   ├── models.py           ← Pydantic request/response schemas
│   └── session_store.py    ← In-memory session management
├── engine/
│   ├── probability_engine.py  ← Bayesian updates, entropy, information gain
│   ├── question_bank.py       ← 45 calibrated questions with attribute scorers
│   └── game_session.py        ← Full game orchestration
├── llm/
│   ├── gemini_client.py    ← Google Gemini REST API client
│   ├── prompts.py          ← All prompt templates
│   └── enhancer.py         ← LLM enhancement with graceful degradation
├── firebase/
│   ├── firestore_client.py ← Firestore CRUD operations
│   └── learning.py         ← Learning loop (failures → insights)
├── data/
│   ├── raw/finalsheet.csv  ← Source CSV (766 players)
│   └── processed/players.json ← Final 802-player dataset
├── scraper/
│   ├── csv_converter.py    ← CSV → player schema converter
│   └── dataset_builder.py  ← Curated 48-player base dataset
├── utils/helpers.py        ← Shared utilities
├── run.py                  ← Server entry point
└── requirements.txt

frontend/               ← Frontend (React / Vite)
└── src/
    ├── App.jsx             ← Game state machine
    ├── api/game.js         ← API service layer
    └── components/
        ├── StartScreen.jsx
        ├── GameScreen.jsx  ← Question + answer + AI panel
        ├── AIPanel.jsx     ← Live probability visualisation
        ├── GuessScreen.jsx ← Final guess reveal
        └── ResultScreen.jsx
```

---

## 🚀 Local Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Gemini API key (free at [aistudio.google.com](https://aistudio.google.com/app/apikey))
- Firebase project with Firestore (optional — see `firebase/setup_firebase.md`)

### Backend

```bash
# Clone and enter project
git clone https://github.com/pratham-bits/ipl-akinator-TEAM-StumpLogic
cd ipl-akinator

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — add GEMINI_API_KEY and FIREBASE_CREDENTIALS

# Build dataset (run once)
python scraper/csv_converter.py

# Start server
python run.py
```

Backend runs at `http://localhost:8000`
API docs at `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`

---

## 🔌 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/game/start` | Start new game session |
| `POST` | `/game/{id}/answer` | Submit answer (yes/no/maybe/dont_know) |
| `POST` | `/game/{id}/confirm` | Confirm if guess was correct |
| `GET` | `/game/{id}/state` | Get current game state |
| `GET` | `/health` | System health + live stats |

### Example Flow

```bash
# Start game
curl -X POST http://localhost:8000/game/start

# Submit answer
curl -X POST http://localhost:8000/game/{session_id}/answer \
  -H "Content-Type: application/json" \
  -d '{"answer": "yes"}'

# Confirm guess
curl -X POST http://localhost:8000/game/{session_id}/confirm \
  -H "Content-Type: application/json" \
  -d '{"correct": true}'
```

---

## 🧬 The Learning System

Every completed game feeds the learning loop:

```
Wrong guess recorded
        ↓
Firestore: learning/{player_id}
  miss_count++
  failure_patterns[] updated
        ↓
After 3+ misses → Gemini analyzes patterns
        ↓
Insight generated:
  "To identify Dinesh Karthik, focus on KKR
   captaincy and finisher role — not just WK"
        ↓
Insight stored in Firestore: insights/{player_id}
        ↓
Next session: insight injected into question prompts
→ Better questions asked for previously missed players
```

---

## 📊 Dataset

| Source | Players | Method |
|---|---|---|
| Hand-curated | 48 | Manual with rich attributes |
| finalsheet.csv | 754 | CSV import via `csv_converter.py` |
| **Total** | **802** | Deduplicated, schema-validated |

Covers all IPL seasons 2008–2024, Indian and overseas players, all roles.

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Backend API | FastAPI + Python | Async, fast, auto-generates API docs |
| AI Reasoning | Custom Bayesian Engine | Genuine probabilistic reasoning — no hardcoded logic |
| LLM | Google Gemini 2.0 Flash | Free tier, fast, natural question rephrasing |
| Session Storage | In-memory (Python dict) | Zero latency, sufficient for demo |
| Persistent Storage | Firebase Firestore | Real-time, persistent learning data |
| Frontend | React + Vite | Fast build, component-based |
| Player Data | JSON (802 players) | LLM-friendly, fast to query |

---

## 🏆 Evaluation Criteria Addressed

| Criterion | How We Address It |
|---|---|
| **Accuracy** | Bayesian updates across 802 players, entropy-optimised question selection |
| **Question Intelligence** | 45 calibrated questions + Gemini rephrasing for natural language |
| **AI Reasoning (Very High)** | Live probability panel proves genuine dynamic reasoning — not scripted |
| **User Experience** | Polished dark UI, animated probability bars, LLM narration before guess |
| **Innovation & Learning** | Firestore learning loop — system genuinely improves from wrong guesses |

---

## 📄 License

MIT License — see [LICENSE](LICENSE)
# IPL-AKINATOR-
# IPL-AKINATOR-
# IPL-AKINATOR-
