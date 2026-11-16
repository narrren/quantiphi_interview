export interface Profile {
  login: string;
  name: string | null;
  avatar_url: string | null;
  bio: string | null;
  company: string | null;
  location: string | null;
  blog: string | null;
  html_url: string;
  followers: number;
  following: number;
  public_repos: number;
  created_at: string | null;
}

export interface LanguageStat {
  name: string;
  count: number;
  percentage: number;
  color: string;
}

export interface Stats {
  total_stars: number;
  total_forks: number;
  total_repos: number;
  top_languages: LanguageStat[];
}

export interface Repository {
  id: number;
  name: string;
  full_name: string;
  description: string | null;
  html_url: string;
  stars: number;
  forks: number;
  language: string | null;
  language_color: string | null;
  topics: string[];
  updated_at: string | null;
  is_fork: boolean;
}

export interface ContributionDay {
  date: string;
  count: number;
  level: number;
}

export type ContributionSource = 'graphql' | 'scrape' | 'unavailable';

export interface Contributions {
  total: number;
  weeks: ContributionDay[][];
  current_streak: number;
  longest_streak: number;
  best_day: { date: string; count: number } | null;
  source: ContributionSource;
}

export interface CacheInfo {
  cached: boolean;
  fetched_at: string;
  ttl_seconds: number;
  stale: boolean;
}

export interface Portfolio {
  profile: Profile;
  stats: Stats;
  repositories: Repository[];
  contributions: Contributions;
  cache: CacheInfo;
}

export type Theme = 'light' | 'dark';

export interface Settings {
  default_username: string;
  theme: Theme;
  cache_ttl_seconds: number;
  last_job_description: string;
}

export type Grade = 'Excellent' | 'Strong' | 'Moderate' | 'Low';

export interface MatchedKeyword {
  keyword: string;
  category: string;
  evidence: string[];
}

export interface MissingKeyword {
  keyword: string;
  category: string;
}

export interface MatchResult {
  match_percentage: number;
  grade: Grade;
  matched: MatchedKeyword[];
  missing: MissingKeyword[];
  jd_keywords_count: number;
  summary: string;
}
