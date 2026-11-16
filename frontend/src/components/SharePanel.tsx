import { useEffect, useRef, useState } from 'react';
import { badgeUrl } from '../api/client';
import type { BadgeMetric } from '../types';
import { CheckIcon, LinkIcon } from './Icons';

const BADGES: { metric: BadgeMetric; label: string }[] = [
  { metric: 'stars', label: 'GitHub stars' },
  { metric: 'followers', label: 'Followers' },
  { metric: 'contributions', label: 'Contributions' },
  { metric: 'streak', label: 'Streak' },
  { metric: 'top_language', label: 'Top language' },
];

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    let ok = false;
    try {
      ok = document.execCommand('copy');
    } catch {
      ok = false;
    }
    document.body.removeChild(ta);
    return ok;
  }
}

export function SharePanel({ username }: { username: string }) {
  const [copied, setCopied] = useState<string | null>(null);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const doCopy = async (key: string, text: string) => {
    const ok = await copyText(text);
    setCopied(ok ? key : 'error');
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setCopied(null), 1800);
  };

  const shareLink = () => {
    const url = new URL(window.location.href);
    url.search = '';
    url.searchParams.set('user', username);
    return url.toString();
  };

  return (
    <section className="card" aria-labelledby="share-title">
      <div className="card-head">
        <h2 id="share-title">Share &amp; Embed</h2>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => void doCopy('link', shareLink())}>
          {copied === 'link' ? <CheckIcon /> : <LinkIcon />}
          {copied === 'link' ? 'Copied!' : 'Copy share link'}
        </button>
      </div>
      <p className="muted small share-intro">Embed live badges in your README. Click to copy the Markdown snippet.</p>
      <ul className="badge-list">
        {BADGES.map((b) => {
          const md = `![${b.label}](${window.location.origin}${badgeUrl(username, b.metric)})`;
          const done = copied === b.metric;
          return (
            <li key={b.metric} className="badge-row">
              <img src={badgeUrl(username, b.metric)} alt={`${b.label} badge for ${username}`} height={20} loading="lazy" />
              <button
                type="button"
                className={`btn btn-ghost btn-sm ${done ? 'is-copied' : ''}`}
                onClick={() => void doCopy(b.metric, md)}
                title={md}
              >
                {done ? <CheckIcon /> : null}
                {done ? 'Copied!' : 'Copy Markdown'}
              </button>
            </li>
          );
        })}
      </ul>
      <div className="sr-only" aria-live="polite">
        {copied && copied !== 'error' ? 'Copied to clipboard' : ''}
      </div>
      {copied === 'error' && (
        <p className="text-danger small" role="alert">
          Could not access the clipboard.
        </p>
      )}
      {copied && copied !== 'error' && <div className="toast">Copied to clipboard</div>}
    </section>
  );
}
