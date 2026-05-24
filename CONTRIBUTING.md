# Contributing & Repo Setup

## First-Time Setup

```bash
git clone https://github.com/yourusername/ipl-akinator
cd ipl-akinator

# Backend
cd ipl_akinator
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Add your API keys

# Build dataset
python scraper/csv_converter.py

# Start backend
python run.py

# Frontend (new terminal)
cd ../ipl-frontend
npm install
npm run dev
```

## Branch Strategy

```
main          ← stable, demo-ready
dev           ← active development
feature/xyz   ← individual features
```

## Key Files To Know

| File | What It Does |
|---|---|
| `engine/probability_engine.py` | Core Bayesian math |
| `engine/question_bank.py` | Add/edit questions here |
| `llm/prompts.py` | Edit LLM prompts here |
| `data/processed/players.json` | Player dataset |
| `scraper/csv_converter.py` | Re-run to rebuild dataset |