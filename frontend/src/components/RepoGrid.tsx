import { useMemo, useState } from 'react';
import type { Repository } from '../types';
import { RepoCard } from './RepoCard';
import { SearchIcon } from './Icons';

type SortKey = 'default' | 'stars' | 'forks' | 'updated';

export function RepoGrid({ repos }: { repos: Repository[] }) {
  const [query, setQuery] = useState('');
  const [lang, setLang] = useState('all');
  const [sort, setSort] = useState<SortKey>('default');

  const languages = useMemo(
    () => Array.from(new Set(repos.map((r) => r.language).filter((l): l is string => Boolean(l)))).sort(),
    [repos],
  );

  // UI-only filtering/sorting of the server-provided list.
  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = repos.filter((r) => {
      if (lang !== 'all' && r.language !== lang) return false;
      if (!q) return true;
      return (
        r.name.toLowerCase().includes(q) ||
        (r.description ?? '').toLowerCase().includes(q) ||
        r.topics.some((t) => t.toLowerCase().includes(q))
      );
    });
    if (sort === 'stars') return [...list].sort((a, b) => b.stars - a.stars);
    if (sort === 'forks') return [...list].sort((a, b) => b.forks - a.forks);
    if (sort === 'updated') return [...list].sort((a, b) => (b.updated_at ?? '').localeCompare(a.updated_at ?? ''));
    return list;
  }, [repos, query, lang, sort]);

  return (
    <section className="card" aria-labelledby="repos-title">
      <div className="card-head repo-toolbar-head">
        <h2 id="repos-title">
          Repositories <span className="count">{repos.length}</span>
        </h2>
        <div className="repo-toolbar">
          <div className="search-field">
            <SearchIcon className="search-icon" />
            <label htmlFor="repo-search" className="sr-only">
              Search repositories
            </label>
            <input
              id="repo-search"
              type="search"
              placeholder="Find a repository…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <label className="sr-only" htmlFor="repo-lang">
            Filter by language
          </label>
          <select id="repo-lang" value={lang} onChange={(e) => setLang(e.target.value)}>
            <option value="all">All languages</option>
            {languages.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
          <label className="sr-only" htmlFor="repo-sort">
            Sort repositories
          </label>
          <select id="repo-sort" value={sort} onChange={(e) => setSort(e.target.value as SortKey)}>
            <option value="default">Sort: Recommended</option>
            <option value="stars">Sort: Stars</option>
            <option value="forks">Sort: Forks</option>
            <option value="updated">Sort: Recently updated</option>
          </select>
        </div>
      </div>
      {repos.length === 0 ? (
        <div className="empty">This user has no public repositories yet.</div>
      ) : visible.length === 0 ? (
        <div className="empty">No repositories match your filters.</div>
      ) : (
        <div className="repo-grid">
          {visible.map((r) => (
            <RepoCard key={r.id} repo={r} />
          ))}
        </div>
      )}
    </section>
  );
}
