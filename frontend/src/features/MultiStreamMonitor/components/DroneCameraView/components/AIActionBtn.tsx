import { ConfigProvider, Dropdown, MenuProps } from 'antd';
import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLoadingContext, useTheme, ToastTopHelper } from 'rj-core';

import API, { endpoint } from '../../../../../services/API';

interface AIModel {
  id: number;
  name: string;
}

interface AIActionBtnProps {
  index?: number;
  currentMode: 'draw' | 'capture' | 'record' | 'ai' | null;
  onModeChange: (mode: 'draw' | 'capture' | 'record' | 'ai' | null) => void;
  onSaveSuccess?: () => void;
  camera: any;
  isLoadingRecording?: boolean;
}

export const AIActionBtn: React.FC<AIActionBtnProps> = ({
  index,
  currentMode,
  isLoadingRecording = false,
  camera,
  onSaveSuccess,
}) => {
  const [aiModels, setAiModels] = useState<AIModel[]>([]);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const { showLoadingGlobal, hideLoadingGlobal } = useLoadingContext();
  const [theme] = useTheme();
  const { t } = useTranslation();

  // Fetch AI models on mount
  useEffect(() => {
    fetchAIModels();
  }, []);

  const fetchAIModels = useCallback(async () => {
    try {
      const response = await API.get(endpoint.aiModels);
      setAiModels(response.data || []);
    } catch (error) {
      console.error('Error fetching AI models:', error);
      setAiModels([]);
    }
  }, []);

  const handleAIModelSelect = useCallback(
    async (aiModelId: number) => {
      try {
        showLoadingGlobal();

        const formData = {
          id: camera.id_stream,
          drone_id: camera.drone_id,
          ip_source: camera.ip_source,
          ai_models: [aiModelId],
          is_visualize:
            camera.isVisualize !== undefined ? camera.isVisualize : true,
          in_use: true, // Enable AI when selecting a model
          order: index || 0,
        };

        console.log('AIActionBtn - Sending data:', formData);

        const response = await API.post(endpoint.streamingList, {
          stream_monitors: [formData],
        });

        console.log('AIActionBtn - Response:', response);

        if (response.success) {
          ToastTopHelper.success(
            response.message || t('AI model updated successfully')
          );
          setDropdownOpen(false);
          if (onSaveSuccess) {
            onSaveSuccess();
          }
        } else {
          ToastTopHelper.error(
            response.message || t('Failed to update AI model')
          );
        }
      } catch (error: any) {
        console.error('Error saving AI settings:', error);
        ToastTopHelper.error(
          error?.response?.data?.message || t('Failed to update AI model')
        );
      } finally {
        hideLoadingGlobal();
      }
    },
    [camera, index, onSaveSuccess, showLoadingGlobal, hideLoadingGlobal, t],
  );

  // Get current selected AI model
  const currentAIModel = camera?.ai_models?.[camera.ai_models.length - 1];
  const hasAI = currentAIModel?.in_use;
  const selectedAIModelId = currentAIModel?.ai_model_id;

  console.log('AIActionBtn - Camera:', camera);
  console.log('AIActionBtn - Current AI Model:', currentAIModel);
  console.log('AIActionBtn - Selected AI Model ID:', selectedAIModelId);
  console.log('AIActionBtn - Available Models:', aiModels);

  // Create menu items from AI models
  const menuItems: MenuProps['items'] = aiModels.map((model) => ({
    key: model.id.toString(),
    label: (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          width: '100%',
          color:
            selectedAIModelId === model.id
              ? theme === 'dark'
                ? 'var(--ga-primary-dark)'
                : 'var(--ga-primary)'
              : theme === 'dark'
                ? '#fff'
                : '#000',
        }}
      >
        <span>{model.name}</span>
        {selectedAIModelId === model.id && (
          <span style={{ color: 'var(--ga-primary)', fontWeight: 'bold' }}>
            ✓
          </span>
        )}
      </div>
    ),
    onClick: (info) => {
      console.log('AIActionBtn - Menu item clicked:', model.id, info);
      handleAIModelSelect(model.id);
    },
    style:
      selectedAIModelId === model.id
        ? {
          // backgroundColor:
          //   theme === 'dark' ? 'var(--ga-primary-2)' : 'var(--ga-primary-3)',
          fontWeight: 600,
        }
        : undefined,
  }));

  return (
    <ConfigProvider
      theme={{
        token: {
          controlItemBgActive: theme === 'dark' ? '#fff' : '#000',
          colorBgElevated: theme === 'dark' ? '#1F1F20' : '#fff',
          colorText: theme === 'dark' ? '#fff' : '#000',
          controlItemBgActiveHover:
            theme === 'dark' ? '#2d2e30' : 'rgba(0,0,0,0.04)',
          controlItemBgHover: theme === 'dark' ? '#2d2e30' : 'rgba(0,0,0,0.04)',
        },
      }}
    >
      <Dropdown
        menu={{ items: menuItems }}
        trigger={['click']}
        placement="topRight"
        open={dropdownOpen}
        onOpenChange={(open) => {
          console.log('AIActionBtn - Dropdown open change:', open);
          setDropdownOpen(open);
        }}
        disabled={aiModels.length === 0}
      >
        <button
          style={{
            width: '32px',
            height: '32px',
            backgroundColor: hasAI ? '#8B5CF6' : 'rgba(255, 255, 255, 0.9)',
            color: hasAI ? 'white' : '#374151',
            border: 'none',
            borderRadius: '50%',
            cursor: aiModels.length === 0 ? 'not-allowed' : 'pointer',
            fontSize: '14px',
            fontWeight: 'bold',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.3s ease',
            boxShadow: '0 4px 16px rgba(0, 0, 0, 0.15)',
            backdropFilter: 'blur(8px)',
            opacity: aiModels.length === 0 ? 0.5 : 1,
          }}
          onMouseEnter={(e) => {
            if (!hasAI && aiModels.length > 0) {
              e.currentTarget.style.transform = 'scale(1.05)';
            }
          }}
          onMouseLeave={(e) => {
            if (!hasAI && aiModels.length > 0) {
              e.currentTarget.style.transform = 'scale(1)';
            }
          }}
          title={
            aiModels.length === 0
              ? t('No AI Models Available')
              : hasAI
                ? `${t('AI Model')}: ${currentAIModel?.ai_model__name || ''}`
                : t('Select AI Model')
          }
        >
          AI
        </button>
      </Dropdown>
    </ConfigProvider>
  );
};
