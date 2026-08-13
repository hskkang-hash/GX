import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CustomModal, ToastTopHelper, useTheme } from 'rj-core';

import { CameraConfig } from '../../..';
import API, { endpoint } from '../../../../../services/API';
import { AISettingsForm } from './AISettingsForm';
import { AISettingsFormSkeleton } from './AISettingsFormSkeleton';

interface DroneCamera {
  id: number;
  name: string;
  code: string;
  drone__name: string;
  drone_id?: number;
  drone: string;
  ip_source: string;
  stream_url: string;
  is_active: boolean;
  is_visualize: boolean;
  order: string;
  ai_models: Array<{ ai_model_id?: number }>;
  in_use: boolean;
}

interface AIModel {
  id: number;
  name: string;
}

interface DroneCameraWithOrder extends DroneCamera {
  displayOrder: number;
}

// Use any type to match API data structure exactly
type AISettingsFormData = Record<number, DroneCameraWithOrder>;

interface AIModalProps {
  cameraConfigs: CameraConfig[];
  isOpen: boolean;
  onClose: () => void;
  onSaveSuccess?: () => void;
}

export const AIModal: React.FC<AIModalProps> = ({
  cameraConfigs = [],
  isOpen,
  onClose,
  onSaveSuccess,
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [droneCameras, setDroneCameras] = useState<DroneCameraWithOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [aiModelOptions, setAiModelOptions] = useState<
    Array<{ id: number; name: string }>
  >([]);
  useEffect(() => {
    if (isOpen) {
      // fetchDroneCameras();
      fetchAIModels();

      if (cameraConfigs.length > 0) {
        const hasValidOrder = cameraConfigs.some(
          (drone: DroneCamera) => drone.order !== '0',
        );

        let dronesWithOrder;

        if (hasValidOrder) {
          // If BE has valid order, sort by order and use it as displayOrder
          dronesWithOrder = cameraConfigs
            .map((drone: DroneCamera) => ({
              ...drone,
              displayOrder: parseInt(drone.order) || 0,
              in_use:
                drone?.ai_models[drone.ai_models.length - 1]?.in_use || false,
            }))
            .sort(
              (a: DroneCameraWithOrder, b: DroneCameraWithOrder) =>
                a.displayOrder - b.displayOrder,
            );
        } else {
          // If all order is "0", use array index as displayOrder (initial state)
          dronesWithOrder = cameraConfigs.map(
            (drone: DroneCamera, index: number) => ({
              ...drone,
              displayOrder: index,
              in_use:
                drone?.ai_models[drone.ai_models.length - 1]?.in_use || false,
            }),
          );
        }

        setDroneCameras(dronesWithOrder);
      }
    }
  }, [isOpen, cameraConfigs]);

  const fetchAIModels = async () => {
    try {
      setLoading(true);
      const response = await API.get(endpoint.aiModels);

      setAiModelOptions(
        response.data.map((item: AIModel) => ({
          ...item,
          value: item.id,
          label: item.name,
        })),
      );
    } catch (error) {
      setLoading(false);
      ToastTopHelper.error(
        error?.response?.data?.message || t('Something went wrong'),
      );
    } finally {
      setLoading(false);
    }
  };

  // const fetchDroneCameras = async () => {
  //   setLoading(true);
  //   try {
  //     const response = await API.get(endpoint.streamingList);

  //     if (response.success && response.data) {
  //       // Check if all drones have order "0" (initial state) or actual order numbers
  //       const hasValidOrder = response.data.some(
  //         (drone: DroneCamera) => drone.order !== '0',
  //       );

  //       let dronesWithOrder;

  //       if (hasValidOrder) {
  //         // If BE has valid order, sort by order and use it as displayOrder
  //         dronesWithOrder = response.data
  //           .map((drone: DroneCamera) => ({
  //             ...drone,
  //             displayOrder: parseInt(drone.order) || 0,
  //           }))
  //           .sort(
  //             (a: DroneCameraWithOrder, b: DroneCameraWithOrder) =>
  //               a.displayOrder - b.displayOrder,
  //           );
  //       } else {
  //         // If all order is "0", use array index as displayOrder (initial state)
  //         dronesWithOrder = response.data.map(
  //           (drone: DroneCamera, index: number) => ({
  //             ...drone,
  //             displayOrder: index,
  //           }),
  //         );
  //       }

  //       setDroneCameras(dronesWithOrder);
  //     }
  //   } catch (error) {
  //     console.error('Error fetching drone cameras:', error);
  //   } finally {
  //     setLoading(false);
  //   }
  // };

  const handleSave = async (formData: AISettingsFormData) => {
    // Convert object to array and prepare data for backend with updated order numbers
    const formDataArray = Object.values(formData);
    const dataToSave = formDataArray.map((drone) => {
      return {
        id: drone.id,
        drone_id: drone?.drone_id,
        ip_source: drone.ip_source,
        is_visualize: drone.is_visualize === true ? true : false,
        order: drone.displayOrder,
        in_use: drone.in_use || false,
        ai_models: drone.ai_models.map(
          (model: { ai_model_id?: number }) => model?.ai_model_id || model,
        ),
      };
    });

    try {
      const response = await API.post(endpoint.streamingList, {
        stream_monitors: dataToSave,
      });
      if (response.success) {
        if (onSaveSuccess) {
          onSaveSuccess();
        }
        ToastTopHelper.success(response.message);
        onClose();
      } else {
        ToastTopHelper.error(response.message);
      }
    } catch (error) {
      console.error('Error saving AI settings:', error);
      ToastTopHelper.error(
        error?.response?.data?.message || t('Something went wrong'),
      );
    }
  };

  const handleReorder = (reorderedDrones: DroneCameraWithOrder[]) => {
    setDroneCameras(reorderedDrones);
  };

  if (!isOpen) return null;

  return (
    <CustomModal
      show={isOpen}
      onHide={onClose}
      title={t('AI Setting')}
    >
      <div style={{ width: '80vw', maxWidth: '1200px', padding: '1rem 0' }}>
        {loading ? (
          <AISettingsFormSkeleton
            theme={theme}
            rowCount={3}
          />
        ) : (
          <AISettingsForm
            droneCameras={droneCameras}
            onSave={handleSave}
            onCancel={onClose}
            loading={loading}
            onReorder={handleReorder}
            aiModelOptions={aiModelOptions}
            theme={theme}
          />
        )}
      </div>
    </CustomModal>
  );
};
