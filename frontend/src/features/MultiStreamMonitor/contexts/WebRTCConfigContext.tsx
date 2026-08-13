import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useRef,
  useCallback,
} from 'react';

interface WebRTCConfig {
  turn_url: string;
  turn_user: string;
  turn_pass: string;
}

interface WebRTCConfigContextValue {
  config: WebRTCConfig | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

const WebRTCConfigContext = createContext<WebRTCConfigContextValue | undefined>(
  undefined,
);

interface WebRTCConfigProviderProps {
  children: React.ReactNode;
  shouldFetch?: boolean;
}

export const WebRTCConfigProvider: React.FC<WebRTCConfigProviderProps> = ({
  children,
  shouldFetch = false,
}) => {
  const [config, setConfig] = useState<WebRTCConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isActiveRef = useRef(true);

  const fetchConfigWithRetry = useCallback(async (): Promise<void> => {
    const maxRetries = Infinity;
    let retryCount = 0;

    while (retryCount < maxRetries && isActiveRef.current) {
      try {
        const configResponse = await fetch(
          `${import.meta.env.VITE_STREAMING_BASE_URL}/api/config`,
        );

        if (!configResponse.ok) {
          throw new Error(`Failed to fetch config: ${configResponse.status}`);
        }
        const configData = await configResponse.json();

        if (isActiveRef.current) {
          setConfig(configData);
          setError(null);
          setIsLoading(false);
          console.log('✅ WebRTC config fetched successfully');
        }
        return;
      } catch (error) {
        retryCount++;
        const errorMsg =
          error instanceof Error ? error.message : 'Unknown error';

        if (isActiveRef.current) {
          setError(errorMsg);
        }

        if (isActiveRef.current) {
          await new Promise((resolve) => {
            retryTimeoutRef.current = setTimeout(resolve, 5000);
          });
        }
      }
    }
  }, []);

  const refetch = useCallback(() => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    setIsLoading(true);
    setError(null);
    fetchConfigWithRetry();
  }, [fetchConfigWithRetry]);

  useEffect(() => {
    if (!shouldFetch) {
      setConfig(null);
      setIsLoading(false);
      setError(null);
      return;
    }

    isActiveRef.current = true;
    setIsLoading(true);
    fetchConfigWithRetry();

    return () => {
      isActiveRef.current = false;
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
        retryTimeoutRef.current = null;
      }
    };
  }, [fetchConfigWithRetry, shouldFetch]);

  const value: WebRTCConfigContextValue = {
    config,
    isLoading,
    error,
    refetch,
  };

  return (
    <WebRTCConfigContext.Provider value={value}>
      {children}
    </WebRTCConfigContext.Provider>
  );
};

export const useWebRTCConfig = (): WebRTCConfigContextValue => {
  const context = useContext(WebRTCConfigContext);
  if (context === undefined) {
    throw new Error(
      'useWebRTCConfig must be used within a WebRTCConfigProvider',
    );
  }
  return context;
};
