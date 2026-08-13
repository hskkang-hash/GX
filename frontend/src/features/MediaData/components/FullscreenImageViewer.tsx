import {
  Add,
  Close,
  Remove,
  ZoomIn,
  ZoomOut,
  ZoomOutMap,
} from '@mui/icons-material';
import { Box, IconButton } from '@mui/material';
import { Modal } from 'antd';
import { useCallback, useMemo, useState } from 'react';

interface FullscreenImageViewerProps {
  open: boolean;
  onClose: () => void;
  imageUrl: string;
  imageName: string;
}

/**
 * Fullscreen image viewer with zoom controls
 * - Header with filename and close button
 * - Zoomable image (25% - 300%)
 * - Bottom zoom controls (zoom out, reset, zoom in)
 */
export const FullscreenImageViewer = ({
  open,
  onClose,
  imageUrl,
  imageName,
}: FullscreenImageViewerProps) => {
  const [zoomLevel, setZoomLevel] = useState<number>(100);

  const handleClose = useCallback(() => {
    onClose();
    setZoomLevel(100);
  }, [onClose]);

  const handleZoomIn = useCallback(() => {
    setZoomLevel((prev) => Math.min(prev + 25, 300));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoomLevel((prev) => Math.max(prev - 25, 25));
  }, []);

  const handleResetZoom = useCallback(() => {
    setZoomLevel(100);
  }, []);

  // Determine reset icon based on zoom level
  // Zoomed in (>100%) → ZoomOut, Zoomed out (<100%) → ZoomIn, Normal (100%) → ZoomOutMap
  const ResetZoomIcon = useMemo(() => {
    if (zoomLevel > 100) return ZoomOut;
    if (zoomLevel < 100) return ZoomIn;
    return ZoomOutMap;
  }, [zoomLevel]);

  return (
    <Modal
      open={open}
      onCancel={handleClose}
      centered
      closable={false}
      width="100vw"
      footer={null}
      styles={{
        body: {
          border: 0,
          padding: 0,
          height: '100vh',
        },
        content: {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          padding: 0,
          boxShadow: 'none',
          borderRadius: 0,
          height: '100vh',
          maxWidth: '100vw',
        },
        wrapper: {
          overflow: 'hidden',
        },
      }}
      style={{ top: 0, padding: 0, maxWidth: '100vw' }}
    >
      <Box
        sx={{
          width: '100%',
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Header with filename and close button */}
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            padding: '12px 16px',
            position: 'relative',
          }}
        >
          <span
            style={{
              color: 'white',
              fontSize: '14px',
              fontWeight: 400,
            }}
          >
            {imageName}
          </span>
          <IconButton
            onClick={handleClose}
            sx={{
              position: 'absolute',
              right: 16,
              color: 'white',
              '&:hover': {
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
              },
            }}
          >
            <Close />
          </IconButton>
        </Box>

        {/* Image container */}
        <Box
          sx={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'auto',
            padding: '16px',
          }}
        >
          <img
            src={imageUrl}
            alt={imageName}
            style={{
              maxWidth: '100%',
              maxHeight: '100%',
              objectFit: 'contain',
              transform: `scale(${zoomLevel / 100})`,
              transition: 'transform 0.2s ease',
            }}
          />
        </Box>

        {/* Zoom controls */}
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            padding: '12px',
            gap: '4px',
          }}
        >
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              backgroundColor: '#141414',
              borderRadius: '20px',
              overflow: 'hidden',
            }}
          >
            <IconButton
              onClick={handleZoomOut}
              disabled={zoomLevel <= 25}
              sx={{
                color: 'white',
                borderRadius: 0,
                padding: '8px 12px',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.1)',
                },
                '&.Mui-disabled': {
                  color: 'rgba(255, 255, 255, 0.3)',
                },
              }}
            >
              <Remove fontSize="small" />
            </IconButton>
            <IconButton
              onClick={handleResetZoom}
              disabled={zoomLevel === 100}
              sx={{
                color: 'white',
                borderRadius: 0,
                padding: '8px 12px',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.1)',
                },
                '&.Mui-disabled': {
                  color: 'rgba(255, 255, 255, 0.3)',
                },
              }}
            >
              <ResetZoomIcon fontSize="small" />
            </IconButton>
            <IconButton
              onClick={handleZoomIn}
              disabled={zoomLevel >= 300}
              sx={{
                color: 'white',
                borderRadius: 0,
                padding: '8px 12px',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.1)',
                },
                '&.Mui-disabled': {
                  color: 'rgba(255, 255, 255, 0.3)',
                },
              }}
            >
              <Add fontSize="small" />
            </IconButton>
          </Box>
        </Box>
      </Box>
    </Modal>
  );
};
