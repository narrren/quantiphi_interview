import { useEffect, useState, type FormEvent } from 'react';
import type { Theme } from '../types';
import { LogoIcon, MoonIcon, RefreshIcon, SearchIcon, SunIcon } from './Icons';

interface Props {
  username: string;
  theme: Theme;
  refreshing: boolean;
  canRefresh: boolean;
  onLoad: (username: string) => void;
  onRefresh: () => void;
  onToggleTheme: () => void;
}

export function TopBar({ username, theme, refreshing, canRefresh, onLoad, onRefresh, onToggleTheme }: Props) {
  const [value, setValue] = useState(username);

  useEffect(() => setValue(username), [username]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const v = value.trim().replace(/^@/, '');
    if (v) onLoad(v);
  };

  return (
    <header className="topbar">
      <div className="topbar-inner container">
        <a className="brand" href="/" aria-label="DevFolio home">
          <LogoIcon />
          <span className="brand-text">
            DevFolio<span className="brand-sub">GitHub Developer Portfolio</span>
          </span>
        </a>

        <form className="search" onSubmit={submit} role="search">
          <label htmlFor="username-input" className="sr-only">
            GitHub username
          </label>
          <div className="search-field">
            <SearchIcon className="search-icon" />
            <input
              id="username-input"
              type="text"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="GitHub username"
              autoComplete="off"
              spellCheck={false}
              maxLength={39}
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={!value.trim()}>
            Load
          </button>
        </form>

        <div className="topbar-actions">
          <button
            type="button"
            className="btn btn-icon"
            onClick={onRefresh}
            disabled={!canRefresh || refreshing}
            aria-label="Refresh data from GitHub"
            title="Refresh data from GitHub"
          >
            <RefreshIcon className={refreshing ? 'spin' : undefined} />
          </button>
          <button
            type="button"
            className="btn btn-icon"
            onClick={onToggleTheme}
            aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
            title={theme === 'dark' ? 'Light theme' : 'Dark theme'}
          >
            {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          </button>
        </div>
      </div>
    </header>
  );
}
