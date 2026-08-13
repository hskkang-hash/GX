import React, { useState } from 'react';
import { Spinner } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import { BsCameraVideo } from 'react-icons/bs';
import { useLoadingContext } from 'rj-core';

interface RecordActionBtnProps {
  currentMode: 'draw' | 'capture' | 'record' | 'ai' | null;
  isRecording: boolean;
  isLoadingRecording?: boolean;
  onModeChange: (mode: 'draw' | 'capture' | 'record' | 'ai' | null) => void;
  onToggleRecording: () => void;
}

export const RecordActionBtn: React.FC<RecordActionBtnProps> = ({
  currentMode,
  isRecording,
  isLoadingRecording = false,
  onModeChange,
  onToggleRecording,
}) => {

  console.log('isLoadingRecording', isLoadingRecording);
  const { t } = useTranslation();
  const handleRecordClick = () => {

    if (currentMode === 'record') {
      // Exit record mode
      onModeChange(null);
    } else {
      // Enter record mode
      onModeChange('record');
    }
    onToggleRecording();
  };

  return (
    <>
      {/* Record Button (normal state) */}
      <button
        onClick={handleRecordClick}
        style={{
          width: '32px',
          height: '32px',
          backgroundColor: 'rgba(255, 255, 255, 0.9)',
          color: '#374151',
          border: 'none',
          borderRadius: '50%',
          cursor: 'pointer',
          fontSize: '18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all 0.3s ease',
          boxShadow: '0 4px 16px rgba(0, 0, 0, 0.15)',
          backdropFilter: 'blur(8px)',
        }}
        disabled={isLoadingRecording}
        onMouseEnter={(e) => {
          if (currentMode !== 'record' && !isRecording) {
            e.currentTarget.style.transform = 'scale(1.05)';
          }
        }}
        onMouseLeave={(e) => {
          if (currentMode !== 'record' && !isRecording) {
            e.currentTarget.style.transform = 'scale(1)';
          }
        }}
        title={isRecording ? t('Stop Recording') : t('Start Recording')}
      >
        {isLoadingRecording ? <Spinner /> : <BsCameraVideo />}

      </button>

      <style>{`
        @keyframes pulse {
          0% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
          100% {
            opacity: 1;
          }
        }
      `}</style>
    </>
  );
};
