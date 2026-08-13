import { Box } from '@mui/material';
import React, { JSX } from 'react';
import { BiExitFullscreen, BiFullscreen } from 'react-icons/bi';
import { FiMinus, FiPlus } from 'react-icons/fi';
import { IoLayersOutline } from 'react-icons/io5';

const btnStyle = {
  background: '#fff',
  border: '1px solid #eee',
  borderRadius: 8,
  padding: 6,
  cursor: 'pointer',
  boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
  outline: 'none',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
};

type MapControlsProps = {
  isFullscreen: boolean;
  onToggleFullscreen: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onToggleOverlay: () => void;
  overlayType: string;
  theme: string;
};

export const MapControls = ({
  isFullscreen,
  onToggleFullscreen,
  onZoomIn,
  onZoomOut,
  onToggleOverlay,
  overlayType,
  theme,
}: MapControlsProps): JSX.Element => (
  <>
    {/* Zoom & Fullscreen Controls */}
    <Box
      style={{
        position: 'absolute',
        top: 16,
        left: 16,
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}
    >
      <Box>
        <button
          onClick={onZoomIn}
          style={{
            ...btnStyle,
            borderBottomLeftRadius: 0,
            borderBottomRightRadius: 0,
            borderBottom: 'none',
            backgroundColor: theme === 'dark' ? '#2D2E30' : '#ffffff',
            border: theme === 'dark' ? '1px solid #444646' : '1px solid #eee',
          }}
          type="button"
          title="Zoom in"
        >
          <FiPlus
            size={20}
            color={theme === 'dark' ? '#ffffff' : '#2D2E30'}
          />
        </button>
        <button
          onClick={onZoomOut}
          style={{
            ...btnStyle,
            borderTopLeftRadius: 0,
            borderTopRightRadius: 0,
            borderTop: 'none',
            backgroundColor: theme === 'dark' ? '#2D2E30' : '#ffffff',
            border: theme === 'dark' ? '1px solid #444646' : '1px solid #eee',
          }}
          type="button"
          title="Zoom out"
        >
          <FiMinus
            size={20}
            color={theme === 'dark' ? '#ffffff' : '#2D2E30'}
          />
        </button>
      </Box>
      <button
        onClick={onToggleFullscreen}
        style={{
          ...btnStyle,
          backgroundColor: theme === 'dark' ? '#2D2E30' : '#ffffff',
          border: theme === 'dark' ? '1px solid #444646' : '1px solid #eee',
        }}
        type="button"
        title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
      >
        {isFullscreen ? (
          <BiExitFullscreen
            size={20}
            color={theme === 'dark' ? '#ffffff' : '#2D2E30'}
          />
        ) : (
          <BiFullscreen
            size={20}
            color={theme === 'dark' ? '#ffffff' : '#2D2E30'}
          />
        )}
      </button>
    </Box>

    {/* Overlay Controls */}
    <Box
      style={{
        position: 'absolute',
        top: 16,
        right: 16,
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}
    >
      <Box>
        <button
          style={{
            ...btnStyle,
            backgroundColor: theme === 'dark' ? '#2D2E30' : '#ffffff',
            border: theme === 'dark' ? '1px solid #444646' : '1px solid #eee',
          }}
          onClick={onToggleOverlay}
          title={overlayType}
          type="button"
        >
          <IoLayersOutline
            size={20}
            color={theme === 'dark' ? '#ffffff' : '#2D2E30'}
          />
        </button>
      </Box>
    </Box>
  </>
);
