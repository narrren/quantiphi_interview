import type { ActivityInsights } from '../types';
import { formatNumber } from '../format';
import { AlertIcon } from './Icons';

interface Props {
  activity: ActivityInsights | null;
  loading: boolean;
  error: string | null;
}

const W = 640;
const H = 180;
const PAD_X = 12;
const PAD_TOP = 16;
const PAD_BOTTOM = 28;

function TrendChart({ monthly }: { monthly: ActivityInsights['monthly'] }) {
  if (monthly.length === 0) return <div className="empty">No monthly data</div>;
  const max = Math.max(1, ...monthly.map((m) => m.total));
  const innerW = W - PAD_X * 2;
  const innerH = H - PAD_TOP - PAD_BOTTOM;
  const step = monthly.length > 1 ? innerW / (monthly.length - 1) : 0;
  const pts = monthly.map((m, i) => ({
    x: PAD_X + (monthly.length > 1 ? i * step : innerW / 2),
    y: PAD_TOP + innerH - (m.total / max) * innerH,
    m,
  }));
  const line = pts.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const baseY = PAD_TOP + innerH;
  const area = `${line} L${pts[pts.length - 1].x.toFixed(1)},${baseY} L${pts[0].x.toFixed(1)},${baseY} Z`;
  return (
    <svg className="trend-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Monthly contributions over the last 12 months">
      <defs>
        <linearGradient id="trend-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--accent)" stopOpacity="0.35" />
          <stop offset="1" stopColor="var(--accent)" stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0.25, 0.5, 0.75, 1].map((f) => (
        <line key={f} x1={PAD_X} x2={W - PAD_X} y1={baseY - innerH * f} y2={baseY - innerH * f} className="trend-grid" />
      ))}
      <line x1={PAD_X} x2={W - PAD_X} y1={baseY} y2={baseY} className="trend-axis" />
      <path d={area} fill="url(#trend-fill)" />
      <path d={line} className="trend-line" />
      {pts.map((p) => (
        <g key={p.m.month} className="trend-point">
          <title>{`${p.m.label}: ${formatNumber(p.m.total)} contributions`}</title>
          <rect x={p.x - step / 2} y={PAD_TOP} width={Math.max(step, 20)} height={innerH} fill="transparent" />
          <circle cx={p.x} cy={p.y} r={3.5} />
          <text x={p.x} y={H - 8} textAnchor="middle" className="trend-label">
            {p.m.label.split(' ')[0]}
          </text>
        </g>
      ))}
    </svg>
  );
}

export function InsightsPanel({ activity, loading, error }: Props) {
  return (
    <section className="card" aria-labelledby="insights-title" aria-busy={loading}>
      <div className="card-head">
        <h2 id="insights-title">Developer Insights</h2>
        <span className="muted small">Activity rhythm over the last year</span>
      </div>

      {error && !activity && (
        <div className="alert alert-error" role="alert">
          <AlertIcon /> Insights unavailable: {error}
        </div>
      )}

      {loading && !activity && (
        <div className="stack">
          <div className="kpi-grid">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="skeleton skel-tile" />
            ))}
          </div>
          <div className="insights-row">
            <div className="skeleton skel-block" />
            <div className="skeleton skel-block" />
          </div>
        </div>
      )}

      {activity && <InsightsBody activity={activity} />}
    </section>
  );
}

function InsightsBody({ activity }: { activity: ActivityInsights }) {
  const { trend } = activity;
  const maxDay = Math.max(1, ...activity.weekday_totals.map((d) => d.total));
  const arrow = trend.direction === 'up' ? '▲' : trend.direction === 'down' ? '▼' : '■';
  return (
    <div className="stack insights">
      <div className="kpi-grid">
        <div className="kpi">
          <span className="kpi-value">{activity.consistency_percentage}%</span>
          <span className="kpi-label">Consistency</span>
          <span className="kpi-sub">
            {formatNumber(activity.active_days)} of {formatNumber(activity.total_days)} days
          </span>
        </div>
        <div className="kpi">
          <span className="kpi-value">{activity.average_per_active_day}</span>
          <span className="kpi-label">Avg per active day</span>
          <span className="kpi-sub">contributions</span>
        </div>
        <div className="kpi">
          <span className="kpi-value">{formatNumber(activity.active_days)}</span>
          <span className="kpi-label">Active days</span>
          <span className="kpi-sub">Most active: {activity.most_active_weekday ?? '—'}</span>
        </div>
        <div className="kpi">
          <span className={`kpi-value trend-${trend.direction}`}>
            {trend.change_percentage === null ? (
              '—'
            ) : (
              <>
                <span aria-hidden>{arrow}</span> {Math.abs(trend.change_percentage)}%
              </>
            )}
          </span>
          <span className="kpi-label">30-day trend</span>
          <span className="kpi-sub">
            {formatNumber(trend.last_30_days)} vs {formatNumber(trend.previous_30_days)} prior
          </span>
        </div>
      </div>

      <div className="insights-row">
        <div>
          <h3 className="sub-title">Weekday rhythm</h3>
          <div className="weekday-chart" role="list" aria-label="Contributions by weekday">
            {activity.weekday_totals.map((d) => {
              const top = d.day === activity.most_active_weekday;
              return (
                <div
                  key={d.day}
                  role="listitem"
                  className={`weekday-col ${top ? 'is-top' : ''}`}
                  title={`${d.day}: ${formatNumber(d.total)} total · ${d.average} avg`}
                >
                  <span className="weekday-val">{formatNumber(d.total)}</span>
                  <div className="weekday-track">
                    <div className="weekday-bar" style={{ height: `${(d.total / maxDay) * 100}%` }} />
                  </div>
                  <span className="weekday-day">{d.day}</span>
                </div>
              );
            })}
          </div>
        </div>
        <div className="min0">
          <h3 className="sub-title">12-month contribution trend</h3>
          <TrendChart monthly={activity.monthly} />
        </div>
      </div>
    </div>
  );
}
