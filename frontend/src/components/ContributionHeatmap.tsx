import type { ReactNode } from 'react';
import type { Contributions } from '../types';
import { formatDate, formatNumber } from '../format';
import { CalendarIcon, FlameIcon, TrophyIcon, SparkleIcon } from './Icons';

interface Props {
  contributions: Contributions;
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const WEEKDAY_LABELS = ['', 'Mon', '', 'Wed', '', 'Fri', ''];

function parseISODate(date: string) {
  const [y, m, d] = date.split('-').map(Number);
  return new Date(Date.UTC(y, (m || 1) - 1, d || 1));
}

function StreakCard({ icon, label, value, sub }: { icon: ReactNode; label: string; value: string; sub?: string }) {
  return (
    <div className="streak-card">
      <span className="streak-icon">{icon}</span>
      <div>
        <div className="streak-value">{value}</div>
        <div className="streak-label">{label}</div>
        {sub && <div className="streak-sub">{sub}</div>}
      </div>
    </div>
  );
}

export function ContributionHeatmap({ contributions }: Props) {
  const { weeks, source } = contributions;
  const unavailable = source === 'unavailable' || weeks.length === 0;

  // Display-only layout: position each day in its weekday row and month labels above columns.
  const monthLabels: { col: number; label: string }[] = [];
  let lastMonth = -1;
  weeks.forEach((week, wi) => {
    if (!week.length) return;
    const m = parseISODate(week[0].date).getUTCMonth();
    if (m !== lastMonth) {
      if (wi > 0 || week.length === 7) monthLabels.push({ col: wi + 1, label: MONTHS[m] });
      lastMonth = m;
    }
  });
  // Avoid overlapping labels if the first label is too close to the next one.
  if (monthLabels.length > 1 && monthLabels[1].col - monthLabels[0].col < 3) monthLabels.shift();

  return (
    <section className="card" aria-labelledby="contrib-title">
      <div className="card-head">
        <h2 id="contrib-title">Contribution Activity</h2>
        {!unavailable && (
          <span className="muted small">{formatNumber(contributions.total)} contributions in the last year</span>
        )}
      </div>

      {unavailable ? (
        <div className="empty">
          Contribution data is unavailable for this user right now. Repository and language insights are still
          shown below.
        </div>
      ) : (
        <>
          <div className="heatmap-scroll" tabIndex={0} aria-label="Contribution calendar, scrollable">
            <div className="heatmap" style={{ ['--weeks' as string]: weeks.length }}>
              <div className="hm-months" aria-hidden>
                {monthLabels.map((m) => (
                  <span key={`${m.col}-${m.label}`} style={{ gridColumn: m.col }}>
                    {m.label}
                  </span>
                ))}
              </div>
              <div className="hm-days" aria-hidden>
                {WEEKDAY_LABELS.map((d, i) => (
                  <span key={i}>{d}</span>
                ))}
              </div>
              <div
                className="hm-grid"
                role="img"
                aria-label={`${formatNumber(contributions.total)} contributions over ${weeks.length} weeks`}
              >
                {weeks.map((week, wi) =>
                  week.map((day) => {
                    const row = parseISODate(day.date).getUTCDay() + 1;
                    const label = `${day.count === 0 ? 'No' : formatNumber(day.count)} contribution${
                      day.count === 1 ? '' : 's'
                    } on ${formatDate(day.date, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}`;
                    return (
                      <span
                        key={day.date}
                        className={`hm-cell lvl-${Math.max(0, Math.min(4, day.level))}`}
                        style={{ gridColumn: wi + 1, gridRow: row }}
                        title={label}
                      />
                    );
                  }),
                )}
              </div>
            </div>
          </div>
          <div className="hm-legend" aria-hidden>
            <span>Less</span>
            {[0, 1, 2, 3, 4].map((l) => (
              <span key={l} className={`hm-cell lvl-${l}`} />
            ))}
            <span>More</span>
          </div>

          <div className="streak-grid">
            <StreakCard
              icon={<CalendarIcon />}
              label="Total contributions"
              value={formatNumber(contributions.total)}
            />
            <StreakCard
              icon={<FlameIcon />}
              label="Current streak"
              value={`${contributions.current_streak} day${contributions.current_streak === 1 ? '' : 's'}`}
            />
            <StreakCard
              icon={<TrophyIcon />}
              label="Longest streak"
              value={`${contributions.longest_streak} day${contributions.longest_streak === 1 ? '' : 's'}`}
            />
            <StreakCard
              icon={<SparkleIcon />}
              label="Best day"
              value={contributions.best_day ? formatNumber(contributions.best_day.count) : '—'}
              sub={contributions.best_day ? formatDate(contributions.best_day.date) : undefined}
            />
          </div>
        </>
      )}
    </section>
  );
}
