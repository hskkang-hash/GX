import { default as i18n, default as i18next } from 'i18next';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ToastTopHelper, useConfigGroupSystem } from 'rj-core';

import { GEOCODING_CONFIG } from '@/configs/Constant';
import API, { endpoint } from '@/services/API';
import { checkCodeValid } from '@/utils/CheckCodeValid';

const KEY_MODEL = {
  MAIN_TYPE: 'devicetype',
};

type FetchConfig = {
  type: 'model' | 'function';
  params: any;
  defaultLabel?: string;
};

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

interface AddressDetail {
  address_name: string;
  region_1depth_name: string;
  region_2depth_name: string;
  region_3depth_name: string;
  road_name: string;
  main_building_no: string;
  sub_building_no: string;
}

interface KakaoAddressResult {
  road_address: KakaoRoadAddress | null;
}

const useCommonAPI = () => {
  const { t } = useTranslation();
  const { configGroupSystem } = useConfigGroupSystem();
  const countryCode = configGroupSystem?.use_map?.country_code || 'KR';
  const isKoreaCountry = checkCodeValid(countryCode?.toUpperCase()) === 'KR';

  const isSystemUseGoogleMap =
    configGroupSystem?.use_map?.select_map?.google_map || false;
  const isEmptyConfigGroupSystem =
    !configGroupSystem || Object.keys(configGroupSystem).length === 0;

  function useFetchOptions(fetcher: (config: any) => any, config: FetchConfig) {
    const [options, setOptions] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const hasFetched = useRef(false);

    const memoizedParams = useMemo(() => config.params, [config?.params]);

    useEffect(() => {
      // Prevent multiple calls if already fetched or currently loading
      if (hasFetched.current || isLoading) return;

      const fetchData = async () => {
        setIsLoading(true);
        hasFetched.current = true;

        try {
          const fetchFunction = fetcher(memoizedParams);

          const { options } = await fetchFunction('', [], {
            page: 1,
            page_size: 1000,
          });

          if (options) {
            setOptions([
              { label: config.defaultLabel ?? 'Select', value: '' },
              ...options,
            ]);
          }
        } catch (error) {
          console.log('Error fetch options', error);
          hasFetched.current = false; // Reset on error to allow retry
        } finally {
          setIsLoading(false);
        }
      };

      fetchData();
    }, [memoizedParams, config?.defaultLabel]);

    return options;
  }

  const getMainType = async () => {
    const params = {
      model_name: KEY_MODEL.MAIN_TYPE,
    };
    try {
      const response = await API.get(endpoint.getDataForSelectInput, {
        params,
      });
      return {
        data: response.data.map((item: any) => ({
          value: item.id,
          label: i18next.t(item.name),
        })),
        status: true,
      };
    } catch (error: any) {
      return {
        data: [],
        status: false,
        message: error.response.data.message,
      };
    }
  };

  interface CustomKeyConfig {
    primary: string;
    secondary: string[];
    separator?: string;
  }

  const getDataByModel = async ({
    name_modal,
    multi_language = true,
  }: {
    name_modal: string;
    multi_language?: boolean;
  }) => {
    try {
      const response = await API.get(endpoint.getDataForSelectInput, {
        params: {
          model_name: name_modal,
          multi_language: multi_language,
          distinct: true,
          page_number: 1,
          page_size: 1000, // Lấy tất cả dữ liệu
        },
      });

      return {
        data: response.data.map(
          (item: { id: number; name: string; code: string }) => ({
            code: item.code,
            label: item.name,
            value: item.id,
          }),
        ),
        status: true,
      };
    } catch (error: any) {
      return {
        data: [],
        status: false,
        message:
          error.response?.data?.message ||
          t('An error occurred while fetching data.'),
      };
    }
  };

  const getOptionsByModel = ({
    name_modal,
    multi_language = true,
    key = 'name',
    value = 'id',
    code = 'code',
    custom_key,
    search_field,
    exclude_code = [],
    search_term,
  }: {
    name_modal: string;
    multi_language?: boolean;
    key?: string;
    value?: string;
    code?: string;
    custom_key?: string[] | CustomKeyConfig;
    search_field?: string;
    exclude_code?: string[];
    search_term?: string;
  }) => {
    return async (
      search: string,
      loadedOptions: any,
      { page = 1, page_size = 10 }: { page?: number; page_size?: number } = {
        page: 1,
        page_size: 10,
      },
    ) => {
      const response = await API.get(endpoint.getDataForSelectInput, {
        params: {
          model_name: name_modal,
          multi_language: multi_language,
          search_term: search || search_term || '',
          page_number: page,
          page_size: page_size,
          distinct: true,
          search_field: search_field || '',
        },
      });

      const data = response.data || [];
      const hasMore = response.current_page < response.total_pages;

      const formatLabel = (item: any) => {
        if (!custom_key) {
          return item[key];
        }

        // Nếu custom_key là array (cách cũ)
        if (Array.isArray(custom_key)) {
          return custom_key.map((k: string) => item[k]).join(' - ');
        }

        // Nếu custom_key là object config (cách mới)
        const { primary, secondary, separator = ', ' } = custom_key;
        const primaryValue = item[primary];
        const secondaryValues = secondary
          .map((k: string) => item[k])
          .filter(Boolean)
          .join(separator);

        return secondaryValues
          ? `${primaryValue} (${secondaryValues})`
          : primaryValue;
      };

      return {
        options: data
          .map((item: any) => {
            if (exclude_code.includes(item[code])) {
              return null;
            }
            return {
              label: formatLabel(item),
              value: item[value],
              code: item[code],
            };
          })
          .filter(Boolean),
        hasMore,
        additional: {
          page: (page ?? 1) + 1,
        },
      };
    };
  };

  const getAddressByLatLong = async (
    lat: number,
    lng: number,
  ): Promise<{ data: AddressDetail | null; status: boolean }> => {
    try {
      const res = await fetch(
        `https://dapi.kakao.com/v2/local/geo/coord2address.json?x=${lng}&y=${lat}`,
        {
          method: 'GET',
          headers: {
            Authorization: `KakaoAK ${import.meta.env.VITE_KAKAO_API_KEY}`,
            KA: `sdk/1.0.0 os/javascript lang=javascript origin/${window.location.origin}`,
          },
        },
      );

      const data = await res.json();
      if (!res.ok || !data.documents || data.documents.length === 0) {
        ToastTopHelper.error(
          t(
            'The input parameter value is not in the service area. Please check the address or lat/long again.',
          ),
        );
        return { data: null, status: false };
      }
      const addr = data.documents[0].road_address
        ? data.documents[0].road_address
        : data.documents[0].address;
      if (!addr) {
        ToastTopHelper.error(
          t('No road address found for the given coordinates.'),
        );
        return { data: null, status: false };
      }
      return {
        data: {
          address_name: addr.address_name,
          region_1depth_name: addr.region_1depth_name,
          region_2depth_name: addr.region_2depth_name,
          region_3depth_name: addr.region_3depth_name,
          road_name: addr.road_name,
          main_building_no: addr.main_building_no,
          sub_building_no: addr.sub_building_no,
        },
        status: true,
      };
    } catch {
      ToastTopHelper.error(t('Error getting address from coordinates.'));
      return { data: null, status: false };
    }
  };

  const getAddressByLatLongSafe = async (
    lat: number,
    lng: number,
  ): Promise<{ data: AddressDetail | null; status: boolean }> => {
    if (!isKoreaCountry) {
      console.log(
        'Skipping Kakao reverse geocoding for non-Korea country:',
        countryCode,
      );
      return { data: null, status: false };
    }

    return await getAddressByLatLong(lat, lng);
  };

  const getLatLongFromAddress = async (fullAddress: string) => {
    const response = await fetch(
      `https://dapi.kakao.com/v2/local/search/address.json?query=${encodeURIComponent(fullAddress)}`,
      {
        method: 'GET',
        headers: {
          Authorization: `KakaoAK ${import.meta.env.VITE_KAKAO_API_KEY}`,
          KA: `sdk/1.0.0 os/javascript lang=javascript origin/${window.location.origin}`,
        },
      },
    );

    const data = await response.json();

    if (!response.ok || data.documents.length === 0) {
      ToastTopHelper.error(
        t(
          'The input parameter value is not in the service area. Please check the address again.',
        ),
      );
      return {
        data: {},
        status: false,
      };
    } else {
      ToastTopHelper.success(t('The Address is in the service area.'));
    }
    return {
      data: data.documents?.[0],
      status: true,
    }; // Chứa lat, long, address info
  };

  /**
   * Lấy tọa độ lat/lng từ địa chỉ sử dụng Google Geocoding API
   * @param address - Địa chỉ cần geocode
   * @returns Promise với object chứa lat, lng và status
   */
  const getLatLongFromAddressGoogle = async (
    address: string,
  ): Promise<{
    data: { lat: number; lng: number; formatted_address?: string } | null;
    status: boolean;
    message?: string;
  }> => {
    try {
      if (isSystemUseGoogleMap || isEmptyConfigGroupSystem) {
        const apiKey = GEOCODING_CONFIG.GOOGLE_PLACES_API_KEY;
        if (!apiKey) {
          ToastTopHelper.error(t('Google Maps API key is not configured.'));
          return {
            data: null,
            status: false,
            message: 'API key not configured',
          };
        }

        const encodedAddress = encodeURIComponent(address);
        const url = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodedAddress}&key=${apiKey}`;

        const response = await fetch(url, {
          method: 'GET',
        });

        const data = await response.json();

        if (data.status === 'OK' && data.results && data.results.length > 0) {
          const result = data.results[0];
          const location = result.geometry.location;

          return {
            data: {
              lat: location.lat,
              lng: location.lng,
              formatted_address: result.formatted_address,
            },
            status: true,
          };
        } else {
          const errorMessage =
            data.status === 'ZERO_RESULTS'
              ? t('No results found for this address.')
              : data.status === 'OVER_QUERY_LIMIT'
                ? t('API quota exceeded. Please try again later.')
                : data.status === 'REQUEST_DENIED'
                  ? t('Request denied. Please check API key configuration.')
                  : t('Error geocoding address. Please try again.');

          ToastTopHelper.error(errorMessage);
          return {
            data: null,
            status: false,
            message: data.status || 'Unknown error',
          };
        }
      }

      const response = await fetch(
        `https://dapi.kakao.com/v2/local/search/address.json?query=${encodeURIComponent(address)}`,
        {
          method: 'GET',
          headers: {
            Authorization: `KakaoAK ${import.meta.env.VITE_KAKAO_API_KEY}`,
            KA: `sdk/1.0.0 os/javascript lang=javascript origin/${window.location.origin}`,
          },
        },
      );

      const data = await response.json();

      if (!response.ok || !data.documents || data.documents.length === 0) {
        const errorMessage = t(
          'The input parameter value is not in the service area. Please check the address again.',
        );
        ToastTopHelper.error(errorMessage);
        return {
          data: null,
          status: false,
          message: 'No results found',
        };
      }

      const document = data.documents[0];
      const roadAddress = document.road_address;
      const addressInfo = document.address;

      return {
        data: {
          lat: document.y,
          lng: document.x,
          formatted_address:
            roadAddress?.address_name || addressInfo?.address_name || address,
        },
        status: true,
      };
    } catch (error) {
      ToastTopHelper.error(t('Error geocoding address. Please try again.'));
      return {
        data: null,
        status: false,
        message: 'Network error',
      };
    }
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
            resolve({
              ...data[0].road_address,
              zonecode: data[0].road_address?.zone_no || '',
            });
          } else {
            reject(new Error('Unable to fetch address detail'));
          }
        },
      );
    });
  };

  const getFunctionTypes = ({ function_type }: { function_type?: string }) => {
    return async (
      search: string,
      loadedOptions: any,
      { page }: { page: number },
    ) => {
      const response = await API.get(endpoint.functionTypes, {
        params: {
          name: search,
          current_page: page ?? 1,
          page_size: 10,
          ...(function_type && { function_types: function_type }),
        },
      });
      console.log('response_group', response);

      const data = response.data || [];
      const hasMore = response.current_page < response.total_pages;

      return {
        // options: data
        //   .map((item: any) => {
        //     return { label: item.name, value: item.id, function_type: item.function_type };
        //   })
        //   .filter(Boolean),
        options: data
          .map((item: any) => {
            const currentLang = i18n.language || 'en';
            const label = item?.name_translations?.[currentLang] || item?.name;
            return {
              label,
              value: item.id,
              function_type: item.function_type,
            };
          })
          .filter(Boolean),
        hasMore,
        additional: {
          page: (page ?? 1) + 1,
        },
      };
    };
  };

  const getListGroup = ({
    exclude_value = [],
  }: { exclude_value?: number[] } = {}) => {
    return async (
      search: string,
      loadedOptions: any,
      { page }: { page: number },
    ) => {
      const response = await API.get(endpoint.groups, {
        params: {
          name: search,
          current_page: page ?? 1,
          page_size: 10,
        },
      });
      const data = response.data || [];
      const hasMore = response.current_page < response.total_pages;

      return {
        options: data
          .map((item: { id: number; name: string }) => {
            if (exclude_value.includes(item.id)) {
              return null;
            }
            return { label: item.name, value: item.id };
          })
          .filter(Boolean),
        hasMore,
        additional: {
          page: (page ?? 1) + 1,
        },
      };
    };
  };

  const getDayOfWeek = async () => {
    try {
      const response = await API.get(endpoint.dayOfWeek);
      return {
        data: response.data.map((item: any) => ({
          name: item.name,
          day_of_week_id: item.id,
          is_active: item.is_active,
          start_time: '08:00:00',
          end_time: '20:00:00',
        })),
        status: true,
        message: response.data.message,
      };
    } catch (error: any) {
      return {
        data: [],
        status: false,
        message: error.response.data.message,
      };
    }
  };
  return {
    useFetchOptions,
    getMainType,
    getOptionsByModel,
    getAddressByLatLong,
    getAddressByLatLongSafe,
    getLatLongFromAddress,
    getLatLongFromAddressGoogle,
    fetchAddressDetail,
    getDataByModel,
    getFunctionTypes,
    getListGroup,
    getDayOfWeek,
  };
};

export default useCommonAPI;
