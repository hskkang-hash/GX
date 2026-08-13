import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * WebSocket message structure from backend for upload detection
 */
export interface UploadDetectionMessage {
  type: 'media_upload_detection' | 'upload_detection' | 'connected' | 'pong' | 'detection_complete';
  msg?: 'upload_detection_completed' | string;
  status?: 'processing' | 'completed' | 'error';
  progress?: number;
  task_id?: string;
  analysis_id?: number;
  data?: {
    analysis?: unknown[];
    video_analysis?: {
      id: number;
      video_path: string;
      analysis_path: string;
      drone_name?: string | null;
      profile_device_id?: number | null;
      stream_monitor_id?: number | null;
      created_at?: string;
      updated_at?: string;
    };
  };
  timestamp?: string;
}

interface UseMediaUploadDetectionWebSocketOptions {
  /**
   * Whether to enable WebSocket connection
   * Should be true when detection is in progress
   */
  enabled: boolean;

  /**
   * Callback when message is received
   */
  onMessage?: (message: UploadDetectionMessage) => void;

  /**
   * Callback when detection is completed
   * @param analysisId - The analysis ID from video_analysis
   * @param videoPath - The video path from video_analysis to match with selected row
   */
  onComplete?: (analysisId?: number, videoPath?: string) => void;

  /**
   * Callback when error occurs
   */
  onError?: (error: string) => void;
}

/**
 * Custom hook for managing WebSocket connection to receive real-time upload detection progress.
 *
 * **When to use:**
 * - Use this hook after calling detectFileTypeAPI
 * - This allows tracking the progress of media detection processing
 *
 * **How it works:**
 * 1. Connects to `ws://[host]/ws/media/upload-detection/` WebSocket endpoint
 * 2. Backend sends progress updates during detection processing
 * 3. Hook receives messages and calls appropriate callbacks
 */
export const useMediaUploadDetectionWebSocket = ({
  enabled,
  onMessage,
  onComplete,
  onError,
}: UseMediaUploadDetectionWebSocketOptions) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState<number>(0);
  const socketRef = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);

  // Keep refs updated
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  /**
   * Handle incoming WebSocket messages
   */
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data: UploadDetectionMessage = JSON.parse(event.data);

      console.log('[UPLOAD_DETECTION][WS] Received message:', data);

      // Handle connection confirmation
      if (data.type === 'connected') {
        console.log('[UPLOAD_DETECTION][WS] Connected successfully');
        return;
      }

      // Call onMessage callback
      if (onMessageRef.current) {
        onMessageRef.current(data);
      }

      // Handle progress updates
      if (data.progress !== undefined) {
        setProgress(data.progress);
      }

      // Handle media_upload_detection with upload_detection_completed message
      if (
        data.type === 'media_upload_detection' &&
        data.msg === 'upload_detection_completed'
      ) {
        console.log('[UPLOAD_DETECTION][WS] Detection completed');
        setIsProcessing(false);
        setProgress(100);
        // Extract analysis_id and video_path from video_analysis if available
        const analysisId = data.data?.video_analysis?.id;
        const videoPath = data.data?.video_analysis?.video_path;
        if (onCompleteRef.current) {
          onCompleteRef.current(analysisId, videoPath);
        }
        return;
      }

      // Handle status updates (legacy format)
      if (data.status === 'processing') {
        setIsProcessing(true);
      } else if (data.status === 'completed' || data.type === 'detection_complete') {
        setIsProcessing(false);
        setProgress(100);
        if (onCompleteRef.current) {
          onCompleteRef.current(data.analysis_id);
        }
      } else if (data.status === 'error') {
        setIsProcessing(false);
        if (onErrorRef.current) {
          onErrorRef.current(data.msg || 'Detection failed');
        }
      }
    } catch (error) {
      console.error('[UPLOAD_DETECTION][WS] Failed to parse message:', error);
    }
  }, []);

  /**
   * Manage WebSocket connection lifecycle
   */
  useEffect(() => {
    // Don't connect if disabled
    if (!enabled) {
      setIsConnected(false);
      setIsProcessing(false);
      setProgress(0);
      return () => {};
    }

    const wsUrl = `${import.meta.env.VITE_STREAMING_WS}/ws/media/upload-detection/`;

    console.log('[UPLOAD_DETECTION][WS] Connecting to:', wsUrl);

    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      setIsConnected(true);
      console.log('[UPLOAD_DETECTION][WS] Connection opened');

      // Send ping to keep connection alive
      const pingInterval = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000); // Ping every 30 seconds

      // Store interval ID for cleanup
      (socket as unknown as { _pingInterval: NodeJS.Timeout })._pingInterval =
        pingInterval;
    };

    socket.onmessage = handleMessage;

    socket.onclose = () => {
      setIsConnected(false);
      socketRef.current = null;
      console.log('[UPLOAD_DETECTION][WS] Connection closed');

      // Clear ping interval
      const socketWithInterval = socket as unknown as {
        _pingInterval?: NodeJS.Timeout;
      };
      if (socketWithInterval._pingInterval) {
        clearInterval(socketWithInterval._pingInterval);
      }
    };

    socket.onerror = (error) => {
      setIsConnected(false);
      console.error('[UPLOAD_DETECTION][WS] Connection error:', error);
      if (onErrorRef.current) {
        onErrorRef.current('WebSocket connection failed');
      }
    };

    // Cleanup on unmount or when dependencies change
    return () => {
      try {
        const socketWithInterval = socket as unknown as {
          _pingInterval?: NodeJS.Timeout;
        };
        if (socketWithInterval._pingInterval) {
          clearInterval(socketWithInterval._pingInterval);
        }

        if (socketRef.current) {
          socketRef.current.close();
          socketRef.current = null;
        } else {
          socket.close();
        }
      } catch (error) {
        console.error('[UPLOAD_DETECTION][WS] Cleanup error:', error);
      }
    };
  }, [enabled, handleMessage]);

  /**
   * Manually close the WebSocket connection
   */
  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    setIsConnected(false);
    setIsProcessing(false);
    setProgress(0);
  }, []);

  return {
    isConnected,
    isProcessing,
    progress,
    disconnect,
  };
};
