import { Box, Button, Typography } from '@mui/material';
import { ConfigProvider, DatePicker } from 'antd';
import enLocale from 'antd/es/locale/en_US';
import koLocale from 'antd/es/locale/ko_KR';
import thLocale from 'antd/es/locale/th_TH';
import dayjs, { Dayjs } from 'dayjs';
import React from 'react';
import { Control, Controller } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { GoHorizontalRule } from 'react-icons/go';
import { useTheme } from 'rj-core';

interface DateRangeQuickSelectProps {
  fromName?: string;
  toName?: string;
  control?: Control<any>; // eslint-disable-line @typescript-eslint/no-explicit-any
  value?: [Dayjs | null, Dayjs | null];
  onChange?: (dates: [Dayjs | null, Dayjs | null]) => void;
  onDateRangeChange?: (dateRange: {
    start_date: string;
    end_date: string;
  }) => void;
  format?: string;
  placeholder?: [string, string];
  picker?: 'date' | 'month' | 'year';
  disabledDate?: (current: dayjs.Dayjs) => boolean;
}

interface QuickSelectOption {
  label: string;
  value: string;
  getDateRange: () => { start: Dayjs; end: Dayjs };
}

export default function DateRangeQuickSelect({
  fromName,
  toName,
  control,
  value,
  onChange,
  onDateRangeChange,
  format = 'MM-DD-YYYY',
  placeholder,
  picker = 'date',
  disabledDate,
  ...props
}: DateRangeQuickSelectProps) {
  const { t, i18n } = useTranslation();
  const [theme] = useTheme();

  const quickSelectOptions: QuickSelectOption[] = [
    {
      label: t('delivery.Today') || 'Today',
      value: 'today',
      getDateRange: () => ({
        start: dayjs().startOf('day'),
        end: dayjs().endOf('day'),
      }),
    },
    {
      label: t('delivery.This week') || 'This week',
      value: 'thisweek',
      getDateRange: () => ({
        start: dayjs().startOf('week'),
        end: dayjs().endOf('week'),
      }),
    },
    {
      label: t('delivery.This month') || 'This month',
      value: 'thismonth',
      getDateRange: () => ({
        start: dayjs().startOf('month'),
        end: dayjs().endOf('month'),
      }),
    },
    {
      label: t('delivery.This year') || 'This year',
      value: 'thisyear',
      getDateRange: () => ({
        start: dayjs().startOf('year'),
        end: dayjs().endOf('year'),
      }),
    },
    {
      label: t('delivery.All') || 'All',
      value: 'all',
      getDateRange: () => ({
        start: null as unknown as Dayjs,
        end: null as unknown as Dayjs,
      }),
    },
  ];

  const handleQuickSelect = (
    option: QuickSelectOption,
    onFromChange: (date: string | null) => void,
    onToChange: (date: string | null) => void,
  ) => {
    const { start, end } = option.getDateRange();
    const startStr = start ? start.format('YYYY-MM-DD') : null;
    const endStr = end ? end.format('YYYY-MM-DD') : null;

    onFromChange(startStr);
    onToChange(endStr);

    // If onDateRangeChange is provided, call it with both dates
    if (onDateRangeChange && startStr && endStr) {
      onDateRangeChange({
        start_date: startStr,
        end_date: endStr,
      });
    }
  };

  // Create disabled date functions for validation
  const getStartDateDisabled = (
    endDate: Dayjs | null,
    customDisabledDate?: (current: dayjs.Dayjs) => boolean,
  ) => {
    return (current: dayjs.Dayjs) => {
      // Apply custom disabled date logic first
      if (customDisabledDate && customDisabledDate(current)) {
        return true;
      }

      // Disable dates after end date
      if (endDate && current.isAfter(endDate, 'day')) {
        return true;
      }

      return false;
    };
  };

  const getEndDateDisabled = (
    startDate: Dayjs | null,
    customDisabledDate?: (current: dayjs.Dayjs) => boolean,
  ) => {
    return (current: dayjs.Dayjs) => {
      // Apply custom disabled date logic first
      if (customDisabledDate && customDisabledDate(current)) {
        return true;
      }

      // Disable dates before start date
      if (startDate && current.isBefore(startDate, 'day')) {
        return true;
      }

      return false;
    };
  };

  // Validation helper function
  const isPartialSelection = (
    fromValue: Dayjs | null,
    toValue: Dayjs | null,
  ): boolean => {
    return (!!fromValue && !toValue) || (!fromValue && !!toValue);
  };

  const renderDateRangePicker = (
    fromValue: Dayjs | null,
    toValue: Dayjs | null,
    onFromChange: (date: string | null) => void,
    onToChange: (date: string | null) => void,
  ) => (
    <Box
      display="flex"
      flexDirection="column"
      gap={2}
    >
      {/* Date Range Picker */}
      <Box
        display="flex"
        alignItems="center"
        gap={1}
      >
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
            },
          }}
        >
          {/* Start Date Picker */}
          <DatePicker
            {...props}
            picker={picker}
            value={fromValue}
            onChange={(date) => {
              const dateStr = date ? date.format('YYYY-MM-DD') : null;

              if (!date) {
                // If clearing start date, also clear end date to maintain validation
                onFromChange(null);
                onToChange(null);
                return;
              }

              onFromChange(dateStr);

              // If start date is after end date, clear end date
              if (date && toValue && date.isAfter(toValue, 'day')) {
                onToChange(null);
                return;
              }

              // If onDateRangeChange is provided, call it with both dates
              if (onDateRangeChange && dateStr && toValue) {
                onDateRangeChange({
                  start_date: dateStr,
                  end_date: toValue.format('YYYY-MM-DD'),
                });
              }
            }}
            placeholder={placeholder?.[0] || 'Start Date'}
            format={format}
            disabledDate={getStartDateDisabled(toValue, disabledDate)}
            className={`${theme}`}
            status={
              isPartialSelection(fromValue, toValue) ? 'error' : undefined
            }
          />

          <GoHorizontalRule
            size={32}
            color={theme === 'dark' ? '#444646' : '#2D2E30'}
          />

          {/* End Date Picker */}
          <DatePicker
            {...props}
            picker={picker}
            value={toValue}
            onChange={(date) => {
              const dateStr = date ? date.format('YYYY-MM-DD') : null;

              if (!date) {
                // If clearing end date, also clear start date to maintain validation
                onFromChange(null);
                onToChange(null);
                return;
              }

              onToChange(dateStr);

              // If end date is before start date, clear start date
              if (date && fromValue && date.isBefore(fromValue, 'day')) {
                onFromChange(null);
                return;
              }

              // If onDateRangeChange is provided, call it with both dates
              if (onDateRangeChange && dateStr && fromValue) {
                onDateRangeChange({
                  start_date: fromValue.format('YYYY-MM-DD'),
                  end_date: dateStr,
                });
              }
            }}
            placeholder={placeholder?.[1] || 'End Date'}
            format={format}
            disabledDate={getEndDateDisabled(fromValue, disabledDate)}
            className={`${theme}`}
            status={
              isPartialSelection(fromValue, toValue) ? 'error' : undefined
            }
          />
        </ConfigProvider>
      </Box>

      {/* Quick Select Buttons */}
      <Box
        className="quick-select-buttons-container"
        display="flex"
        flexWrap="wrap"
        gap={1}
        sx={{
          '& .quick-select-btn': {
            fontSize: '0.875rem',
            padding: '4px 8px',
            textTransform: 'none',
            minWidth: 'auto',
            borderRadius: '1.25rem',
            fontWeight: '400',
            color: theme === 'dark' ? '#fff' : '#000',
            backgroundColor: '#F2F2F2',
            '&:hover': {
              fontWeight: '600',
              color:
                theme === 'dark'
                  ? 'var(--ga-primary-dark)'
                  : 'var(--ga-primary)',
            },
            '&.clear-btn': {
              backgroundColor: '#fff2f0',
              color: '#ff4d4f',
              borderColor: '#ffccc7',
              '&:hover': {
                backgroundColor: '#fff1f0',
                borderColor: '#ff7875',
              },
            },
          },
        }}
      >
        {quickSelectOptions.map((option) => (
          <Button
            key={option.value}
            className={`quick-select-btn ${option.value === 'clear' ? 'clear-btn' : ''}`}
            size="small"
            onClick={() => handleQuickSelect(option, onFromChange, onToChange)}
          >
            {option.label}
          </Button>
        ))}
      </Box>

      {/* Validation Helper Text */}
      {isPartialSelection(fromValue, toValue) && (
        <Box>
          <Typography
            variant="caption"
            sx={{
              color: '#ff4d4f',
              fontSize: '0.75rem',
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
            }}
          >
            ⚠️{' '}
            {t('Please select both start and end dates, or clear both') ||
              'Please select both start and end dates, or clear both'}
          </Typography>
        </Box>
      )}
    </Box>
  );

  // Helper function to parse date string with multiple format support
  const parseDateValue = (value: string | null | undefined): Dayjs | null => {
    if (!value) return null;

    // Try parsing with the provided format first
    const parsedWithFormat = dayjs(value, format, true);
    if (parsedWithFormat.isValid()) {
      return parsedWithFormat;
    }

    // Fallback: try ISO format (YYYY-MM-DD) which is used by quick select and onChange
    const parsedISO = dayjs(value, 'YYYY-MM-DD', true);
    if (parsedISO.isValid()) {
      return parsedISO;
    }

    // Last resort: let dayjs try to parse automatically
    const parsedAuto = dayjs(value);
    if (parsedAuto.isValid()) {
      return parsedAuto;
    }

    return null;
  };

  // If using with form control (fromName and toName)
  if (control && fromName && toName) {
    return (
      <Controller
        name={fromName}
        control={control}
        render={({ field: fromField }) => (
          <Controller
            name={toName}
            control={control}
            render={({ field: toField }) =>
              renderDateRangePicker(
                parseDateValue(fromField.value),
                parseDateValue(toField.value),
                fromField.onChange,
                toField.onChange,
              )
            }
          />
        )}
      />
    );
  }

  // If using with value and onChange props
  return renderDateRangePicker(
    value?.[0] || null,
    value?.[1] || null,
    (date) => onChange?.([date ? dayjs(date, 'YYYY-MM-DD') : null, value?.[1] || null]),
    (date) => onChange?.([value?.[0] || null, date ? dayjs(date, 'YYYY-MM-DD') : null]),
  );
}
