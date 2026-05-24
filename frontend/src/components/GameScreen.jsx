// src/components/GameScreen.jsx
import { useState } from 'react';
import AIPanel from './AIPanel';

const ANSWERS = [
  { value: 'yes',       label: 'YES',        emoji: '✅', color: 'var(--green-accent)' },
  { value: 'no',        label: 'NO',         emoji: '❌', color: 'var(--red-accent)' },
  { value: 'maybe',     label: 'MAYBE',      emoji: '🤔', color: 'var(--gold)' },
  { value: 'dont_know', label: "DON'T KNOW", emoji: '❓', color: 'var(--blue-accent)' },
];

// Answer button — animates on select
function AnswerButton({ answer, selected, onClick, disabled }) {
  const isSelected = selected === answer.value;

  return (
    <button
      onClick={() => onClick(answer.value)}
      disabled={disabled}
      style={{
        flex: 1,
        minWidth: 'clamp(90px, 20vw, 140px)',
        padding: 'clamp(10px, 2vw, 16px) clamp(6px, 1.5vw, 10px)',
        borderRadius: 'var(--radius)',
        fontSize: 'clamp(0.65rem, 1.5vw, 0.8rem)',
        fontFamily: 'var(--font-mono)',
        letterSpacing: '0.08em',
        background: isSelected
          ? `${answer.color}22`
          : 'var(--bg-glass)',
        border: `1px solid ${isSelected ? answer.color : 'var(--border)'}`,
        color: isSelected ? answer.color : 'var(--text-secondary)',
        transform: isSelected ? 'scale(1.04)' : 'scale(1)',
        boxShadow: isSelected ? `0 0 16px ${answer.color}44` : 'none',
        transition: 'all 0.2s cubic-bezier(0.34,1.56,0.64,1)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '4px',
        opacity: disabled && !isSelected ? 0.5 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
      }}
    >
      <span style={{ fontSize: 'clamp(1rem, 2.5vw, 1.3rem)' }}>{answer.emoji}</span>
      <span>{answer.label}</span>
    </button>
  );
}

// Progress bar at top
function ProgressBar({ current, max }) {
  return (
    <div style={{ marginBottom: 'clamp(8px, 2vw, 12px)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'clamp(4px, 1vw, 8px)', flexWrap: 'wrap', gap: '8px' }}>
        <span style={{ fontSize: 'clamp(0.6rem, 1.5vw, 0.75rem)', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
          Question {current} of {max}
        </span>
        <span style={{ fontSize: 'clamp(0.6rem, 1.5vw, 0.75rem)', fontFamily: 'var(--font-mono)', color: 'var(--gold)' }}>
          {max - current} remaining
        </span>
      </div>
      <div style={{ height: '3px', background: 'var(--border)', borderRadius: '100px', overflow: 'hidden' }}>
        <div style={{
          height: '100%',
          width: `${(current / max) * 100}%`,
          background: 'linear-gradient(90deg, var(--gold), var(--gold-light))',
          borderRadius: '100px',
          transition: 'width 0.5s ease',
        }} />
      </div>
    </div>
  );
}

// History item in sidebar
function HistoryItem({ turn }) {
  const answerColors = {
    yes: 'var(--green-accent)', no: 'var(--red-accent)',
    maybe: 'var(--gold)', dont_know: 'var(--blue-accent)',
  };

  return (
    <div style={{
      padding: 'clamp(6px, 1.5vw, 10px)',
      borderRadius: '8px',
      background: 'var(--bg-glass)',
      border: '1px solid var(--border)',
      marginBottom: 'clamp(4px, 1vw, 8px)',
      animation: 'fadeUp 0.3s ease',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
        <span style={{ fontSize: 'clamp(0.65rem, 1.5vw, 0.75rem)', color: 'var(--text-secondary)', lineHeight: 1.4, flex: 1, minWidth: 0 }}>
          <span style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: 'clamp(0.6rem, 1.2vw, 0.7rem)' }}>
            Q{turn.question_number}.{' '}
          </span>
          {turn.question_text?.slice(0, 55)}{turn.question_text?.length > 55 ? '...' : ''}
        </span>
        <span style={{
          fontSize: 'clamp(0.6rem, 1.2vw, 0.7rem)',
          fontFamily: 'var(--font-mono)',
          color: answerColors[turn.answer] || 'var(--text-dim)',
          fontWeight: 700,
          whiteSpace: 'nowrap',
          letterSpacing: '0.05em',
        }}>
          {turn.answer?.toUpperCase()}
        </span>
      </div>
    </div>
  );
}

export default function GameScreen({ gameData, onAnswer, loading, history }) {
  const [selected, setSelected]   = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleAnswer = async (value) => {
    if (submitting) return;
    setSelected(value);
    setSubmitting(true);
    await onAnswer(value);
    setSelected(null);
    setSubmitting(false);
  };

  const q   = gameData?.current_question;
  const num = gameData?.question_number ?? 1;

  return (
    <div style={{
      minHeight: '100vh',
      display: 'grid',
      gridTemplateColumns: 'clamp(100%, calc(100% - 320px), 1fr) clamp(0, 320px, 100%)',
      gridTemplateRows: 'auto 1fr',
      gap: '0',
      maxWidth: '1200px',
      margin: '0 auto',
      padding: 'clamp(16px, 4vw, 28px)',
      '@media (max-width: 768px)': {
        gridTemplateColumns: '1fr',
      }
    }}>

      {/* ── TOP BAR ──────────────────────────────────────────────────────── */}
      <div style={{
        gridColumn: '1 / -1',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 'clamp(16px, 4vw, 24px)',
        paddingBottom: 'clamp(12px, 3vw, 18px)',
        borderBottom: '1px solid var(--border)',
        flexWrap: 'wrap',
        gap: 'clamp(12px, 3vw, 16px)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'clamp(8px, 2vw, 12px)' }}>
          <span style={{ fontSize: 'clamp(1.2rem, 5vw, 1.8rem)' }}>🏏</span>
          <span style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(1rem, 3vw, 1.4rem)', letterSpacing: '0.1em', color: 'var(--text-primary)' }}>
            IPL AKINATOR
          </span>
        </div>
        <div className="badge badge-gold">
          {gameData?.questions_asked ?? 0} / 8 Questions
        </div>
      </div>

      {/* ── MAIN GAME AREA ────────────────────────────────────────────────── */}
      <div style={{ paddingRight: 'clamp(12px, 3vw, 20px)', display: 'flex', flexDirection: 'column', gap: 'clamp(12px, 3vw, 18px)' }}>

        {/* Progress */}
        <ProgressBar current={num} max={8} />

        {/* Question card */}
        <div
          key={q?.id}   // Key change triggers re-animation on each new question
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-gold)',
            borderRadius: 'var(--radius-lg)',
            padding: 'clamp(20px, 5vw, 36px)',
            animation: 'fadeUp 0.4s ease',
          }}
        >
          <div className="badge badge-gold" style={{ marginBottom: 'clamp(12px, 3vw, 18px)' }}>
            {q?.category?.toUpperCase() ?? 'QUESTION'}
          </div>

          <h2 style={{
            fontFamily: 'var(--font-display)',
            fontSize: 'clamp(1.3rem, 4vw, 2.4rem)',
            color: 'var(--text-primary)',
            lineHeight: 1.2,
            letterSpacing: '0.03em',
            marginBottom: 'clamp(8px, 2vw, 12px)',
          }}>
            {loading ? 'AI is thinking...' : (q?.text ?? 'Loading...')}
          </h2>

          {loading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '8px' }}>
              <div style={{
                width: '12px', height: '12px', borderRadius: '50%',
                border: '2px solid var(--gold)',
                borderTopColor: 'transparent',
                animation: 'spin 0.8s linear infinite',
              }} />
              <span style={{ fontSize: 'clamp(0.7rem, 1.5vw, 0.85rem)', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                Processing answer...
              </span>
            </div>
          )}
        </div>

        {/* Answer buttons */}
        <div style={{ display: 'flex', gap: 'clamp(8px, 2vw, 12px)', flexWrap: 'wrap' }}>
          {ANSWERS.map(ans => (
            <AnswerButton
              key={ans.value}
              answer={ans}
              selected={selected}
              onClick={handleAnswer}
              disabled={loading || submitting}
            />
          ))}
        </div>

        {/* History — recent Q&A (Mobile: visible, Desktop: in sidebar) */}
        {history.length > 0 && (
          <div style={{ marginTop: 'clamp(12px, 3vw, 16px)', display: 'block' }}>
            <p style={{ fontSize: 'clamp(0.65rem, 1.5vw, 0.75rem)', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 'clamp(8px, 2vw, 12px)' }}>
              Question History
            </p>
            <div style={{ maxHeight: 'clamp(150px, 30vh, 300px)', overflowY: 'auto' }}>
              {[...history].reverse().map((turn, i) => (
                <HistoryItem key={i} turn={turn} />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── AI PANEL (Hidden on mobile) ──────────────────────────────────────── */}
      <div style={{ display: 'contents' }}>
        <AIPanel
          candidates={gameData?.top_candidates ?? []}
          entropy={gameData?.entropy}
          activeCount={gameData?.active_count}
          questionCount={gameData?.questions_asked ?? 0}
        />
      </div>
    </div>
  );
}