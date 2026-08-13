import { useState, useEffect, useRef } from 'react';
import { ToastTopHelper } from 'rj-core';

import i18n from '@/i18n';
import API, { endpoint } from '@/services/API';

export const useRecording = (
  streamMonitorCode?: string,
  aiModelCode: string | null = null,
) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const [recordId, setRecordId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const startRecording = async () => {
    if (!streamMonitorCode) {
      console.error('Stream monitor code is required for recording');
      return;
    }

    try {
      setIsLoading(true);
      const response = await API.post(
        `${endpoint.startRecording}?stream_monitor_code=${streamMonitorCode}${aiModelCode ? `&ai_model__code=${aiModelCode}` : ''
        }`,
      );

      if (response?.success) {
        setIsRecording(true);
        setIsPaused(false);
        setRecordingTime(0);
        setRecordId(response.data?.record_id);
      }
    } catch (error) {
      console.error('Error starting recording:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const stopRecording = async () => {
    if (!streamMonitorCode) {
      console.error('Stream monitor code is required for recording');
      return;
    }

    try {
      setIsLoading(true);
      const response = await API.post(
        `${endpoint.stopRecording}?stream_monitor_code=${streamMonitorCode}&record_id=${recordId}${aiModelCode ? `&ai_model__code=${aiModelCode}` : ''
        }`,
      );

      if (response?.success) {
        setIsRecording(false);
        setIsPaused(false);
        setRecordingTime(0);
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        ToastTopHelper.success(i18n.t('Video recording stopped'));
      }
    } catch (error) {
      console.error('Error stopping recording:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const togglePause = async () => {
    if (!streamMonitorCode) {
      console.error('Stream monitor code is required for recording');
      return;
    }
    if (isPaused) {
      try {
        setIsLoading(true);
        const response = await API.post(
          `${endpoint.resumeRecording}?stream_monitor_code=${streamMonitorCode}&record_id=${recordId}${aiModelCode ? `&ai_model__code=${aiModelCode}` : ''
          }`,
        );

        if (response?.success) {
          setIsPaused(!isPaused);
          ToastTopHelper.success(i18n.t('Video recording resumed'));
        }
      } catch (error) {
        console.error('Error toggling pause:', error);
      } finally {
        setIsLoading(false);
      }
    } else {
      try {
        setIsLoading(true);
        const response = await API.post(
          `${endpoint.pauseRecording}?stream_monitor_code=${streamMonitorCode}&record_id=${recordId}${aiModelCode ? `&ai_model__code=${aiModelCode}` : ''
          }`,
        );

        if (response?.success) {
          setIsPaused(!isPaused);
          ToastTopHelper.success(i18n.t('Video recording paused'));
        }
      } catch (error) {
        console.error('Error toggling pause:', error);
      } finally {
        setIsLoading(false);
      }
    }
  };

  const formatTime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  useEffect(() => {
    if (isRecording && !isPaused) {
      intervalRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isRecording, isPaused]);

  return {
    isRecording,
    isPaused,
    recordingTime,
    formattedTime: formatTime(recordingTime),
    startRecording,
    stopRecording,
    togglePause,
    isLoading,
  };
};
