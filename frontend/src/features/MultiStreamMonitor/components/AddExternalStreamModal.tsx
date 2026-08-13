import { yupResolver } from '@hookform/resolvers/yup';
import dayjs from 'dayjs';
import React from 'react';
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

interface AddExternalStreamModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaveSuccess?: () => void;
}

interface ExternalStreamFormData {
  name: string;
  rtsp_url: string;
  external_drone_name: string;
  external_operation_name: string;
  external_registration_number: string;
  external_manufacturer: string;
  external_flight_distance: string;
  external_flight_time: string;
  external_flight_altitude: string;
  external_start_point_x: string;
  external_start_point_y: string;
  external_end_point_x: string;
  external_end_point_y: string;
  external_start_time: any;
  external_end_time: any;
  remark: string;
}

const createValidationSchema = (t: any) =>
  yup.object({
    name: yup
      .string()
      .required(() => t('Stream name is required'))
      .trim()
      .min(1, () => t('Stream name must be at least 1 character')),
    rtsp_url: yup.string().required(() => t('IP is required')),
    external_drone_name: yup.string(),
    external_operation_name: yup.string(),
    external_registration_number: yup.string(),
    external_manufacturer: yup.string(),
    external_flight_distance: yup.string(),
    external_flight_time: yup.string(),
    external_flight_altitude: yup.string(),
    external_start_point_x: yup.string(),
    external_start_point_y: yup.string(),
    external_end_point_x: yup.string(),
    external_end_point_y: yup.string(),
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
    remark: yup.string(),
  });

export const AddExternalStreamModal: React.FC<AddExternalStreamModalProps> = ({
  isOpen,
  onClose,
  onSaveSuccess,
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const methods = useForm<ExternalStreamFormData>({
    mode: 'onChange',
    defaultValues: {
      name: '',
      rtsp_url: '',
      external_drone_name: '',
      external_operation_name: '',
      external_registration_number: '',
      external_manufacturer: '',
      external_flight_distance: '',
      external_flight_time: '',
      external_flight_altitude: '',
      external_start_point_x: '',
      external_start_point_y: '',
      external_end_point_x: '',
      external_end_point_y: '',
      external_start_time: null,
      external_end_time: null,
      remark: '',
    },
    resolver: yupResolver(createValidationSchema(t)),
  });

  const {
    control,
    handleSubmit,
    reset,
    trigger,
    watch,
    formState: {
      dirtyFields,
      validateErrors,
      errors,
      isSubmitting,
      isValid,
      isValidating,
    },
  } = methods;

  const startTime = watch('external_start_time');
  const endTime = watch('external_end_time');
  const name = watch('name');
  const rtspUrl = watch('rtsp_url');

  // Check if form can be submitted - required fields filled and no errors on required fields
  const canSubmit = React.useMemo(() => {
    const hasRequiredFields =
      name && name.trim().length > 0 && rtspUrl && rtspUrl.trim().length > 0;
    // Only check errors for required fields (name and rtsp_url)
    const hasRequiredFieldErrors = errors.name || errors.rtsp_url;
    return hasRequiredFields && !hasRequiredFieldErrors;
  }, [name, rtspUrl, errors.name, errors.rtsp_url]);

  // Disable end dates before start date
  const getDisabledEndDate = React.useCallback(
    (current: dayjs.Dayjs) => {
      if (!startTime || !current) return false;
      const start = dayjs(startTime);
      // Disable all dates before the start date
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

      // Only disable times if the selected date is the same as start date
      if (!selectedDate.isSame(start, 'day')) {
        return {};
      }

      // Disable hours, minutes, and seconds before or equal to start time
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
      // Disable all dates after the end date
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

      // Only disable times if the selected date is the same as end date
      if (!selectedDate.isSame(end, 'day')) {
        return {};
      }

      // Disable hours, minutes, and seconds after or equal to end time
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

  // Debug logging
  console.log('=== FORM DEBUG ===');
  console.log('name:', name);
  console.log('rtspUrl:', rtspUrl);
  console.log('errors:', errors);
  console.log('canSubmit:', canSubmit);
  console.log('isValid:', isValid);
  console.log('==================');

  const onSubmit = async (data: ExternalStreamFormData) => {
    try {
      const response = await API.post(endpoint.createExternalStream, {
        name: data.name,
        ip_source: data.rtsp_url,
        external_drone_name: data.external_drone_name,
        external_operation_name: data.external_operation_name,
        external_registration_number: data.external_registration_number,
        external_manufacturer: data.external_manufacturer,
        external_flight_distance: data.external_flight_distance
          ? parseFloat(data.external_flight_distance)
          : null,
        external_flight_time: data.external_flight_time
          ? parseFloat(data.external_flight_time)
          : null,
        external_flight_altitude: data.external_flight_altitude
          ? parseFloat(data.external_flight_altitude)
          : null,
        external_start_point_x: data.external_start_point_x,
        external_start_point_y: data.external_start_point_y,
        external_end_point_x: data.external_end_point_x,
        external_end_point_y: data.external_end_point_y,
        external_start_time: data.external_start_time
          ? dayjs(data.external_start_time).toISOString()
          : null,
        external_end_time: data.external_end_time
          ? dayjs(data.external_end_time).toISOString()
          : null,
        remark: data.remark,
      });
      if (response.success) {
        ToastTopHelper.success(t('External stream added successfully'));
        reset();
        onClose();
        onSaveSuccess?.();
      } else {
        ToastTopHelper.error(t('Failed to add external stream'));
      }
    } catch (error) {
      ToastTopHelper.error(t('Failed to add external stream'));
    }
  };

  const handleCancel = () => {
    reset();
    onClose();
  };

  return (
    <CustomModal
      title={t('Add External Stream')}
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
              '&::-webkit-scrollbar': {
                width: '6px',
              },
              '&::-webkit-scrollbar-track': {
                background: theme === 'dark' ? '#212529' : '#f8f9fa',
                borderRadius: '4px',
              },
              '&::-webkit-scrollbar-thumb': {
                background: theme === 'dark' ? '#444646' : '#c1c1c1',
                borderRadius: '4px',
                '&:hover': {
                  background: theme === 'dark' ? '#555' : '#a8a8a8',
                },
              },
              '&::-webkit-scrollbar-button': {
                display: 'none',
              },
              overflowY: 'auto',
              padding: '0',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
            }}
          >
            {/* Name and IP - Row 1 */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '16px',
              }}
            >
              <CustomInputHookForm
                name="name"
                control={control}
                label={t('Name')}
                placeholder={t('Name')}
                required
                type="text"
              />
              <CustomInputHookForm
                name="rtsp_url"
                control={control}
                label={t('IP')}
                placeholder="IP"
                required
                type="text"
              />
            </div>

            {/* Section Header */}
            <div>
              <p style={{ fontSize: '0.875rem', color: '#666', margin: 0 }}>
                {t(
                  'The following information is used for generating the report:',
                )}
              </p>
            </div>

            {/* Drone and Operator - Row 2 */}
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
                label={t('Drone')}
                placeholder={t('Drone')}
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

            {/* Registration Number and Manufacturer - Row 3 */}
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

            {/* Flight Distance and Flight Time - Row 4 */}
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

            {/* Flight Altitude - Row 5 */}
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
            </div>

            {/* Start Point X and Y - Row 6 */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '16px',
              }}
            >
              <CustomInputHookForm
                name="external_start_point_x"
                control={control}
                label={t('Start Point') + ' ' + t('X')}
                placeholder={t('Start Point') + ' ' + t('X')}
                type="text"
              />
              <CustomInputHookForm
                name="external_start_point_y"
                control={control}
                label={t('Start Point') + ' ' + t('Y')}
                placeholder={t('Start Point') + ' ' + t('Y')}
                type="text"
              />
            </div>

            {/* End Point X and Y - Row 7 */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '16px',
              }}
            >
              <CustomInputHookForm
                name="external_end_point_x"
                control={control}
                label={t('End Point') + ' ' + t('X')}
                placeholder={t('End Point') + ' ' + t('X')}
                type="text"
              />
              <CustomInputHookForm
                name="external_end_point_y"
                control={control}
                label={t('End Point') + ' ' + t('Y')}
                placeholder={t('End Point') + ' ' + t('Y')}
                type="text"
              />
            </div>

            {/* Start Time and End Time - Row 8 */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '16px',
              }}
            >
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
            </div>

            {/* Remarks - Row 9 */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr',
                gap: '16px',
              }}
            >
              <CustomInputHookForm
                name="remark"
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
                disabled={isSubmitting || !canSubmit}
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
