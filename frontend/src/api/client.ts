import type { BadgeMetric, CompareResult, Insights, MatchResult, Portfolio, Settings } from '../types';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

const BASE = '/api';

function extractDetail(body: unknown): string | null {
  if (!body || typeof body !== 'object') return null;
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((d) => {
        if (typeof d === 'string') return d;
        if (d && typeof d === 'object' && 'msg' in d) {
          const msg = String((d as { msg: unknown }).msg);
          return msg.replace(/^Value error,\s*/i, '');
        }
        return null;
      })
      .filter((m): m is string => Boolean(m));
    if (msgs.length) return msgs.join('; ');
  }
  return null;
}

function fallbackMessage(status: number): string {
  switch (status) {
    case 404:
      return 'Not found.';
    case 422:
      return 'The request was invalid.';
    case 429:
      return 'GitHub rate limit reached. Please try again in a few minutes.';
    case 502:
    case 503:
    case 504:
      return 'GitHub is unreachable right now. Please try again shortly.';
    default:
      return `Request failed (HTTP ${status}).`;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError('Cannot reach the server. Is the backend running on port 8000?', 0);
  }

  let body: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }

  if (!res.ok) {
    throw new ApiError(extractDetail(body) ?? fallbackMessage(res.status), res.status);
  }
  return body as T;
}

const enc = encodeURIComponent;

export const api = {
  getPortfolio: (username: string, refresh = false) =>
    request<Portfolio>(`/portfolio/${enc(username)}?refresh=${refresh ? 'true' : 'false'}`),
  getSettings: () => request<Settings>('/settings'),
  updateSettings: (patch: Partial<Settings>) =>
    request<Settings>('/settings', { method: 'PUT', body: JSON.stringify(patch) }),
  match: (username: string, job_description: string) =>
    request<MatchResult>('/match', {
      method: 'POST',
      body: JSON.stringify({ username, job_description }),
    }),
  getInsights: (username: string, refresh = false) =>
    request<Insights>(`/insights/${enc(username)}?refresh=${refresh ? 'true' : 'false'}`),
  compareDevelopers: (a: string, b: string) => request<CompareResult>(`/compare?users=${enc(a)},${enc(b)}`),
};

export function badgeUrl(username: string, metric: BadgeMetric): string {
  return `/api/badge/${enc(username)}?metric=${metric}`;
}

export function errorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  return 'Something went wrong.';
}
