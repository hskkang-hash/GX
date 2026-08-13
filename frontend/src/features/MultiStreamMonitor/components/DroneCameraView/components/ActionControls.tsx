import React from 'react';
import { useTranslation } from 'react-i18next';
import { BsPencil } from 'react-icons/bs';

import { AIActionBtn } from './AIActionBtn';
import { CaptureActionBtn } from './CaptureActionBtn';
import { DetelteExternalStreamBtn } from './DetelteExternalStreamBtn';
import { RecordActionBtn } from './RecordActionBtn';

interface ActionControlsProps {
  index?: number;
  camera?: any;
  currentMode: 'draw' | 'capture' | 'record' | 'ai' | null;
  recordingState?: boolean;
  startRecording?: () => void;
  stopRecording?: () => void;
  onDeleteExternalStream?: () => void;
  streamMonitorCode?: string;
  onModeChange: (mode: 'draw' | 'capture' | 'record' | 'ai' | null) => void;
  onCaptureFlash?: () => void;
  onSaveSuccess?: () => void;
  aiModelCode?: string | null;
  isStreamingAI?: boolean;
  isLoadingRecording?: boolean;
}

export const ActionControls: React.FC<ActionControlsProps> = ({
  index,
  camera,
  currentMode,
  isLoadingRecording = false,
  recordingState = false,
  startRecording = () => {},
  stopRecording = () => {},
  onDeleteExternalStream,
  streamMonitorCode,
  onModeChange,
  onCaptureFlash,
  onSaveSuccess,
  aiModelCode,
  isStreamingAI = false,
}) => {
  const { t } = useTranslation();
  const handleModeClick = (mode: 'draw' | 'capture' | 'record') => {
    if (currentMode === mode) {
      // If clicking the same mode, exit it
      onModeChange(null);
    } else {
      // Switch to new mode
      onModeChange(mode);
    }
  };

  return (
    <div
      style={{
        position: 'absolute',
        right: '10px',
        bottom: '10px',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        zIndex: 999,
      }}
    >
      {onDeleteExternalStream && (
        <DetelteExternalStreamBtn
          currentMode={currentMode}
          onDeleteExternalStream={onDeleteExternalStream}
        />
      )}
      {/* Draw Button */}
      {!isStreamingAI && (
        <button
          onClick={() => handleModeClick('draw')}
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
            if (currentMode !== 'draw') {
              e.currentTarget.style.transform = 'scale(1.05)';
            }
          }}
          onMouseLeave={(e) => {
            if (currentMode !== 'draw') {
              e.currentTarget.style.transform = 'scale(1)';
            }
          }}
          title={t('Drawing Mode')}
        >
          <BsPencil />
        </button>
      )}

      {/* Capture Button */}
      <CaptureActionBtn
        isStreamingAI={isStreamingAI}
        aiModelCode={aiModelCode}
        currentMode={currentMode}
        streamMonitorCode={streamMonitorCode}
        onModeChange={onModeChange}
        onCaptureFlash={onCaptureFlash}
        onCaptureSuccess={onSaveSuccess}
      />

      {/* Record Button */}
      <RecordActionBtn
        currentMode={currentMode}
        isRecording={recordingState}
        isLoadingRecording={isLoadingRecording}
        onModeChange={onModeChange}
        onToggleRecording={recordingState ? stopRecording : startRecording}
      />

      {/* AI Button */}
      {!isStreamingAI && (
        <AIActionBtn
          index={index}
          camera={camera}
          currentMode={currentMode}
          isLoadingRecording={isLoadingRecording}
          onModeChange={onModeChange}
          onSaveSuccess={onSaveSuccess}
        />
      )}
    </div>
  );
};
