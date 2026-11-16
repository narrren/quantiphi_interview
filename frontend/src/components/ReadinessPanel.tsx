import type { Readiness } from '../types';
import { AlertIcon, CheckIcon, CloseIcon } from './Icons';

interface Props {
  readiness: Readiness | null;
  loading: boolean;
  error: string | null;
}

const R = 52;
const C = 2 * Math.PI * R;

function Gauge({ score, grade }: { score: number; grade: string }) {
  const clamped = Math.max(0, Math.min(100, score));
  return (
    <div className={`gauge grade-${grade.toLowerCase()}`}>
      <svg viewBox="0 0 128 128" width="128" height="128" role="img" aria-label={`Readiness score ${score} of 100, ${grade}`}>
        <circle cx="64" cy="64" r={R} className="gauge-track" />
        <circle
          cx="64"
          cy="64"
          r={R}
          className="gauge-value"
          strokeDasharray={`${(clamped / 100) * C} ${C}`}
          transform="rotate(-90 64 64)"
        />
      </svg>
      <div className="gauge-center">
        <span className="gauge-score">{score}</span>
        <span className="gauge-grade">{grade}</span>
      </div>
    </div>
  );
}

export function ReadinessPanel({ readiness, loading, error }: Props) {
  return (
    <section className="card" aria-labelledby="readiness-title" aria-busy={loading}>
      <div className="card-head">
        <h2 id="readiness-title">Portfolio Readiness</h2>
        {readiness && (
          <span className="muted small">
            {readiness.checks.filter((c) => c.passed).length}/{readiness.checks.length} checks passed
          </span>
        )}
      </div>

      {error && !readiness && (
        <div className="alert alert-error" role="alert">
          <AlertIcon /> Readiness unavailable: {error}
        </div>
      )}

      {loading && !readiness && (
        <div className="stack">
          <div className="skeleton" style={{ width: 128, height: 128, borderRadius: '50%' }} />
          <div className="skeleton skel-line" style={{ width: '80%' }} />
          <div className="skeleton skel-line" style={{ width: '65%' }} />
          <div className="skeleton skel-line" style={{ width: '72%' }} />
        </div>
      )}

      {readiness && (
        <div className="stack readiness">
          <div className="readiness-top">
            <Gauge score={readiness.score} grade={readiness.grade} />
            <ul className="checklist">
              {readiness.checks.map((c) => (
                <li key={c.id} className={c.passed ? 'check-ok' : 'check-fail'}>
                  <span className="check-icon" aria-label={c.passed ? 'Passed' : 'Failed'}>
                    {c.passed ? <CheckIcon size={12} /> : <CloseIcon size={12} />}
                  </span>
                  <div className="min0">
                    <strong>{c.label}</strong>
                    {c.detail && <p className="muted small">{c.detail}</p>}
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {readiness.recommendations.length > 0 && (
            <div>
              <h3 className="sub-title">How to improve</h3>
              <ul className="reco-list">
                {readiness.recommendations.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </div>
          )}

          {readiness.repositories.length > 0 && (
            <div>
              <h3 className="sub-title">Repository health</h3>
              <ul className="health-list">
                {readiness.repositories.map((r) => (
                  <li key={r.name} className="health-item">
                    <div className="health-head">
                      <span className="health-name" title={r.name}>
                        {r.name}
                      </span>
                      <span className="health-score">{r.score}</span>
                    </div>
                    <div className="score-bar" aria-hidden>
                      <span style={{ width: `${Math.max(0, Math.min(100, r.score))}%` }} />
                    </div>
                    {r.issues.length > 0 && (
                      <ul className="chips chips-sm">
                        {r.issues.map((i) => (
                          <li key={i} className="chip chip-missing">
                            {i}
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
