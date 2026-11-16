import { useState } from 'react';
import type { LanguageStat } from '../types';

interface Props {
  languages: LanguageStat[];
}

const SIZE = 180;
const STROKE = 26;
const R = (SIZE - STROKE) / 2;
const C = 2 * Math.PI * R;
const GAP = 2;

export function LanguagePieChart({ languages }: Props) {
  const [active, setActive] = useState<string | null>(null);
  const activeLang = languages.find((l) => l.name === active) ?? null;
  const top = languages[0];

  let offset = 0;
  const segments = languages.map((lang) => {
    const len = (lang.percentage / 100) * C;
    const seg = { lang, len, offset };
    offset += len;
    return seg;
  });

  return (
    <section className="card" aria-labelledby="lang-title">
      <div className="card-head">
        <h2 id="lang-title">Top Languages</h2>
        <span className="muted small">by repository</span>
      </div>
      {languages.length === 0 ? (
        <div className="empty">No language data — this user has no original public repositories.</div>
      ) : (
        <div className="donut-wrap">
          <svg
            className="donut"
            viewBox={`0 0 ${SIZE} ${SIZE}`}
            role="img"
            aria-label={`Language breakdown: ${languages.map((l) => `${l.name} ${l.percentage}%`).join(', ')}`}
          >
            <circle cx={SIZE / 2} cy={SIZE / 2} r={R} fill="none" stroke="var(--track)" strokeWidth={STROKE} />
            <g transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}>
              {segments.map(({ lang, len, offset: off }) => {
                const visible = languages.length > 1 ? Math.max(len - GAP, 0.5) : len;
                return (
                  <circle
                    key={lang.name}
                    cx={SIZE / 2}
                    cy={SIZE / 2}
                    r={R}
                    fill="none"
                    stroke={lang.color}
                    strokeWidth={active === lang.name ? STROKE + 6 : STROKE}
                    strokeDasharray={`${visible} ${C - visible}`}
                    strokeDashoffset={-off}
                    opacity={active && active !== lang.name ? 0.35 : 1}
                    className="donut-seg"
                    onMouseEnter={() => setActive(lang.name)}
                    onMouseLeave={() => setActive(null)}
                  >
                    <title>{`${lang.name}: ${lang.percentage}% (${lang.count} repos)`}</title>
                  </circle>
                );
              })}
            </g>
            <text x="50%" y="47%" textAnchor="middle" className="donut-value">
              {(activeLang ?? top).percentage}%
            </text>
            <text x="50%" y="60%" textAnchor="middle" className="donut-caption">
              {(activeLang ?? top).name}
            </text>
          </svg>
          <ul className="legend">
            {languages.map((lang) => (
              <li
                key={lang.name}
                className={active === lang.name ? 'active' : undefined}
                onMouseEnter={() => setActive(lang.name)}
                onMouseLeave={() => setActive(null)}
              >
                <span className="dot" style={{ background: lang.color }} />
                <span className="legend-name">{lang.name}</span>
                <span className="legend-count muted">{lang.count}</span>
                <span className="legend-pct">{lang.percentage.toFixed(1)}%</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
