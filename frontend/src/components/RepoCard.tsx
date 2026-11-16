import type { Repository } from '../types';
import { formatNumber, relativeTime } from '../format';
import { ForkIcon, LinkIcon, RepoIcon, StarIcon } from './Icons';

export function RepoCard({ repo }: { repo: Repository }) {
  const topics = repo.topics.slice(0, 4);
  return (
    <article className="repo-card">
      <div className="repo-head">
        <RepoIcon className="muted" />
        <a className="repo-name" href={repo.html_url} target="_blank" rel="noreferrer" title={repo.full_name}>
          {repo.name}
        </a>
        {repo.is_fork && <span className="badge">Fork</span>}
        {repo.archived && <span className="pill pill-warn pill-sm">Archived</span>}
        {repo.homepage && (
          <a
            className="repo-homepage"
            href={repo.homepage}
            target="_blank"
            rel="noreferrer"
            aria-label={`${repo.name} homepage`}
            title={repo.homepage}
          >
            <LinkIcon />
          </a>
        )}
      </div>
      <p className={repo.description ? 'repo-desc' : 'repo-desc muted italic'}>
        {repo.description || 'No description provided'}
      </p>
      {topics.length > 0 && (
        <ul className="topics" aria-label="Topics">
          {topics.map((t) => (
            <li key={t} className="topic">
              {t}
            </li>
          ))}
          {repo.topics.length > 4 && <li className="topic topic-more">+{repo.topics.length - 4}</li>}
        </ul>
      )}
      <div className="repo-meta">
        {repo.language && (
          <span className="repo-lang">
            <span className="dot" style={{ background: repo.language_color ?? 'var(--muted)' }} />
            {repo.language}
          </span>
        )}
        <span title={`${formatNumber(repo.stars)} stars`}>
          <StarIcon /> {formatNumber(repo.stars)}
        </span>
        <span title={`${formatNumber(repo.forks)} forks`}>
          <ForkIcon /> {formatNumber(repo.forks)}
        </span>
        {repo.license && (
          <span className="license-chip" title={`License: ${repo.license}`}>
            {repo.license}
          </span>
        )}
        {repo.updated_at && <span className="repo-updated">Updated {relativeTime(repo.updated_at)}</span>}
      </div>
    </article>
  );
}
