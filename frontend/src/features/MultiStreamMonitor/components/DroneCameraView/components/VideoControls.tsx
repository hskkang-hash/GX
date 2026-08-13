import React from 'react';
import { Spinner } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import { BsCamera, BsCameraVideo, BsStopFill } from 'react-icons/bs';

interface VideoControlsProps {
  isRecording: boolean;
  onToggleRecording: () => void;
  onCaptureFrame: () => void;
}

export const VideoControls: React.FC<VideoControlsProps> = ({
  isRecording,
  onToggleRecording,
  onCaptureFrame,
}) => {
  const { t } = useTranslation();
  return (
    <div
      style={{
        position: 'absolute',
        bottom: '1rem',
        right: '1rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        zIndex: 2000,
      }}
    >
      {/* Capture Frame Button */}
      <button
        onClick={onCaptureFrame}
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
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'scale(1.05)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
        }}
        title={t('Capture Frame')}
      >
        <BsCamera />
      </button>

      {/* Record Button */}
      <button
        onClick={onToggleRecording}
        style={{
          width: '32px',
          height: '32px',
          backgroundColor: isRecording ? '#EF4444' : 'rgba(255, 255, 255, 0.9)',
          color: isRecording ? 'white' : '#374151',
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
        onMouseEnter={(e) => {
          if (!isRecording) {
            e.currentTarget.style.transform = 'scale(1.05)';
          }
        }}
        onMouseLeave={(e) => {
          if (!isRecording) {
            e.currentTarget.style.transform = 'scale(1)';
          }
        }}
        title={isRecording ? t('Stop Recording') : t('Start Recording')}
      >
        {isRecording ? <BsStopFill /> : <BsCameraVideo />}
      </button>
    </div>
  );
};
