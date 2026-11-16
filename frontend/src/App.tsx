import { useCallback, useEffect, useState } from 'react';
import { api } from './api/client';
import { usePortfolio } from './hooks/usePortfolio';
import { useInsights } from './hooks/useInsights';
import type { MatchResult, Theme } from './types';
import { TopBar } from './components/TopBar';
import { ProfileHeader } from './components/ProfileHeader';
import { LanguagePieChart } from './components/LanguagePieChart';
import { ContributionHeatmap } from './components/ContributionHeatmap';
import { JobMatchPanel } from './components/JobMatchPanel';
import { RepoGrid } from './components/RepoGrid';
import { DashboardSkeleton, ErrorCard } from './components/States';
import { GitHubIcon } from './components/Icons';
import { InsightsPanel } from './components/InsightsPanel';
import { ReadinessPanel } from './components/ReadinessPanel';
import { SharePanel } from './components/SharePanel';
import { CompareView } from './components/CompareView';

const FALLBACK_USERNAME = 'octocat';

type View = 'overview' | 'compare';

function readQuery() {
  const q = new URLSearchParams(window.location.search);
  const user = q.get('user')?.trim().replace(/^@/, '') || null;
  const raw = q.get('compare');
  const parts = raw ? raw.split(',').map((p) => p.trim()).filter(Boolean) : [];
  const compare: [string, string] | null = parts.length === 2 ? [parts[0], parts[1]] : null;
  const view: View = raw !== null || q.get('view') === 'compare' ? 'compare' : 'overview';
  return { user, compare, view };
}

const initialQuery = readQuery();

function writeQuery(user: string | null, view: View, compare: [string, string] | null) {
  const q = new URLSearchParams();
  if (user) q.set('user', user);
  if (view === 'compare') {
    if (compare) q.set('compare', compare.join(','));
    else q.set('view', 'compare');
  }
  const search = q.toString();
  const next = `${window.location.pathname}${search ? `?${search}` : ''}${window.location.hash}`;
  if (next !== `${window.location.pathname}${window.location.search}${window.location.hash}`) {
    window.history.replaceState(null, '', next);
  }
}

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute('data-theme', theme);
}

export default function App() {
  const [username, setUsername] = useState<string | null>(initialQuery.user);
  const [view, setView] = useState<View>(initialQuery.view);
  const [comparePair, setComparePair] = useState<[string, string] | null>(initialQuery.compare);
  const [theme, setTheme] = useState<Theme>('dark');
  const [jobDescription, setJobDescription] = useState('');
  const [match, setMatch] = useState<MatchResult | null>(null);
  const { data, loading, refreshing, error, status, reload } = usePortfolio(username);
  const loadedLogin = data?.profile.login ?? null;
  const insights = useInsights(loadedLogin);

  useEffect(() => {
    let cancelled = false;
    api
      .getSettings()
      .then((s) => {
        if (cancelled) return;
        setTheme(s.theme === 'light' ? 'light' : 'dark');
        setJobDescription(s.last_job_description ?? '');
        // URL ?user= takes precedence over the saved default.
        setUsername((u) => u ?? (s.default_username?.trim() || FALLBACK_USERNAME));
      })
      .catch(() => {
        if (!cancelled) setUsername((u) => u ?? FALLBACK_USERNAME);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => applyTheme(theme), [theme]);

  useEffect(() => writeQuery(username, view, comparePair), [username, view, comparePair]);

  // Persist the successfully loaded username as the default.
  useEffect(() => {
    if (loadedLogin) api.updateSettings({ default_username: loadedLogin }).catch(() => undefined);
  }, [loadedLogin]);

  const handleLoad = useCallback(
    (next: string) => {
      if (username && next.toLowerCase() === username.toLowerCase()) {
        void reload(false);
        void insights.reload(false);
      } else {
        setMatch(null);
        setUsername(next);
      }
    },
    [username, reload, insights.reload],
  );

  const toggleTheme = () => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    api.updateSettings({ theme: next }).catch(() => undefined);
  };

  return (
    <div className="app">
      <TopBar
        username={username ?? ''}
        theme={theme}
        refreshing={refreshing}
        canRefresh={Boolean(data)}
        onLoad={(u) => {
          handleLoad(u);
          setView('overview');
        }}
        onRefresh={() => {
          void reload(true);
          void insights.reload(true);
        }}
        onToggleTheme={toggleTheme}
      />

      <nav className="view-tabs" aria-label="Views">
        <div className="container view-tabs-inner" role="tablist">
          {(['overview', 'compare'] as const).map((v) => (
            <button
              key={v}
              type="button"
              role="tab"
              aria-selected={view === v}
              className={`view-tab ${view === v ? 'active' : ''}`}
              onClick={() => setView(v)}
            >
              {v === 'overview' ? 'Overview' : 'Compare'}
            </button>
          ))}
        </div>
      </nav>

      <main className="container main">
        {view === 'compare' && (
          <CompareView
            defaultA={loadedLogin ?? username ?? ''}
            initial={comparePair}
            onCompared={(a, b) => setComparePair([a, b])}
          />
        )}
        {view === 'overview' && error && !data && <ErrorCard message={error} status={status} onRetry={() => void reload(false)} />}
        {view === 'overview' && error && data && (
          <div className="alert alert-error" role="alert">
            Refresh failed: {error}
          </div>
        )}
        {view === 'overview' && (loading || !username) && !data && !error && <DashboardSkeleton />}

        {view === 'overview' && data && (
          <div className={`dashboard ${loading ? 'is-loading' : ''}`}>
            <ProfileHeader profile={data.profile} stats={data.stats} cache={data.cache} match={match} />

            <div className="row row-charts">
              <LanguagePieChart languages={data.stats.top_languages} />
              <ContributionHeatmap contributions={data.contributions} />
            </div>

            <InsightsPanel
              activity={insights.data?.activity ?? null}
              loading={insights.loading}
              error={insights.error}
            />

            <div className="row row-2col">
              <ReadinessPanel
                readiness={insights.data?.readiness ?? null}
                loading={insights.loading}
                error={insights.error}
              />
              <SharePanel username={data.profile.login} />
            </div>

            <JobMatchPanel
              username={data.profile.login}
              jobDescription={jobDescription}
              onJobDescriptionChange={setJobDescription}
              result={match}
              onResult={setMatch}
            />

            <RepoGrid repos={data.repositories} />
          </div>
        )}
      </main>

      <footer className="footer">
        <div className="container footer-inner">
          <span>
            <strong>DevFolio</strong> · GitHub Developer Portfolio
          </span>
          <span className="muted">
            <GitHubIcon /> Data from the public GitHub API
          </span>
        </div>
      </footer>
    </div>
  );
}
