import { useCallback, useEffect, useState } from 'react';
import { api } from './api/client';
import { usePortfolio } from './hooks/usePortfolio';
import type { MatchResult, Theme } from './types';
import { TopBar } from './components/TopBar';
import { ProfileHeader } from './components/ProfileHeader';
import { LanguagePieChart } from './components/LanguagePieChart';
import { ContributionHeatmap } from './components/ContributionHeatmap';
import { JobMatchPanel } from './components/JobMatchPanel';
import { RepoGrid } from './components/RepoGrid';
import { DashboardSkeleton, ErrorCard } from './components/States';
import { GitHubIcon } from './components/Icons';

const FALLBACK_USERNAME = 'octocat';

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute('data-theme', theme);
}

export default function App() {
  const [username, setUsername] = useState<string | null>(null);
  const [theme, setTheme] = useState<Theme>('dark');
  const [jobDescription, setJobDescription] = useState('');
  const [match, setMatch] = useState<MatchResult | null>(null);
  const { data, loading, refreshing, error, status, reload } = usePortfolio(username);

  useEffect(() => {
    let cancelled = false;
    api
      .getSettings()
      .then((s) => {
        if (cancelled) return;
        setTheme(s.theme === 'light' ? 'light' : 'dark');
        setJobDescription(s.last_job_description ?? '');
        setUsername(s.default_username?.trim() || FALLBACK_USERNAME);
      })
      .catch(() => {
        if (!cancelled) setUsername(FALLBACK_USERNAME);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => applyTheme(theme), [theme]);

  // Persist the successfully loaded username as the default.
  const loadedLogin = data?.profile.login ?? null;
  useEffect(() => {
    if (loadedLogin) api.updateSettings({ default_username: loadedLogin }).catch(() => undefined);
  }, [loadedLogin]);

  const handleLoad = useCallback(
    (next: string) => {
      if (username && next.toLowerCase() === username.toLowerCase()) {
        void reload(false);
      } else {
        setMatch(null);
        setUsername(next);
      }
    },
    [username, reload],
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
        onLoad={handleLoad}
        onRefresh={() => void reload(true)}
        onToggleTheme={toggleTheme}
      />

      <main className="container main">
        {error && !data && <ErrorCard message={error} status={status} onRetry={() => void reload(false)} />}
        {error && data && (
          <div className="alert alert-error" role="alert">
            Refresh failed: {error}
          </div>
        )}
        {(loading || !username) && !data && !error && <DashboardSkeleton />}

        {data && (
          <div className={`dashboard ${loading ? 'is-loading' : ''}`}>
            <ProfileHeader profile={data.profile} stats={data.stats} cache={data.cache} match={match} />

            <div className="row row-charts">
              <LanguagePieChart languages={data.stats.top_languages} />
              <ContributionHeatmap contributions={data.contributions} />
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
