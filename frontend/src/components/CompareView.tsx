import { useEffect, useState, type FormEvent } from 'react';
import { api, ApiError, errorMessage } from '../api/client';
import type { CompareResult } from '../types';
import { formatNumber } from '../format';
import { AlertIcon, TrophyIcon } from './Icons';

interface Props {
  defaultA: string;
  initial: [string, string] | null;
  onCompared: (a: string, b: string) => void;
}

const clean = (v: string) => v.trim().replace(/^@/, '');

export function CompareView({ defaultA, initial, onCompared }: Props) {
  const [a, setA] = useState(initial?.[0] ?? defaultA);
  const [b, setB] = useState(initial?.[1] ?? '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<{ msg: string; status: number | null } | null>(null);
  const [result, setResult] = useState<CompareResult | null>(null);

  const run = async (x: string, y: string) => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.compareDevelopers(x, y);
      setResult(r);
      onCompared(x, y);
    } catch (err) {
      setResult(null);
      setError({ msg: errorMessage(err), status: err instanceof ApiError ? err.status : null });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initial && initial[0] && initial[1]) void run(initial[0], initial[1]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const x = clean(a);
    const y = clean(b);
    if (x && y) void run(x, y);
  };

  const devs = result?.developers ?? [];

  return (
    <div className="dashboard">
      <section className="card" aria-labelledby="compare-title">
        <div className="card-head">
          <h2 id="compare-title">Compare Developers</h2>
          <span className="muted small">Side-by-side GitHub metrics</span>
        </div>
        <form className="compare-form" onSubmit={submit}>
          <label className="sr-only" htmlFor="cmp-a">
            First username
          </label>
          <input id="cmp-a" type="text" value={a} onChange={(e) => setA(e.target.value)} placeholder="First username" maxLength={39} spellCheck={false} autoComplete="off" />
          <span className="compare-vs" aria-hidden>
            vs
          </span>
          <label className="sr-only" htmlFor="cmp-b">
            Second username
          </label>
          <input id="cmp-b" type="text" value={b} onChange={(e) => setB(e.target.value)} placeholder="Second username" maxLength={39} spellCheck={false} autoComplete="off" />
          <button type="submit" className="btn btn-primary" disabled={loading || !clean(a) || !clean(b)}>
            {loading ? <span className="spinner" aria-hidden /> : null}
            {loading ? 'Comparing…' : 'Compare'}
          </button>
        </form>
        {error && (
          <div className="alert alert-error compare-error" role="alert">
            <AlertIcon />
            <span>
              <strong>{error.status === 404 ? 'User not found' : error.status === 422 ? 'Invalid request' : 'Comparison failed'}:</strong>{' '}
              {error.msg}
            </span>
          </div>
        )}
      </section>

      {loading && !result && (
        <div className="card skeleton-card" aria-busy="true">
          <div className="skeleton skel-block" />
        </div>
      )}

      {result && devs.length === 2 && (
        <section className={`card ${loading ? 'is-loading' : ''}`} aria-label="Comparison result">
          <p className="compare-summary">{result.summary}</p>
          <div className="compare-table-wrap">
            <table className="compare-table">
              <thead>
                <tr>
                  <th scope="col" className="metric-col">
                    <span className="sr-only">Metric</span>
                  </th>
                  {devs.map((d) => (
                    <th key={d.login} scope="col">
                      <div className="compare-dev">
                        {d.avatar_url ? (
                          <img className="compare-avatar" src={d.avatar_url} alt="" width={56} height={56} />
                        ) : (
                          <span className="compare-avatar avatar-fallback">{d.login[0]?.toUpperCase()}</span>
                        )}
                        <strong className="compare-name">{d.name || d.login}</strong>
                        <a href={d.html_url} target="_blank" rel="noreferrer" className="muted small">
                          @{d.login}
                        </a>
                        <span className="badge">{d.top_language ?? 'No top language'}</span>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.metrics.map((m) => (
                  <tr key={m.key}>
                    <th scope="row" className="metric-col">
                      {m.label}
                    </th>
                    {devs.map((d, i) => {
                      const lead = m.leader !== null && m.leader.toLowerCase() === d.login.toLowerCase();
                      return (
                        <td key={d.login} className={lead ? 'is-leader' : ''}>
                          <span className="compare-value">{formatNumber(m.values[i] ?? 0)}</span>
                          {lead && (
                            <span className="leader-badge">
                              <TrophyIcon size={12} /> Leader
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="compare-shared">
            <h3 className="sub-title">Shared languages</h3>
            {result.shared_languages.length ? (
              <ul className="chips">
                {result.shared_languages.map((l) => (
                  <li key={l} className="chip chip-ok">
                    {l}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted small">No languages in common.</p>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
