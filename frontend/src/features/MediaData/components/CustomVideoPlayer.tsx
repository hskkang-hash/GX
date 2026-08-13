import { CircularProgress } from '@mui/material';
import { useCallback, useEffect, useRef, useState } from 'react';
import { BsPlayFill, BsPauseFill } from 'react-icons/bs';
import { MdFullscreen, MdFullscreenExit } from 'react-icons/md';

import './CustomVideoPlayer.scss';

interface CustomVideoPlayerProps {
  videoUrl: string;
  onError?: (error: Error) => void;
}

export const CustomVideoPlayer = ({
  videoUrl,
  onError,
}: CustomVideoPlayerProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isBuffering, setIsBuffering] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isHovered, setIsHovered] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showControls, setShowControls] = useState(false);
  const controlsTimeoutRef = useRef<NodeJS.Timeout>();

  // Format time to MM:SS
  const formatTime = useCallback((seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }, []);

  // Handle play/pause
  const togglePlayPause = useCallback(() => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
    }
  }, [isPlaying]);

  // Handle fullscreen
  const toggleFullscreen = useCallback(() => {
    if (!wrapperRef.current) return;

    if (!isFullscreen) {
      if (wrapperRef.current.requestFullscreen) {
        wrapperRef.current.requestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
  }, [isFullscreen]);

  // Handle time update
  const handleTimeUpdate = useCallback(() => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  }, []);

  // Handle duration change
  const handleDurationChange = useCallback(() => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration || 0);
    }
  }, []);

  // Handle video events
  const handleCanPlay = useCallback(() => {
    setIsBuffering(false);
  }, []);

  const handleWaiting = useCallback(() => {
    setIsBuffering(true);
  }, []);

  const handlePlaying = useCallback(() => {
    setIsPlaying(true);
    setIsBuffering(false);
  }, []);

  const handlePause = useCallback(() => {
    setIsPlaying(false);
  }, []);

  const handleError = useCallback(
    (e: React.SyntheticEvent<HTMLVideoElement, Event>) => {
      setIsBuffering(false);
      const videoElement = e.currentTarget;
      if (videoElement.error) {
        const error = new Error(
          `Video error: ${videoElement.error.message || 'Unknown error'}`,
        );
        onError?.(error);
      }
    },
    [onError],
  );

  // Handle progress bar click
  const handleProgressClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!videoRef.current || !wrapperRef.current) return;

      const progressBar = e.currentTarget;
      const rect = progressBar.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const percentage = clickX / rect.width;
      const newTime = percentage * duration;

      videoRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    },
    [duration],
  );

  // Show controls on hover
  const handleMouseEnter = useCallback(() => {
    setIsHovered(true);
    setShowControls(true);
    if (controlsTimeoutRef.current) {
      clearTimeout(controlsTimeoutRef.current);
    }
  }, []);

  const handleMouseLeave = useCallback(() => {
    setIsHovered(false);
    // Hide controls after 2 seconds of no hover
    controlsTimeoutRef.current = setTimeout(() => {
      setShowControls(false);
    }, 200);
  }, []);

  const handleMouseMove = useCallback(() => {
    if (!isHovered) {
      setIsHovered(true);
      setShowControls(true);
    }
    if (controlsTimeoutRef.current) {
      clearTimeout(controlsTimeoutRef.current);
    }
    controlsTimeoutRef.current = setTimeout(() => {
      if (!isHovered) {
        setShowControls(false);
      }
    }, 500);
  }, [isHovered]);

  // Handle fullscreen change
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, []);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (controlsTimeoutRef.current) {
        clearTimeout(controlsTimeoutRef.current);
      }
    };
  }, []);

  const progressPercentage = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div
      ref={wrapperRef}
      className="custom-video-player-wrapper"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onMouseMove={handleMouseMove}
    >
      <video
        ref={videoRef}
        className="custom-video-player"
        src={videoUrl}
        preload="auto"
        onTimeUpdate={handleTimeUpdate}
        onDurationChange={handleDurationChange}
        onLoadedMetadata={(e) => {
          // Adjust wrapper to fit video aspect ratio
          const video = e.currentTarget;
          if (video.videoWidth && video.videoHeight) {
            const aspectRatio = video.videoWidth / video.videoHeight;
            if (wrapperRef.current) {
              wrapperRef.current.style.aspectRatio = `${aspectRatio}`;
            }
          }
        }}
        onCanPlay={handleCanPlay}
        onWaiting={handleWaiting}
        onPlaying={handlePlaying}
        onPause={handlePause}
        onError={handleError}
      />

      {/* Loading indicator */}
      {isBuffering && (
        <div className="video-loading">
          <CircularProgress
            sx={{ color: 'white' }}
            size={40}
          />
        </div>
      )}

      {/* Custom controls overlay */}
      <div className={`video-controls-overlay ${true ? 'visible' : ''}`}>
        {/* Controls bar */}
        <div className="video-controls-bar">
          {/* Progress bar */}
          <div
            className="progress-bar-container"
            onClick={handleProgressClick}
          >
            <div className="progress-bar-background">
              <div
                className="progress-bar-fill"
                style={{ width: `${progressPercentage}%` }}
              />
              <div
                className="progress-bar-handle"
                style={{ left: `${progressPercentage}%` }}
              />
            </div>
          </div>

          <div className="video-controls-bar-buttons">
            {/* Play/Pause button */}
            <button
              className="control-button play-button"
              onClick={togglePlayPause}
              aria-label={isPlaying ? 'Pause' : 'Play'}
            >
              {isPlaying ? <BsPauseFill size={20} /> : <BsPlayFill size={20} />}
            </button>

            {/* Duration display */}
            <div className="duration-display">
              {formatTime(currentTime)} / {formatTime(duration)}
            </div>

            {/* Fullscreen button */}
            <button
              className="control-button fullscreen-button"
              onClick={toggleFullscreen}
              aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
            >
              {isFullscreen ? (
                <MdFullscreenExit size={20} />
              ) : (
                <MdFullscreen size={20} />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
