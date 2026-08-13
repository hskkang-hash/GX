import { EnvironmentOutlined } from '@ant-design/icons';
import { Box, styled } from '@mui/material';
import {
  theme as antdTheme,
  AutoComplete,
  ConfigProvider,
  Pagination,
  Radio,
  Skeleton,
  Spin,
  Table,
  Typography,
} from 'antd';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme, useUserInfo } from 'rj-core';

import getDateTimeFormat from '@/features/Dashboard/utils/formatDateTime';

import './CustomSearchMapV2.scss';

const { Text } = Typography;

const CustomAutoComplete = styled(AutoComplete)`
  & .ant-select {
    & .ant-select-selector {
      height: 2.9rem;
    }
  }
`;

interface LocationSuggestion {
  id: string;
  description: string;
  city?: string;
  place_id?: string;
  structured_formatting?: {
    main_text: string;
    secondary_text: string;
  };
  lat?: number;
  lng?: number;
  zonecode?: string;
  roadAddress?: string;
  jibunAddress?: string;
  sido?: string;
  sigungu?: string;
  bname?: string;
  province?: string;
  district?: string;
  township?: string;
  road_name?: string;
  main_building_no?: string;
  sub_building_no?: string;
  building_name?: string;
  disabled?: boolean;
  weatherData?: any;
}

interface KakaoAddressResult {
  address: {
    address_name: string;
    region_1depth_name: string;
    region_2depth_name: string;
    region_3depth_name: string;
    mountain_yn: string;
    main_address_no: string;
    sub_address_no: string;
    zip_code: string;
  } | null;
  road_address: {
    address_name: string;
    region_1depth_name: string;
    region_2depth_name: string;
    region_3depth_name: string;
    road_name: string;
    underground_yn: string;
    main_building_no: string;
    sub_building_no: string;
    building_name: string;
    zone_no: string;
  } | null;
}

interface CustomSearchMapProps {
  placeholder?: string;
  onSelect?: (value: string, option: LocationSuggestion) => void;
  onSearch?: (searchText: string) => void;
  className?: string;
  style?: React.CSSProperties;
  disabled?: boolean;
  allowClear?: boolean;
  autoFocus?: boolean;
  value?: string;
  onChange?: (value: string) => void;
  onClear?: () => void;
  label?: string;
  isRequired?: boolean;
}

const CustomTable = styled(Table)<{ $theme?: string }>`
  & .ant-table-thead > tr > th {
    background-color: ${({ $theme }) =>
      $theme === 'dark' ? '#3C3D3E' : '#f0f0f0'};
    font-weight: 400;
    // color: #000;
  }

  & .ant-table-cell:first-of-type {
    border-left: 1px solid
      ${({ $theme }) => ($theme === 'dark' ? '#3C3D3E' : '#DDDFE2')};
    border-right: 1px solid
      ${({ $theme }) => ($theme === 'dark' ? '#3C3D3E' : '#DDDFE2')};
    text-align: center;
    border-start-start-radius: 0 !important;
  }
  & .ant-table-cell:nth-of-type(2) {
    border-right: 1px solid
      ${({ $theme }) => ($theme === 'dark' ? '#3C3D3E' : '#DDDFE2')};
  }

  & .ant-table-cell:last-child {
    border-right: none;
    border-start-end-radius: 0 !important;
  }

  .ant-table-body {
    scrollbar-width: auto;
    scrollbar-color: auto;
  }
  .ant-table-body::-webkit-scrollbar {
    width: 6px;
  }

  .ant-table-body::-webkit-scrollbar-track {
    background-color: transparent;
  }

  .ant-table-body::-webkit-scrollbar-thumb {
    border-radius: 6px;
    background-color: #c1c1c1;
    cursor: pointer;
  }
  .ant-table-body::-webkit-scrollbar-thumb:hover {
    border-radius: 6px;
    background-color: #c9c9c9;
    cursor: pointer !important;
  }

  /* Sử dụng !important và specificity cao hơn */
  && .ant-select-dropdown {
    background-color: ${({ $theme }) =>
      $theme === 'dark' ? 'red' : '#ffffff'} !important;
  }

  /* Hoặc sử dụng CSS selector mạnh hơn */
  &&&& .ant-select-dropdown {
    background-color: ${({ $theme }) =>
      $theme === 'dark' ? 'red' : '#ffffff'} !important;
  }
`;

const CustomPagination = styled(Pagination)`
  height: 32px !important;
  text-align: center;
  padding: 4px 0;
  margin-bottom: 4px;
  & .ant-pagination-item {
    border-radius: 0;
    height: 32px !important;
    width: 32px !important;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    // border: 1px solid #DDDFE2;
    // color: #000;
    // font-size: 12px;
    // font-weight: 400;
  }

  & .ant-pagination-prev,
  & .ant-pagination-next {
    height: 32px !important;
    width: 32px !important;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  & .ant-pagination-item-active {
    border: none;
    background-color: var(--ga-primary);
    color: #fff;
  }
  & .ant-pagination-item-link {
    background-color: var(--ga-primary);
    color: #fff;
  }
  & .ant-pagination-item-link:hover {
    background-color: var(--ga-primary);
    color: #fff;
  }
`;

const CustomSearchMapAnYang: React.FC<CustomSearchMapProps> = ({
  placeholder = 'Address',
  onSelect,
  onSearch,
  className,
  disabled = false,
  allowClear = true,
  autoFocus = false,
  value,
  label,
  isRequired,
  onChange,
  onClear,
  style,
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [searchValue, setSearchValue] = useState<string>(value || '');
  const [suggestions, setSuggestions] = useState<LocationSuggestion[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [searchResults, setSearchResults] = useState<LocationSuggestion[]>([]);
  const [searchLoading, setSearchLoading] = useState<boolean>(false);
  const [searchPage, setSearchPage] = useState<number>(1);
  const [searchTextPage, setSearchTextPage] = useState<number>(1);
  const [searchHasNext, setSearchHasNext] = useState<boolean>(false);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [enrichingIds, setEnrichingIds] = useState<string[]>([]);
  const [selectedDetail, setSelectedDetail] =
    useState<LocationSuggestion | null>(null);

  const [activeTab, setActiveTab] = useState<string>('road');
  const debounceTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const autoCompleteRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [weatherLoadingIds, setWeatherLoadingIds] = useState<string[]>([]);
  const [showDropdown, setShowDropdown] = useState<boolean>(false);

  // Autocomplete suggestions with pagination
  const fetchAutocompleteSuggestions = useCallback(
    async (
      searchText: string,
      page: number,
    ): Promise<{
      results: LocationSuggestion[];
      hasNext: boolean;
      last: number;
      total: number;
    }> => {
      if (
        !searchText ||
        searchText.length < 2 ||
        !window.kakao?.maps?.services
      ) {
        return { results: [], hasNext: false, last: 1, total: 0 };
      }
      return new Promise((resolve) => {
        const places = new window.kakao.maps.services.Places();
        places.keywordSearch(
          searchText,
          (data: any[], status: string, pagination: any) => {
            if (status === window.kakao.maps.services.Status.OK) {
              const mapped: LocationSuggestion[] = data.map((item) => {
                return {
                  id: item.id || item.road_address_name,
                  description: item.road_address_name,
                  city: item.road_address_name.split(' ')[0],
                  place_id: item.id,
                  lat: item.y,
                  lng: item.x,
                  structured_formatting: {
                    main_text: item.place_name,
                    secondary_text: item.road_address_name,
                  },
                };
              });
              resolve({
                results: mapped,
                hasNext: pagination.hasNextPage,
                last: pagination.last,
                total: pagination.totalCount || 0,
              });
            } else {
              resolve({ results: [], hasNext: false, last: 1, total: 0 });
            }
          },
          { page, size: 10 },
        );
      });
    },
    [],
  );

  // Search results (page, size=10)
  const fetchSearchResults = useCallback(
    async (
      searchText: string,
      page: number,
    ): Promise<{
      results: LocationSuggestion[];
      hasNext: boolean;
      last: number;
    }> => {
      if (
        !searchText ||
        searchText.length < 2 ||
        !window.kakao?.maps?.services
      ) {
        return { results: [], hasNext: false, last: 1 };
      }
      return new Promise((resolve) => {
        const places = new window.kakao.maps.services.Places();
        places.keywordSearch(
          searchText,
          (data: any[], status: string, pagination: any) => {
            console.log(data, status, pagination);
            if (status === window.kakao.maps.services.Status.OK) {
              const mapped: LocationSuggestion[] = data.map((item) => ({
                id: item.id || item.road_address_name,
                description: item.road_address_name,
                place_id: item.id,
                lat: item.y,
                lng: item.x,
                structured_formatting: {
                  main_text: item.place_name,
                  secondary_text: item.road_address_name,
                },
              }));
              resolve({
                results: mapped,
                hasNext: pagination.hasNextPage,
                last: pagination.last,
              });
            } else {
              resolve({ results: [], hasNext: false, last: 1 });
            }
          },
          { page, size: 10 },
        );
      });
    },
    [],
  );

  // get full address info from lat/lng
  const fetchFullAddressInfo = (
    lat: number,
    lng: number,
  ): Promise<{
    fullAddress: string;
    province: string;
    district: string;
    township: string;
    sido: string;
    sigungu: string;
    bname: string;
    roadAddress: string;
    jibunAddress: string;
    zonecode: string;
    road_name: string;
    main_building_no: string;
    sub_building_no: string;
    building_name: string;
  }> => {
    return new Promise((resolve, reject) => {
      const geocoder = new window.kakao.maps.services.Geocoder();
      geocoder.coord2Address(lng, lat, (result: any[], status: string) => {
        if (
          status === window.kakao.maps.services.Status.OK &&
          result.length > 0
        ) {
          const addr = result[0].road_address;
          const jibunAddr = result[0].address;
          resolve({
            fullAddress: addr?.address_name,
            province: addr?.region_1depth_name,
            district: addr?.region_2depth_name,
            township: addr?.region_3depth_name,
            sido: addr?.region_1depth_name,
            sigungu: addr?.region_2depth_name,
            bname: addr?.region_3depth_name,
            roadAddress: addr?.address_name,
            jibunAddress: jibunAddr?.address_name,
            zonecode: addr?.zone_no || '',
            road_name: addr?.road_name || '',
            main_building_no: addr?.main_building_no || '',
            sub_building_no: addr?.sub_building_no || '',
            building_name: addr?.building_name || '',
          });
        } else {
          reject('Unable to reverse geocode');
        }
      });
    });
  };
  const userInfo = useUserInfo();
  interface NominatimResponse {
    display_name: string;
    address: {
      city?: string;
      town?: string;
      village?: string;
      state?: string;
      country?: string;
    };
  }

  interface OpenMeteoResponse {
    latitude: number;
    longitude: number;
    generationtime_ms: number;
    utc_offset_seconds: number;
    timezone: string;
    timezone_abbreviation: string;
    elevation: number;
    current_weather_units: {
      time: string;
      interval: string;
      temperature: string;
      windspeed: string;
      winddirection: string;
      is_day: string;
      weathercode: string;
    };
    current_weather: {
      time: string;
      interval: number;
      temperature: number;
      windspeed: number;
      winddirection: number;
      is_day: number;
      weathercode: number;
    };
  }
  interface WeatherData {
    temperature?: number;
    humidity?: number;
    wind_speed?: number;
    temperature_unit?: string;
    wind_speed_unit?: string;
    region?: string;
    data_updated_at?: string;
  }

  const fetchRegionData = async (
    latitude: number,
    longitude: number,
  ): Promise<string | null> => {
    try {
      // Get language from userInfo
      const language =
        userInfo?.language__code === 'ko'
          ? 'ko'
          : userInfo?.language__code === 'th'
            ? 'th'
            : 'en';

      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}&accept-language=${language}`,
        {
          headers: {
            'Accept-Language': language,
          },
        },
      );

      if (!response.ok) {
        throw new Error('Failed to fetch region data');
      }

      const data: NominatimResponse = await response.json();

      // Try to get the most specific location name
      const locationName =
        data.address.city ||
        data.address.town ||
        data.address.village ||
        data.display_name;
      return locationName;
    } catch (error) {
      console.error('Error fetching region data:', error);
      return null;
    }
  };
  const fetchWeatherData = async (latitude: number, longitude: number) => {
    try {
      setLoading(true);

      // Fetch weather and region data in parallel
      const [weatherResponse, regionName] = await Promise.all([
        fetch(
          `https://api.open-meteo.com/v1/forecast?latitude=${latitude}&longitude=${longitude}&current_weather=true`,
        ),
        fetchRegionData(latitude, longitude),
      ]);

      if (!weatherResponse.ok) {
        throw new Error('Failed to fetch weather data');
      }

      const data: OpenMeteoResponse = await weatherResponse.json();

      const userInfo = localStorage.getItem('userInfo');
      const time_format = userInfo
        ? JSON.parse(userInfo).settings?.time_format__code
        : null;
      const date_format = userInfo
        ? JSON.parse(userInfo).settings?.date_format__code
        : null;

      const weatherInfo: WeatherData = {
        temperature: data.current_weather.temperature,
        wind_speed: data.current_weather.windspeed,
        temperature_unit: data?.current_weather_units?.temperature,
        wind_speed_unit: ` ${data?.current_weather_units?.windspeed}`,
        region: regionName || data.timezone,
        data_updated_at: getDateTimeFormat(date_format, time_format),
      };
      return weatherInfo;

      // setWeatherData(weatherInfo);
      // setIsInitialLoad(false);
    } catch (error) {
      console.error('Error fetching weather data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Enrich search results with zonecode and address info (parallel, loading each row)
  const enrichResultsWithZonecode = useCallback(
    async (results: LocationSuggestion[]) => {
      setEnrichingIds(results.map((item) => item.id));
      const enriched = await Promise.all(
        results.map(async (item) => {
          try {
            const info = await fetchFullAddressInfo(
              Number(item.lat),
              Number(item.lng),
            );

            setEnrichingIds((prev) => prev.filter((id) => id !== item.id));
            console.log('info', item, info);
            return {
              ...item,
              ...info,
              zonecode: info.zonecode,
              roadAddress: info.roadAddress,
              jibunAddress: info.jibunAddress,
              province: info.province,
              district: info.district,
              township: info.township,
              road_name: info.road_name,
              main_building_no: info.main_building_no,
              sub_building_no: info.sub_building_no,
              building_name: info.building_name,
              disabled: !info.zonecode,
            };
          } catch {
            setEnrichingIds((prev) => prev.filter((id) => id !== item.id));
            return item;
          }
        }),
      );
      setSearchResults(enriched);
    },
    [],
  );

  // Debounced autocomplete with pagination
  const debouncedSearch = useCallback(
    (searchText: string) => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
      debounceTimeoutRef.current = setTimeout(async () => {
        if (searchText && searchText.length >= 2) {
          setLoading(true);
          setShowDropdown(true);
          try {
            setSearchValue(searchText);
            const currentPage = 1;
            const results = await fetchAutocompleteSuggestions(
              searchText,
              currentPage,
            );

            //Display basic data first
            const basicData =
              results?.results?.map((item) => ({
                ...item,
                lat: item.lat || 0,
                lng: item.lng || 0,
                name: item.description,
                weatherData: null,
              })) || [];

            setSuggestions(basicData);
            setSearchTextPage(currentPage);
            setSearchHasNext(results?.hasNext || false);
            setTotalPages(results?.last || 1);

            //Then fetch weather data for each item
            const enrichedData = await Promise.all(
              basicData.map(async (item) => {
                try {
                  setWeatherLoadingIds((prev) => [...prev, item.id]);
                  const weatherData = await fetchWeatherData(
                    item.lat || 0,
                    item.lng || 0,
                  );
                  setWeatherLoadingIds((prev) =>
                    prev.filter((id) => id !== item.id),
                  );

                  return {
                    ...item,
                    weatherData: weatherData,
                  };
                } catch (error) {
                  setWeatherLoadingIds((prev) =>
                    prev.filter((id) => id !== item.id),
                  );
                  return {
                    ...item,
                    weatherData: null,
                  };
                }
              }),
            );

            setSuggestions(enrichedData);
          } catch {
            setSuggestions([]);
          } finally {
            setLoading(false);
          }
        } else {
          setSuggestions([]);
          setShowDropdown(false);
          setLoading(false);
        }
      }, 300);
    },
    [fetchAutocompleteSuggestions, searchTextPage],
  );

  const handleSearch = useCallback(
    (searchText: string) => {
      setSearchValue(searchText);
      onChange?.(searchText);
      onSearch?.(searchText);
      debouncedSearch(searchText);
    },
    [onChange, onSearch, debouncedSearch],
  );

  // When pressing Enter in AutoComplete
  const handleKeyDown = async (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && searchValue && searchValue.length >= 2) {
      setSearchPage(1);
      setSearchLoading(true);
      const { results, hasNext, last } = await fetchSearchResults(
        searchValue,
        1,
      );
      setTotalPages(last);
      await enrichResultsWithZonecode(results);
      setSearchLoading(false);
    }
  };

  // Pagination for autocomplete suggestions
  const handleAutocompletePageChange = async (nextPage: number) => {
    if (!searchValue || searchValue.length < 2) return;

    setSearchTextPage(nextPage);
    setLoading(true);
    setShowDropdown(true);
    try {
      const results = await fetchAutocompleteSuggestions(searchValue, nextPage);

      //Display basic data first
      const basicData =
        results?.results?.map((item) => ({
          ...item,
          lat: item.lat || 0,
          lng: item.lng || 0,
          name: item.description,
          weatherData: null,
        })) || [];

      setSuggestions(basicData);
      setSearchHasNext(results?.hasNext || false);
      setTotalPages(results?.last || 1);

      //Then fetch weather data for each item
      const enrichedData = await Promise.all(
        basicData.map(async (item) => {
          try {
            setWeatherLoadingIds((prev) => [...prev, item.id]);
            const weatherData = await fetchWeatherData(
              item.lat || 0,
              item.lng || 0,
            );
            setWeatherLoadingIds((prev) => prev.filter((id) => id !== item.id));

            return {
              ...item,
              weatherData: weatherData,
            };
          } catch (error) {
            setWeatherLoadingIds((prev) => prev.filter((id) => id !== item.id));
            return {
              ...item,
              weatherData: null,
            };
          }
        }),
      );

      setSuggestions(enrichedData);
    } catch (error) {
      console.error('Error fetching autocomplete page:', error);
    } finally {
      setLoading(false);
    }
  };

  // When selecting a row in autocomplete
  const handleSelect = useCallback(
    (value: string, option: any) => {
      console.log('value_handleSelect', value, option);
      const selectedOption = suggestions.find((item) => item.id === option.key);
      if (selectedOption && !selectedOption.disabled) {
        setSearchValue(value);
        onChange?.(value);
        setSuggestions([]);
        setShowDropdown(false);
        setSelectedDetail(selectedOption);
        onSelect?.(value, selectedOption);
      }
    },
    [suggestions, onChange, onSelect],
  );

  const handleClear = useCallback(() => {
    setSearchValue('');
    setSuggestions([]);
    setShowDropdown(false);
    setSelectedDetail(null);
    setSearchResults([]);
    setSearchPage(1);
    setSearchHasNext(false);
    onChange?.('');
    onSearch?.('');
    onClear?.();
  }, [onChange, onSearch, onClear]);

  // Sync with external value changes
  useEffect(() => {
    if (value !== undefined && value !== searchValue) {
      setSearchValue(value);
    }
  }, [value]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        autoCompleteRef.current &&
        !autoCompleteRef.current.contains(event.target as Node)
      ) {
        setSearchResults([]);
      }
    }
    if (searchResults.length > 0) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [searchResults]);

  const options = React.useMemo(
    () =>
      suggestions.map((suggestion) => ({
        key: suggestion.id,
        value: suggestion.description,
        label: (
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <EnvironmentOutlined
              style={{
                marginRight: 8,
                color: suggestion.disabled ? '#ccc' : 'var(--ga-primary)',
                fontSize: 16,
              }}
            />
            <div style={{ flex: 1 }}>
              {suggestion.structured_formatting ? (
                <>
                  <div
                    style={{
                      fontWeight: 500,
                      color: suggestion.disabled
                        ? '#ccc'
                        : theme === 'dark'
                          ? '#fff'
                          : '#000',
                    }}
                  >
                    {suggestion.structured_formatting.main_text}
                  </div>
                  <div
                    style={{
                      fontSize: '12px',
                      color: suggestion.disabled ? '#ccc' : '#8c8c8c',
                    }}
                  >
                    {suggestion.structured_formatting.secondary_text}
                  </div>
                </>
              ) : (
                <div
                  style={{ color: suggestion.disabled ? '#ccc' : '#262626' }}
                >
                  {suggestion.description}
                </div>
              )}
            </div>
          </div>
        ),
        disabled: suggestion.disabled,
      })) as {
        key: string;
        value: string;
        label: React.ReactNode;
        disabled: boolean;
      }[],
    [suggestions, theme],
  );

  const [page, setPage] = useState(1);
  const pageSize = 5;
  const [selectedKey, setSelectedKey] = useState<number | null>(null);
  const data = React.useMemo(() => {
    return suggestions.map((item) => ({
      key: item.place_id,
      value: item?.name,
      address:
        item?.structured_formatting?.main_text +
        ' (' +
        item?.structured_formatting?.secondary_text +
        ')',
      weather: item?.weatherData ? (
        `${item.weatherData.temperature} ${item.weatherData.temperature_unit}, ${item.weatherData.region}, 
        ${item.weatherData.wind_speed_unit.includes('km/h') ? `${(item.weatherData.wind_speed * 0.27778).toFixed(2) + ' m/s'}` : `${item.weatherData.wind_speed}${item.weatherData.wind_speed_unit}`}`
      ) : weatherLoadingIds.includes(item.id) ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Skeleton.Input
            active
            style={{ height: 20 }}
          />
        </div>
      ) : (
        t('Weather data not available.')
      ),
    }));
  }, [suggestions, weatherLoadingIds]);

  const columns = React.useMemo(
    () => [
      {
        title: '',
        dataIndex: 'radio',
        width: 50,
        render: (_: any, record: any) => (
          <Radio
            checked={selectedKey === record.key}
            onChange={() => {
              setSelectedKey(record.key);
              // When selecting radio, automatically set value for input
              const selectedItem = suggestions.find(
                (item) => (item.place_id || item.id) === record.key,
              );
              if (selectedItem?.weatherData == null) return;
              if (selectedItem) {
                setSearchValue(selectedItem.description);
                onChange?.(selectedItem.description);
                setSuggestions([]);
                setSelectedDetail(selectedItem);
                onSelect?.(selectedItem.description, selectedItem);
              }
            }}
          />
        ),
      },
      { title: t('Address'), dataIndex: 'address', width: '50%' },
      {
        title: t('Weather'),
        dataIndex: 'weather',
        width: '50%',
        render: (weather: any) => {
          if (React.isValidElement(weather)) {
            return weather; // Return React element (skeleton)
          }
          return weather || 'Loading...';
        },
      },
    ],
    [selectedKey, suggestions, weatherLoadingIds],
  );
  const pagedData = data;

  return (
    <div
      className={`custom-search-map ${theme} ${className || ''}`}
      style={style}
    >
      {label && (
        <label
          style={{
            display: 'block',
            marginBottom: '0.4rem',
            fontWeight: 600,
            fontSize: '1rem',
            color: theme === 'dark' ? '#fff' : '#000',
            position: 'relative',
          }}
        >
          {t(label)}{' '}
          {isRequired && (
            <span style={{ color: '#ff4d4f', marginLeft: '0.25rem' }}>*</span>
          )}
          {searchResults.length > 0 && (
            <div
              style={{
                position: 'absolute',
                top: '-8px',
                left: '0',
                background: theme === 'dark' ? '#1677ff' : '#e6f7ff',
                color: theme === 'dark' ? '#fff' : '#1677ff',
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: 500,
                border: `1px solid ${theme === 'dark' ? '#1677ff' : '#91d5ff'}`,
                zIndex: 10,
                whiteSpace: 'nowrap',
              }}
            >
              {t('Please select address that have zonecode')}
            </div>
          )}
        </label>
      )}
      <ConfigProvider
        theme={{
          algorithm:
            theme === 'dark'
              ? antdTheme.darkAlgorithm
              : antdTheme.defaultAlgorithm,
          token: {
            fontSizeIcon: 16,
            fontSize: 12,
          },
        }}
      >
        <div
          style={{ position: 'relative' }}
          ref={autoCompleteRef}
        >
          <CustomAutoComplete
            styles={{
              popup: {
                root: {
                  backgroundColor: theme === 'dark' ? '#1F1F20' : '#ffffff',
                },
              },
            }}
            value={searchValue}
            options={options}
            onSelect={(value: any, option: any) => {
              handleSelect(value, option);
            }}
            onSearch={handleSearch}
            disabled={disabled}
            autoFocus={autoFocus}
            allowClear={allowClear}
            onClear={handleClear}
            placeholder={t(placeholder)}
            notFoundContent={
              loading ? <Spin size="small" /> : t('No results found.')
            }
            filterOption={false}
            style={{ width: '100%' }}
            onKeyDown={handleKeyDown}
            defaultActiveFirstOption={false}
            open={showDropdown}
            // onPopupScroll={handlePopupScroll}
            popupRender={() =>
              suggestions.length > 0 ? (
                <Box sx={{ padding: '4px' }}>
                  <Box
                    sx={{
                      fontSize: 14,
                      fontWeight: '600',
                      padding: '4px 0 12px',
                    }}
                  >
                    {t('Results')}
                  </Box>
                  <Radio.Group
                    value={selectedKey}
                    style={{ width: '100%' }}
                  >
                    <CustomTable
                      $theme={theme}
                      columns={columns}
                      dataSource={pagedData}
                      pagination={false}
                      scroll={{ y: 400 }}
                      size="small"
                      onRow={(record: any) => {
                        const selectedItem = suggestions.find(
                          (item) => (item.place_id || item.id) === record.key,
                        );
                        const isDisabled = selectedItem?.weatherData == null;
                        return {
                          onClick: () => {
                            if (isDisabled) return;
                            setSelectedKey(record?.key);
                            if (selectedItem) {
                              setSearchValue(selectedItem.description);
                              onChange?.(selectedItem.description);
                              setSuggestions([]);
                              setShowDropdown(false);
                              setSelectedDetail(selectedItem);
                              onSelect?.(
                                selectedItem.description,
                                selectedItem,
                              );
                            }
                          },
                          style: {
                            cursor: isDisabled ? 'not-allowed' : 'pointer',
                            opacity: isDisabled ? 0.5 : 1,
                          },
                          className: isDisabled ? 'disabled-row' : '',
                        };
                      }}
                    />
                  </Radio.Group>
                  <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                    <CustomPagination
                      size="small"
                      current={searchTextPage}
                      pageSize={10}
                      total={totalPages * 10}
                      onChange={handleAutocompletePageChange}
                      showSizeChanger={false}
                      showQuickJumper={false}
                      // showTotal={(total, range) => `${range[0]}-${range[1]} of ${total} items`}
                    />
                  </Box>
                </Box>
              ) : (
                <Box sx={{ padding: '0 6px' }}>{t('No results found.')}</Box>
              )
            }
          />
        </div>
      </ConfigProvider>
    </div>
  );
};

export default CustomSearchMapAnYang;
