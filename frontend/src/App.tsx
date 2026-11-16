import { useCallback, useEffect, useRef, useState } from 'react';
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
import { ChevronDownIcon, GitHubIcon } from './components/Icons';
import { InsightsPanel } from './components/InsightsPanel';
import { ReadinessPanel } from './components/ReadinessPanel';
import { SharePanel } from './components/SharePanel';
import { CompareView } from './components/CompareView';

const FALLBACK_USERNAME = 'octocat';

function readQuery() {
  const q = new URLSearchParams(window.location.search);
  const user = q.get('user')?.trim().replace(/^@/, '') || null;
  const raw = q.get('compare');
  const parts = raw ? raw.split(',').map((p) => p.trim()).filter(Boolean) : [];
  const compare: [string, string] | null = parts.length === 2 ? [parts[0], parts[1]] : null;
  // Deep links to an advanced feature open the advanced section directly.
  const advanced = raw !== null || q.get('advanced') === '1';
  return { user, compare, advanced };
}

const initialQuery = readQuery();

function writeQuery(user: string | null, advanced: boolean, compare: [string, string] | null) {
  const q = new URLSearchParams();
  if (user) q.set('user', user);
  if (advanced) {
    if (compare) q.set('compare', compare.join(','));
    else q.set('advanced', '1');
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
  const [showAdvanced, setShowAdvanced] = useState<boolean>(initialQuery.advanced);
  const advancedRef = useRef<HTMLElement>(null);
  const [comparePair, setComparePair] = useState<[string, string] | null>(initialQuery.compare);
  const [theme, setTheme] = useState<Theme>('dark');
  const [jobDescription, setJobDescription] = useState('');
  const [match, setMatch] = useState<MatchResult | null>(null);
  const { data, loading, refreshing, error, status, reload } = usePortfolio(username);
  const loadedLogin = data?.profile.login ?? null;
  // Advanced insights are fetched lazily, only once the advanced section is opened.
  const insights = useInsights(showAdvanced ? loadedLogin : null);

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

  useEffect(() => writeQuery(username, showAdvanced, comparePair), [username, showAdvanced, comparePair]);

  const toggleAdvanced = () => {
    const next = !showAdvanced;
    setShowAdvanced(next);
    if (next) {
      // Wait for the section to render, then scroll it into view.
      window.requestAnimationFrame(() =>
        advancedRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
      );
    }
  };

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
        onLoad={handleLoad}
        onRefresh={() => {
          void reload(true);
          if (showAdvanced) void insights.reload(true);
        }}
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
            {/* Core dashboard — the features defined in the problem statement. */}
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

            <div className="advanced-toggle-wrap">
              <button
                type="button"
                className={`advanced-toggle ${showAdvanced ? 'open' : 'closed'}`}
                aria-expanded={showAdvanced}
                aria-controls="advanced-features"
                onClick={toggleAdvanced}
              >
                {showAdvanced ? 'Hide advanced features' : 'Explore advanced features'}
                <span className="chevron">
                  <ChevronDownIcon />
                </span>
              </button>
              {!showAdvanced && (
                <span className="advanced-hint">
                  Developer Insights · Portfolio Readiness · Share &amp; Embed · Compare Developers
                </span>
              )}
            </div>

            {showAdvanced && (
              <section id="advanced-features" ref={advancedRef} className="advanced-section" aria-label="Advanced features">
                <div className="advanced-heading">Advanced features</div>

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

                <CompareView
                  defaultA={loadedLogin ?? username ?? ''}
                  initial={comparePair}
                  onCompared={(a, b) => setComparePair([a, b])}
                />
              </section>
            )}
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
