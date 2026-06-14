# 🏏 IPL Akinator — AI-Powered IPL Player Guessing System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-green?style=flat-square&logo=fastapi)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)
![Gemini](https://img.shields.io/badge/Gemini_AI-2.0_Flash-4285F4?style=flat-square&logo=google)
![Firebase](https://img.shields.io/badge/Firebase-Firestore-FFCA28?style=flat-square&logo=firebase)

### Think of any IPL cricketer — the AI will identify them in ≤8 questions.

Built using **Naive Bayes**, **Entropy-Based Question Selection**, and **LLM-powered reasoning narration**.

[Live Demo](#) • [API Docs](http://localhost:8000/docs)

</div>

--

# 🎯 Overview

IPL Akinator is an AI-powered cricket guessing game inspired by the classic Akinator experience.

The system predicts any IPL cricketer (2008–2024) by asking a sequence of intelligent yes/no questions. Unlike traditional rule-based systems, this project uses:

- **Naive Bayes probability updates**
- **Shannon Entropy & Information Gain**
- **Dynamic candidate ranking**
- **Google Gemini AI for natural reasoning**

The engine continuously narrows down a pool of **802 IPL players** based on user responses and identifies the most probable player within a few questions.

---

# 🧠 AI & Machine Learning Logic

## 1️⃣ Naive Bayes Probability Engine

Each IPL player initially starts with equal probability.

After every answer:

:contentReference[oaicite:0]{index=0}

- Matching players receive higher probability
- Non-matching players receive lower probability
- Probabilities are normalized after every question

This allows the engine to intelligently rank players instead of using hardcoded elimination logic.

---

## 2️⃣ Entropy-Based Question Selection

The next question is selected using **Information Gain**.

:contentReference[oaicite:1]{index=1}

The system always chooses the question that reduces uncertainty the most.

This minimizes the number of questions needed to identify the player.

---

## 3️⃣ LLM Enhancement Layer

Google Gemini AI is used for:

- Human-like question phrasing
- Dynamic reasoning narration
- Final prediction explanation
- Improved gameplay experience

Example:

> “You mentioned the player is an overseas batter and has captained an IPL side. That strongly narrows the possibilities…”

---

# ✨ Features

| Feature | Description |
|---|---|
| 🧠 AI-Based Guessing | Uses Naive Bayes instead of scripted logic |
| 📊 Entropy Optimization | Selects smartest next question |
| 🏏 802 IPL Players | Covers IPL players from 2008–2024 |
| ⚡ ≤8 Questions | Efficient uncertainty reduction |
| 🤖 Gemini AI Narration | Natural reasoning explanations |
| 📈 Live Probability Panel | Dynamic probability updates |
| 🔥 Firebase Learning System | Stores failed guesses for improvements |
| 🛡️ Graceful Degradation | Works even without Gemini/Firebase |

---

# 🏗️ System Architecture

```text
Frontend (React + Vite)
        ↓
FastAPI Backend
        ↓
Naive Bayes Engine
        ↓
Entropy Question Selector
        ↓
Gemini AI Layer
        ↓
Firebase Learning System
        ↓
802-Player Dataset# IPL-AKINATOR-
