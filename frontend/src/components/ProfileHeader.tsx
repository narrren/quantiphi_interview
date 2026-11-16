import type { CacheInfo, MatchResult, Profile, Stats } from '../types';
import { formatCompact, formatNumber, formatTime, normalizeUrl } from '../format';
import { useState, type ReactNode } from 'react';
import { ForkIcon, LinkIcon, LocationIcon, OrgIcon, PeopleIcon, PersonIcon, RepoIcon, StarIcon } from './Icons';

interface Props {
  profile: Profile;
  stats: Stats;
  cache: CacheInfo;
  match: MatchResult | null;
}

function CachePill({ cache }: { cache: CacheInfo }) {
  if (cache.stale) {
    return (
      <span className="pill pill-warn" title={`Fetched ${formatTime(cache.fetched_at)} — GitHub unavailable`}>
        <span className="pill-dot" /> Stale cache
      </span>
    );
  }
  if (cache.cached) {
    return (
      <span className="pill pill-info" title={`Served from cache (TTL ${cache.ttl_seconds}s)`}>
        <span className="pill-dot" /> Cached · {formatTime(cache.fetched_at)}
      </span>
    );
  }
  return (
    <span className="pill pill-ok" title="Fetched live from GitHub">
      <span className="pill-dot" /> Live
    </span>
  );
}

function StatTile({ icon, label, value }: { icon: ReactNode; label: string; value: number }) {
  return (
    <div className="stat-tile">
      <span className="stat-icon">{icon}</span>
      <span className="stat-value" title={formatNumber(value)}>
        {formatCompact(value)}
      </span>
      <span className="stat-label">{label}</span>
    </div>
  );
}

export function ProfileHeader({ profile, stats, cache, match }: Props) {
  // Track which avatar URL failed so a new profile retries its own image.
  const [failedAvatar, setFailedAvatar] = useState<string | null>(null);
  const showAvatar = Boolean(profile.avatar_url) && failedAvatar !== profile.avatar_url;

  return (
    <section className="card profile" aria-labelledby="profile-name">
      {match && (
        <div className={`match-banner grade-${match.grade.toLowerCase()}`} role="status">
          <div className="match-score">
            <span className="match-pct">{match.match_percentage}%</span>
            <span className="match-label">Match</span>
          </div>
          <div className="match-text">
            <strong>{match.grade} fit</strong>
            <span>{match.summary}</span>
          </div>
        </div>
      )}

      <div className="profile-main">
        {showAvatar && profile.avatar_url ? (
          <img
            className="avatar"
            src={profile.avatar_url}
            alt={`${profile.login} avatar`}
            width={96}
            height={96}
            onError={() => setFailedAvatar(profile.avatar_url)}
          />
        ) : (
          <div className="avatar avatar-fallback" aria-hidden>
            {profile.login.slice(0, 1).toUpperCase()}
          </div>
        )}
        <div className="profile-info">
          <div className="profile-title-row">
            <div>
              <h1 id="profile-name" className="profile-name">
                {profile.name || profile.login}
              </h1>
              <a className="profile-login" href={profile.html_url} target="_blank" rel="noreferrer">
                @{profile.login}
              </a>
            </div>
            <CachePill cache={cache} />
          </div>
          {profile.bio && <p className="profile-bio">{profile.bio}</p>}
          <ul className="profile-meta">
            {profile.company && (
              <li>
                <OrgIcon /> {profile.company}
              </li>
            )}
            {profile.location && (
              <li>
                <LocationIcon /> {profile.location}
              </li>
            )}
            {profile.blog && (
              <li>
                <LinkIcon />
                <a href={normalizeUrl(profile.blog)} target="_blank" rel="noreferrer">
                  {profile.blog.replace(/^https?:\/\//, '').replace(/\/$/, '')}
                </a>
              </li>
            )}
          </ul>
        </div>
      </div>

      <div className="stat-grid">
        <StatTile icon={<PeopleIcon />} label="Followers" value={profile.followers} />
        <StatTile icon={<PersonIcon />} label="Following" value={profile.following} />
        <StatTile icon={<StarIcon />} label="Total Stars" value={stats.total_stars} />
        <StatTile icon={<RepoIcon />} label="Public Repos" value={profile.public_repos} />
        <StatTile icon={<ForkIcon />} label="Total Forks" value={stats.total_forks} />
      </div>
    </section>
  );
}
