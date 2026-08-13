import { EnvironmentOutlined, SearchOutlined } from '@ant-design/icons';
import { AutoComplete, ConfigProvider, Spin, theme as antdTheme } from 'antd';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FiSearch } from 'react-icons/fi';
import { CustomModal, useTheme } from 'rj-core';

import './CustomSearchMap.scss';

interface KakaoRoadAddress {
  address_name: string;
  region_1depth_name: string;
  region_2depth_name: string;
  region_3depth_name: string;
  road_name: string;
  main_building_no: string;
  sub_building_no: string;
  zone_no?: string;
}

interface KakaoSearchResult {
  id: string;
  road_address_name: string;
  place_name: string;
  y: number;
  x: number;
}

interface KakaoAddressResult {
  road_address: KakaoRoadAddress | null;
}

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
  autoSearch?: boolean;
  searchPopup?: boolean;
}

const CustomSearchMap: React.FC<CustomSearchMapProps> = ({
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
  autoSearch = true,
  searchPopup = false,
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [searchValue, setSearchValue] = useState<string>(value || '');
  const [suggestions, setSuggestions] = useState<LocationSuggestion[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [isSearchIconHovered, setIsSearchIconHovered] =
    useState<boolean>(false);
  const [showSearchModal, setShowSearchModal] = useState<boolean>(false);
  const [modalSearchValue, setModalSearchValue] = useState<string>('');
  const [modalSuggestions, setModalSuggestions] = useState<
    LocationSuggestion[]
  >([]);
  const [modalLoading, setModalLoading] = useState<boolean>(false);
  const debounceTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const autoCompleteRef = useRef<HTMLDivElement>(null);

  const fetchLocationSuggestions = useCallback(
    async (searchText: string): Promise<LocationSuggestion[]> => {
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
          (data: KakaoSearchResult[], status: string) => {
            console.log('data', data);
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
              resolve(mapped);
            } else {
              resolve([]);
            }
          },
        );
      });
    },
    [],
  );

  const fetchFullAddressInfo = (
    lat: number,
    lng: number,
  ): Promise<{
    fullAddress: string;
    province: string;
    district: string;
    township: string;
    road_name: string;
    main_building_no: string;
    sub_building_no: string;
  }> => {
    return new Promise((resolve, reject) => {
      const geocoder = new window.kakao.maps.services.Geocoder();

      geocoder.coord2Address(
        lng,
        lat,
        (result: KakaoAddressResult[], status: string) => {
          console.log('result', result);

          if (
            status === window.kakao.maps.services.Status.OK &&
            result.length > 0 &&
            result[0].road_address
          ) {
            const addr = result[0].road_address;
            resolve({
              fullAddress: addr.address_name,
              province: addr.region_1depth_name,
              district: addr.region_2depth_name,
              township: addr.region_3depth_name,
              road_name: addr.road_name,
              main_building_no: addr.main_building_no,
              sub_building_no: addr.sub_building_no,
            });
          } else {
            reject(t('Unable to reverse geocode'));
          }
        },
      );
    });
  };

  const fetchAddressDetail = async (
    address: string,
  ): Promise<{ zonecode: string }> => {
    return new Promise((resolve, reject) => {
      const geocoder = new window.kakao.maps.services.Geocoder();

      geocoder.addressSearch(
        address,
        (data: KakaoAddressResult[], status: string) => {
          console.log('address detail data', data);
          if (
            status === window.kakao.maps.services.Status.OK &&
            data.length > 0
          ) {
            resolve({ zonecode: data[0].road_address?.zone_no || '' });
          } else {
            reject(new Error('Unable to fetch address detail'));
          }
        },
      );
    });
  };

  const debouncedSearch = useCallback(
    (searchText: string) => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }

      debounceTimeoutRef.current = setTimeout(async () => {
        if (searchText && searchText.length >= 2) {
          setLoading(true);
          try {
            const results = await fetchLocationSuggestions(searchText);
            setSuggestions(results);
          } catch (error) {
            console.error('Error fetching location suggestions:', error);
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
    [fetchLocationSuggestions],
  );

  const handleSearch = useCallback(
    (searchText: string) => {
      setSearchValue(searchText);
      onChange?.(searchText);
      onSearch?.(searchText);

      // Only trigger search if autoSearch is true
      if (autoSearch) {
        debouncedSearch(searchText);
      }
    },
    [onChange, onSearch, debouncedSearch, autoSearch],
  );

  const handleManualSearch = useCallback(() => {
    if (searchValue && searchValue.length >= 2) {
      setLoading(true);
      fetchLocationSuggestions(searchValue)
        .then((results) => {
          setSuggestions(results);
          console.log(
            'autoCompleteRef.current',
            autoCompleteRef.current,
            autoCompleteRef.current?.querySelector('input'),
          );

          // Use setTimeout to ensure state update is complete
          setTimeout(() => {
            if (autoCompleteRef.current) {
              const inputElement = autoCompleteRef.current.querySelector(
                'input',
              ) as HTMLInputElement;
              if (inputElement) {
                inputElement.focus();
                // Trigger click to open dropdown
                inputElement.click();
                // Also trigger a focus event to ensure dropdown opens
                inputElement.dispatchEvent(
                  new Event('focus', { bubbles: true }),
                );
                // Try mouse down event as well
                inputElement.dispatchEvent(
                  new MouseEvent('mousedown', { bubbles: true }),
                );
              }
            }
          }, 0);
        })
        .catch((error) => {
          console.error('Error fetching location suggestions:', error);
          setSuggestions([]);
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [searchValue, fetchLocationSuggestions]);

  const handleSelect = useCallback(
    async (value: string, option: { key: string; value: string }) => {
      const selectedOption = suggestions.find((item) => item.id === option.key);

      if (selectedOption) {
        setSearchValue(value);
        onChange?.(value);
        setSuggestions([]);

        try {
          // Get full address info from coordinates
          const addressInfo = await fetchFullAddressInfo(
            Number(selectedOption.lat),
            Number(selectedOption.lng),
          );

          // Get zone code from address search
          const addressDetail = await fetchAddressDetail(value);

          const enrichedOption: LocationSuggestion & {
            fullAddress: string;
            province: string;
            district: string;
            township: string;
            zonecode: string;
          } = {
            ...selectedOption,
            ...addressInfo,
            ...addressDetail,
          };

          console.log('Enriched option with zonecode:', enrichedOption);
          onSelect?.(value, enrichedOption);
        } catch (error) {
          console.error(error);
          onSelect?.(value, selectedOption); // fallback
        }
      }
    },
    [suggestions, onChange, onSelect],
  );

  const handleClear = useCallback(() => {
    setSearchValue('');
    setSuggestions([]);
    onChange?.('');
    onSearch?.('');
    onClear?.();
  }, [onChange, onSearch, onClear]);

  // Modal search handlers
  const handleModalSearch = useCallback(
    (searchText: string) => {
      setModalSearchValue(searchText);

      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }

      debounceTimeoutRef.current = setTimeout(async () => {
        if (searchText && searchText.length >= 2) {
          setModalLoading(true);
          try {
            const results = await fetchLocationSuggestions(searchText);
            setModalSuggestions(results);
          } catch (error) {
            console.error('Error fetching location suggestions:', error);
            setModalSuggestions([]);
          } finally {
            setModalLoading(false);
          }
        } else {
          setModalSuggestions([]);
          setModalLoading(false);
        }
      }, 300);
    },
    [fetchLocationSuggestions],
  );

  const handleModalSelect = useCallback(
    async (value: string, option: { key: string; value: string }) => {
      const selectedOption = modalSuggestions.find(
        (item) => item.id === option.key,
      );

      if (selectedOption) {
        setModalSearchValue(value);
        setModalSuggestions([]);

        try {
          // Get full address info from coordinates
          const addressInfo = await fetchFullAddressInfo(
            Number(selectedOption.lat),
            Number(selectedOption.lng),
          );

          // Get zone code from address search
          const addressDetail = await fetchAddressDetail(value);

          const enrichedOption: LocationSuggestion & {
            fullAddress: string;
            province: string;
            district: string;
            township: string;
            zonecode: string;
          } = {
            ...selectedOption,
            ...addressInfo,
            ...addressDetail,
          };

          console.log('Enriched option with zonecode:', enrichedOption);
          onSelect?.(value, enrichedOption);
          setShowSearchModal(false);
          setSearchValue(value);
          onChange?.(value);
        } catch (error) {
          console.error(error);
          onSelect?.(value, selectedOption); // fallback
          setShowSearchModal(false);
          setSearchValue(value);
          onChange?.(value);
        }
      }
    },
    [modalSuggestions, onSelect, onChange],
  );

  const handleOpenSearchModal = useCallback(() => {
    setShowSearchModal(true);
    setModalSearchValue(searchValue);
    setModalSuggestions([]);
    if (searchValue && searchValue.length >= 2) {
      setModalLoading(true);
      fetchLocationSuggestions(searchValue)
        .then((results) => setModalSuggestions(results))
        .catch(() => setModalSuggestions([]))
        .finally(() => setModalLoading(false));
    }
  }, [searchValue, fetchLocationSuggestions]);

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

  const options = suggestions.map((suggestion) => ({
    key: suggestion.id,
    value: suggestion.description,
    label: (
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <EnvironmentOutlined
          style={{
            marginRight: 8,
            color: 'var(--ga-primary)',
            fontSize: 16,
          }}
        />
        <div style={{ flex: 1 }}>
          {suggestion.structured_formatting ? (
            <>
              <div
                style={{
                  fontWeight: 500,
                  color: theme === 'dark' ? '#fff' : '#000',
                }}
              >
                {suggestion.structured_formatting.main_text}
              </div>
              <div style={{ fontSize: '12px', color: '#8c8c8c' }}>
                {suggestion.structured_formatting.secondary_text}
              </div>
            </>
          ) : (
            <div style={{ color: '#262626' }}>{suggestion.description}</div>
          )}
        </div>
      </div>
    ),
  })) as { key: string; value: string; label: React.ReactNode }[];

  const modalOptions = modalSuggestions.map((suggestion) => ({
    key: suggestion.id,
    value: suggestion.description,
    label: (
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <EnvironmentOutlined
          style={{
            marginRight: 8,
            color: 'var(--ga-primary)',
            fontSize: 16,
          }}
        />
        <div style={{ flex: 1 }}>
          {suggestion.structured_formatting ? (
            <>
              <div
                style={{
                  fontWeight: 500,
                  color: theme === 'dark' ? '#fff' : '#000',
                }}
              >
                {suggestion.structured_formatting.main_text}
              </div>
              <div style={{ fontSize: '12px', color: '#8c8c8c' }}>
                {suggestion.structured_formatting.secondary_text}
              </div>
            </>
          ) : (
            <div style={{ color: '#262626' }}>{suggestion.description}</div>
          )}
        </div>
      </div>
    ),
  })) as { key: string; value: string; label: React.ReactNode }[];

  return (
    <div className={`custom-search-map ${theme}`}>
      {label && (
        <label
          style={{
            display: 'block',
            marginBottom: '0.4rem',
            fontWeight: 600,
            fontSize: '1rem',
            color: theme === 'dark' ? '#fff' : '#000',
          }}
        >
          {t(label)}{' '}
          {isRequired && (
            <span
              style={{
                color: '#ff4d4f',
                marginLeft: '0.25rem',
              }}
            >
              *
            </span>
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

            colorBgBase: theme === 'dark' ? '' : '#ffffff',
          },
        }}
      >
        <div
          style={{ position: 'relative' }}
          ref={autoCompleteRef}
        >
          <AutoComplete
            value={searchValue}
            options={options}
            onSelect={handleSelect}
            onSearch={handleSearch}
            className={`${className} ${
              !autoSearch && !searchPopup ? 'manual-search' : ''
            } ${searchPopup ? 'search-popup' : ''}`}
            disabled={disabled}
            autoFocus={autoFocus}
            allowClear={allowClear}
            onClear={handleClear}
            placeholder={placeholder}
            notFoundContent={
              loading ? <Spin size="small" /> : t('No results found.')
            }
            filterOption={false}
          />
          {!autoSearch && (
            <SearchOutlined
              onClick={handleManualSearch}
              onMouseEnter={() => setIsSearchIconHovered(true)}
              onMouseLeave={() => setIsSearchIconHovered(false)}
              style={{
                position: 'absolute',
                right: '8px',
                top: 'calc(50% + 2px)',
                transform: 'translateY(-50%)',
                cursor: 'pointer',
                color:
                  isSearchIconHovered || searchValue
                    ? 'var(--ga-primary)'
                    : theme === 'dark'
                      ? '#424242'
                      : '#d9d9d9',
                fontSize: 18,
                zIndex: 1,
              }}
            />
          )}
          {searchPopup && (
            <SearchOutlined
              onClick={handleOpenSearchModal}
              onMouseEnter={() => setIsSearchIconHovered(true)}
              onMouseLeave={() => setIsSearchIconHovered(false)}
              style={{
                position: 'absolute',
                right: '8px',
                top: 'calc(50% + 2px)',
                transform: 'translateY(-50%)',
                cursor: 'pointer',
                color: isSearchIconHovered
                  ? 'var(--ga-primary)'
                  : theme === 'dark'
                    ? '#424242'
                    : '#d9d9d9',
                fontSize: 18,
                zIndex: 1,
              }}
            />
          )}
        </div>
      </ConfigProvider>

      {/* Search Modal */}
      <CustomModal
        title={t('Search Address')}
        show={showSearchModal}
        onHide={() => setShowSearchModal(false)}
      >
        <div
          className={`custom-search-map ${theme}`}
          style={{ width: '45rem', paddingBottom: '2em' }}
        >
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
                colorBgBase: theme === 'dark' ? '' : '#ffffff',
              },
            }}
          >
            <AutoComplete
              value={modalSearchValue}
              options={modalOptions}
              onSelect={handleModalSelect}
              onSearch={handleModalSearch}
              className="search-popup-modal"
              autoFocus={true}
              allowClear={true}
              placeholder={placeholder}
              notFoundContent={
                modalLoading ? <Spin size="small" /> : t('No results found.')
              }
              filterOption={false}
              defaultOpen={!!searchValue}
            />
          </ConfigProvider>
        </div>
      </CustomModal>
    </div>
  );
};

export default CustomSearchMap;
