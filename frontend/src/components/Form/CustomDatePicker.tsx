import { ConfigProvider, DatePicker } from 'antd';
import enLocale from 'antd/es/locale/en_US';
import koLocale from 'antd/es/locale/ko_KR';
import thLocale from 'antd/es/locale/th_TH';
import dayjs from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import utc from 'dayjs/plugin/utc';
import { Control, Controller } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '@/configs/Colors';

import './CustomDatePicker.scss';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';
import timezone from 'dayjs/plugin/timezone';

dayjs.extend(customParseFormat);
dayjs.extend(utc);
dayjs.extend(timezone);

// Standard format for storing/sending to backend
const STORAGE_DATE_FORMAT = 'YYYY-MM-DD';

interface CustomDatePickerProps {
  name?: string;
  label?: string;
  control?: Control<any>;
  required?: boolean;
  value?: any; // dayjs object
  onChange?: (date: any) => void;
  format?: string;
  placeholder?: string;
  picker?: 'date' | 'month' | 'year' | 'datetime';
  disabledDate?: (current: dayjs.Dayjs) => boolean;
  disabled?: boolean;
  disablePastTime?: boolean;
  minDate?: dayjs.Dayjs | string;
  description?: string;
  disableDateFromDate?: dayjs.Dayjs | string;
  disabledTime?: (current: dayjs.Dayjs | null) => any;
}

const CustomDatePicker = ({
  name,
  label,
  control,
  required,
  value,
  onChange,
  disablePastTime = false,
  format = 'DD/MM/YYYY HH:mm',
  placeholder,
  picker = 'date',
  disabledDate,
  description,
  disableDateFromDate,
  disabledTime: customDisabledTime,
  ...props
}: CustomDatePickerProps) => {
  const { i18n } = useTranslation();
  const [theme] = useTheme();
  const { timeZoneFormat } = useConvertDate();

  console.log('timeZoneFormatvalue', value);

  const renderDatePicker = (
    dateValue: any,
    onDateChange: (date: any) => void,
    errorMessage?: string,
  ) => (
    <div className="flex flex-col custom-datepicker">
      {label && (
        <label
          style={{ marginBottom: '0.4em' }}
          className={` fw-semibold text-base  ${theme === 'dark' ? 'text-light' : 'text-black'}`}
        >
          {label} {required && <span style={{ color: Colors.Red }}>*</span>}
        </label>
      )}
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
            DatePicker: {
              activeBg: theme === 'dark' ? '#141414' : 'transparent',
              hoverBg: theme === 'dark' ? '#141414' : 'transparent',

              activeBorderColor:
                theme === 'dark'
                  ? 'var(--ga-light-theme-font-color)'
                  : 'var(--ga-primary-2)',
              hoverBorderColor:
                theme === 'dark'
                  ? 'var(--ga-dark-line-color)'
                  : 'var(--ga-primary)',
              cellActiveWithRangeBg:
                theme === 'dark' ? '#141414' : 'transparent',

              cellHoverBg:
                theme === 'dark'
                  ? 'var(--ga-light-theme-font-color)'
                  : 'var(--ga-primary-4)',
            },
          },
          token: {
            colorText:
              theme === 'dark'
                ? 'var(--ga-dark-theme-font-color)'
                : 'var(--ga-light-theme-font-color)',
            colorBgElevated: theme === 'dark' ? '#141414' : 'white',
            controlItemBgActive:
              theme === 'dark'
                ? 'var(--ga-light-theme-font-color)'
                : 'var(--ga-primary-4)',
            colorPrimaryBorder:
              theme === 'dark'
                ? 'var(--ga-dark-line-color)'
                : 'var(--ga-primary-2)',
            colorTextDisabled:
              theme === 'dark'
                ? 'var(--ga-dark-theme-font-color)'
                : 'var(--ga-light-theme-font-color)',
            colorIconHover:
              theme === 'dark'
                ? 'var(--ga-light-theme-font-color)'
                : 'var(--ga-primary-4)',
            colorBgContainerDisabled: theme === 'dark' ? '#262626' : '#f5f5f5',
          },
        }}
      >
        <DatePicker
          {...props}
          picker={picker === 'datetime' ? undefined : picker}
          showTime={picker === 'datetime'}
          value={
            dateValue
              ? dayjs.isDayjs(dateValue)
                ? dateValue
                : typeof dateValue === 'string'
                  ? // Check if ISO format (contains T and timezone offset like +00:00 or Z)
                  /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(dateValue)
                    ? dayjs(dateValue) // Parse ISO string directly (handles timezone)
                    : // Check if standard date format (YYYY-MM-DD)
                    /^\d{4}-\d{2}-\d{2}$/.test(dateValue)
                      ? dayjs(dateValue, STORAGE_DATE_FORMAT)
                      : format && dayjs(dateValue, format).isValid()
                        ? dayjs(dateValue, format)
                        : dayjs(dateValue)
                  : dayjs(dateValue)
              : null
          }
          onChange={(date) => {
            // Save in standard format for backend (YYYY-MM-DD for date, ISO for datetime)
            if (date) {
              const outputFormat = picker === 'datetime' ? undefined : STORAGE_DATE_FORMAT;
              onDateChange(outputFormat ? date.format(outputFormat) : date.toISOString());
            } else {
              onDateChange(null);
            }
          }}
          placeholder={placeholder || label}
          format={format}
          disabledDate={(current) => {
            if (!current) return false;
            if (disabledDate) return disabledDate(current);
            if (disableDateFromDate) {
              const min = dayjs(disableDateFromDate)
                .tz(timeZoneFormat)
                .add(1, 'day')
                .startOf('day');
              if (current.isBefore(min)) return true;
            }

            if (disablePastTime) {
              return current.isBefore(dayjs().tz(timeZoneFormat).startOf('day'));
            }
            return false;
          }}
          //if select today, disable past time
          disabledTime={(current) => {
            // If custom disabledTime is provided, use it
            if (customDisabledTime) {
              return customDisabledTime(current);
            }
            
            if (!disablePastTime || !current || disabledDate) return {};
            // if select today, disable past time
            if (current.tz(timeZoneFormat).isSame(dayjs().tz(timeZoneFormat), 'day')) {
              const currentHour = dayjs().tz(timeZoneFormat).hour();
              const currentMinute = dayjs().tz(timeZoneFormat).minute();

              return {
                disabledHours: () =>
                  Array.from({ length: currentHour }, (_, i) => i), // disable past hours
                disabledMinutes: (selectedHour) =>
                  selectedHour === currentHour
                    ? Array.from({ length: currentMinute }, (_, i) => i) // disable past minutes in current hour
                    : [],
              };
            }
            return {};
          }}
          status={errorMessage ? 'error' : undefined}
        />
      </ConfigProvider>

      {errorMessage && <div className="error-message">{errorMessage}</div>}
      {description && <div className="description">{description}</div>}
    </div>
  );

  if (control && name) {
    return (
      <Controller
        name={name}
        control={control}
        render={({ field, fieldState: { error } }) =>
          renderDatePicker(field.value, field.onChange, error?.message)
        }
      />
    );
  }

  return renderDatePicker(value, onChange || (() => { }));
};

export default CustomDatePicker;
