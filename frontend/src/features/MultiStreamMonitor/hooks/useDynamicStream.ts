import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

export type StreamProtocol = 'hls' | 'webrtc' | 'auto';
export type StreamQuality = 'high' | 'medium' | 'low';

interface StreamConfig {
  protocol: StreamProtocol;
  quality: StreamQuality;
  hlsUrl?: string;
  webrtcUrl?: string;
  rtspUrl?: string;
}

interface ConnectionMetrics {
  latency: number;
  bandwidth: number;
  packetLoss: number;
  connectionStability: number;
}

interface UseDynamicStreamProps {
  streamId: string;
  hlsUrl?: string;
  webrtcUrl?: string;
  rtspUrl?: string;
  initialProtocol?: StreamProtocol;
  autoSwitch?: boolean;
  onProtocolSwitch?: (from: StreamProtocol, to: StreamProtocol) => void;
  onQualityChange?: (quality: StreamQuality) => void;
}

export const useDynamicStream = ({
  streamId,
  hlsUrl,
  webrtcUrl,
  rtspUrl,
  initialProtocol = 'auto',
  autoSwitch = true,
  onProtocolSwitch,
  onQualityChange,
}: UseDynamicStreamProps) => {
  const [currentProtocol, setCurrentProtocol] =
    useState<StreamProtocol>(initialProtocol);
  const [currentQuality, setCurrentQuality] = useState<StreamQuality>('high');
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [connectionMetrics, setConnectionMetrics] = useState<ConnectionMetrics>(
    {
      latency: 0,
      bandwidth: 0,
      packetLoss: 0,
      connectionStability: 100,
    },
  );
  const [retryCount, setRetryCount] = useState(0);
  const [maxRetries] = useState(3);
  const monitoringIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const isInitializedRef = useRef(false);

  // Determine the best protocol based on available URLs and conditions
  const determineBestProtocol = useCallback((): StreamProtocol => {
    // If auto mode is disabled, keep current protocol
    if (currentProtocol !== 'auto' && !autoSwitch) {
      return currentProtocol;
    }

    // If we have both URLs, decide based on connection quality for auto mode
    if (currentProtocol === 'auto') {
      // Check connection quality
      const { latency, packetLoss, connectionStability } = connectionMetrics;

      // For real-time applications with low latency requirements
      if (
        (webrtcUrl || rtspUrl) &&
        latency < 100 &&
        packetLoss < 2 &&
        connectionStability > 80
      ) {
        return 'webrtc';
      }

      // For stable connections with higher latency tolerance
      if (hlsUrl && connectionStability > 60) {
        return 'hls';
      }
    }

    // Simple fallback based on available URLs
    // Priority: match current protocol if URL available, otherwise fallback
    if (currentProtocol === 'webrtc' && (webrtcUrl || rtspUrl)) return 'webrtc';
    if (currentProtocol === 'hls' && hlsUrl) return 'hls';

    // Default fallback priority: WebRTC > HLS if URLs are available
    if (webrtcUrl || rtspUrl) return 'webrtc';
    if (hlsUrl) return 'hls';

    return 'hls'; // Ultimate fallback
  }, [
    hlsUrl,
    webrtcUrl,
    rtspUrl,
    connectionMetrics,
    currentProtocol,
    autoSwitch,
  ]);

  // Get the appropriate stream URL based on current protocol (memoized)
  const streamUrl = useMemo(() => {
    switch (currentProtocol) {
      case 'webrtc':
        return webrtcUrl || rtspUrl;
      case 'hls':
        return hlsUrl;
      case 'auto':
        const bestProtocol = determineBestProtocol();
        return bestProtocol === 'webrtc' ? webrtcUrl || rtspUrl : hlsUrl;
      default:
        return hlsUrl;
    }
  }, [currentProtocol, hlsUrl, webrtcUrl, rtspUrl, determineBestProtocol]);

  // Get streaming configuration (memoized)
  const streamConfig = useMemo((): StreamConfig => {
    const activeProtocol =
      currentProtocol === 'auto' ? determineBestProtocol() : currentProtocol;

    return {
      protocol: activeProtocol,
      quality: currentQuality,
      hlsUrl,
      webrtcUrl,
      rtspUrl,
    };
  }, [
    currentProtocol,
    currentQuality,
    hlsUrl,
    webrtcUrl,
    rtspUrl,
    determineBestProtocol,
  ]);

  // Switch protocol manually or automatically
  const switchProtocol = useCallback(
    (newProtocol: StreamProtocol, reason?: string) => {
      if (newProtocol === currentProtocol) return;

      console.log(
        `🔄 Switching stream protocol from ${currentProtocol} to ${newProtocol}`,
        {
          streamId,
          reason,
          metrics: connectionMetrics,
        },
      );

      const oldProtocol = currentProtocol;
      setCurrentProtocol(newProtocol);
      setIsLoading(true);
      setRetryCount(0);

      onProtocolSwitch?.(oldProtocol, newProtocol);
    },
    [currentProtocol, streamId, connectionMetrics, onProtocolSwitch],
  );

  // Monitor connection quality and auto-switch if needed
  useEffect(() => {
    // Clear existing interval
    if (monitoringIntervalRef.current) {
      clearInterval(monitoringIntervalRef.current);
      monitoringIntervalRef.current = null;
    }

    if (!autoSwitch || currentProtocol !== 'auto') return;

    monitoringIntervalRef.current = setInterval(() => {
      // Simulate connection quality monitoring
      // In a real implementation, you would measure actual network metrics
      const simulatedMetrics: ConnectionMetrics = {
        latency: Math.random() * 200, // 0-200ms
        bandwidth: Math.random() * 100, // 0-100 Mbps
        packetLoss: Math.random() * 5, // 0-5%
        connectionStability: 70 + Math.random() * 30, // 70-100%
      };

      setConnectionMetrics((prev) => {
        // Only update if values have significantly changed to prevent unnecessary re-renders
        const hasSignificantChange =
          Math.abs(prev.latency - simulatedMetrics.latency) > 10 ||
          Math.abs(prev.bandwidth - simulatedMetrics.bandwidth) > 5 ||
          Math.abs(prev.packetLoss - simulatedMetrics.packetLoss) > 0.5 ||
          Math.abs(
            prev.connectionStability - simulatedMetrics.connectionStability,
          ) > 5;

        return hasSignificantChange ? simulatedMetrics : prev;
      });

      // Only check for protocol switch if initialized
      if (isInitializedRef.current) {
        const bestProtocol = determineBestProtocol();
        const currentActiveProtocol =
          currentProtocol === 'auto'
            ? determineBestProtocol()
            : currentProtocol;

        if (bestProtocol !== currentActiveProtocol) {
          switchProtocol(
            bestProtocol,
            'Auto-switch based on connection quality',
          );
        }
      }
    }, 10000); // Check every 10 seconds (increased to reduce frequency)

    return () => {
      if (monitoringIntervalRef.current) {
        clearInterval(monitoringIntervalRef.current);
        monitoringIntervalRef.current = null;
      }
    };
  }, [autoSwitch, currentProtocol, determineBestProtocol, switchProtocol]);

  // Initialize flag after first render
  useEffect(() => {
    isInitializedRef.current = true;
  }, []);

  // Handle connection failures and retry logic
  const handleConnectionError = useCallback(
    (error: Error) => {
      console.error(`❌ Stream connection error for ${streamId}:`, error);

      if (retryCount < maxRetries) {
        setRetryCount((prev) => prev + 1);
        setTimeout(
          () => {
            console.log(
              `🔄 Retrying connection (${retryCount + 1}/${maxRetries})`,
            );
            setIsLoading(true);
          },
          2000 * Math.pow(2, retryCount),
        ); // Exponential backoff
      } else {
        // Try switching to fallback protocol
        const currentActiveProtocol =
          currentProtocol === 'auto'
            ? determineBestProtocol()
            : currentProtocol;

        if (currentActiveProtocol === 'webrtc' && hlsUrl) {
          switchProtocol('hls', 'Fallback due to WebRTC connection failure');
        } else if (currentActiveProtocol === 'hls' && (webrtcUrl || rtspUrl)) {
          switchProtocol('webrtc', 'Fallback due to HLS connection failure');
        }
      }
    },
    [
      retryCount,
      maxRetries,
      currentProtocol,
      hlsUrl,
      webrtcUrl,
      rtspUrl,
      switchProtocol,
      determineBestProtocol,
      streamId,
    ],
  );

  // Handle successful connection
  const handleConnectionSuccess = useCallback(() => {
    console.log(`✅ Stream connected successfully for ${streamId}`);
    setIsConnected(true);
    setIsLoading(false);
    setRetryCount(0);
  }, [streamId]);

  // Adjust quality based on connection performance
  const adjustQuality = useCallback(
    (newQuality: StreamQuality) => {
      if (newQuality === currentQuality) return;

      console.log(
        `📊 Adjusting stream quality from ${currentQuality} to ${newQuality}`,
        {
          streamId,
          metrics: connectionMetrics,
        },
      );

      setCurrentQuality(newQuality);
      onQualityChange?.(newQuality);
    },
    [currentQuality, streamId, connectionMetrics, onQualityChange],
  );

  // Auto-adjust quality based on connection metrics (throttled)
  useEffect(() => {
    if (!autoSwitch || !isInitializedRef.current) return;

    const { bandwidth, packetLoss, connectionStability } = connectionMetrics;

    let targetQuality: StreamQuality = currentQuality;

    if (bandwidth > 10 && packetLoss < 1 && connectionStability > 90) {
      targetQuality = 'high';
    } else if (bandwidth > 5 && packetLoss < 3 && connectionStability > 70) {
      targetQuality = 'medium';
    } else {
      targetQuality = 'low';
    }

    // Only adjust if quality actually needs to change
    if (targetQuality !== currentQuality) {
      adjustQuality(targetQuality);
    }
  }, [connectionMetrics, autoSwitch, adjustQuality, currentQuality]);

  return {
    // Current state
    currentProtocol,
    currentQuality,
    isConnected,
    isLoading,
    connectionMetrics,
    retryCount,
    maxRetries,

    // Configuration (memoized)
    streamConfig,
    streamUrl,
    isHls: useMemo(
      () =>
        currentProtocol === 'hls' ||
        (currentProtocol === 'auto' && determineBestProtocol() === 'hls'),
      [currentProtocol, determineBestProtocol],
    ),
    isWebRTC: useMemo(
      () =>
        currentProtocol === 'webrtc' ||
        (currentProtocol === 'auto' && determineBestProtocol() === 'webrtc'),
      [currentProtocol, determineBestProtocol],
    ),

    // Actions
    switchProtocol,
    adjustQuality,
    handleConnectionError,
    handleConnectionSuccess,

    // Status methods
    canSwitchToWebRTC: !!webrtcUrl || !!rtspUrl,
    canSwitchToHLS: !!hlsUrl,

    // Utility
    reset: useCallback(() => {
      // Clear any running intervals
      if (monitoringIntervalRef.current) {
        clearInterval(monitoringIntervalRef.current);
        monitoringIntervalRef.current = null;
      }

      setCurrentProtocol(initialProtocol);
      setCurrentQuality('high');
      setIsConnected(false);
      setIsLoading(false);
      setRetryCount(0);
      isInitializedRef.current = false;
    }, [initialProtocol]),
  };
};
