import { useCallback, useEffect, useRef, useState } from 'react';

interface UseAutoRefreshOptions {
  refreshTime: number;
  isActive: boolean;
}

interface UseAutoRefreshResult {
  shouldRefresh: boolean;
  consumeRefreshFlag: () => void;
  resetAutoRefreshTimer: () => void;
}

export const useAutoRefresh = ({
  refreshTime,
  isActive,
}: UseAutoRefreshOptions): UseAutoRefreshResult => {
  const autoRefreshIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [shouldRefresh, setShouldRefresh] = useState(false);

  const startAutoRefreshInterval = useCallback(() => {
    if (autoRefreshIntervalRef.current) {
      clearInterval(autoRefreshIntervalRef.current);
      autoRefreshIntervalRef.current = null;
    }

    if (!refreshTime || refreshTime <= 0 || !isActive) {
      return;
    }

    autoRefreshIntervalRef.current = setInterval(() => {
      setShouldRefresh(true);
    }, refreshTime * 1000);
  }, [refreshTime, isActive]);

  useEffect(() => {
    startAutoRefreshInterval();

    return () => {
      if (autoRefreshIntervalRef.current) {
        clearInterval(autoRefreshIntervalRef.current);
        autoRefreshIntervalRef.current = null;
      }
    };
  }, [startAutoRefreshInterval]);

  const consumeRefreshFlag = useCallback(() => setShouldRefresh(false), []);

  const resetAutoRefreshTimer = useCallback(() => {
    setShouldRefresh(false);
    startAutoRefreshInterval();
  }, [startAutoRefreshInterval]);

  return { shouldRefresh, consumeRefreshFlag, resetAutoRefreshTimer };
};
