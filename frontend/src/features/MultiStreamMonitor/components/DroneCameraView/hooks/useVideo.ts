import Hls from 'hls.js';
import { useRef, useEffect } from 'react';

interface UseVideoProps {
  videoUrl: string;
  isHls: boolean;
}

export const useVideo = ({ videoUrl, isHls }: UseVideoProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !videoUrl) return;

    // Optimize video element for better performance
    const optimizeVideoElement = (videoElement: HTMLVideoElement) => {
      videoElement.preload = 'none'; // Don't preload to save bandwidth
      videoElement.playsInline = true; // Enable inline playback on mobile
      videoElement.muted = true; // Mute to avoid autoplay issues
      videoElement.crossOrigin = 'anonymous'; // Enable CORS

      // Force GPU acceleration for better performance
      videoElement.style.willChange = 'transform';
      videoElement.style.transform = 'translateZ(0)';
      videoElement.style.backfaceVisibility = 'hidden';
      videoElement.style.perspective = '1000px';

      // Ensure video fills container completely
      videoElement.style.width = '100%';
      videoElement.style.height = '100%';
      videoElement.style.objectFit = 'cover';
      videoElement.style.objectPosition = 'center';
      videoElement.style.position = 'absolute';
      videoElement.style.top = '50%';
      videoElement.style.left = '50%';
      videoElement.style.transform = 'translate(-50%, -50%)';
      videoElement.style.zIndex = '1';
    };

    // Apply optimizations
    optimizeVideoElement(video);

    const handleVideoReady = () => {
      console.log('📺 Video ready');
    };

    const handleVideoError = (event: Event) => {
      console.error('❌ Video error:', event);
    };

    const handleVideoLoadStart = () => {
      console.log('🔄 Video load started');
    };

    const handleVideoCanPlay = () => {
      console.log('▶️ Video can play');
    };

    // Add optimized event listeners
    video.addEventListener('loadedmetadata', handleVideoReady);
    video.addEventListener('error', handleVideoError);
    video.addEventListener('loadstart', handleVideoLoadStart);
    video.addEventListener('canplay', handleVideoCanPlay);

    if (isHls && videoUrl.includes('.m3u8')) {
      if (Hls.isSupported()) {
        if (hlsRef.current) {
          console.log('🧹 Destroying existing HLS instance');
          hlsRef.current.destroy();
        }

        // HLS.js configuration to prevent memory leaks - OPTIMIZED
        const hlsConfig = {
          // Minimal buffer settings to prevent memory accumulation
          maxBufferLength: 3, // Max 3 seconds buffer
          maxMaxBufferLength: 5, // Hard limit 5 seconds
          backBufferLength: 2, // Only keep 2 seconds in back buffer (was 90!)
          maxBufferSize: 2 * 1000 * 1000, // 2MB max buffer size
          maxBufferHole: 0.05, // Reduced from 0.1 to 0.05 for better performance
          highBufferWatchdogPeriod: 1, // Check buffer every 1 second

          // Live streaming optimizations - ENHANCED
          liveSyncDurationCount: 0.5, // Faster sync to live edge
          liveMaxLatencyDurationCount: 2, // Max 2 segments latency
          liveDurationInfinity: false,
          liveBackBufferLength: 1, // Only keep 1 second back buffer for live

          // Fragment loading - OPTIMIZED timeouts
          fragLoadingTimeOut: 3000, // Reduced from 5000 to 3000ms
          fragLoadingMaxRetry: 1, // Reduced from 2 to 1 retry
          fragLoadingRetryDelay: 200, // Reduced from 500 to 200ms
          fragLoadingMaxRetryDelay: 500, // Max 500ms retry delay

          // Manifest loading - OPTIMIZED timeouts
          manifestLoadingTimeOut: 3000, // Reduced from 5000 to 3000ms
          manifestLoadingMaxRetry: 1, // Reduced from 2 to 1 retry
          manifestLoadingRetryDelay: 200, // Reduced from 500 to 200ms
          manifestLoadingMaxRetryDelay: 500, // Max 500ms retry delay

          // Level loading - OPTIMIZED timeouts
          levelLoadingTimeOut: 3000, // Reduced from 5000 to 3000ms
          levelLoadingMaxRetry: 1, // Reduced from 2 to 1 retry
          levelLoadingRetryDelay: 200, // Reduced from 500 to 200ms
          levelLoadingMaxRetryDelay: 500, // Max 500ms retry delay

          // Bandwidth optimization - ENHANCED settings
          abrEwmaDefaultEstimate: 100000, // Lower default estimate
          abrBandWidthFactor: 0.8, // More conservative bandwidth usage
          abrBandWidthUpFactor: 0.5, // More conservative up factor
          abrMaxWithRealBitrate: false, // Disable to save memory
          abrEwmaFastLive: 3.0, // Faster adaptive bitrate for live
          abrEwmaSlowLive: 9.0, // Reduced latency for adaptive bitrate

          // Additional memory leak prevention - ENHANCED
          maxStarvationDelay: 500, // Reduced from 1000 to 500ms
          maxLoadingDelay: 500, // Reduced from 1000 to 500ms

          // Disable features that consume memory
          enableDateRangeMetadataCues: false,
          enableEmsgMetadataCues: false,
          enableID3MetadataCues: false,
          enableWebVTT: false,
          enableIMSC1: false,
          enableCEA708Captions: false,

          // Worker settings - ENHANCED
          enableWorker: true,
          lowLatencyMode: true,

          // Additional performance optimizations
          maxFragLookUpTolerance: 0.2, // Faster fragment lookup
        };

        console.log('🔧 Initializing HLS.js with memory-optimized config');
        const hls = new Hls(hlsConfig);
        hlsRef.current = hls;

        hls.loadSource(videoUrl);
        hls.attachMedia(video);

        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          console.log('📋 HLS.js manifest parsed');
          video.play().catch((e) => console.log('Auto-play prevented:', e));
        });

        hls.on(Hls.Events.ERROR, (event, data) => {
          console.error('❌ HLS.js error:', data);
          if (data.fatal) {
            switch (data.type) {
              case Hls.ErrorTypes.NETWORK_ERROR:
                console.log('🔄 Attempting to recover from network error');
                // Enhanced network error recovery
                if (data.details === Hls.ErrorDetails.MANIFEST_LOAD_ERROR) {
                  console.log(
                    '🔄 Manifest load error, retrying with shorter timeout',
                  );
                  // Retry with shorter timeout
                  setTimeout(() => {
                    hls.startLoad();
                  }, 1000);
                } else if (data.details === Hls.ErrorDetails.FRAG_LOAD_ERROR) {
                  console.log(
                    '🔄 Fragment load error, skipping problematic fragment',
                  );
                  // Skip problematic fragment and continue
                  hls.startLoad();
                } else {
                  hls.startLoad();
                }
                break;
              case Hls.ErrorTypes.MEDIA_ERROR:
                console.log('🔄 Attempting to recover from media error');
                // Enhanced media error recovery
                if (data.details === Hls.ErrorDetails.FRAG_LOAD_ERROR) {
                  console.log(
                    '🔄 Fragment decode error, attempting media recovery',
                  );
                  hls.recoverMediaError();
                } else {
                  console.log('🔄 Fragment parsing error, skipping fragment');
                  hls.recoverMediaError();
                }
                break;
              default:
                console.log('💥 Fatal error, destroying HLS instance');
                // Enhanced fatal error handling
                try {
                  hls.destroy();
                  // Recreate HLS instance with optimized config after delay
                  setTimeout(() => {
                    console.log('🔄 Recreating HLS instance after fatal error');
                    const newHls = new Hls(hlsConfig);
                    hlsRef.current = newHls;
                    newHls.loadSource(videoUrl);
                    newHls.attachMedia(video);
                  }, 2000);
                } catch (error) {
                  console.error('Error during HLS recovery:', error);
                }
                break;
            }
          } else {
            // Handle non-fatal errors
            console.log('⚠️ Non-fatal HLS error:', data.details);
            if (data.details === Hls.ErrorDetails.FRAG_LOAD_TIMEOUT) {
              console.log('⏰ Fragment load timeout, continuing...');
            } else if (
              data.details === Hls.ErrorDetails.MANIFEST_LOAD_TIMEOUT
            ) {
              console.log('⏰ Manifest load timeout, continuing...');
            }
          }
        });
      } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        video.src = videoUrl;
      }
    } else {
      video.src = videoUrl;
    }

    return () => {
      // Cleanup all event listeners
      video.removeEventListener('loadedmetadata', handleVideoReady);
      video.removeEventListener('error', handleVideoError);
      video.removeEventListener('loadstart', handleVideoLoadStart);
      video.removeEventListener('canplay', handleVideoCanPlay);

      // Cleanup HLS instance on unmount
      if (hlsRef.current) {
        console.log('🧹 Cleaning up HLS.js instance on unmount');
        try {
          hlsRef.current.destroy();
          hlsRef.current = null;
        } catch (error) {
          console.log('HLS cleanup error:', error);
        }
      }

      // Additional video element cleanup
      try {
        // Clear video source
        video.srcObject = null;
        video.src = '';
        video.load();

        // Reset video element styles
        video.style.willChange = 'auto';
        video.style.transform = 'none';
        video.style.backfaceVisibility = 'visible';
        video.style.perspective = 'none';
      } catch (error) {
        console.log('Video element cleanup error:', error);
      }
    };
  }, [videoUrl, isHls]);

  return { videoRef, hlsRef };
};
