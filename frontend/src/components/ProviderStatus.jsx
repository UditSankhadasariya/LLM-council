import { useState, useEffect } from 'react';
import { api } from '../api';
import './ProviderStatus.css';

export default function ProviderStatus() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  const fetchHealth = async () => {
    try {
      const data = await api.checkHealth();
      setHealth(data);
      setError(false);
      // Reset dismissed when status changes to allow re-showing
      if (!data.all_ready) {
        setDismissed(false);
      }
    } catch {
      setError(true);
      setHealth(null);
      setDismissed(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // Backend is unreachable
  if (error) {
    return (
      <div className="provider-status provider-status-error">
        <div className="provider-status-content">
          <span className="provider-status-icon">!</span>
          <div className="provider-status-text">
            <strong>Backend unreachable</strong>
            <span>Cannot connect to the LLM Council backend on port 8001.</span>
          </div>
          <button className="provider-status-retry" onClick={fetchHealth}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  // All good or still loading
  if (!health || health.all_ready || dismissed) {
    return null;
  }

  const downProviders = Object.entries(health.providers).filter(
    ([, p]) => !p.ready
  );

  return (
    <div className="provider-status provider-status-warning">
      <div className="provider-status-content">
        <span className="provider-status-icon">!</span>
        <div className="provider-status-text">
          <strong>
            {downProviders.length === Object.keys(health.providers).length
              ? 'All providers are down'
              : `${downProviders.length} provider${downProviders.length > 1 ? 's' : ''} down`}
          </strong>
          <div className="provider-status-list">
            {downProviders.map(([id, p]) => (
              <div key={id} className="provider-status-item">
                <span className="provider-dot provider-dot-down" />
                <span className="provider-name">{p.name}</span>
                <span className="provider-hint">
                  {p.initializing
                    ? 'Starting up...'
                    : p.provider === 'browser'
                      ? 'Session expired — VNC in to re-login'
                      : 'SSH in and run `claude` to re-auth'}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div className="provider-status-actions">
          <button className="provider-status-retry" onClick={fetchHealth}>
            Recheck
          </button>
          <button
            className="provider-status-dismiss"
            onClick={() => setDismissed(true)}
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}
