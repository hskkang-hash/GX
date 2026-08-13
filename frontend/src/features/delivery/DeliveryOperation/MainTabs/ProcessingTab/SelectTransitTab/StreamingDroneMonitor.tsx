import { Box, IconButton } from '@mui/material';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BsArrowLeft, BsArrowRight } from 'react-icons/bs';
import { useTheme } from 'rj-core';

import { useVideo } from '@/features/MultiStreamMonitor/components/DroneCameraView/hooks/useVideo';
import { useDynamicStream } from '@/features/MultiStreamMonitor/hooks/useDynamicStream';
import { useWebRTC } from '@/features/MultiStreamMonitor/hooks/useWebRTC';

interface OrderData {
  stream_path?: string[];
  is_use_webrtc: boolean;
  webrtc_data?: string[];
  streamming_data?: string[];
  id?: number;
  order_id?: string;
  current_status__code?: string;
  order_time?: string;
  sender?: string;
  recipient?: string;
  creator?: string;
  number_of_package?: number;
  origin?: string;
  destination?: string;
  estimated_distance?: string;
  estimated_duration?: string;
}

interface StreamingDroneMonitorProps {
  selectedOrder: OrderData;
  width?: string | number;
  height?: string | number;
}

export default function StreamingDroneMonitor({
  selectedOrder,
  width = '100%',
  height = 400,
}: StreamingDroneMonitorProps) {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [currentVideoIndex, setCurrentVideoIndex] = useState(0);
  const [dimensions, setDimensions] = useState({ width: 800, height: 450 });
  const containerRef = useRef<HTMLDivElement>(null);

  console.log('selectedOrder-------', selectedOrder);

  // Get video URLs from streaming data
  const videoUrls = selectedOrder?.is_use_webrtc
    ? selectedOrder?.stream_path || []
    : selectedOrder?.streamming_data || [];
  const currentVideoUrl = videoUrls[currentVideoIndex] || '';

  // Memoize stream URLs to prevent unnecessary re-renders
  const streamUrls = useMemo(() => {
    const isHlsStream = currentVideoUrl.includes('.m3u8');
    const isRtspStream = true;

    return {
      hlsUrl: isHlsStream ? currentVideoUrl : undefined,
      rtspUrl: isRtspStream ? currentVideoUrl : undefined,
      webrtcUrl: isRtspStream ? currentVideoUrl : undefined,
    };
  }, [currentVideoUrl]);

  // Memoize callbacks to prevent re-renders
  const onProtocolSwitch = useCallback(
    (from: string, to: string) => {
      console.log(
        `📡 StreamingDroneMonitor: Protocol switched from ${from} to ${to} for order ${selectedOrder?.order_id}`,
      );
    },
    [selectedOrder?.order_id],
  );

  const onQualityChange = useCallback(
    (quality: string) => {
      console.log(
        `📊 StreamingDroneMonitor: Quality changed to ${quality} for order ${selectedOrder?.order_id}`,
      );
    },
    [selectedOrder?.order_id],
  );

  // Dynamic stream management
  const dynamicStream = useDynamicStream({
    streamId: `order-${selectedOrder?.order_id}-video-${currentVideoIndex}`,
    ...streamUrls,
    initialProtocol: streamUrls.rtspUrl ? 'webrtc' : 'hls',
    autoSwitch: false, // Manual control for delivery operations
    onProtocolSwitch,
    onQualityChange,
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

  // WebRTC error and success callbacks (memoized)
  const onWebRTCError = useCallback(
    (error: string) => {
      dynamicStream.handleConnectionError(new Error(error));
    },
    [dynamicStream],
  );

  const onWebRTCSuccess = useCallback(() => {
    dynamicStream.handleConnectionSuccess();
  }, [dynamicStream]);

  const onWebRTCStatusChange = useCallback((status: string, type: string) => {
    console.log(`🔄 StreamingDroneMonitor WebRTC ${type}:`, status);
  }, []);

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
    startStream,
    stopStream,
  } = useWebRTC({
    rtspUrl: videoConfig.webrtcUrl,
    isActive: videoConfig.isWebRTCActive,
    onError: onWebRTCError,
    onSuccess: onWebRTCSuccess,
    onStatusChange: onWebRTCStatusChange,
  });

  // Store previous URL to detect actual changes
  const prevVideoUrlRef = useRef<string>('');

  // Force restart WebRTC connection when currentVideoUrl actually changes
  useEffect(() => {
    const prevUrl = prevVideoUrlRef.current;
    const urlChanged = prevUrl !== currentVideoUrl && prevUrl !== '';
    prevVideoUrlRef.current = currentVideoUrl;

    if (
      dynamicStream.isWebRTC &&
      currentVideoUrl &&
      urlChanged &&
      (isWebRTCConnected || isWebRTCLoading)
    ) {
      console.log(
        '🔄 StreamingDroneMonitor WebRTC URL changed, restarting connection...',
        {
          prevUrl,
          newUrl: currentVideoUrl,
          wasConnected: isWebRTCConnected,
          wasLoading: isWebRTCLoading,
          protocol: dynamicStream.currentProtocol,
        },
      );

      // Stop current connection and restart with new URL
      stopStream()
        .then(() => {
          console.log(
            '🔄 StreamingDroneMonitor WebRTC stopped, starting with new URL...',
          );
          // Start new connection after cleanup completes
          startStream().catch((error) => {
            console.error(
              '❌ StreamingDroneMonitor Error restarting WebRTC with new URL:',
              error,
            );
          });
        })
        .catch((error) => {
          console.error(
            '❌ StreamingDroneMonitor Error stopping WebRTC for URL change:',
            error,
          );
        });
    }
  }, [
    currentVideoUrl,
    dynamicStream.isWebRTC,
    dynamicStream.currentProtocol,
    isWebRTCConnected,
    isWebRTCLoading,
    stopStream,
    startStream,
  ]);

  // Use the appropriate video ref based on dynamic stream type
  const activeVideoRef = dynamicStream.isWebRTC ? webrtcVideoRef : videoRef;

  // Calculate 16:9 aspect ratio dimensions
  const getAspectRatioDimensions = useCallback(
    (containerWidth: number, containerHeight: number) => {
      const aspectRatio = 16 / 9;

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
    [],
  );

  useEffect(() => {
    setCurrentVideoIndex(0);
  }, [selectedOrder?.id, selectedOrder?.order_id, videoUrls?.length]);

  // Update dimensions when container size changes
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        const newDimensions = getAspectRatioDimensions(rect.width, rect.height);
        setDimensions(newDimensions);
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);

    return () => window.removeEventListener('resize', updateDimensions);
  }, [getAspectRatioDimensions]);

  // Navigation functions
  const goToPreviousVideo = () => {
    if (videoUrls.length > 1) {
      setCurrentVideoIndex((prev) =>
        prev === 0 ? videoUrls.length - 1 : prev - 1,
      );
    }
  };

  const goToNextVideo = () => {
    if (videoUrls.length > 1) {
      setCurrentVideoIndex((prev) =>
        prev === videoUrls.length - 1 ? 0 : prev + 1,
      );
    }
  };

  // No videos available or unsupported stream type
  if (!videoUrls.length || !dynamicStream.streamUrl) {
    return (
      <Box
        ref={containerRef}
        sx={{
          width,
          height,
          backgroundColor: theme === 'dark' ? '#1F1F20' : '#f5f5f5',
          borderRadius: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: theme === 'dark' ? '#fff' : '#666',
          fontSize: '16px',
        }}
      >
        {t('No streaming data available')}
      </Box>
    );
  }

  return (
    <Box
      ref={containerRef}
      sx={{
        width,
        height,
        position: 'relative',
        backgroundColor: '#000',
        borderRadius: 2,
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* Video Element */}
      <video
        ref={activeVideoRef}
        style={{
          width: `${dimensions.width}px`,
          height: `${dimensions.height}px`,
          objectFit: 'cover',
          objectPosition: 'center',
        }}
        autoPlay
        muted
        loop={!dynamicStream.isWebRTC}
        playsInline
        crossOrigin="anonymous"
      />

      {/* Navigation Controls */}
      {videoUrls.length > 1 && (
        <>
          <Box
            sx={{
              position: 'absolute',
              left: '50%',
              bottom: 10,
              transform: 'translateX(-50%)',
            }}
          >
            {/* Previous Button */}
            <IconButton
              onClick={goToPreviousVideo}
              sx={{
                backgroundColor: 'rgba(255, 255, 255, 0.7)',
                color: 'black',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 1)',
                },
                mx: '0.25rem',
              }}
            >
              <BsArrowLeft />
            </IconButton>

            {/* Next Button */}
            <IconButton
              onClick={goToNextVideo}
              sx={{
                backgroundColor: 'rgba(255, 255, 255, 0.7)',
                color: 'black',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 1)',
                },
                mx: '0.25rem',
              }}
            >
              <BsArrowRight />
            </IconButton>
          </Box>

          {/* Video Counter */}
          <Box
            sx={{
              position: 'absolute',
              bottom: 16,
              right: 16,
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              color: 'white',
              padding: '4px 8px',
              borderRadius: 1,
              fontSize: '12px',
              zIndex: 10,
            }}
          >
            {currentVideoIndex + 1} / {videoUrls.length}
          </Box>
        </>
      )}

      {/* Loading indicator when no video URL */}
      {!currentVideoUrl && (
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            color: 'white',
            fontSize: '14px',
          }}
        >
          {selectedOrder?.streamming_data?.length &&
          selectedOrder?.streamming_data?.length > 0
            ? t('Loading video...')
            : t('No streaming data available')}
        </Box>
      )}
    </Box>
  );
}
