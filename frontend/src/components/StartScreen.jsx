// src/components/StartScreen.jsx
import { useState } from 'react';

export default function StartScreen({ onStart }) {
  const [loading, setLoading] = useState(false);

  const handleStart = async () => {
    setLoading(true);
    await onStart();
    setLoading(false);
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 'clamp(16px, 5vw, 32px)',
      animation: 'fadeIn 0.6s ease',
    }}>
      {/* Cricket ball decoration */}
      <div style={{ fontSize: 'clamp(48px, 12vw, 80px)', marginBottom: 'clamp(16px, 4vw, 32px)', lineHeight: 1 }}>🏏</div>

      {/* Title */}
      <h1 style={{
        fontFamily: 'var(--font-display)',
        fontSize: 'clamp(2.5rem, 7vw, 6rem)',
        color: 'var(--text-primary)',
        letterSpacing: '0.06em',
        textAlign: 'center',
        lineHeight: 1,
        marginBottom: 'clamp(8px, 2vw, 16px)',
      }}>
        IPL AKINATOR
      </h1>

      <p style={{
        fontFamily: 'var(--font-display)',
        fontSize: 'clamp(0.9rem, 3vw, 1.5rem)',
        color: 'var(--gold)',
        letterSpacing: '0.2em',
        marginBottom: 'clamp(20px, 5vw, 40px)',
        textAlign: 'center',
      }}>
        THE AI THAT READS YOUR MIND
      </p>

      {/* Description card */}
      <div style={{
        maxWidth: '480px',
        width: '100%',
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: 'clamp(20px, 5vw, 32px)',
        marginBottom: 'clamp(20px, 5vw, 40px)',
        textAlign: 'center',
      }}>
        <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: 'clamp(16px, 3vw, 24px)', fontSize: 'clamp(0.85rem, 2vw, 1rem)' }}>
          Think of any IPL cricketer — past or present. I'll ask up to
          <span style={{ color: 'var(--gold)', fontWeight: 600 }}> 8 smart questions </span>
          and identify your player using AI-powered reasoning.
        </p>

        {/* How it works */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: 'clamp(16px, 4vw, 24px)', flexWrap: 'wrap' }}>
          {[
            { icon: '🧠', label: 'Bayesian AI' },
            { icon: '⚡', label: '≤8 Questions' },
            { icon: '🎯', label: 'Smart Guessing' },
          ].map(item => (
            <div key={item.label} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 'clamp(1.2rem, 3vw, 1.8rem)', marginBottom: 'clamp(4px, 1vw, 8px)' }}>{item.icon}</div>
              <div style={{ fontSize: 'clamp(0.6rem, 1.5vw, 0.75rem)', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                {item.label}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Start button */}
      <button
        onClick={handleStart}
        disabled={loading}
        style={{
          padding: 'clamp(12px, 3vw, 18px) clamp(32px, 8vw, 56px)',
          fontSize: 'clamp(0.9rem, 2vw, 1.1rem)',
          fontFamily: 'var(--font-display)',
          letterSpacing: '0.15em',
          background: loading
            ? 'rgba(245,166,35,0.3)'
            : 'linear-gradient(135deg, var(--gold), var(--gold-light))',
          color: loading ? 'var(--gold)' : '#000',
          borderRadius: '100px',
          boxShadow: loading ? 'none' : '0 0 30px rgba(245,166,35,0.3)',
          transition: 'all 0.3s ease',
          border: 'none',
          cursor: loading ? 'not-allowed' : 'pointer',
        }}
      >
        {loading ? '🔄 LOADING...' : '▶ START GAME'}
      </button>

      <p style={{ marginTop: '20px', fontSize: '0.75rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
        800+ IPL players · 2008 – 2024
      </p>
    </div>
  );
}