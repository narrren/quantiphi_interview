import { useCallback, useEffect, useRef, useState } from 'react';
import { api, errorMessage } from '../api/client';
import type { Insights } from '../types';

interface State {
  data: Insights | null;
  loading: boolean;
  error: string | null;
}

/** Loads insights/readiness for a username once the portfolio has loaded. */
export function useInsights(username: string | null) {
  const [state, setState] = useState<State>({ data: null, loading: false, error: null });
  const reqId = useRef(0);

  const load = useCallback(
    async (refresh = false) => {
      if (!username) return;
      const id = ++reqId.current;
      setState((s) => ({ data: refresh ? s.data : null, loading: true, error: null }));
      try {
        const data = await api.getInsights(username, refresh);
        if (id !== reqId.current) return;
        setState({ data, loading: false, error: null });
      } catch (err) {
        if (id !== reqId.current) return;
        // Keep previously loaded insights if only a refresh failed.
        setState((s) => ({ data: refresh ? s.data : null, loading: false, error: errorMessage(err) }));
      }
    },
    [username],
  );

  useEffect(() => {
    if (!username) {
      reqId.current++;
      setState({ data: null, loading: false, error: null });
      return;
    }
    void load(false);
  }, [username, load]);

  return { ...state, reload: load };
}
