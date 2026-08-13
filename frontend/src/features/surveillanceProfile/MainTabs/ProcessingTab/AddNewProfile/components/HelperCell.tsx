import { ConfigProvider, Tooltip } from 'antd';
import enLocale from 'antd/es/locale/en_US';
import koLocale from 'antd/es/locale/ko_KR';
import thLocale from 'antd/es/locale/th_TH';
import TimePicker from 'antd/es/time-picker';
import dayjs from 'dayjs';
import { useTranslation } from 'react-i18next';
import { BsPinMap } from 'react-icons/bs';
import { useTheme } from 'rj-core';

import SwitchBtn from '@/components/Form/SwitchBtn';
import PaginationSelect from '@/components/selects/PaginationSelect';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';

import type { DroneAssignment } from '../AddNewProfile.d';

export const DroneCell = ({
  row,
  missionOptions,
  updateDroneAssignmentByIndex,
  flagErrorDrone,
  flagWarningDrone,
}: {
  row: any;
  missionOptions: any[];
  flagErrorDrone: boolean;
  flagWarningDrone: boolean;
  updateDroneAssignmentByIndex: (
    index: number,
    field: keyof DroneAssignment,
    value: any,
  ) => void;
}) => {
  const currentValue = {
    value: row?.row?.original?.device?.id,
    label: row?.row?.original?.device?.name,
  };
  const { t } = useTranslation();
  return (
    <Tooltip
      title={currentValue?.label || ''}
      placement="topLeft"
    >
      <div>
        <PaginationSelect
          required
          error={flagErrorDrone}
          warning={flagWarningDrone}
          value={currentValue || null}
          loadOptions={async (inputValue: string) => {
            if (!inputValue) {
              return {
                options: missionOptions,
                hasMore: false,
              };
            }
            const filteredOptions = missionOptions.filter((item: any) =>
              item.label.toLowerCase().includes(inputValue.toLowerCase()),
            );
            return {
              options: filteredOptions,
              hasMore: false,
            };
          }}
          onChange={(value: any) => {
            console.log('onChange - value:', value);
            if (value) {
              updateDroneAssignmentByIndex(
                row?.row?.index,
                'device_id',
                value.value,
              );
            }
          }}
          placeholder={t('Select')}
        />
      </div>
    </Tooltip>
  );
};
export const StartTimeCell = ({
  row,
  updateDroneAssignmentByIndex,
  realStartTime,
  flagErrorWaypoint,
  startTime,
}: {
  row: any;
  updateDroneAssignmentByIndex: (
    index: number,
    field: keyof DroneAssignment,
    value: any,
  ) => void;
  realStartTime: dayjs.Dayjs | null;
  flagErrorWaypoint: boolean;
  startTime: dayjs.Dayjs | null;
}) => {
  const {
    timeFormat,
    dateFormat,
    datetimeFormat,
    timeZoneFormat,
    converRawDateToTimeFormat,
    convertDateFormatToUTCfollowUserTimeZone,
  } = useConvertDate();
  const { i18n } = useTranslation();
  const [theme] = useTheme();

  const timeValue = row?.row?.original?.scheduled_start_time
    ? converRawDateToTimeFormat(row?.row?.original?.scheduled_start_time)
    : '';

  return (
    <ConfigProvider
      locale={
        i18n.language === 'en'
          ? enLocale
          : i18n.language === 'ko'
            ? koLocale
            : thLocale
      }
      theme={{
        components: {
          TimePicker: {
            activeBg: theme === 'dark' ? '#1F1F20' : '#fff',
            hoverBg: theme === 'dark' ? '#2a2a2a' : '#f9f9f9',
            activeBorderColor:
              theme === 'dark' ? 'var(--ga-primary)' : 'var(--ga-primary)',
            hoverBorderColor:
              theme === 'dark' ? 'var(--ga-primary)' : 'var(--ga-primary)',
            cellActiveWithRangeBg:
              theme === 'dark' ? '#262626' : 'var(--ga-primary-4)',
            cellHoverBg:
              theme === 'dark' ? 'var(--ga-primary)' : 'var(--ga-primary-4)',
          },
        },
        token: {
          colorText:
            theme === 'dark'
              ? 'var(--ga-dark-theme-font-color)'
              : 'var(--ga-light-theme-font-color)',
          colorTextDisabled: theme === 'dark' ? '#777' : '#bfbfbf',
          colorBgContainer: theme === 'dark' ? '#141414' : '#fff',
          colorBgElevated: theme === 'dark' ? '#1f1f1f' : '#fff',
          colorPrimaryBorder:
            theme === 'dark'
              ? 'var(--ga-dark-line-color)'
              : 'var(--ga-primary-2)',
          colorBorder: theme === 'dark' ? '#303030' : '#d9d9d9',
          colorIcon: theme === 'dark' ? '#bfbfbf' : '#595959',
          colorIconHover:
            theme === 'dark'
              ? 'var(--ga-light-theme-font-color)'
              : 'var(--ga-primary)',
          colorBgContainerDisabled: theme === 'dark' ? '#262626' : '#f5f5f5',
          colorTextPlaceholder: theme === 'dark' ? '#8c8c8c' : '#bfbfbf',
          controlItemBgActive:
            theme === 'dark'
              ? 'var(--ga-light-theme-font-color)'
              : 'var(--ga-primary-4)',
          colorBorderError: '#ff4d4f',
        },
      }}
    >
      <TimePicker
        className="custom-timepicker"
        format={timeFormat}
        status={flagErrorWaypoint ? 'error' : undefined}
        value={timeValue ? dayjs(timeValue, timeFormat) : null}
        disabled={row?.row?.index === 0}
        disabledDate={(current) => {
          if (!current) return false;
          return current.isBefore(dayjs().startOf('day'));
        }}
        disabledTime={(current) => {
          if (!current) return {};
          // if startTime is selected, disable time before startTime
          if (startTime) {
            // if selected date is the same as startTime date, disable time before startTime
            const startHour = startTime
              ? dayjs(startTime, datetimeFormat).hour()
              : 0;
            const startMinute = startTime
              ? dayjs(startTime, datetimeFormat).minute()
              : 0;

            return {
              disabledHours: () =>
                Array.from({ length: startHour }, (_, i) => i), // disable hours < startHour

              disabledMinutes: (hour) =>
                hour === startHour
                  ? Array.from({ length: startMinute }, (_, i) => i) // disable minutes < startMinute
                  : [],
            };
          }

          return {};
        }}
        onChange={(time) => {
          if (time) {
            const dateValue = startTime
              ? dayjs(startTime).format(dateFormat)
              : dayjs().format(dateFormat);
            const timeValue = dayjs(time).format(timeFormat);

            const fulldateTimeValue = `${dateValue} ${timeValue}`;
            const utcDateTimeValue =
              convertDateFormatToUTCfollowUserTimeZone(fulldateTimeValue);
            updateDroneAssignmentByIndex(
              row?.row?.index,
              'scheduled_start_time',
              utcDateTimeValue,
            );
          } else {
            updateDroneAssignmentByIndex(
              row?.row?.index,
              'scheduled_start_time',
              null,
            );
          }
        }}
        style={{
          width: '100%',
          borderRadius: 6,
          backgroundColor: theme === 'dark' ? '#1F1F20' : 'white',
          // borderColor:
          // 	theme === 'dark' ? '#303030' : '#d9d9d9',
        }}
        popupClassName={
          theme === 'dark'
            ? 'custom-timepicker-dark'
            : 'custom-timepicker-light'
        }
      />
    </ConfigProvider>
  );
};

export const WaypointCell = ({
  row,
  waypointOptions,
  updateDroneAssignmentByIndex,
  flagErrorWaypoint,
  isDisabled,
  type,
}: {
  row: any;
  waypointOptions: any[];
  isDisabled: boolean;
  updateDroneAssignmentByIndex: (
    index: number,
    field: keyof DroneAssignment,
    value: any,
  ) => void;
  flagErrorWaypoint: boolean;
  type: 'start' | 'end';
}) => {
  const { t } = useTranslation();

  const fieldKey = type === 'start' ? 'start_waypoint_id' : 'end_waypoint_id';
  const currentValue = row?.row?.original?.[fieldKey]
    ? waypointOptions.find(
        (item: any) =>
          String(item.code) === String(row?.row?.original?.[fieldKey]),
      )
    : null;

  return (
    <Tooltip
      title={currentValue?.label || ''}
      placement="topLeft"
    >
      <div>
        <PaginationSelect
          error={flagErrorWaypoint}
          value={currentValue || null}
          disabled={(type === 'start' && row?.row?.index === 0) || isDisabled}
          loadOptions={async (inputValue: string) => {
            const filteredOptions = inputValue
              ? waypointOptions.filter((item: any) =>
                  item.label.toLowerCase().includes(inputValue.toLowerCase()),
                )
              : waypointOptions;

            return {
              options: filteredOptions.map((wp: any) => ({
                value: wp.value,
                label: wp.label,
                code: wp.code,
              })),
              hasMore: false,
            };
          }}
          onChange={(value: any) => {
            if (value && row?.row?.original?.[fieldKey] !== undefined) {
              updateDroneAssignmentByIndex(
                row?.row?.index,
                fieldKey,
                value.code || null,
              );
            }
          }}
          placeholder={t('Select')}
        />
      </div>
    </Tooltip>
  );
};

export const SwitchCell = ({
  row,
  field,
  defaultValue = false,
  updateDroneAssignmentByIndex,
}: {
  row: any;
  field: keyof DroneAssignment;
  defaultValue?: boolean;
  updateDroneAssignmentByIndex: (
    index: number,
    field: keyof DroneAssignment,
    value: any,
  ) => void;
}) => {
  const value = row?.row?.original?.[field] ?? defaultValue;
  return (
    <SwitchBtn
      statusValue={value}
      onChange={() => {
        if (row?.row?.original?.[field] !== undefined) {
          updateDroneAssignmentByIndex(row?.row?.index, field, !value);
        }
      }}
    />
  );
};

export const WaitingCoordinatesCell = ({
  row,
  onOpenModal,
  isDisabled = false,
}: {
  row: any;
  onOpenModal: (rowIndex: number) => void;
  isDisabled?: boolean;
}) => {
  const { t } = useTranslation();
  const waitingCoordinates = row?.row?.original?.waiting_coordinates;
  const rowIndex = row?.row?.index ?? 0;

  const coordinatesText =
    waitingCoordinates &&
    Array.isArray(waitingCoordinates) &&
    waitingCoordinates.length === 2
      ? `${waitingCoordinates[0].toFixed(7)}, ${waitingCoordinates[1].toFixed(7)}`
      : '-';

  const disabledTooltipText = t(
    'The selected mission was imported, so the route cannot be modified.',
  );

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        width: '100%',
        opacity: isDisabled ? 0.5 : 1,
      }}
    >
      <Tooltip
        title={coordinatesText}
        placement="topLeft"
      >
        <span
          style={{
            flex: 1,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {coordinatesText}
        </span>
      </Tooltip>
      <Tooltip
        title={isDisabled ? disabledTooltipText : ''}
        placement="top"
      >
        <button
          type="button"
          onClick={() => !isDisabled && onOpenModal(rowIndex)}
          disabled={isDisabled}
          style={{
            background: 'none',
            border: 'none',
            cursor: isDisabled ? 'not-allowed' : 'pointer',
            padding: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <BsPinMap size={16} />
        </button>
      </Tooltip>
    </div>
  );
};
