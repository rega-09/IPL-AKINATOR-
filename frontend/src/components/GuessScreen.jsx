// src/components/GuessScreen.jsx — Final guess reveal
import { useState } from 'react';

export default function GuessScreen({ guessData, onConfirm }) {
  const [actualPlayer, setActualPlayer] = useState('');
  const [answered, setAnswered]         = useState(false);

  const handleCorrect = async () => {
    setAnswered(true);
    await onConfirm(true, null);
  };

  const handleWrong = async () => {
    if (!actualPlayer.trim()) return;
    setAnswered(true);
    await onConfirm(false, actualPlayer.trim());
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 'clamp(16px, 5vw, 32px)',
      animation: 'fadeIn 0.5s ease',
    }}>
      {/* Reveal card */}
      <div style={{
        maxWidth: '520px',
        width: '100%',
        background: 'var(--bg-card)',
        border: '1px solid var(--border-gold)',
        borderRadius: 'var(--radius-lg)',
        padding: 'clamp(28px, 6vw, 48px)',
        textAlign: 'center',
        boxShadow: '0 0 60px rgba(245,166,35,0.1)',
      }}>
        {/* AI narration */}
        <div style={{
          background: 'var(--bg-glass)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: 'clamp(12px, 3vw, 18px)',
          marginBottom: 'clamp(20px, 5vw, 32px)',
          textAlign: 'left',
        }}>
          <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
            <div className="badge badge-gold">AI REASONING</div>
          </div>
          <p style={{ fontSize: 'clamp(0.8rem, 2vw, 0.95rem)', color: 'var(--text-secondary)', lineHeight: 1.7, fontStyle: 'italic' }}>
            "{guessData?.message}"
          </p>
        </div>

        {/* The guess */}
        <p style={{ fontSize: 'clamp(0.75rem, 1.5vw, 0.9rem)', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: 'clamp(8px, 2vw, 16px)' }}>
          I believe your player is...
        </p>

        <h1 style={{
          fontFamily: 'var(--font-display)',
          fontSize: 'clamp(2rem, 6vw, 4.5rem)',
          background: 'linear-gradient(135deg, var(--gold), var(--gold-light))',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          letterSpacing: '0.04em',
          marginBottom: 'clamp(8px, 2vw, 16px)',
          animation: 'fadeUp 0.5s 0.2s ease both',
        }}>
          {guessData?.final_guess}
        </h1>

        <div className="badge badge-gold" style={{ marginBottom: 'clamp(20px, 5vw, 32px)', justifyContent: 'center', width: '100%' }}>
          {guessData?.confidence_pct} confidence · {guessData?.questions_asked} questions
        </div>

        {/* Confirm buttons */}
        {!answered ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'clamp(8px, 2vw, 14px)' }}>
            <button
              onClick={handleCorrect}
              style={{
                padding: 'clamp(10px, 2vw, 16px)',
                borderRadius: 'var(--radius)',
                background: 'rgba(34,197,94,0.15)',
                border: '1px solid rgba(34,197,94,0.4)',
                color: 'var(--green-accent)',
                fontSize: 'clamp(0.8rem, 1.5vw, 0.95rem)',
                fontFamily: 'var(--font-mono)',
                letterSpacing: '0.08em',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
              }}
            >
              ✅ YES, THAT'S MY PLAYER!
            </button>

            <div style={{ display: 'flex', gap: 'clamp(6px, 1.5vw, 10px)', flexDirection: 'column' }}>
              <input
                type="text"
                placeholder="Type actual player name..."
                value={actualPlayer}
                onChange={e => setActualPlayer(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleWrong()}
                style={{
                  flex: 1,
                  padding: 'clamp(10px, 2vw, 14px)',
                  borderRadius: 'var(--radius)',
                  background: 'var(--bg-glass)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-primary)',
                  fontSize: 'clamp(0.75rem, 1.5vw, 0.9rem)',
                  fontFamily: 'var(--font-body)',
                  outline: 'none',
                }}
              />
              <button
                onClick={handleWrong}
                disabled={!actualPlayer.trim()}
                style={{
                  padding: 'clamp(10px, 2vw, 14px)',
                  borderRadius: 'var(--radius)',
                  background: 'rgba(239,68,68,0.15)',
                  border: '1px solid rgba(239,68,68,0.4)',
                  color: 'var(--red-accent)',
                  fontSize: 'clamp(0.75rem, 1.5vw, 0.9rem)',
                  fontFamily: 'var(--font-mono)',
                  opacity: actualPlayer.trim() ? 1 : 0.4,
                  cursor: actualPlayer.trim() ? 'pointer' : 'not-allowed',
                  transition: 'all 0.3s ease',
                }}
              >
                ❌ WRONG
              </button>
            </div>
          </div>
        ) : (
          <div style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: 'clamp(0.75rem, 1.5vw, 0.9rem)', animation: 'fadeIn 0.3s ease' }}>
            Recording result...
          </div>
        )}
      </div>
    </div>
  );
}