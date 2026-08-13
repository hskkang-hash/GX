import { yupResolver } from '@hookform/resolvers/yup';
import dayjs from 'dayjs';
import React, { useEffect } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  ActionBtn,
  CustomBtn,
  CustomModal,
  CustomInputHookForm,
  ToastTopHelper,
  useTheme,
} from 'rj-core';
import * as yup from 'yup';

import CustomDatePicker from '@/components/Form/CustomDatePicker';
import API, { endpoint } from '@/services/API';

interface UpdateExternalStreamModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaveSuccess?: () => void;
  streamMonitorId: number | null;
  streamMonitorName?: string;
  streamMonitorIpSource?: string;
  initialData?: {
    external_drone_name?: string;
    external_operation_name?: string;
    external_registration_number?: string;
    external_manufacturer?: string;
    external_flight_distance?: number | string;
    external_flight_time?: number | string;
    external_flight_altitude?: number | string;
    external_start_point_x?: string | number;
    external_start_point_y?: string | number;
    external_end_point_x?: string | number;
    external_end_point_y?: string | number;
    external_start_time?: string;
    external_end_time?: string;
    external_remark?: string;
  };
}

interface ExternalStreamFormData {
  external_drone_name: string;
  external_operation_name: string;
  external_registration_number: string;
  external_manufacturer: string;
  external_flight_distance: string;
  external_flight_time: string;
  external_flight_altitude: string;
  external_start_point: string;
  external_end_point: string;
  external_start_time: any;
  external_end_time: any;
  external_remark: string;
}

const createValidationSchema = (t: any) =>
  yup.object({
    external_drone_name: yup.string(),
    external_operation_name: yup.string(),
    external_registration_number: yup.string(),
    external_manufacturer: yup.string(),
    external_flight_distance: yup.string(),
    external_flight_time: yup.string(),
    external_flight_altitude: yup.string(),
    external_start_point: yup.string(),
    external_end_point: yup.string(),
    external_start_time: yup.mixed().nullable(),
    external_end_time: yup
      .mixed()
      .nullable()
      .test(
        'is-after-start',
        () => t('End time must be after start time'),
        function (value) {
          const { external_start_time } = this.parent;
          if (!value || !external_start_time) return true;
          return dayjs(value).isAfter(dayjs(external_start_time));
        },
      ),
    external_remark: yup.string(),
  });

export const UpdateExternalStreamModal: React.FC<
  UpdateExternalStreamModalProps
> = ({
  isOpen,
  onClose,
  onSaveSuccess,
  streamMonitorId,
  streamMonitorName,
  streamMonitorIpSource,
  initialData,
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const methods = useForm<ExternalStreamFormData>({
    mode: 'onChange',
    defaultValues: {
      external_drone_name: '',
      external_operation_name: '',
      external_registration_number: '',
      external_manufacturer: '',
      external_flight_distance: '',
      external_flight_time: '',
      external_flight_altitude: '',
      external_start_point: '',
      external_end_point: '',
      external_start_time: null,
      external_end_time: null,
      external_remark: '',
    },
    resolver: yupResolver(createValidationSchema(t)),
  });

  const {
    control,
    handleSubmit,
    reset,
    watch,
    formState: { isSubmitting },
  } = methods;

  const startTime = watch('external_start_time');
  const endTime = watch('external_end_time');

  // Update form when initialData changes
  useEffect(() => {
    if (initialData && isOpen) {
      reset({
        external_drone_name: initialData.external_drone_name || '',
        external_operation_name: initialData.external_operation_name || '',
        external_registration_number:
          initialData.external_registration_number || '',
        external_manufacturer: initialData.external_manufacturer || '',
        external_flight_distance:
          initialData.external_flight_distance != null
            ? String(initialData.external_flight_distance)
            : '',
        external_flight_time:
          initialData.external_flight_time != null
            ? String(initialData.external_flight_time)
            : '',
        external_flight_altitude:
          initialData.external_flight_altitude != null
            ? String(initialData.external_flight_altitude)
            : '',
        external_start_point:
          initialData.external_start_point_x != null ||
          initialData.external_start_point_y != null
            ? `${initialData.external_start_point_x || ''}, ${
                initialData.external_start_point_y || ''
              }`
                .trim()
                .replace(/^,\s*|,\s*$/g, '')
            : '',
        external_end_point:
          initialData.external_end_point_x != null ||
          initialData.external_end_point_y != null
            ? `${initialData.external_end_point_x || ''}, ${
                initialData.external_end_point_y || ''
              }`
                .trim()
                .replace(/^,\s*|,\s*$/g, '')
            : '',
        external_start_time: initialData.external_start_time
          ? dayjs(initialData.external_start_time).toDate()
          : null,
        external_end_time: initialData.external_end_time
          ? dayjs(initialData.external_end_time).toDate()
          : null,
        external_remark: initialData.external_remark || '',
      });
    }
  }, [initialData, isOpen, reset]);

  // Disable end dates before start date
  const getDisabledEndDate = React.useCallback(
    (current: dayjs.Dayjs) => {
      if (!startTime || !current) return false;
      const start = dayjs(startTime);
      return current.isBefore(start, 'day');
    },
    [startTime],
  );

  // Disable end times before start time when same date is selected
  const getDisabledEndTime = React.useCallback(() => {
    if (!startTime) return undefined;

    return (current: any) => {
      if (!current) return {};

      const start = dayjs(startTime);
      const selectedDate = dayjs(current);

      if (!selectedDate.isSame(start, 'day')) {
        return {};
      }

      const startHour = start.hour();
      const startMinute = start.minute();
      const startSecond = start.second();

      return {
        disabledHours: () => {
          const hours = [];
          for (let i = 0; i < startHour; i++) {
            hours.push(i);
          }
          return hours;
        },
        disabledMinutes: (selectedHour: number) => {
          if (selectedHour === startHour) {
            const minutes = [];
            for (let i = 0; i < startMinute; i++) {
              minutes.push(i);
            }
            return minutes;
          }
          return [];
        },
        disabledSeconds: (selectedHour: number, selectedMinute: number) => {
          if (selectedHour === startHour && selectedMinute === startMinute) {
            const seconds = [];
            for (let i = 0; i <= startSecond; i++) {
              seconds.push(i);
            }
            return seconds;
          }
          return [];
        },
      };
    };
  }, [startTime]);

  // Disable start dates after end date
  const getDisabledStartDate = React.useCallback(
    (current: dayjs.Dayjs) => {
      if (!endTime || !current) return false;
      const end = dayjs(endTime);
      return current.isAfter(end, 'day');
    },
    [endTime],
  );

  // Disable start times after end time when same date is selected
  const getDisabledStartTime = React.useCallback(() => {
    if (!endTime) return undefined;

    return (current: any) => {
      if (!current) return {};

      const end = dayjs(endTime);
      const selectedDate = dayjs(current);

      if (!selectedDate.isSame(end, 'day')) {
        return {};
      }

      const endHour = end.hour();
      const endMinute = end.minute();
      const endSecond = end.second();

      return {
        disabledHours: () => {
          const hours = [];
          for (let i = endHour + 1; i < 24; i++) {
            hours.push(i);
          }
          return hours;
        },
        disabledMinutes: (selectedHour: number) => {
          if (selectedHour === endHour) {
            const minutes = [];
            for (let i = endMinute + 1; i < 60; i++) {
              minutes.push(i);
            }
            return minutes;
          }
          return [];
        },
        disabledSeconds: (selectedHour: number, selectedMinute: number) => {
          if (selectedHour === endHour && selectedMinute === endMinute) {
            const seconds = [];
            for (let i = endSecond; i < 60; i++) {
              seconds.push(i);
            }
            return seconds;
          }
          return [];
        },
      };
    };
  }, [endTime]);

  const onSubmit = async (data: ExternalStreamFormData) => {
    if (!streamMonitorId) {
      ToastTopHelper.error(t('Stream monitor ID is required'));
      return;
    }
    if (!streamMonitorName) {
      ToastTopHelper.error(t('Stream monitor name is required'));
      return;
    }
    if (!streamMonitorIpSource) {
      ToastTopHelper.error(t('Stream monitor IP source is required'));
      return;
    }

    try {
      // Parse start and end points
      const startPointParts = data.external_start_point
        ? data.external_start_point.split(',').map((p) => p.trim())
        : [];
      const endPointParts = data.external_end_point
        ? data.external_end_point.split(',').map((p) => p.trim())
        : [];

      // Use PUT endpoint /external-stream-monitors with ExternalStreamMonitorInSchema
      const response = await API.put(endpoint.updateExternalStream, {
        id: streamMonitorId,
        name: streamMonitorName,
        ip_source: streamMonitorIpSource,
        external_drone_name: data.external_drone_name || null,
        external_operation_name: data.external_operation_name || null,
        external_registration_number: data.external_registration_number || null,
        external_manufacturer: data.external_manufacturer || null,
        external_flight_distance: data.external_flight_distance
          ? parseFloat(data.external_flight_distance)
          : null,
        external_flight_time: data.external_flight_time
          ? parseFloat(data.external_flight_time)
          : null,
        external_flight_altitude: data.external_flight_altitude
          ? parseFloat(data.external_flight_altitude)
          : null,
        external_start_point_x: startPointParts[0] || null,
        external_start_point_y: startPointParts[1] || null,
        external_end_point_x: endPointParts[0] || null,
        external_end_point_y: endPointParts[1] || null,
        external_start_time: data.external_start_time
          ? dayjs(data.external_start_time).toISOString()
          : null,
        external_end_time: data.external_end_time
          ? dayjs(data.external_end_time).toISOString()
          : null,
        remark: data.external_remark || null,
      });
      if (response.success) {
        ToastTopHelper.success(t('External stream data updated successfully'));
        onClose();
        onSaveSuccess?.();
      } else {
        ToastTopHelper.error(
          response.message || t('Failed to update external stream data'),
        );
      }
    } catch (error: any) {
      ToastTopHelper.error(
        error?.response?.data?.message ||
          t('Failed to update external stream data'),
      );
    }
  };

  const handleCancel = () => {
    reset();
    onClose();
  };

  return (
    <CustomModal
      title={t('Fill in Data')}
      show={isOpen}
      onHide={handleCancel}
    >
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)}>
          <div
            style={{
              width: '50vw',
              maxWidth: '1200px',
              maxHeight: '65vh',
              overflowY: 'auto',
              padding: '0',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
            }}
          >
            {/* Row 1: Device (Left) and Operator (Right) */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '16px',
              }}
            >
              <CustomInputHookForm
                name="external_drone_name"
                control={control}
                label={t('Device')}
                placeholder={t('Device')}
                type="text"
              />
              <CustomInputHookForm
                name="external_operation_name"
                control={control}
                label={t('Operator')}
                placeholder={t('Operator')}
                type="text"
              />
            </div>

            {/* Row 2: Registration Number (Left) and Manufacturer (Right) */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '16px',
              }}
            >
              <CustomInputHookForm
                name="external_registration_number"
                control={control}
                label={t('Registration Number')}
                placeholder={t('Registration Number')}
                type="text"
              />
              <CustomInputHookForm
                name="external_manufacturer"
                control={control}
                label={t('Manufacturer')}
                placeholder={t('Manufacturer')}
                type="text"
              />
            </div>

            {/* Row 3: Flight Distance (Left) and Flight Time (Right) */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '16px',
              }}
            >
              <CustomInputHookForm
                name="external_flight_distance"
                control={control}
                label={t('Flight Distance')}
                placeholder={t('Flight Distance')}
                type="number"
              />
              <CustomInputHookForm
                name="external_flight_time"
                control={control}
                label={t('Flight Time')}
                placeholder={t('Flight Time')}
                type="number"
              />
            </div>

            {/* Row 4: Flight Altitude (Left) and Start Point (Right) */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '16px',
              }}
            >
              <CustomInputHookForm
                name="external_flight_altitude"
                control={control}
                label={t('Flight Altitude')}
                placeholder={t('Flight Altitude')}
                type="number"
              />
              <CustomInputHookForm
                name="external_start_point"
                control={control}
                label={t('Start Point')}
                placeholder={t('Start Point')}
                type="text"
              />
            </div>

            {/* Row 5: End Point (Left) and Start Time (Right) */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '16px',
              }}
            >
              <CustomInputHookForm
                name="external_end_point"
                control={control}
                label={t('End Point')}
                placeholder={t('End Point')}
                type="text"
              />
              <CustomDatePicker
                name="external_start_time"
                control={control}
                label={t('Start Time')}
                placeholder={t('Start Time')}
                format="MM-DD-YYYY HH:mm:ss"
                picker="datetime"
                disabledDate={getDisabledStartDate}
                disabledTime={getDisabledStartTime()}
              />
            </div>

            {/* Row 6: End Time (Left) and Remarks (Right) */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '16px',
              }}
            >
              <CustomDatePicker
                name="external_end_time"
                control={control}
                label={t('End Time')}
                placeholder={t('End Time')}
                format="MM-DD-YYYY HH:mm:ss"
                picker="datetime"
                disabledDate={getDisabledEndDate}
                disabledTime={getDisabledEndTime()}
              />
              <CustomInputHookForm
                name="external_remark"
                control={control}
                label={t('Remarks')}
                placeholder={t('Remarks')}
                type="text"
              />
            </div>
          </div>

          <ActionBtn
            leftButtons={[
              <CustomBtn
                key="save-btn"
                type="submit"
                color="primary"
                size="lg"
                label={t('Save')}
                loading={isSubmitting}
                disabled={isSubmitting}
              />,
            ]}
            rightButtons={[
              <CustomBtn
                key="cancel-btn"
                type="button"
                variant="outline"
                color="secondary"
                size="lg"
                onClick={handleCancel}
                label={t('Cancel')}
                disabled={isSubmitting}
              />,
            ]}
          />
        </form>
      </FormProvider>
    </CustomModal>
  );
};
