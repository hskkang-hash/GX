import React, { useState } from 'react';
import { Spinner } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import { BsCamera } from 'react-icons/bs';
import { ToastTopHelper } from 'rj-core';

import API, { endpoint } from '@/services/API';

interface CaptureActionBtnProps {
  currentMode: 'draw' | 'capture' | 'record' | 'ai' | null;
  isStreamingAI?: boolean;
  aiModelCode?: string;
  streamMonitorCode?: string;
  onModeChange: (mode: 'draw' | 'capture' | 'record' | 'ai' | null) => void;
  onCaptureSuccess?: () => void;
  onCaptureFlash?: () => void;
}

export const CaptureActionBtn: React.FC<CaptureActionBtnProps> = ({
  isStreamingAI,
  aiModelCode,
  currentMode,
  streamMonitorCode,
  onModeChange,
  onCaptureSuccess,
  onCaptureFlash,
}) => {
  const [isCapturing, setIsCapturing] = useState(false);
  const { t } = useTranslation();
  const handleCaptureClick = async () => {
    if (!streamMonitorCode) {
      console.error('Stream monitor code is required for capture');
      return;
    }

    // Set capture mode temporarily
    onModeChange('capture');
    setIsCapturing(true);

    if (onCaptureFlash) {
      onCaptureFlash();
    }
    try {
      const response = await API.post(
        endpoint.captureVideo,
        isStreamingAI
          ? {
              stream_monitor_code: streamMonitorCode,
              ai_model__code: aiModelCode,
            }
          : {
              stream_monitor_code: streamMonitorCode,
            },
      );
      console.log({ response });

      if (response?.success) {
        response?.message
          ? ToastTopHelper.success(response?.message)
          : ToastTopHelper.success(t('Capture successful'));
        // if (onCaptureSuccess) {
        //   onCaptureSuccess();
        // }
      }
    } catch (error) {
      console.error('Error capturing video:', error);
    } finally {
      setIsCapturing(false);
      // Exit capture mode after capturing
      setTimeout(() => onModeChange(null), 100);
    }
  };

  return (
    <button
      onClick={handleCaptureClick}
      disabled={isCapturing}
      style={{
        width: '32px',
        height: '32px',
        backgroundColor:
          currentMode === 'capture' || isCapturing
            ? '#10B981'
            : 'rgba(255, 255, 255, 0.9)',
        color: currentMode === 'capture' || isCapturing ? 'white' : '#374151',
        border: 'none',
        borderRadius: '50%',
        cursor: isCapturing ? 'not-allowed' : 'pointer',
        fontSize: '18px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        transition: 'all 0.3s ease',
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.15)',
        backdropFilter: 'blur(8px)',
        opacity: isCapturing ? 0.7 : 1,
      }}
      onMouseEnter={(e) => {
        if (currentMode !== 'capture' && !isCapturing) {
          e.currentTarget.style.transform = 'scale(1.05)';
        }
      }}
      onMouseLeave={(e) => {
        if (currentMode !== 'capture' && !isCapturing) {
          e.currentTarget.style.transform = 'scale(1)';
        }
      }}
      title={isCapturing ? t('Capturing...') : t('Capture Frame')}
    >
      {isCapturing ? <Spinner /> : <BsCamera />}
    </button>
  );
};
