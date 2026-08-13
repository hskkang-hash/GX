import { useCallback, useEffect, useRef, useState } from 'react';

interface UseWebRTCProps {
  rtspUrl: string;
  isActive: boolean;
  onError?: (error: string) => void;
  onSuccess?: () => void;
  onStatusChange?: (status: string, type: 'info' | 'success' | 'error') => void;
  isStreamingAI?: boolean;
}

export const useWebRTC = ({
  rtspUrl,
  isActive,
  isStreamingAI = false,
  onError,
  onSuccess,
  onStatusChange,
}: UseWebRTCProps) => {
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const connectionIdRef = useRef<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasStreamFailed, setHasStreamFailed] = useState(false);

  const startStream = useCallback(async () => {
    if (!rtspUrl || isLoading || isConnected) return;

    // Reset failure flag when manually starting stream
    setHasStreamFailed(false);

    try {
      setIsLoading(true);
      setError(null);
      onStatusChange?.('Initializing WebRTC connection...', 'info');

      // Create RTCPeerConnection using shared config
      const pc = new RTCPeerConnection({
        iceServers: [
          {
            urls: import.meta.env.VITE_TURN_URL,
            username: import.meta.env.VITE_TURN_USERNAME,
            credential: import.meta.env.VITE_TURN_PASSWORD,
          },
        ],
      });

      pcRef.current = pc;

      // Handle incoming tracks
      pc.ontrack = (event) => {
        if (event.track.kind === 'video' && videoRef.current) {
          videoRef.current.srcObject = event.streams[0];
          setIsConnected(true);
          setIsLoading(false);
          onStatusChange?.('Video stream connected successfully!', 'success');
          onSuccess?.();
        }
      };

      // Handle connection state changes
      pc.onconnectionstatechange = () => {
        if (
          pc.connectionState === 'failed' ||
          pc.connectionState === 'disconnected'
        ) {
          const errorMsg = 'WebRTC connection failed or disconnected';
          setError(errorMsg);
          onError?.(errorMsg);
        }
      };

      // Handle ICE connection state changes
      pc.oniceconnectionstatechange = () => {
        if (pc.iceConnectionState === 'failed') {
          const errorMsg = 'ICE connection failed';
          setError(errorMsg);
          onError?.(errorMsg);
        }
      };

      // Create offer
      const offer = await pc.createOffer({
        offerToReceiveVideo: true,
        offerToReceiveAudio: false,
      });
      await pc.setLocalDescription(offer);

      // Send offer to server with retry logic (max 5 attempts, 1 second delay)
      const maxRetries = 5;
      const retryDelay = 1000; // 1 second
      let lastError: Error | null = null;
      let response: Response | null = null;

      for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
          onStatusChange?.(
            `Connecting to stream (attempt ${attempt}/${maxRetries})...`,
            'info',
          );

          response = await fetch(
            `${import.meta.env.VITE_STREAMING_BASE_URL}/webrtc/${rtspUrl}/whep`,
            {
              method: 'POST',
              headers: {
                'Content-Type': 'application/sdp',
              },
              body: offer.sdp,
            },
          );

          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }

          // Success - break out of retry loop
          break;
        } catch (error) {
          lastError = error instanceof Error ? error : new Error(String(error));
          console.warn(
            `WebRTC connection attempt ${attempt}/${maxRetries} failed:`,
            lastError.message,
          );

          // If this is not the last attempt, wait before retrying
          if (attempt < maxRetries) {
            onStatusChange?.(
              `Connection failed, retrying in ${retryDelay / 1000} second...`,
              'error',
            );
            await new Promise((resolve) => setTimeout(resolve, retryDelay));
          }
        }
      }

      // If all retries failed, throw the last error
      if (!response || !response.ok) {
        throw (
          lastError ||
          new Error(`Failed to connect after ${maxRetries} attempts`)
        );
      }

      const answer = await response.text();

      // Store connection ID for cleanup
      if (answer) {
        connectionIdRef.current = answer;
      }

      // Set remote description
      await pc.setRemoteDescription(
        new RTCSessionDescription({
          type: 'answer',
          sdp: answer,
        }),
      );

      onStatusChange?.('WebRTC connection established!', 'success');
    } catch (error) {
      console.error('Error starting WebRTC stream:', error);
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error occurred';
      setError(errorMessage);
      setIsLoading(false);
      setHasStreamFailed(true);
      onError?.(errorMessage);
      onStatusChange?.(errorMessage, 'error');
    }
  }, [rtspUrl, isLoading, isConnected, onError, onSuccess, onStatusChange]);

  const stopStream = useCallback(async () => {
    try {
      onStatusChange?.('Stream stopped', 'info');
    } catch (error) {
      console.error('Error stopping stream:', error);
      const errorMessage =
        error instanceof Error
          ? error.message
          : 'Unknown error stopping stream';
      onStatusChange?.(errorMessage, 'error');
    }
  }, [onStatusChange]);

  // Reset failure flag when rtspUrl changes (new stream)
  useEffect(() => {
    setHasStreamFailed(false);
  }, [rtspUrl]);

  // Auto start/stop stream based on isActive prop and config availability
  useEffect(() => {
    if (isActive && rtspUrl && !isConnected && !isLoading && !hasStreamFailed) {
      startStream();
    } else if (!isActive && (isConnected || isLoading)) {
      // Handle async stopStream
      stopStream().catch((error) => {
        console.error('Error in auto-stop:', error);
      });
    }
  }, [
    isActive,
    rtspUrl,
    isConnected,
    isLoading,
    hasStreamFailed,
    startStream,
    stopStream,
  ]);

  // Cleanup on unmount and page navigation
  useEffect(() => {
    // Handle page unload/navigation
    const handleBeforeUnload = () => {
      // Call DELETE API for connection cleanup using sendBeacon for reliability
      // if (connectionIdRef.current) {
      //   connectionIdRef.current = null;
      // }

      // Close peer connection
      if (pcRef.current) {
        pcRef.current.close();
        pcRef.current = null;
      }
    };

    // Add beforeunload listener
    window.addEventListener('beforeunload', handleBeforeUnload);

    // Cleanup function for component unmount
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  return {
    videoRef,
    isConnected,
    isLoading,
    error,
    startStream,
    stopStream,
  };
};
