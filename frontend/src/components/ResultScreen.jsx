// src/components/ResultScreen.jsx — Final win/loss summary
export default function ResultScreen({ result, onPlayAgain }) {
  const correct = result?.correct;

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
      <div style={{
        maxWidth: '560px',
        width: '100%',
        textAlign: 'center',
      }}>
        {/* Outcome emoji */}
        <div style={{ fontSize: 'clamp(60px, 12vw, 90px)', marginBottom: 'clamp(12px, 3vw, 24px)', lineHeight: 1 }}>
          {correct ? '🎉' : '😅'}
        </div>

        {/* Outcome title */}
        <h1 style={{
          fontFamily: 'var(--font-display)',
          fontSize: 'clamp(2rem, 6vw, 4.5rem)',
          color: correct ? 'var(--green-accent)' : 'var(--gold)',
          letterSpacing: '0.06em',
          marginBottom: 'clamp(8px, 2vw, 16px)',
        }}>
          {correct ? 'GOT IT!' : 'CLOSE ONE!'}
        </h1>

        <p style={{
          color: 'var(--text-secondary)',
          marginBottom: 'clamp(20px, 5vw, 32px)',
          fontSize: 'clamp(0.85rem, 2vw, 1rem)',
          lineHeight: 1.6,
        }}>
          {result?.message}
        </p>

        {/* Stats card */}
        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          padding: 'clamp(16px, 4vw, 28px)',
          marginBottom: 'clamp(16px, 4vw, 28px)',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 'clamp(12px, 2vw, 18px)',
          textAlign: 'center',
        }}>
          {[
            { label: 'Questions Asked', value: result?.questions_asked, color: 'var(--blue-accent)' },
            { label: 'Correct', value: correct ? 'YES ✅' : 'NO ❌', color: correct ? 'var(--green-accent)' : 'var(--red-accent)' },
            { label: 'Guessed', value: result?.guessed, color: 'var(--gold)' },
            { label: 'Actual Player', value: result?.correct_player || result?.guessed, color: 'var(--text-primary)' },
          ].map(stat => (
            <div key={stat.label} style={{ padding: 'clamp(10px, 2vw, 14px)', background: 'var(--bg-glass)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: 'clamp(0.6rem, 1.2vw, 0.75rem)', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 'clamp(4px, 1vw, 8px)' }}>
                {stat.label}
              </div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(1rem, 2vw, 1.3rem)', color: stat.color, letterSpacing: '0.04em' }}>
                {stat.value}
              </div>
            </div>
          ))}
        </div>

        {/* Learning note */}
        {!correct && (
          <div style={{
            background: 'rgba(245,166,35,0.08)',
            border: '1px solid var(--border-gold)',
            borderRadius: 'var(--radius)',
            padding: 'clamp(12px, 3vw, 18px)',
            marginBottom: 'clamp(16px, 4vw, 28px)',
          }}>
            <p style={{ fontSize: 'clamp(0.75rem, 1.5vw, 0.9rem)', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              🧠 <strong style={{ color: 'var(--gold)' }}>Learning system activated</strong> — The AI has recorded this session
              and will improve its reasoning for <strong>{result?.correct_player}</strong> in future games.
            </p>
          </div>
        )}

        {/* Play again */}
        <button
          onClick={onPlayAgain}
          style={{
            padding: 'clamp(12px, 3vw, 18px) clamp(32px, 8vw, 56px)',
            fontSize: 'clamp(0.9rem, 2vw, 1.1rem)',
            fontFamily: 'var(--font-display)',
            letterSpacing: '0.15em',
            background: 'linear-gradient(135deg, var(--gold), var(--gold-light))',
            color: '#000',
            borderRadius: '100px',
            boxShadow: '0 0 30px rgba(245,166,35,0.3)',
            border: 'none',
            cursor: 'pointer',
            transition: 'all 0.3s ease',
          }}
        >
          🔄 PLAY AGAIN
        </button>
      </div>
    </div>
  );
}