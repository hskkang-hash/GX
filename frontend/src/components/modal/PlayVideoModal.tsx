import { Close } from '@mui/icons-material';
import { IconButton, Box, CircularProgress } from '@mui/material';
import { Modal } from 'antd';
import { useEffect, useRef, useState } from 'react';

interface PlayVideoModalProps {
  videoUrl: string;
  open: boolean;
  onClose: () => void;
}

const PlayVideoModal = ({ videoUrl, open, onClose }: PlayVideoModalProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isBuffering, setIsBuffering] = useState(true);

  const handleClose = () => {
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
    }
    setIsBuffering(true);
    onClose();
  };

  const handleVideoError = (
    e: React.SyntheticEvent<HTMLVideoElement, Event>,
  ) => {
    setIsBuffering(false);
    console.error('Video playback error:', e);
    const videoElement = e.currentTarget;
    if (videoElement.error) {
      console.error('Video error code:', videoElement.error.code);
      console.error('Video error message:', videoElement.error.message);
    }
  };

  // Play video only when enough data is buffered
  const handleCanPlay = () => {
    setIsBuffering(false);
    videoRef.current?.play().catch((error: Error) => {
      if (error.name !== 'AbortError') {
        console.error('Error playing video:', error);
      }
    });
  };

  // Show loading when video is waiting for more data
  const handleWaiting = () => setIsBuffering(true);
  const handlePlaying = () => setIsBuffering(false);

  useEffect(() => {
    if (open) {
      setIsBuffering(true);
    } else if (videoRef.current) {
      videoRef.current.pause();
    }
  }, [open]);

  // Validate video URL before rendering
  const isValidVideoUrl =
    videoUrl &&
    videoUrl !== '-' &&
    videoUrl.trim() !== '' &&
    (videoUrl.startsWith('http://') ||
      videoUrl.startsWith('https://') ||
      videoUrl.startsWith('/') ||
      videoUrl.startsWith('blob:') ||
      videoUrl.startsWith('data:'));

  return (
    <Modal
      open={open}
      onCancel={onClose}
      centered
      closable={false}
      width={'90rem'}
      height={'50rem'}
      footer={null}
      styles={{
        body: {
          border: 0,
          padding: 0,
        },
        content: {
          backgroundColor: 'transparent',
          padding: 0,
          boxShadow: 'none',
        },
      }}
    >
      <Box
        sx={{
          width: '100%',
          height: '100%',
          bgcolor: 'transparent',
          outline: 'none',
          padding: 0,
          position: 'relative',
        }}
      >
        <IconButton
          onClick={handleClose}
          sx={{
            position: 'absolute',
            top: '-10%',
            right: '-100px',
            color: 'white',
            zIndex: 1,
          }}
        >
          <Close />
        </IconButton>
        {isValidVideoUrl ? (
          <>
            {isBuffering && (
              <Box
                sx={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  zIndex: 2,
                }}
              >
                <CircularProgress sx={{ color: 'white' }} />
              </Box>
            )}
            <video
              ref={videoRef}
              controls
              preload="auto"
              src={videoUrl}
              onCanPlay={handleCanPlay}
              onWaiting={handleWaiting}
              onPlaying={handlePlaying}
              onError={handleVideoError}
              style={{ width: '100%', borderRadius: '8px' }}
            />
          </>
        ) : (
          <Box
            sx={{
              width: '100%',
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '2rem',
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              borderRadius: '8px',
              color: 'white',
            }}
          >
            <p>Video not available or format not supported.</p>
            <p style={{ marginTop: '1rem', fontSize: '0.9rem', opacity: 0.8 }}>
              Please check the video URL or try a different format.
            </p>
          </Box>
        )}
      </Box>
    </Modal>
  );
};

export default PlayVideoModal;
