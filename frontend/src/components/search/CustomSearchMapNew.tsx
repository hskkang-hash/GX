import {
  EnvironmentOutlined,
  LeftOutlined,
  RightOutlined,
} from '@ant-design/icons';
import { Box, styled } from '@mui/material';
import {
  theme as antdTheme,
  AutoComplete,
  ConfigProvider,
  List,
  Space,
  Spin,
  Typography,
} from 'antd';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '@/configs/Colors';

import './CustomSearchMap.scss';

const { Text } = Typography;

const CustomAutoComplete = styled(AutoComplete, {
  shouldForwardProp: (prop) => prop !== 'error' && prop !== 'themeMode',
})<{ error?: string; themeMode?: string }>`
  &.ant-select-outlined:not(.ant-select-customize-input) .ant-select-selector {
    height: 2.9rem !important;
    border: 1px solid
      ${(props) =>
        props.error
          ? '#ff4d4f'
          : props.themeMode === 'dark'
            ? Colors.Gray6
            : Colors.Gray4} !important;

    &:hover {
      border-color: ${(props) =>
        props.error ? '#ff4d4f' : Colors.Primary} !important;
      box-shadow: ${(props) =>
        props.error
          ? '0 0 0 2px rgba(255, 77, 79, 0.2)'
          : '0 0 0 2px rgba(5, 145, 255, 0.1)'} !important;
    }
    &: focus, &.ant-select-focused {
      border-color: ${(props) =>
        props.error ? '#ff4d4f' : Colors.Primary} !important;
      box-shadow: ${(props) =>
        props.error
          ? '0 0 0 2px rgba(255, 77, 79, 0.2)'
          : '0 0 0 2px rgba(5, 145, 255, 0.1)'} !important;
    }
  }
  .ant-select-focused {
    border-color: ${(props) =>
      props.error ? '#ff4d4f' : Colors.Primary} !important;
    box-shadow: ${(props) =>
      props.error
        ? '0 0 0 2px rgba(255, 77, 79, 0.2)'
        : '0 0 0 2px rgba(5, 145, 255, 0.1)'} !important;
  }
`;

interface LocationSuggestion {
  id: string;
  description: string;
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
  onError?: string;
}

const CustomSearchMapNew: React.FC<CustomSearchMapProps> = ({
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
  onError,
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
  const [detailResults, setDetailResults] = useState<KakaoAddressResult[]>([]);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>('road');
  const debounceTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const autoCompleteRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  console.log('searchValue', searchValue);

  // Autocomplete suggestions (page=1, size=5)
  const fetchAutocompleteSuggestions = useCallback(
    async (searchText: string, page: number): Promise<LocationSuggestion[]> => {
      if (
        !searchText ||
        searchText.length < 2 ||
        !window.kakao?.maps?.services
      ) {
        return [];
      }
      return new Promise((resolve) => {
        const places = new window.kakao.maps.services.Places();
        places.keywordSearch(
          searchText,
          (data: any[], status: string, pagination: any) => {
            if (status === window.kakao.maps.services.Status.OK) {
              const mapped: LocationSuggestion[] = data?.map((item) => ({
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
              const mapped: LocationSuggestion[] = data?.map((item) => ({
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

  // Enrich search results with zonecode and address info (parallel, loading each row)
  const enrichResultsWithZonecode = useCallback(
    async (results: LocationSuggestion[]) => {
      setEnrichingIds(results?.map((item) => item.id));
      const enriched = await Promise.all(
        results?.map(async (item) => {
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

  // Debounced autocomplete
  const debouncedSearch = useCallback(
    (searchText: string) => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
      debounceTimeoutRef.current = setTimeout(async () => {
        if (searchText && searchText.length >= 2) {
          setLoading(true);
          try {
            setSearchValue(searchText);
            const currentPage = 1;
            const results = await fetchAutocompleteSuggestions(
              searchText,
              currentPage,
            );
            setSearchTextPage(currentPage);
            setSuggestions(results.results);
            setSearchHasNext(results.hasNext);
          } catch {
            setSuggestions([]);
          } finally {
            setLoading(false);
          }
        } else {
          setSuggestions([]);
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

  // Pagination search results
  const handlePageChange = async (nextPage: number) => {
    setSearchPage(nextPage);
    setSearchLoading(true);
    const { results, hasNext, last } = await fetchSearchResults(
      searchValue,
      nextPage,
    );
    setTotalPages(last);
    await enrichResultsWithZonecode(results);
    setSearchLoading(false);
  };

  // When selecting a row in autocomplete
  const handleSelect = useCallback(
    (value: string, option: { key: string; value: string }) => {
      const selectedOption = suggestions.find((item) => item.id === option.key);
      if (selectedOption && !selectedOption.disabled) {
        setSearchValue(value);
        onChange?.(value);
        setSuggestions([]);
        setSelectedDetail(selectedOption);
        onSelect?.(value, selectedOption);
      }
    },
    [suggestions, onChange, onSelect],
  );

  // When selecting a row in searchResults
  const handleResultSelect = (item: LocationSuggestion) => {
    if (!item.disabled) {
      setSearchValue(item.description);
      setSelectedDetail(item);
      onSelect?.(item.description, item);
      setSearchResults([]);
    }
  };

  const handleClear = useCallback(() => {
    setSearchValue('');
    setSuggestions([]);
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

  const options = suggestions?.map((suggestion) => ({
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
            <div style={{ color: suggestion.disabled ? '#ccc' : '#262626' }}>
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
  }[];

  const handlePopupScroll = useCallback(
    async (e) => {
      const { scrollTop, scrollHeight, offsetHeight } = e.target;
      if (
        !loading &&
        searchHasNext &&
        scrollTop + offsetHeight >= scrollHeight - 10
      ) {
        const currentPage = searchTextPage + 1;
        const results = await fetchAutocompleteSuggestions(
          searchValue,
          currentPage,
        );
        setSuggestions((prev) => [...prev, ...results.results]);
        setSearchHasNext(results.hasNext);
        setSearchTextPage(currentPage);
      }
    },
    [loading, searchValue, searchTextPage, searchHasNext],
  );

  return (
    <div
      className={`custom - search - map ${theme} ${className || ''} `}
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
                border: `1px solid ${theme === 'dark' ? '#1677ff' : '#91d5ff'} `,
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
            colorBgContainer: theme === 'dark' ? 'transparent' : '#ffffff',
            fontSizeIcon: 16,
            fontSize: 12,
            colorBgBase: theme === 'dark' ? '#18191a' : '#ffffff',
          },
        }}
      >
        <div
          style={{ position: 'relative' }}
          ref={autoCompleteRef}
        >
          <CustomAutoComplete
            error={onError}
            themeMode={theme as 'dark' | 'light'}
            value={searchValue}
            options={options}
            onSelect={handleSelect}
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
            onPopupScroll={handlePopupScroll}
          />
          {searchResults.length > 0 && (
            <div
              ref={dropdownRef}
              style={{
                position: 'absolute',
                left: 0,
                right: 0,
                top: '100%',
                zIndex: 1000,
                background: theme === 'dark' ? '#212529' : '#fff',
                border: `1px solid ${theme === 'dark' ? 'var(--ga-dark-line-color)' : '#e5e5e5'} `,
                borderRadius: 8,
                boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
                marginTop: 8,
                maxHeight: 400,
                overflowY: 'auto',
              }}
            >
              <List
                size="small"
                loading={searchLoading}
                dataSource={searchResults}
                renderItem={(item) => (
                  <List.Item
                    style={{
                      cursor: item.disabled ? 'not-allowed' : 'pointer',
                      opacity: item.disabled ? 0.6 : 1,
                    }}
                    onClick={() => !item.disabled && handleResultSelect(item)}
                  >
                    <div style={{ width: '100%' }}>
                      <Box>
                        <span
                          style={{
                            color: item.disabled ? 'red' : 'red',
                            fontSize: '1.25rem',
                          }}
                        >
                          {item.zonecode ||
                            (enrichingIds.includes(item.id) ? (
                              <Spin size="small" />
                            ) : (
                              ''
                            ))}
                          {item.disabled &&
                            !item.zonecode &&
                            !enrichingIds.includes(item.id) &&
                            ' (' + t('No zonecode') + ')'}
                        </span>
                        {/* <Text strong>{item.description}</Text> */}
                      </Box>
                      <Box sx={{ my: '0.5rem' }}>
                        <span style={{ marginRight: 8 }}>
                          <span
                            style={{
                              color: item.disabled ? '#ccc' : '#1677ff',
                              fontWeight: 500,
                              padding: '2px',
                              borderRadius: '4px',
                              border: `1px solid ${item.disabled ? '#ccc' : '#1677ff'} `,
                            }}
                          >
                            도로명
                          </span>{' '}
                          <span
                            style={{
                              color: item.disabled ? '#ccc' : 'inherit',
                            }}
                          >
                            {item.roadAddress ||
                              (enrichingIds.includes(item.id) ? (
                                <Spin size="small" />
                              ) : (
                                ''
                              ))}
                          </span>
                        </span>
                      </Box>
                      <div>
                        <span>
                          <span
                            style={{
                              color: item.disabled ? '#ccc' : '#2db7f5',
                              fontWeight: 500,
                              padding: '2px',
                              borderRadius: '4px',
                              border: `1px solid ${item.disabled ? '#ccc' : '#2db7f5'} `,
                              marginRight: '12px',
                            }}
                          >
                            지번
                          </span>{' '}
                          <span
                            style={{
                              color: item.disabled ? '#ccc' : 'inherit',
                            }}
                          >
                            {item.jibunAddress ||
                              (enrichingIds.includes(item.id) ? (
                                <Spin size="small" />
                              ) : (
                                ''
                              ))}
                          </span>
                        </span>
                      </div>
                    </div>
                  </List.Item>
                )}
              />
              <Space
                style={{
                  width: '100%',
                  marginTop: '0.5rem',
                  padding: '0.5rem',
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  borderTop: `1px solid ${
                    theme === 'dark' ? 'var(--ga-dark-line-color)' : '#e5e5e5'
                  } `,
                }}
              >
                {searchPage > 1 ? (
                  <span
                    style={{
                      cursor: 'pointer',
                      fontSize: 18,
                      width: 24,
                      textAlign: 'center',
                    }}
                    onClick={() => handlePageChange(searchPage - 1)}
                  >
                    <LeftOutlined />
                  </span>
                ) : (
                  <span style={{ width: 18, display: 'inline-block' }} />
                )}
                <span style={{ minWidth: 40, textAlign: 'center', flex: 1 }}>
                  {searchPage} / {totalPages}
                </span>
                {searchPage < totalPages ? (
                  <span
                    style={{
                      cursor: 'pointer',
                      fontSize: 18,
                      width: 24,
                      textAlign: 'center',
                    }}
                    onClick={() => handlePageChange(searchPage + 1)}
                  >
                    <RightOutlined />
                  </span>
                ) : (
                  <span style={{ width: 18, display: 'inline-block' }} />
                )}
              </Space>
            </div>
          )}
        </div>
      </ConfigProvider>

      {(onError || searchValue.trim()) && (
        <div
          style={{ color: 'red', fontSize: '0.875rem', marginTop: '0.5rem' }}
        >
          {onError}
        </div>
      )}
    </div>
  );
};

export default CustomSearchMapNew;
