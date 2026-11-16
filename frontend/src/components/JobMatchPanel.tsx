import { useState, type FormEvent } from 'react';
import { api, errorMessage } from '../api/client';
import type { MatchResult } from '../types';
import { formatNumber } from '../format';
import { AlertIcon, CheckIcon, CloseIcon } from './Icons';

interface Props {
  username: string;
  jobDescription: string;
  onJobDescriptionChange: (jd: string) => void;
  result: MatchResult | null;
  onResult: (r: MatchResult | null, forUser?: string) => void;
}

const MAX_CHARS = 20000;

export function JobMatchPanel({ username, jobDescription, onJobDescriptionChange, result, onResult }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      // Tag the result with the user it was computed for, so a late reply can't land on another profile.
      onResult(await api.match(username, jobDescription), username);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card" aria-labelledby="match-title">
      <div className="card-head">
        <h2 id="match-title">Tech Stack Compatibility</h2>
        <span className="muted small">The Vibe Check</span>
      </div>
      <form onSubmit={submit} className="stack">
        <label htmlFor="jd-input" className="field-label">
          Paste a job description
        </label>
        <textarea
          id="jd-input"
          rows={6}
          value={jobDescription}
          onChange={(e) => onJobDescriptionChange(e.target.value)}
          placeholder="e.g. We're hiring a backend engineer experienced with Python, FastAPI, PostgreSQL, Docker and React…"
          aria-describedby="jd-count"
        />
        <div className="form-row">
          <span id="jd-count" className={`muted small ${jobDescription.length > MAX_CHARS ? 'text-danger' : ''}`}>
            {formatNumber(jobDescription.length)} / {formatNumber(MAX_CHARS)} characters
          </span>
          <div className="form-actions">
            {result && (
              <button type="button" className="btn btn-ghost" onClick={() => onResult(null)}>
                Clear result
              </button>
            )}
            <button type="submit" className="btn btn-primary" disabled={loading || !jobDescription.trim() || jobDescription.length > MAX_CHARS}>
              {loading ? <span className="spinner" aria-hidden /> : null}
              {loading ? 'Analyzing…' : 'Analyze'}
            </button>
          </div>
        </div>
      </form>

      {error && (
        <div className="alert alert-error" role="alert">
          <AlertIcon /> {error}
        </div>
      )}

      {result && (
        <div className="match-result" aria-live="polite">
          <div className={`match-inline grade-${result.grade.toLowerCase()}`}>
            <span className="match-inline-pct">{result.match_percentage}%</span>
            <div>
              <strong>{result.grade}</strong>
              <p className="muted small">{result.summary}</p>
            </div>
          </div>

          {result.matched.length > 0 && (
            <div>
              <h3 className="sub-title">Matched ({result.matched.length})</h3>
              <ul className="chips">
                {result.matched.map((m) => {
                  const tip = m.evidence.length ? `Found in: ${m.evidence.join(', ')}` : 'Found in profile';
                  return (
                    <li key={m.keyword} className="chip chip-ok" data-tip={tip} title={tip} tabIndex={0}>
                      <CheckIcon size={12} /> {m.keyword}
                      <span className="chip-cat">{m.category}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {result.missing.length > 0 && (
            <div>
              <h3 className="sub-title">Missing ({result.missing.length})</h3>
              <ul className="chips">
                {result.missing.map((m) => (
                  <li key={m.keyword} className="chip chip-missing" title={`${m.category} not found in repositories`}>
                    <CloseIcon size={12} /> {m.keyword}
                    <span className="chip-cat">{m.category}</span>
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
