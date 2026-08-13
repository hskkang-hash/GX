import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { yupResolver } from '@hookform/resolvers/yup';
import React, { useEffect, useState } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { RxDragHandleHorizontal } from 'react-icons/rx';
import {
  CustomBtn,
  CustomInputHookForm,
  useLoadingContext,
  ToastTopHelper,
} from 'rj-core';
import * as yup from 'yup';

import CustomSelectControlled from '@/components/selects/CustomSelectControlled';

import { CustomSwitchBtn } from '../../../../../components/Form/CustomSwitchBtn';

interface DroneCamera {
  id: number;
  name: string;
  code: string;
  drone__name: string;
  drone: string;
  ip_source: string;
  stream_url: string;
  is_active: boolean;
  is_visualize: boolean;
  order: string;
  ai_models: Array<any>;
}

interface DroneCameraWithOrder extends DroneCamera {
  displayOrder: number;
}

// Use any type to match API data structure exactly
type FormData = any;

// Simple validation schema
const aiSettingsSchema = yup.object().shape({
  // Add validation as needed
});

interface AISettingsFormProps {
  droneCameras: DroneCameraWithOrder[];
  onSave: (data: FormData) => Promise<void>;
  onCancel: () => void;
  loading?: boolean;
  onReorder?: (reorderedDrones: DroneCameraWithOrder[]) => void;
  aiModelOptions: Array<{
    id: number;
    name: string;
    value?: number;
    label?: string;
  }>;
  theme?: string;
}

const SortableDroneItem: React.FC<{
  drone: DroneCameraWithOrder;
  index: number;
  control: any;
  getValues: any;
  setValue: any;
  watch: any;
  aiModelOptions: any;
  theme?: string;
}> = ({
  drone,
  index,
  control,
  getValues,
  setValue,
  watch,
  aiModelOptions,
  theme,
}) => {
  const { t } = useTranslation();
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: drone.id,
  });

  // Watch the ai_models field to make it reactive
  const currentAiModels = watch(`${index}.ai_models`);

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <tr
      ref={setNodeRef}
      style={{
        ...style,
        border: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E5E7EB'}`,
        backgroundColor: theme === 'dark' ? '#1f1f20' : 'white',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        color: theme === 'dark' ? '#F9FAFB' : '#111827',
      }}
    >
      {/* Drag Handle */}
      <td
        style={{
          padding: '16px',
          textAlign: 'center',
          minWidth: '40px',
          color: theme === 'dark' ? '#9CA3AF' : '#6B7280',
          borderRight: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
        }}
      >
        <div
          {...attributes}
          {...listeners}
          style={{
            cursor: 'grab',
            padding: '4px',
            fontSize: '16px',
            textAlign: 'center',
          }}
        >
          <RxDragHandleHorizontal size={24} />
        </div>
      </td>

      {/* Drone Name */}
      <td
        style={{
          padding: '16px',
          minWidth: '120px',
          fontWeight: '500',
          fontSize: '1rem',
          color: theme === 'dark' ? '#F9FAFB' : '#111827',
          borderRight: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
        }}
      >
        {drone?.drone__name}
      </td>

      {/* Stream URL */}
      <td
        style={{
          padding: '16px',
          minWidth: '200px',
          borderRight: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
        }}
      >
        <CustomInputHookForm
          name={`${index}.ip_source`}
          label=""
          disabled
        />
      </td>

      {/* AI Model Dropdown */}
      <td
        style={{
          padding: '16px',
          minWidth: '150px',
          borderRight: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
        }}
      >
        <CustomSelectControlled
          name={`${index}.ai_models`}
          label=""
          options={aiModelOptions}
          value={(() => {
            console.log(
              'AISettingsForm - Watched value for index',
              index,
              ':',
              currentAiModels,
            );

            let currentModelId;
            if (Array.isArray(currentAiModels)) {
              const firstItem = currentAiModels[0];
              currentModelId =
                typeof firstItem === 'object'
                  ? firstItem?.ai_model_id
                  : firstItem;
            } else if (
              typeof currentAiModels === 'object' &&
              currentAiModels !== null
            ) {
              currentModelId = currentAiModels.ai_model_id;
            } else {
              currentModelId = currentAiModels;
            }

            console.log('AISettingsForm - Extracted model ID:', currentModelId);

            const foundOption = aiModelOptions.find(
              (opt) => opt.value === currentModelId,
            );
            console.log('AISettingsForm - Found option:', foundOption);

            return foundOption || null;
          })()}
          setValue={(opt) => {
            console.log('AISettingsForm - Setting value:', opt);
            setValue(`${index}.ai_models`, opt ? [opt.value] : [], {
              shouldDirty: true,
            });
          }}
          placeholder={t('Select AI Model')}
        />
      </td>

      {/* Display Toggle */}
      <td
        style={{
          padding: '16px',
          textAlign: 'center',
          minWidth: '100px',
          borderRight: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
        }}
      >
        <CustomSwitchBtn
          control={control}
          name={`${index}.is_visualize`}
          isHorizontal
        />
        {/* <input
          type="checkbox"
          defaultChecked={drone.is_visualize}
          onChange={(e) => {
            const newValue = e.target.checked;
            setValue(`${index}.is_visualize`, newValue);
            console.log(`Setting ${index}.is_visualize to:`, newValue);
          }}
          style={{
            width: '18px',
            height: '18px',
            cursor: 'pointer',
            accentColor: 'var(--primary-color)',
          }}
        /> */}
      </td>
      <td style={{ padding: '16px', textAlign: 'center', minWidth: '100px' }}>
        <CustomSwitchBtn
          control={control}
          name={`${index}.in_use`}
          isHorizontal
        />
        {/* <input
          type="checkbox"
          defaultChecked={drone.in_use}
          onChange={(e) => {
            const newValue = e.target.checked;
            setValue(`${index}.in_use`, newValue);
          }}
          style={{
            width: '18px',
            height: '18px',
            cursor: 'pointer',
            accentColor: 'var(--primary-color)',
          }}
        /> */}
      </td>
    </tr>
  );
};

export const AISettingsForm: React.FC<AISettingsFormProps> = ({
  droneCameras,
  onSave,
  onCancel,
  loading = false,
  onReorder,
  aiModelOptions = [],
  theme = 'light',
}) => {
  const { t } = useTranslation();
  const { showLoading, hideLoading } = useLoadingContext();

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const methods = useForm<FormData>({
    resolver: yupResolver(aiSettingsSchema),
    defaultValues: droneCameras.reduce((acc, drone, index) => {
      acc[index] = drone;
      return acc;
    }, {} as any), // Convert array to object with index keys
  });
  console.log('droneCameras', droneCameras);

  const {
    handleSubmit,
    getValues,
    setValue,
    watch,
    formState: { isSubmitting, isValid },
  } = methods;

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (active.id !== over?.id) {
      const oldIndex = droneCameras.findIndex((item) => item.id === active.id);
      const newIndex = droneCameras.findIndex((item) => item.id === over?.id);

      // Get current form values to preserve any changes made by the user
      const currentFormValues = getValues();
      console.log(
        'AISettingsForm - Current form values before reorder:',
        currentFormValues,
      );

      const reorderedItems = arrayMove(droneCameras, oldIndex, newIndex);

      // Update displayOrder for all items after reordering
      // Merge with current form values to preserve user changes
      const updatedItems = reorderedItems.map((item, newPosition) => {
        // Find the old position of this item in the form
        const oldPosition = droneCameras.findIndex((d) => d.id === item.id);
        // Get the form values for this item from its old position
        const formValues = currentFormValues[oldPosition] || {};

        console.log(
          `AISettingsForm - Reordering item ${item.id}: old pos ${oldPosition} -> new pos ${newPosition}`,
        );
        console.log('AISettingsForm - Form values for this item:', formValues);
        console.log('AISettingsForm - Original item data:', item);

        return {
          ...item,
          ...formValues, // Preserve form changes (is_visualize, in_use, ai_models, etc.)
          displayOrder: newPosition,
        };
      });

      console.log(
        'AISettingsForm - Updated items after reorder:',
        updatedItems,
      );

      // Call onReorder callback if provided
      if (onReorder) {
        onReorder(updatedItems);
      }
    }
  };
  const currentLanguage = localStorage.getItem('language');

  // Track if this is initial mount
  const isInitialMount = React.useRef(true);
  const prevDroneCamerasLength = React.useRef(droneCameras.length);

  // Update form when droneCameras changes (but not on every re-render)
  useEffect(() => {
    if (droneCameras.length > 0) {
      const formData = droneCameras.reduce((acc, drone, index) => {
        acc[index] = drone;
        return acc;
      }, {} as any);

      // Only reset if:
      // 1. Initial mount
      // 2. Number of drones changed (reordering doesn't change length, so user edits are preserved)
      if (
        isInitialMount.current ||
        prevDroneCamerasLength.current !== droneCameras.length
      ) {
        console.log('AISettingsForm - Resetting form with data:', formData);
        methods.reset(formData);
        isInitialMount.current = false;
        prevDroneCamerasLength.current = droneCameras.length;
      } else {
        // On reorder, update form with new positions
        // The droneCameras prop already has merged form values from handleDragEnd
        console.log(
          'AISettingsForm - Updating form positions after reorder:',
          formData,
        );
        methods.reset(formData, { keepDirty: true, keepTouched: true });
      }
    }
  }, [droneCameras, methods]);

  const handleFormSubmit = async (data: FormData) => {
    showLoading();
    try {
      await onSave(data);
      // ToastTopHelper.success(
      //   currentLanguage === 'en'
      //     ? 'AI settings saved successfully'
      //     : currentLanguage === 'ko'
      //       ? 'AI 설정이 성공적으로 저장되었습니다'
      //       : 'AI ตั้งค่าสำเร็จ',
      // );
    } catch (error) {
      console.error('Error saving AI settings:', error);
      // ToastTopHelper.error(
      //   currentLanguage === 'en'
      //     ? 'Failed to save AI settings'
      //     : currentLanguage === 'ko'
      //       ? 'AI 설정 저장에 실패했습니다'
      //       : 'AI ตั้งค่าไม่สำเร็จ',
      // );
    } finally {
      hideLoading();
    }
  };

  const onError = (errors: Record<string, unknown>) => {
    console.error('Form errors:', errors);
    ToastTopHelper.error('Please fill in all required fields');
  };

  return (
    <FormProvider {...methods}>
      <form
        onSubmit={handleSubmit(handleFormSubmit, onError)}
        style={{
          backgroundColor: theme === 'dark' ? '#1f1f20' : 'white',
          color: theme === 'dark' ? '#F9FAFB' : '#111827',
          borderRadius: '8px',
          gap: '1rem',
          paddingBottom: '0 !important',
        }}
      >
        {/* Drag and Drop Context */}
        <div style={{ overflowY: 'auto', height: '50rem' }}>
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={droneCameras.map((drone) => drone.id)}
              strategy={verticalListSortingStrategy}
            >
              {/* Table */}
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                {/* Table Header */}
                <thead>
                  <tr
                    style={{
                      backgroundColor: theme === 'dark' ? '#2D2E30' : '#F8FAFC',
                      border: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
                      borderRadius: '8px',
                      fontWeight: '400',
                      fontSize: '1rem',
                      color: theme === 'dark' ? '#F9FAFB' : '#1E293B',
                    }}
                  >
                    <th
                      style={{
                        padding: '16px',
                        textAlign: 'left',
                        minWidth: '40px',
                        borderRight: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
                      }}
                    ></th>
                    <th
                      style={{
                        padding: '16px',
                        textAlign: 'left',
                        minWidth: '120px',
                        borderRight: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
                      }}
                    >
                      {t('Drone Name')}
                    </th>
                    <th
                      style={{
                        padding: '16px',
                        textAlign: 'left',
                        minWidth: '300px',
                        borderRight: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
                      }}
                    >
                      {t('IP')}
                    </th>
                    <th
                      style={{
                        padding: '16px',
                        textAlign: 'left',
                        minWidth: '150px',
                        borderRight: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
                      }}
                    >
                      {t('AI')}
                    </th>
                    <th
                      style={{
                        padding: '16px',
                        textAlign: 'center',
                        width: '80px',
                        borderRight: `1px solid ${theme === 'dark' ? '#3C3D3E' : '#E2E8F0'}`,
                      }}
                    >
                      {t('Display')}
                    </th>
                    <th
                      style={{
                        padding: '16px',
                        textAlign: 'center',
                        width: '80px',
                      }}
                    >
                      {t('AI Enabled')}
                    </th>
                  </tr>
                </thead>

                {/* Table Body */}
                <tbody>
                  {droneCameras.map((drone, index) => (
                    <SortableDroneItem
                      key={drone.id}
                      drone={drone}
                      index={index}
                      control={methods.control}
                      getValues={getValues}
                      setValue={setValue}
                      watch={watch}
                      aiModelOptions={aiModelOptions}
                      theme={theme}
                    />
                  ))}
                </tbody>
              </table>
            </SortableContext>
          </DndContext>
        </div>

        {/* Action Buttons */}
        <div
          style={{
            display: 'flex',
            gap: '12px',
            justifyContent: 'center',
          }}
        >
          <CustomBtn
            label={t('Save')}
            color="primary"
            size="lg"
            type="submit"
            loading={isSubmitting || loading}
            disabled={isSubmitting || loading || !isValid}
          />
          <CustomBtn
            label={t('Cancel')}
            variant="outline"
            color="secondary"
            size="lg"
            onClick={onCancel}
            disabled={loading}
          />
        </div>
      </form>
    </FormProvider>
  );
};
