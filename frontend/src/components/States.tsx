import { AlertIcon, RefreshIcon } from './Icons';

export function ErrorCard({ message, status, onRetry }: { message: string; status: number | null; onRetry: () => void }) {
  const title =
    status === 404
      ? 'User not found'
      : status === 429
        ? 'Rate limit reached'
        : status === 422
          ? 'Invalid username'
          : status === 0
            ? 'Server unreachable'
            : 'Could not load portfolio';
  return (
    <section className="card error-card" role="alert">
      <span className="error-icon">
        <AlertIcon size={24} />
      </span>
      <h2>{title}</h2>
      <p className="muted">{message}</p>
      <button type="button" className="btn btn-primary" onClick={onRetry}>
        <RefreshIcon /> Try again
      </button>
    </section>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="dashboard" aria-busy="true" aria-label="Loading portfolio">
      <section className="card">
        <div className="profile-main">
          <div className="skeleton skel-avatar" />
          <div className="profile-info">
            <div className="skeleton skel-line" style={{ width: '40%', height: 24 }} />
            <div className="skeleton skel-line" style={{ width: '20%' }} />
            <div className="skeleton skel-line" style={{ width: '70%' }} />
          </div>
        </div>
        <div className="stat-grid">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="skeleton skel-tile" />
          ))}
        </div>
      </section>
      <div className="row row-charts">
        <div className="card skeleton-card">
          <div className="skeleton skel-block" />
        </div>
        <div className="card skeleton-card">
          <div className="skeleton skel-block" />
        </div>
      </div>
      <div className="card skeleton-card">
        <div className="repo-grid">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton skel-repo" />
          ))}
        </div>
      </div>
    </div>
  );
}
