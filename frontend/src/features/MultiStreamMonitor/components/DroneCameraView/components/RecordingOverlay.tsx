import React from 'react';
import { useTranslation } from 'react-i18next';
import { FaRegCirclePlay } from 'react-icons/fa6';
import { ImPause, ImStop } from 'react-icons/im';

interface RecordingOverlayProps {
  isRecording: boolean;
  isPaused: boolean;
  recordingTime: string;
  droneCode: string;
  onTogglePause: () => void;
  onStopRecording: () => void;
  isLoadingRecording?: boolean;
}

export const RecordingOverlay: React.FC<RecordingOverlayProps> = ({
  isRecording,
  isPaused,
  isLoadingRecording,
  recordingTime,
  droneCode,
  onTogglePause,
  onStopRecording,
}) => {
  const { t } = useTranslation();
  if (!isRecording) return null;

  console.log('isLoadingRecording', isLoadingRecording);

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        border: '3px solid #EF4444',
        borderRadius: '8px',
        pointerEvents: 'none',
        zIndex: 1000,
      }}
    >
      {/* Recording indicator */}
      <div
        style={{
          position: 'absolute',
          top: '1rem',
          left: '1rem',
          backgroundColor: 'var(--ga-primary-2)',
          color: 'var(--ga-primary)',
          padding: '0.5rem 0.875rem',
          borderRadius: '0.5rem',
          fontSize: '1rem',
          fontWeight: '600',
          zIndex: 999,
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
        }}
      >
        <div
          style={{
            width: '8px',
            height: '8px',
            backgroundColor: 'var(--ga-primary)',
            borderRadius: '50%',
          }}
        />
        {droneCode}
      </div>

      {/* Timer */}
      <div
        style={{
          position: 'absolute',
          top: '10px',
          left: '50%',
          transform: 'translateX(-50%)',
          backgroundColor: '#EF4444',
          color: 'white',
          padding: '4px 8px',
          borderRadius: '4px',
          fontSize: '12px',
          fontWeight: 'bold',
        }}
      >
        {recordingTime}
      </div>

      {/* Recording Controls */}
      <div
        style={{
          position: 'absolute',
          bottom: '20px',
          left: '50%',
          transform: 'translateX(-50%)',
          display: 'flex',
          gap: '12px',
          pointerEvents: 'auto',
        }}
      >
        {/* Pause/Resume Button */}
        <button
          onClick={onTogglePause}
          style={{
            width: '32px',
            height: '32px',
            backgroundColor: 'rgba(255, 255, 255, 1)',
            color: '#2D2E30',
            border: 'none',
            borderRadius: '50%',
            cursor: 'pointer',
            fontSize: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.3s ease',
            backdropFilter: 'blur(8px)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.05)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)';
          }}
          title={isPaused ? t('Resume Recording') : t('Pause Recording')}
        >
          {isPaused ? <FaRegCirclePlay size={20} /> : <ImPause size={20} />}
        </button>

        {/* Stop Button */}
        <button
          onClick={onStopRecording}
          disabled={isLoadingRecording}
          style={{
            width: '32px',
            height: '32px',
            backgroundColor: 'rgba(255, 255, 255, 1)',
            color: '#2D2E30',
            border: 'none',
            borderRadius: '50%',
            cursor: 'pointer',
            fontSize: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.3s ease',
            backdropFilter: 'blur(8px)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.05)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)';
          }}
          title={t('Stop Recording')}
        >
          <ImStop size={20} />
        </button>
      </div>

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
    </div>
  );
};
