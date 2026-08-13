import { ConfigProvider, DatePicker } from 'antd';
import enLocale from 'antd/es/locale/en_US';
import koLocale from 'antd/es/locale/ko_KR';
import thLocale from 'antd/es/locale/th_TH';
import { Dayjs } from 'dayjs';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { GoHorizontalRule } from 'react-icons/go';
import { CustomBtn, FormBlock, useTheme } from 'rj-core';

import SearchIcon from '@/assets/images/Union.svg?react';

import i18n from '../../../i18n';
import { useDateFormat } from '../hooks/useDateFormat';

export const SearchCardDateTime = ({
  ref,
  value,
  setValue,
  handleSearch,
}: {
  ref: React.RefObject<HTMLDivElement | null>;
  value: {
    startDate: Dayjs | null;
    endDate: Dayjs | null;
  };
  setValue: (data: { startDate: Dayjs | null; endDate: Dayjs | null }) => void;
  handleSearch: (data: { startDate: Dayjs; endDate: Dayjs }) => void;
}) => {
  const [theme] = useTheme();
  const { t } = useTranslation();
  const { dateFormat } = useDateFormat();

  // Parse dates with fallback - try with format first, then without format
  const startDateValue = useMemo(() => {
    if (!value.startDate) return null;
    return value.startDate.isValid() ? value.startDate : null;
  }, [value.startDate]);

  const endDateValue = useMemo(() => {
    if (!value.endDate) return null;
    return value.endDate.isValid() ? value.endDate : null;
  }, [value.endDate]);

  return (
    <FormBlock
      ref={ref}
      className="d-flex gap-3 align-items-center"
    >
      <label
        className={`fw-semibold ${
          theme === 'dark' ? 'text-light' : 'text-black'
        }`}
      >
        {t('handover.Date to Search')}
      </label>
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
            colorBorder:
              theme === 'dark'
                ? 'var(--ga-dark-line-color)'
                : 'var(--ga-primary-2)',
          },
        }}
      >
        <DatePicker
          placeholder="Start Date"
          format={dateFormat}
          value={startDateValue}
          onChange={(date: Dayjs | null) => {
            setValue({
              ...value,
              startDate: date,
              endDate: null,
            });
          }}
          style={{ width: '11rem' }}
        />
        <GoHorizontalRule
          size={16}
          color={theme === 'dark' ? '#444646' : '#2D2E30'}
        />
        <DatePicker
          placeholder="End Date"
          format={dateFormat}
          value={endDateValue}
          onChange={(date: Dayjs | null) => {
            setValue({
              ...value,
              endDate: date,
            });
          }}
          disabledDate={(current) => {
            if (!startDateValue) return false;
            return current && current.isBefore(startDateValue, 'day');
          }}
          style={{ width: '11rem' }}
        />
        <CustomBtn
          type="button"
          variant="outline"
          color="primary"
          onClick={() => {
            handleSearch({
              startDate: value.startDate,
              endDate: value.endDate,
            });
          }}
          className="px-2"
          icon={
            <SearchIcon
              style={{
                width: '1.5rem',
                height: '1.5rem',
                color: 'var(--ga-primary)',
              }}
              className="search-plus"
              aria-label="search"
            />
          }
          id="advanceSearch"
        />
      </ConfigProvider>
    </FormBlock>
  );
};
