// src/components/AIPanel.jsx
// Live AI reasoning panel — shows candidates + probability bars + entropy
import { useEffect, useState } from 'react';

// Animated probability bar for each candidate
function CandidateBar({ candidate, index, maxProb }) {
  const [width, setWidth] = useState(0);
  const pct = (candidate.probability / maxProb) * 100;

  // Animate bar on mount + whenever probability changes
  useEffect(() => {
    const t = setTimeout(() => setWidth(pct), index * 80);
    return () => clearTimeout(t);
  }, [pct, index]);

  const prob = Math.round(candidate.probability * 100);

  return (
    <div style={{ marginBottom: 'clamp(8px, 1.5vw, 12px)' }}>
      {/* Name + percentage */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'clamp(4px, 1vw, 6px)' }}>
        <span style={{
          fontSize: 'clamp(0.75rem, 1.5vw, 0.9rem)',
          fontWeight: 600,
          color: index === 0 ? 'var(--gold)' : 'var(--text-secondary)',
          fontFamily: 'var(--font-body)',
        }}>
          {index === 0 && '🎯 '}{candidate.name}
        </span>
        <span style={{
          fontSize: 'clamp(0.65rem, 1.2vw, 0.8rem)',
          fontFamily: 'var(--font-mono)',
          color: index === 0 ? 'var(--gold)' : 'var(--text-dim)',
        }}>
          {prob}%
        </span>
      </div>

      {/* Bar track */}
      <div style={{
        height: '6px',
        background: 'rgba(255,255,255,0.06)',
        borderRadius: '100px',
        overflow: 'hidden',
      }}>
        {/* Animated fill */}
        <div style={{
          height: '100%',
          width: `${width}%`,
          borderRadius: '100px',
          background: index === 0
            ? 'linear-gradient(90deg, var(--gold), var(--gold-light))'
            : 'rgba(255,255,255,0.2)',
          transition: 'width 0.6s cubic-bezier(0.34,1.56,0.64,1)',
          boxShadow: index === 0 ? '0 0 8px rgba(245,166,35,0.5)' : 'none',
        }} />
      </div>
    </div>
  );
}

// Entropy meter — visual uncertainty indicator
function EntropyMeter({ entropy, maxEntropy = 6 }) {
  const pct = Math.max(0, Math.min(100, (entropy / maxEntropy) * 100));
  const color = pct > 60 ? '#ef4444' : pct > 30 ? 'var(--gold)' : 'var(--green-accent)';

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'clamp(4px, 1vw, 6px)' }}>
        <span style={{ fontSize: 'clamp(0.6rem, 1.2vw, 0.75rem)', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
          Uncertainty
        </span>
        <span style={{ fontSize: 'clamp(0.6rem, 1.2vw, 0.75rem)', color, fontFamily: 'var(--font-mono)' }}>
          {entropy?.toFixed(2)} bits
        </span>
      </div>
      <div style={{ height: '4px', background: 'rgba(255,255,255,0.06)', borderRadius: '100px', overflow: 'hidden' }}>
        <div style={{
          height: '100%',
          width: `${pct}%`,
          background: color,
          borderRadius: '100px',
          transition: 'width 0.8s ease, background 0.4s ease',
        }} />
      </div>
    </div>
  );
}

export default function AIPanel({ candidates = [], entropy, activeCount, questionCount }) {
  const maxProb = candidates.length > 0 ? candidates[0].probability : 1;

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)',
      padding: 'clamp(14px, 3vw, 24px)',
      height: '100%',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: 'clamp(12px, 2vw, 18px)' }}>
        <div style={{
          width: '8px', height: '8px', borderRadius: '50%',
          background: 'var(--green-accent)',
          boxShadow: '0 0 6px var(--green-accent)',
          animation: 'pulse-gold 2s infinite',
        }} />
        <span style={{
          fontSize: 'clamp(0.65rem, 1.2vw, 0.8rem)',
          fontFamily: 'var(--font-mono)',
          color: 'var(--green-accent)',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          fontWeight: 500,
        }}>
          AI Reasoning
        </span>
      </div>

      {/* Candidates */}
      {candidates.length > 0 ? (
        <div style={{ marginBottom: 'clamp(12px, 2vw, 18px)' }}>
          <p style={{ fontSize: 'clamp(0.6rem, 1.2vw, 0.75rem)', color: 'var(--text-dim)', marginBottom: 'clamp(8px, 1.5vw, 12px)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Top Suspects
          </p>
          {candidates.map((c, i) => (
            <CandidateBar key={c.player_id} candidate={c} index={i} maxProb={maxProb} />
          ))}
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: 'clamp(12px, 2vw, 18px) 0', color: 'var(--text-dim)', fontSize: 'clamp(0.75rem, 1.5vw, 0.9rem)' }}>
          Awaiting first answer...
        </div>
      )}

      {/* Divider */}
      <div style={{ height: '1px', background: 'var(--border)', margin: 'clamp(10px, 2vw, 16px) 0' }} />

      {/* Stats row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'clamp(10px, 2vw, 16px)' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 'clamp(1.1rem, 2vw, 1.5rem)', fontFamily: 'var(--font-display)', color: 'var(--gold)' }}>
            {activeCount ?? '—'}
          </div>
          <div style={{ fontSize: 'clamp(0.6rem, 1vw, 0.7rem)', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            In Pool
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 'clamp(1.1rem, 2vw, 1.5rem)', fontFamily: 'var(--font-display)', color: 'var(--blue-accent)' }}>
            {questionCount ?? 0}
          </div>
          <div style={{ fontSize: 'clamp(0.6rem, 1vw, 0.7rem)', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Asked
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 'clamp(1.1rem, 2vw, 1.5rem)', fontFamily: 'var(--font-display)', color: 'var(--text-secondary)' }}>
            8
          </div>
          <div style={{ fontSize: 'clamp(0.6rem, 1vw, 0.7rem)', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Max Q's
          </div>
        </div>
      </div>

      {/* Entropy meter */}
      {entropy !== undefined && <EntropyMeter entropy={entropy} />}

      {/* Bayesian label */}
      <div style={{ marginTop: 'clamp(10px, 2vw, 16px)', padding: 'clamp(6px, 1vw, 10px)', background: 'var(--bg-glass)', borderRadius: '8px', textAlign: 'center' }}>
        <span style={{ fontSize: 'clamp(0.6rem, 1vw, 0.75rem)', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
          Bayesian · Entropy · Information Gain
        </span>
      </div>
    </div>
  );
}