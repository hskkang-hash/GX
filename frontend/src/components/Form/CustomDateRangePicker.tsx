import { ConfigProvider, DatePicker } from 'antd';
import enLocale from 'antd/es/locale/en_US';
import koLocale from 'antd/es/locale/ko_KR';
import thLocale from 'antd/es/locale/th_TH';
import dayjs, { Dayjs } from 'dayjs';
import { Control, Controller, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '@/configs/Colors';

import './CustomDatePicker.scss';

interface CustomDateRangePickerProps {
  fromName: string;
  toName: string;
  label?: string;
  control?: Control<any>;
  required?: boolean;
  value?: [Dayjs | null, Dayjs | null];
  onChange?: (dates: [Dayjs | null, Dayjs | null]) => void;
  format?: string;
  placeholder?: [string, string];
  heightForDashboard?: boolean;
}

const CustomDateRangePicker = ({
  fromName,
  toName,
  label,
  control,
  required,
  value,
  onChange,
  format = 'MM-DD-YYYY',
  placeholder,
  heightForDashboard = false,
  ...props
}: CustomDateRangePickerProps) => {
  const { i18n } = useTranslation();
  const [theme] = useTheme();
  const renderDateRangePicker = (
    fromValue: Dayjs | null,
    toValue: Dayjs | null,
    onFromChange: (date: string | null) => void,
    onToChange: (date: string | null) => void,
  ) => (
    <div
      className={` custom-datepicker ${heightForDashboard ? 'height-for-dashboard' : ''}`}
    >
      {label && (
        <label
          className={`mb-2 fw-semibold text-base  ${theme === 'dark' ? 'text-light' : 'text-black'
            }`}
        >
          {label} {required && <span className="text-red-500">*</span>}
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
              colorPrimary:
                theme === 'dark' ? Colors.PrimaryDark : Colors.Primary,
              colorBorder: theme === 'dark' ? Colors.Gray6 : Colors.Gray4,

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
          },
        }}
      >
        <DatePicker.RangePicker
          className={`custom-dateRangePicker `}
          {...props}
          value={[
            fromValue ? (typeof fromValue === 'string' ? dayjs(fromValue, format) : dayjs(fromValue)) : null,
            toValue ? (typeof toValue === 'string' ? dayjs(toValue, format) : dayjs(toValue)) : null,
          ]}
          onChange={(dates) => {
            const [fromDate, toDate] = dates || [null, null];
            onFromChange(fromDate ? fromDate.format(format) : null);
            onToChange(toDate ? toDate.format(format) : null);
          }}
          placeholder={placeholder || ['', '']}
          format={format}
          allowClear={false}
        />
      </ConfigProvider>
    </div>
  );

  if (control) {
    return (
      <>
        <Controller
          name={fromName}
          control={control}
          render={({ field: fromField }) => (
            <Controller
              name={toName}
              control={control}
              render={({ field: toField }) =>
                renderDateRangePicker(
                  fromField.value
                    ? typeof fromField.value === 'string'
                      ? dayjs(fromField.value, format)
                      : dayjs(fromField.value)
                    : null,
                  toField.value
                    ? typeof toField.value === 'string'
                      ? dayjs(toField.value, format)
                      : dayjs(toField.value)
                    : null,
                  fromField.onChange,
                  toField.onChange,
                )
              }
            />
          )}
        />
      </>
    );
  }

  return renderDateRangePicker(
    value?.[0] || null,
    value?.[1] || null,
    (date) => onChange?.([date ? (typeof date === 'string' ? dayjs(date, format) : dayjs(date)) : null, value?.[1] || null]),
    (date) => onChange?.([value?.[0] || null, date ? (typeof date === 'string' ? dayjs(date, format) : dayjs(date)) : null]),
  );
};

export default CustomDateRangePicker;
