import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError, errorMessage } from '../api/client';
import type { Portfolio } from '../types';

interface State {
  data: Portfolio | null;
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  status: number | null;
}

export function usePortfolio(username: string | null) {
  const [state, setState] = useState<State>({
    data: null,
    loading: false,
    refreshing: false,
    error: null,
    status: null,
  });
  const reqId = useRef(0);

  const load = useCallback(
    async (refresh = false) => {
      if (!username) return;
      const id = ++reqId.current;
      setState((s) => ({
        ...s,
        loading: !refresh || !s.data,
        refreshing: refresh,
        error: null,
        status: null,
        data: refresh ? s.data : s.data?.profile.login.toLowerCase() === username.toLowerCase() ? s.data : null,
      }));
      try {
        const data = await api.getPortfolio(username, refresh);
        if (id !== reqId.current) return;
        setState({ data, loading: false, refreshing: false, error: null, status: null });
      } catch (err) {
        if (id !== reqId.current) return;
        setState((s) => ({
          ...s,
          data: refresh ? s.data : null,
          loading: false,
          refreshing: false,
          error: errorMessage(err),
          status: err instanceof ApiError ? err.status : null,
        }));
      }
    },
    [username],
  );

  useEffect(() => {
    void load(false);
  }, [load]);

  return { ...state, reload: load };
}
