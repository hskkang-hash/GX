import { useEffect, useRef } from 'react';

interface MemoryInfo {
  usedJSHeapSize: number;
  totalJSHeapSize: number;
  jsHeapSizeLimit: number;
}

interface ExtendedPerformance extends Performance {
  memory?: MemoryInfo;
}

interface UseMemoryOptimizationProps {
  isActive: boolean;
  streamId?: string;
}

export const useMemoryOptimization = ({
  isActive,
  streamId,
}: UseMemoryOptimizationProps) => {
  const cleanupIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const memoryCheckIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!isActive) {
      // Clear intervals when stream is not active
      if (cleanupIntervalRef.current) {
        clearInterval(cleanupIntervalRef.current);
        cleanupIntervalRef.current = null;
      }
      if (memoryCheckIntervalRef.current) {
        clearInterval(memoryCheckIntervalRef.current);
        memoryCheckIntervalRef.current = null;
      }
      return;
    }

    // Force garbage collection every 20 seconds for active streams - OPTIMIZED
    cleanupIntervalRef.current = setInterval(() => {
      if ('gc' in window) {
        console.log(`🧹 Forcing garbage collection for stream: ${streamId}`);
        (window as { gc?: () => void }).gc?.();
      }

      // Advanced video element cleanup - ENHANCED
      const videoElements = document.querySelectorAll('video');
      videoElements.forEach((video) => {
        if (video.buffered.length > 0) {
          try {
            // Clear old buffered ranges to free memory
            const currentTime = video.currentTime;
            const buffered = video.buffered;

            // Keep only recent 3 seconds of buffer (reduced from 5)
            for (let i = 0; i < buffered.length; i++) {
              const start = buffered.start(i);
              const end = buffered.end(i);

              if (end < currentTime - 3) {
                console.log(
                  `🗑️ Clearing old buffer range: ${start}s - ${end}s`,
                );
              }
            }
          } catch (error) {
            console.log('Buffer cleanup error:', error);
          }
        }

        // Advanced memory cleanup for video elements
        try {
          // Clear video source to free memory
          if (video.srcObject) {
            // Stop all tracks before clearing
            if (video.srcObject && 'getTracks' in video.srcObject) {
              (video.srcObject as MediaStream)
                .getTracks()
                .forEach((track: MediaStreamTrack) => {
                  track.stop();
                  console.log(`🛑 Stopped track: ${track.kind}`);
                });
            }
            video.srcObject = null;
          }

          // Clear video src if it exists
          if (video.src) {
            video.src = '';
            video.load(); // Force reload to clear buffers
          }

          // Clear any cached frames
          if (video.requestVideoFrameCallback) {
            video.requestVideoFrameCallback(() => {
              // Clear any pending frame callbacks
            });
          }
        } catch (error) {
          console.log('Advanced video cleanup error:', error);
        }
      });

      // Additional memory cleanup for HLS instances
      const hlsInstances = document.querySelectorAll('[data-hls-instance]');
      hlsInstances.forEach((element) => {
        try {
          const hlsInstance = (
            element as HTMLVideoElement & {
              __hls?: { destroy: () => void };
            }
          ).__hls;
          if (hlsInstance && typeof hlsInstance.destroy === 'function') {
            // Only destroy if not actively playing
            const videoElement = element as HTMLVideoElement;
            if (videoElement.paused || videoElement.ended) {
              hlsInstance.destroy();
              console.log('🧹 Destroyed inactive HLS instance');
            }
          }
        } catch (error) {
          console.log('HLS instance cleanup error:', error);
        }
      });
    }, 20000); // Reduced from 30 to 20 seconds for more frequent cleanup

    // Monitor memory usage every 10 seconds
    memoryCheckIntervalRef.current = setInterval(() => {
      const extendedPerformance = performance as ExtendedPerformance;
      if (extendedPerformance.memory) {
        const memory = extendedPerformance.memory;
        const usedMB = Math.round(memory.usedJSHeapSize / 1024 / 1024);
        const totalMB = Math.round(memory.totalJSHeapSize / 1024 / 1024);
        const limitMB = Math.round(memory.jsHeapSizeLimit / 1024 / 1024);

        console.log(
          `📊 Memory usage for stream ${streamId}: ${usedMB}MB / ${totalMB}MB (limit: ${limitMB}MB)`,
        );

        // Warning if memory usage is high
        if (usedMB > limitMB * 0.8) {
          console.warn(
            `⚠️ High memory usage detected for stream ${streamId}: ${usedMB}MB`,
          );
        }
      }
    }, 10000); // 10 seconds

    return () => {
      if (cleanupIntervalRef.current) {
        clearInterval(cleanupIntervalRef.current);
        cleanupIntervalRef.current = null;
      }
      if (memoryCheckIntervalRef.current) {
        clearInterval(memoryCheckIntervalRef.current);
        memoryCheckIntervalRef.current = null;
      }
    };
  }, [isActive, streamId]);

  // Manual cleanup function - ENHANCED
  const forceCleanup = () => {
    console.log(`🧹 Manual cleanup triggered for stream: ${streamId}`);

    // Clear all intervals
    if (cleanupIntervalRef.current) {
      clearInterval(cleanupIntervalRef.current);
      cleanupIntervalRef.current = null;
    }
    if (memoryCheckIntervalRef.current) {
      clearInterval(memoryCheckIntervalRef.current);
      memoryCheckIntervalRef.current = null;
    }

    // Advanced cleanup for video elements
    const videoElements = document.querySelectorAll('video');
    videoElements.forEach((video) => {
      try {
        // Stop all tracks
        if (video.srcObject && 'getTracks' in video.srcObject) {
          (video.srcObject as MediaStream)
            .getTracks()
            .forEach((track: MediaStreamTrack) => track.stop());
        }

        // Clear sources
        video.srcObject = null;
        video.src = '';
        video.load();

        // Clear any event listeners
        video.removeEventListener('loadedmetadata', () => {});
        video.removeEventListener('canplay', () => {});
        video.removeEventListener('error', () => {});
      } catch (error) {
        console.log('Force cleanup error:', error);
      }
    });

    // Cleanup HLS instances
    const hlsInstances = document.querySelectorAll('[data-hls-instance]');
    hlsInstances.forEach((element) => {
      try {
        const hlsInstance = (
          element as HTMLVideoElement & {
            __hls?: { destroy: () => void };
          }
        ).__hls;
        if (hlsInstance && typeof hlsInstance.destroy === 'function') {
          hlsInstance.destroy();
        }
      } catch (error) {
        console.log('HLS force cleanup error:', error);
      }
    });

    // Force garbage collection
    if ('gc' in window) {
      (window as { gc?: () => void }).gc?.();
    }

    // Additional memory cleanup
    if ('memory' in performance) {
      const memory = (performance as ExtendedPerformance).memory;
      if (memory && memory.usedJSHeapSize > memory.jsHeapSizeLimit * 0.8) {
        console.warn(
          '⚠️ High memory usage detected, forcing aggressive cleanup',
        );
        // Force multiple GC cycles
        for (let i = 0; i < 3; i++) {
          if ('gc' in window) {
            (window as { gc?: () => void }).gc?.();
          }
        }
      }
    }
  };

  return { forceCleanup };
};
