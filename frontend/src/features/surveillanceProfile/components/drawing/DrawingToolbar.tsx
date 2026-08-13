import { Box } from '@mui/material';
import React, { JSX } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import { useDrawingModeStore } from '@/features/surveillanceProfile/stores/drawingModeStore';
import { DrawingMode } from './types';

type CustomButtonProps = {
  children: React.ReactNode;
  isActive: boolean;
  onClick: () => void;
  type?: 'button' | 'submit' | 'reset';
  theme?: 'light' | 'dark';
};

const CustomButton = ({
  children,
  isActive,
  onClick,
  type = 'button',
  theme = 'light',
}: CustomButtonProps): JSX.Element => (
  <button
    type={type}
    onClick={onClick}
    style={{
      backgroundColor: isActive
        ? 'var(--ga-primary)'
        : theme === 'dark'
          ? '#1F2937'
          : '#fff',
      color: isActive
        ? '#fff'
        : theme === 'dark'
          ? '#fff'
          : 'var(--ga-primary)',
      border:
        theme === 'dark' ? '1px solid #444646' : '1px solid var(--ga-primary)',
      padding: '0.5rem 1rem',
      cursor: 'pointer',
      fontSize: '1rem',
      fontWeight: 600,
      letterSpacing: '0.01rem',
      borderRadius: '0.504em',
      whiteSpace: 'nowrap',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      transition: 'all 0.2s ease',
    }}
    onMouseEnter={(e) => {
      if (!isActive) {
        e.currentTarget.style.backgroundColor =
          theme === 'dark' ? '#1F2937' : '#fff';
        e.currentTarget.style.color =
          theme === 'dark' ? '#fff' : 'var(--ga-primary)';
      }
    }}
    onMouseLeave={(e) => {
      if (!isActive) {
        e.currentTarget.style.backgroundColor =
          theme === 'dark' ? '#1F2937' : '#fff';
        e.currentTarget.style.color =
          theme === 'dark' ? '#fff' : 'var(--ga-primary)';
      }
    }}
  >
    {children}
  </button>
);

type DrawingToolbarProps = {
  drawingMode: DrawingMode;
  handleDrawingModeChange: (mode: DrawingMode) => void;
  handleClearDrawing: () => void;
};

export const DrawingToolbar = ({
  drawingMode,
  handleDrawingModeChange,
  handleClearDrawing,
}: DrawingToolbarProps) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const setWaypointsList = useDrawingModeStore(
    (state) => state.setWaypointsList,
  );
  const setCurrentShape = useDrawingModeStore((state) => state.setCurrentShape);

  const drawingModes: { mode: DrawingMode; label: string }[] = [
    { mode: 'LINE', label: t('Line') },
    { mode: 'POLYGON', label: t('Polygon') },
    { mode: 'CIRCULAR', label: t('Circular') },
    { mode: 'TRACE', label: t('Trace') },
  ];

  return (
    <Box
      style={{
        position: 'absolute',
        top: 8,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 1000,
        display: 'flex',
        backgroundColor: theme === 'dark' ? '#2D2E30' : '#FFFFFF',
        backdropFilter: 'blur(4px)',
        padding: '0.5rem',
        borderRadius: '0.5rem',
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.1)',
        border: `1px solid ${theme === 'dark' ? '#444646' : '#DDDFE2'}`,
        gap: 8,
      }}
    >
      {drawingModes.map(({ mode, label }) => (
        <CustomButton
          key={mode}
          isActive={drawingMode === mode}
          theme={theme as 'light' | 'dark'}
          onClick={() => {
            setCurrentShape(null);
            setWaypointsList([]);
            handleDrawingModeChange(mode);
          }}
        >
          {label}
        </CustomButton>
      ))}
      {/* <CustomButton
        isActive={false}
        theme={theme as 'light' | 'dark'}
        onClick={() => {
          handleClearDrawing();
        }}
      >
        {t('Clear')}
      </CustomButton> */}
    </Box>
  );
};
