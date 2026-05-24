// src/api/game.js
// ─────────────────────────────────────────────────────────────────────────────
// WHY THIS FILE?
//   All API calls in ONE place. If the backend URL changes, we change it here.
//   Components never call fetch() directly — they import these functions.
//   This is the Repository Pattern applied to frontend API calls.
// ─────────────────────────────────────────────────────────────────────────────

import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// WHY axios and not fetch?
//   axios automatically parses JSON, throws on 4xx/5xx, and has
//   better error messages than raw fetch. Less boilerplate per call.
const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,  // 15s — LLM calls can take a moment
  headers: { 'Content-Type': 'application/json' },
});

export const startGame = async () => {
  const res = await api.post('/game/start', {});
  return res.data;
};

export const submitAnswer = async (sessionId, answer) => {
  const res = await api.post(`/game/${sessionId}/answer`, { answer });
  return res.data;
};

export const confirmGuess = async (sessionId, correct, actualPlayer = null) => {
  const res = await api.post(`/game/${sessionId}/confirm`, {
    correct,
    actual_player: actualPlayer,
  });
  return res.data;
};

export const getGameState = async (sessionId) => {
  const res = await api.get(`/game/${sessionId}/state`);
  return res.data;
};

export const checkHealth = async () => {
  const res = await api.get('/health');
  return res.data;
};