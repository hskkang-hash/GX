import { SearchOutlined } from '@ant-design/icons';
import { Box, styled } from '@mui/material';
import {
  Radio,
  Button,
  Checkbox,
  ConfigProvider,
  DatePicker,
  Input,
  AutoComplete,
  Select,
  Spin,
  theme as antdTheme,
} from 'antd';
import enLocale from 'antd/es/locale/en_US';
import koLocale from 'antd/es/locale/ko_KR';
import thLocale from 'antd/es/locale/th_TH';
import dayjs from 'dayjs';
import React, { useState, useEffect, forwardRef } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { GoDash } from 'react-icons/go';
import {
  FormBlock,
  CustomInputHookForm,
  CustomBtn,
  useTheme,
  ToastTopHelper,
} from 'rj-core';

import '@/assets/styles/CustomDateTimePicker.scss';
import CustomTextarea from '@/components/Form/CustomTextarea';
import type { NotamSearchParams } from '@/services/notamService';
import { getDefaultSearchParams } from '@/services/notamService';

import './NotamSearchForm.scss';

const CustomSelect = styled(Select)`
  & .ant-select-selector {
    min-height: 2.9rem !important;
    padding: 4px 11px !important;
  }

  & .ant-select-selection-overflow {
    gap: 4px;
  }
`;

interface NotamSearchFormProps {
  onSearch: (params: NotamSearchParams) => void;
  loading?: boolean;
}

interface AirportOption {
  DESIGNATOR: string;
  NAME: string;
}

const SERIES_OPTIONS = ['A', 'C', 'D', 'E', 'G', 'Z', 'SNOWTAM'];

const NotamSearchForm = forwardRef<HTMLDivElement, NotamSearchFormProps>(
  ({ onSearch, loading = false }, ref) => {
    const { t, i18n } = useTranslation();
    const [theme] = useTheme();
    const { control, watch, setValue } = useForm({
      defaultValues: {
        search_type: 'V',
        sch_inorout: 'D',
        sch_notam_no: '',
        sch_airport: '',
        sch_elevation_min: '',
        sch_elevation_max: '',
        sch_full_text: '',
      },
    });

    const [selectedSeries, setSelectedSeries] = useState<string[]>([]);
    const [seriesInputText, setSeriesInputText] = useState<string>('');
    const [airspaceType, setAirspaceType] = useState<string[]>([]);
    const [startDateTime, setStartDateTime] = useState<dayjs.Dayjs | null>(
      null,
    );
    const [endDateTime, setEndDateTime] = useState<dayjs.Dayjs | null>(null);
    const [locationOptions, setLocationOptions] = useState<AirportOption[]>([]);
    const [locationLoading, setLocationLoading] = useState(false);
    const [locationSearchValue, setLocationSearchValue] = useState<string>('');
    const [selectedLocations, setSelectedLocations] = useState<string[]>([]);

    const inorout = watch('sch_inorout');

    useEffect(() => {
      // Initialize datetime with default values
      const defaultParams = getDefaultSearchParams();
      const startDT = `${defaultParams.sch_from_date} ${defaultParams.sch_from_time?.slice(0, 2)}:${defaultParams.sch_from_time?.slice(2, 4)}`;
      const endDT = `${defaultParams.sch_to_date} ${defaultParams.sch_to_time?.slice(0, 2)}:${defaultParams.sch_to_time?.slice(2, 4)}`;

      setStartDateTime(dayjs(startDT));
      setEndDateTime(dayjs(endDT));
    }, []);

    // Clear location search when switching between DOM/INT
    useEffect(() => {
      setLocationSearchValue('');
      setLocationOptions([]);
      setSelectedLocations([]);
      setValue('sch_airport', '');
    }, [inorout, setValue]);

    // Search airports for location autocomplete (INT mode)
    const searchAirports = async (searchText: string) => {
      if (!searchText || searchText.trim().length < 2) {
        setLocationOptions([]);
        return;
      }

      setLocationLoading(true);
      try {
        const apiUrl = import.meta.env.VITE_API_URL || '';
        const proxyEndpoint = `${apiUrl}/api/proxy/airport-search`;

        const response = await fetch(proxyEndpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            sch_location: searchText.trim(),
            sch_fir: '',
          }),
        });

        if (response.ok) {
          const data: AirportOption[] = await response.json();
          setLocationOptions(data || []);
        } else {
          console.error('Airport search failed:', response.statusText);
          setLocationOptions([]);
        }
      } catch (error) {
        console.error('Error searching airports:', error);
        setLocationOptions([]);
      } finally {
        setLocationLoading(false);
      }
    };

    const handleSeriesClick = (series: string) => {
      if (series === 'SNOWTAM') {
        // SNOWTAM is separate - toggle selection
        setSelectedSeries((prev) => {
          return prev.includes('SNOWTAM')
            ? prev.filter((s) => s !== 'SNOWTAM')
            : [...prev, 'SNOWTAM'];
        });
        return;
      }

      setSelectedSeries((prev) => {
        const newSelection = prev.includes(series)
          ? prev.filter((s) => s !== series)
          : [...prev, series];

        return newSelection;
      });
    };

    const handleAirspaceChange = (values: string[]) => {
      setAirspaceType(values);
    };

    const handleSearch = () => {
      const values = watch();

      // Validation for INT mode: location is required
      if (inorout === 'I') {
        if (selectedLocations.length === 0) {
          ToastTopHelper.error(
            t('Location is required for International (INT) search'),
          );
          return;
        }
      }

      // Parse datetime values
      let fromDate = '';
      let fromTime = '';
      let toDate = '';
      let toTime = '';

      if (startDateTime) {
        fromDate = startDateTime.format('YYYY-MM-DD');
        fromTime = startDateTime.format('HHmm');
      }

      if (endDateTime) {
        toDate = endDateTime.format('YYYY-MM-DD');
        toTime = endDateTime.format('HHmm');
      }

      // For INT mode, use text input for series; for DOM mode, use button selections
      const seriesValue =
        inorout === 'I' ? seriesInputText : selectedSeries.join(',');

      const searchParams: NotamSearchParams = {
        ...values,
        sch_series: seriesValue,
        sch_select: airspaceType.join(','),
        sch_from_date: fromDate,
        sch_from_time: fromTime,
        sch_to_date: toDate,
        sch_to_time: toTime,
        ibpage: 1,
      };

      onSearch(searchParams);
    };

    return (
      <div
        className="notam-search-form"
        ref={ref}
      >
        <FormBlock>
          <div className="form-grid">
            {/* DOM/INT Radio */}
            <div className="">
              <div className="radio-group-container">
                <Radio.Group
                  value={inorout}
                  onChange={(e) => setValue('sch_inorout', e.target.value)}
                >
                  <Radio value="D">{t('DOM')}</Radio>
                  <Radio value="I">{t('INT')}</Radio>
                </Radio.Group>
              </div>
            </div>

            {/* AIRSPACE */}
            <div className="">
              <div className="airspace-field">
                <label className="field-label">{t('Airspace')}</label>
                <Checkbox.Group
                  options={[
                    { label: t('All'), value: 'all' },
                    { label: t('Prohibited'), value: 'prohibited' },
                    { label: t('Restricted'), value: 'restricted' },
                    {
                      label: t('Temporary Restricted'),
                      value: 'temporary_restricted',
                    },
                    {
                      label: t('Airspace Reservation'),
                      value: 'airspace_reservation',
                    },
                  ]}
                  onChange={handleAirspaceChange}
                />
              </div>
            </div>

            {/* Date Range */}
            <div className="">
              <div className="datetime-range-container">
                <label className="datetime-label">{t('Effective Date')}</label>
                <div className="datetime-pickers">
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
                          activeBg:
                            theme === 'dark' ? '#141414' : 'transparent',
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
                    <DatePicker
                      showTime
                      className="date-picker"
                      placeholder=""
                      format="YYYY-MM-DD HH:mm"
                      value={startDateTime}
                      onChange={(date) => setStartDateTime(date)}
                    />
                    <GoDash className="datetime-separator" />
                    <DatePicker
                      showTime
                      className="date-picker"
                      placeholder=""
                      format="YYYY-MM-DD HH:mm"
                      value={endDateTime}
                      onChange={(date) => setEndDateTime(date)}
                      disabledDate={(current) =>
                        !!(
                          current &&
                          startDateTime &&
                          current.isBefore(startDateTime, 'day')
                        )
                      }
                    />
                  </ConfigProvider>
                </div>
              </div>
            </div>

            {/* SERIES */}
            <div className="">
              <div className="series-field">
                <label
                  className="field-label"
                  style={{
                    color: theme === 'dark' ? '#fff' : '#000',
                  }}
                >
                  SERIES
                </label>
                {inorout === 'I' ? (
                  <CustomInputHookForm
                    name="sch_series"
                    control={control}
                    placeholder="Enter series"
                  />
                ) : (
                  <div className="series-buttons">
                    {SERIES_OPTIONS.map((series) => (
                      <Button
                        key={series}
                        type={
                          selectedSeries.includes(series)
                            ? 'primary'
                            : 'default'
                        }
                        onClick={() => handleSeriesClick(series)}
                        className="series-button"
                      >
                        {series}
                      </Button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* NOTAM NO + LOCATION */}
            <div>
              <CustomInputHookForm
                name="sch_notam_no"
                label="NOTAM NO"
                control={control}
                placeholder="NOTAM NO"
              />
            </div>
            <div>
              <div>
                <label
                  style={{
                    display: 'block',
                    marginBottom: '0.4rem',
                    fontWeight: 600,
                    fontSize: '1rem',
                    color: theme === 'dark' ? '#fff' : '#000',
                  }}
                >
                  {t('Location')}{' '}
                  {inorout === 'I' && <span style={{ color: 'red' }}>*</span>}
                </label>
                <ConfigProvider
                  theme={{
                    algorithm:
                      theme === 'dark'
                        ? antdTheme.darkAlgorithm
                        : antdTheme.defaultAlgorithm,
                    token: {
                      fontSizeIcon: 16,
                      fontSize: 14,
                      controlHeight: '2.975rem',
                      colorText:
                        theme === 'dark'
                          ? 'var(--ga-dark-theme-font-color)'
                          : 'var(--ga-light-theme-font-color)',
                      colorBgElevated: theme === 'dark' ? '#141414' : 'white',
                      controlItemBgActive:
                        theme === 'dark'
                          ? 'var(--ga-light-theme-font-color)'
                          : 'var(--ga-primary-4)',
                    },
                  }}
                >
                  <CustomSelect
                    mode="multiple"
                    value={selectedLocations}
                    options={locationOptions.map((airport) => ({
                      value: airport.DESIGNATOR,
                      label: (
                        <div
                          style={{
                            color: theme === 'dark' ? '#fff' : '#000',
                            fontSize: '14px',
                          }}
                        >
                          <span style={{ fontWeight: 500 }}>
                            {airport.DESIGNATOR}
                          </span>{' '}
                          -{' '}
                          <span style={{ color: '#8c8c8c' }}>
                            {airport.NAME}
                          </span>
                        </div>
                      ),
                    }))}
                    onSearch={(text) => {
                      setLocationSearchValue(text);
                      searchAirports(text);
                    }}
                    onChange={(values: string[]) => {
                      setSelectedLocations(values);
                      setValue('sch_airport', values.join(','));
                      // Clear search after selection to allow searching for more
                      setLocationSearchValue('');
                      setLocationOptions([]);
                    }}
                    placeholder={t('Search location...')}
                    style={{ width: '100%' }}
                    notFoundContent={
                      locationLoading ? (
                        <Spin size="small" />
                      ) : locationSearchValue.length >= 2 ? (
                        t('No results found')
                      ) : null
                    }
                    filterOption={false}
                    allowClear
                    showSearch
                    searchValue={locationSearchValue}
                    onClear={() => {
                      setSelectedLocations([]);
                      setValue('sch_airport', '');
                      setLocationSearchValue('');
                      setLocationOptions([]);
                    }}
                    dropdownStyle={{
                      backgroundColor: theme === 'dark' ? '#1F1F20' : '#ffffff',
                    }}
                  />
                </ConfigProvider>
              </div>
            </div>

            {/* ELEVATION */}
            <div className="">
              <div className="elevation-field">
                <label className="elevation-main-label">{t('Elevation')}</label>
                <div className="elevation-group">
                  <div className="elevation-group-item">
                    <span className="elevation-label">LOWER</span>
                    <CustomInputHookForm
                      name="sch_elevation_min"
                      control={control}
                      placeholder="000"
                    />
                    <span className="elevation-unit">FL</span>
                  </div>
                  <div className="elevation-group-item">
                    <span className="elevation-label">UPPER</span>
                    <CustomInputHookForm
                      name="sch_elevation_max"
                      control={control}
                      placeholder="999"
                    />
                    <span className="elevation-unit">FL</span>
                  </div>
                </div>
              </div>
            </div>

            {/* TEXT */}
            <div className="">
              <CustomTextarea
                control={control}
                name="sch_full_text"
                label={t('Text')}
                placeholder={t(
                  'If you want to search for multiple words shall be entered separated by "&".',
                )}
                className="message-textarea"
                rows={3}
              />
            </div>

            {/* Search Button */}
            <Box
              className="grid-span-full"
              display="flex"
              justifyContent="center"
              mt={1.5}
            >
              <CustomBtn
                type="button"
                variant="outline"
                color="primary"
                size="lg"
                onClick={handleSearch}
                loading={loading}
                icon={<SearchOutlined style={{ marginRight: '0.5rem' }} />}
                label={t('Search')}
              />
            </Box>
          </div>
        </FormBlock>
      </div>
    );
  },
);

export default NotamSearchForm;
