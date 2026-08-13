import React, {
  useRef,
  useEffect,
  useState,
  useCallback,
  useMemo,
} from 'react';

import { useDynamicStream } from '../../hooks/useDynamicStream';
import { useWebRTC } from '../../hooks/useWebRTC';
import { ActionControls } from '../DroneCameraView/components/ActionControls';
import { RecordingOverlay } from '../DroneCameraView/components/RecordingOverlay';
import { useRecording } from '../DroneCameraView/hooks/useRecording';
import { useVideo } from '../DroneCameraView/hooks/useVideo';

interface AIStreamViewProps {
  streamUrl: string;
  width?: string | number;
  height?: string | number;
  label?: string;
  droneCode?: string;
  droneColor?: string;
  aiModelCode?: string | null;
  gridColumn?: number;
  ratio?: string; // Aspect ratio like '16:9', '4:3', etc.
}

const AIStreamView: React.FC<AIStreamViewProps> = ({
  streamUrl,
  width = '100%',
  height = '100%',
  label = 'AI Stream',
  gridColumn = 1,
  droneCode,
  droneColor = '#0CBA47',
  aiModelCode,
  ratio = '16:9',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const videoContainerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 450 });
  const [currentMode, setCurrentMode] = useState<
    'draw' | 'capture' | 'record' | 'ai' | null
  >(null);
  const [isStreamingAI] = useState(true); // AIStreamView is always streaming AI

  // Calculate aspect ratio dimensions (same as DroneCameraView)
  const getAspectRatioDimensions = useCallback(
    (containerWidth: number, containerHeight: number) => {
      const [widthRatio, heightRatio] = ratio.split(':').map(Number);
      const aspectRatio = widthRatio / heightRatio;

      let videoWidth, videoHeight;

      if (containerWidth / containerHeight > aspectRatio) {
        // Container is wider than video ratio - fit to height
        videoHeight = containerHeight;
        videoWidth = containerHeight * aspectRatio;
      } else {
        // Container is taller than video ratio - fit to width
        videoWidth = containerWidth;
        videoHeight = containerWidth / aspectRatio;
      }

      return { width: videoWidth, height: videoHeight };
    },
    [ratio],
  );

  // Memoize stream URLs to prevent unnecessary re-renders
  const streamUrls = useMemo(
    () => ({
      hlsUrl: streamUrl,
      rtspUrl: streamUrl,
      webrtcUrl: streamUrl, // WebRTC can use RTSP URL
    }),
    [streamUrl],
  );

  // Dynamic stream management with memoized props
  const dynamicStream = useDynamicStream({
    streamId: 'ai-stream',
    ...streamUrls,
    initialProtocol: streamUrl.includes('.m3u8') ? 'hls' : 'webrtc', // Use WebRTC if RTSP stream is available
    autoSwitch: true, // Enable auto-switch for fallback when HLS fails
  });

  // Memoize video configuration to prevent unnecessary re-renders
  const videoConfig = useMemo(() => {
    const config = {
      hlsVideoUrl: dynamicStream.isHls ? dynamicStream.streamUrl || '' : '',
      webrtcUrl: dynamicStream.isWebRTC ? dynamicStream.streamUrl || '' : '',
      isHlsActive: dynamicStream.isHls,
      isWebRTCActive: dynamicStream.isWebRTC && !!dynamicStream.streamUrl,
    };

    return config;
  }, [dynamicStream.isHls, dynamicStream.isWebRTC, dynamicStream.streamUrl]);

  // Video setup for HLS streams
  const { videoRef } = useVideo({
    videoUrl: videoConfig.hlsVideoUrl,
    isHls: videoConfig.isHlsActive,
  });

  // WebRTC setup for RTSP streams
  const {
    videoRef: webrtcVideoRef,
    isConnected: isWebRTCConnected,
    isLoading: isWebRTCLoading,
    error: webrtcError,
  } = useWebRTC({
    rtspUrl: videoConfig.webrtcUrl,
    isActive: videoConfig.isWebRTCActive,
    isStreamingAI: true,
  });

  // Use the appropriate video ref based on stream type
  const activeVideoRef = dynamicStream.isWebRTC ? webrtcVideoRef : videoRef;

  const {
    isLoading: isLoadingRecording,
    isRecording: recordingState,
    isPaused: recordingPaused,
    formattedTime: recordingTime,
    startRecording,
    stopRecording,
    togglePause,
  } = useRecording(droneCode, aiModelCode);

  // Handlers for ActionControls
  const handleModeChange = useCallback(
    (mode: 'draw' | 'capture' | 'record' | 'ai' | null) => {
      setCurrentMode(mode);
    },
    [],
  );

  const handleCaptureFlash = useCallback(() => {
    // Flash effect for capture
    console.log('📸 Capture flash triggered');
  }, []);

  const onSaveSuccess = useCallback(() => {
    console.log('💾 Save successful');
  }, []);

  useEffect(() => {
    if (webrtcError) {
      setError(webrtcError || 'Failed to load AI stream');
    } else if (isWebRTCConnected || dynamicStream.isConnected) {
      setError(null);
    }
  }, [isWebRTCConnected, dynamicStream.isConnected, webrtcError]);

  // Update container size and calculate video dimensions
  useEffect(() => {
    const updateContainerSize = () => {
      const container = videoContainerRef.current;
      if (!container) return;

      const rect = container.getBoundingClientRect();
      const containerWidth = rect.width;
      const containerHeight = rect.height;

      if (containerWidth > 0 && containerHeight > 0) {
        const videoDimensions = getAspectRatioDimensions(
          containerWidth,
          containerHeight,
        );
        setDimensions(videoDimensions);
      }
    };

    // Initial calculation with delay to ensure container is ready
    setTimeout(() => {
      updateContainerSize();
    }, 100);

    const resizeObserver = new ResizeObserver(updateContainerSize);
    if (videoContainerRef.current) {
      resizeObserver.observe(videoContainerRef.current);
    }

    window.addEventListener('resize', updateContainerSize);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener('resize', updateContainerSize);
    };
  }, [getAspectRatioDimensions]);

  // Update dimensions when ratio changes
  useEffect(() => {
    const updateDimensionsForRatio = () => {
      const container = videoContainerRef.current;
      if (!container) return;

      const rect = container.getBoundingClientRect();
      const containerWidth = rect.width;
      const containerHeight = rect.height;

      if (containerWidth > 0 && containerHeight > 0) {
        const videoDimensions = getAspectRatioDimensions(
          containerWidth,
          containerHeight,
        );
        setDimensions(videoDimensions);
      }
    };

    const timer = setTimeout(updateDimensionsForRatio, 50);
    return () => clearTimeout(timer);
  }, [ratio, getAspectRatioDimensions]);

  // Video setup with container switching
  useEffect(() => {
    const video = activeVideoRef.current;
    if (!video || !dynamicStream.streamUrl) return;

    const targetContainer = videoContainerRef.current;
    if (targetContainer) {
      if (video.parentNode !== targetContainer) {
        targetContainer.appendChild(video);
        console.log('📺 AI Video moved to container');
      }
    }
  }, [
    dynamicStream.streamUrl,
    dynamicStream.isHls,
    dynamicStream.isWebRTC,
    activeVideoRef,
  ]);

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width,
        height,
        backgroundColor: '#000',
        borderRadius: '8px',
        overflow: 'hidden',
        boxShadow: '0 0 10px rgba(255, 107, 53, 0.3)',
      }}
    >
      {/* AI Stream Label */}
      <div
        style={{
          position: 'absolute',
          top: '1rem',
          left: '1rem',
          backgroundColor: droneColor,
          color: 'white',
          padding: '0.5rem 0.875rem',
          borderRadius: '0.5rem',
          fontSize: (gridColumn === 1 || gridColumn === 2) ? '1rem' : '0.875rem',
          fontWeight: '600',
          zIndex: 999,
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          textTransform: 'uppercase',
        }}
      >

        {label}
      </div>

      {/* Video Container */}
      <div
        ref={videoContainerRef}
        style={{
          position: 'relative',
          width: '100%',
          height: '100%',
          overflow: 'hidden',
        }}
      >
        {/* Video Element will be appended here by useEffect */}
      </div>

      {/* Video Element - Will be moved to container by useEffect */}
      <video
        ref={activeVideoRef}
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '100%',
          height: '100%',
          objectFit: 'contain', // Maintains aspect ratio, creates letterboxing
          objectPosition: 'center',
          zIndex: 1,
        }}
        autoPlay
        muted
        playsInline
        crossOrigin="anonymous"
      />

      {!recordingState && (
        <>
          <ActionControls
            currentMode={currentMode}
            isLoadingRecording={isLoadingRecording}
            recordingState={recordingState}
            startRecording={startRecording}
            stopRecording={stopRecording}
            streamMonitorCode={droneCode}
            onModeChange={handleModeChange}
            onCaptureFlash={handleCaptureFlash}
            onSaveSuccess={onSaveSuccess}
            aiModelCode={aiModelCode}
            isStreamingAI={isStreamingAI}
          />
        </>
      )}

      {/* Loading State */}
      {isWebRTCLoading && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            color: 'white',
            fontSize: '14px',
            zIndex: 5,
          }}
        >
          Loading AI Stream...
        </div>
      )}

      {/* Error State */}
      {error && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            color: '#ff6b35',
            fontSize: '12px',
            textAlign: 'center',
            zIndex: 5,
            padding: '8px',
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            borderRadius: '4px',
          }}
        >
          {error}
        </div>
      )}

      {/* Recording overlay */}
      <RecordingOverlay
        isRecording={recordingState}
        isPaused={recordingPaused}
        isLoadingRecording={isLoadingRecording}
        recordingTime={recordingTime}
        droneCode={droneCode || 'AI Stream'}
        onTogglePause={togglePause}
        onStopRecording={stopRecording}
      />
    </div>
  );
};

export default AIStreamView;
