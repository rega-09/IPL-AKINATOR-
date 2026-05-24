// src/App.jsx
// ─────────────────────────────────────────────────────────────────────────────
// WHY A STATE MACHINE APPROACH?
//   The game has 4 distinct phases: start → playing → guessing → result.
//   Each phase shows a completely different screen and has different valid actions.
//   A `screen` state variable acts as a simple state machine — clean and predictable.
// ─────────────────────────────────────────────────────────────────────────────
import { useState, useCallback } from 'react';
import { startGame, submitAnswer, confirmGuess } from './api/game';
import StartScreen  from './components/StartScreen';
import GameScreen   from './components/GameScreen';
import GuessScreen  from './components/GuessScreen';
import ResultScreen from './components/ResultScreen';
import './index.css';

// Game screens — our state machine states
const SCREENS = { START: 'start', GAME: 'game', GUESS: 'guess', RESULT: 'result' };

export default function App() {
  const [screen,    setScreen]    = useState(SCREENS.START);
  const [sessionId, setSessionId] = useState(null);
  const [gameData,  setGameData]  = useState(null);   // Current question + candidates
  const [guessData, setGuessData] = useState(null);   // Final guess details
  const [result,    setResult]    = useState(null);   // End game summary
  const [history,   setHistory]   = useState([]);     // Q&A history for display
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState(null);

  // ── START GAME ─────────────────────────────────────────────────────────────
  const handleStart = useCallback(async () => {
    try {
      setError(null);
      const data = await startGame();
      setSessionId(data.session_id);
      setGameData(data);
      setHistory([]);
      setScreen(SCREENS.GAME);
    } catch (err) {
      setError('Could not connect to server. Is the backend running on port 8000?');
      console.error(err);
    }
  }, []);

  // ── SUBMIT ANSWER ──────────────────────────────────────────────────────────
  const handleAnswer = useCallback(async (answer) => {
    if (!sessionId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await submitAnswer(sessionId, answer);

      if (data.status === 'active') {
        // Add completed turn to history
        setHistory(prev => [...prev, {
          question_number: gameData?.question_number ?? 1,
          question_text:   gameData?.current_question?.text ?? '',
          answer,
        }]);
        setGameData(data);

      } else if (data.status === 'guessing') {
        // Add last turn to history
        setHistory(prev => [...prev, {
          question_number: gameData?.question_number ?? 1,
          question_text:   gameData?.current_question?.text ?? '',
          answer,
        }]);
        setGuessData(data);
        setScreen(SCREENS.GUESS);
      }
    } catch (err) {
      setError('Something went wrong. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [sessionId, gameData]);

  // ── CONFIRM GUESS ──────────────────────────────────────────────────────────
  const handleConfirm = useCallback(async (correct, actualPlayer) => {
    if (!sessionId) return;
    try {
      const data = await confirmGuess(sessionId, correct, actualPlayer);
      setResult(data);
      setScreen(SCREENS.RESULT);
    } catch (err) {
      setError('Failed to confirm guess.');
      console.error(err);
    }
  }, [sessionId]);

  // ── PLAY AGAIN ─────────────────────────────────────────────────────────────
  const handlePlayAgain = useCallback(() => {
    setScreen(SCREENS.START);
    setSessionId(null);
    setGameData(null);
    setGuessData(null);
    setResult(null);
    setHistory([]);
    setError(null);
  }, []);

  // ── ERROR BANNER ───────────────────────────────────────────────────────────
  const ErrorBanner = () => error ? (
    <div style={{
      position: 'fixed', top: '16px', left: '50%', transform: 'translateX(-50%)',
      background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.4)',
      borderRadius: 'var(--radius)', padding: '12px 20px',
      color: 'var(--red-accent)', fontSize: '0.85rem',
      fontFamily: 'var(--font-mono)', zIndex: 1000,
      maxWidth: '500px', textAlign: 'center',
      animation: 'fadeUp 0.3s ease',
    }}>
      ⚠️ {error}
    </div>
  ) : null;

  // ── RENDER ─────────────────────────────────────────────────────────────────
  return (
    <>
      <ErrorBanner />
      {screen === SCREENS.START  && <StartScreen  onStart={handleStart} />}
      {screen === SCREENS.GAME   && <GameScreen   gameData={gameData} onAnswer={handleAnswer} loading={loading} history={history} />}
      {screen === SCREENS.GUESS  && <GuessScreen  guessData={guessData} onConfirm={handleConfirm} />}
      {screen === SCREENS.RESULT && <ResultScreen result={result} onPlayAgain={handlePlayAgain} />}
    </>
  );
}