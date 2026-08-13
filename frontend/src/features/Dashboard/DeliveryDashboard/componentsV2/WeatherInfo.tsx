// WeatherInfo component
import { Box, IconButton, Tooltip } from '@mui/material';
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FiWind } from 'react-icons/fi';
import { FiRefreshCw } from 'react-icons/fi';
import { TiWeatherPartlySunny } from 'react-icons/ti';
import { WiHumidity } from 'react-icons/wi';
import { useConfigSystem, useTheme, useUserInfo } from 'rj-core';

import { border as borderColor, textLabel } from '@/configs/Colors';
import { getDashboardLocation } from '@/utils/requestLocationPermission';

import { DashboardData } from '../../types/IDashboard';
import getDateTimeFormat, { getDateFormatStringForDayjs, getTimeFormatString2, useConvertDate } from '../../utils/formatDateTime';
import WeatherInfoSkeleton from '../components/WeatherInfoSkeleton';
import dayjs from 'dayjs';
import { IUserInfo } from '@/types/form';

interface WeatherData {
  temperature?: number;
  humidity?: number;
  wind_speed?: number;
  temperature_unit?: string;
  wind_speed_unit?: string;
  region?: string;
  data_updated_at?: string;
}

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

const WeatherInfo: React.FC<{
  data: DashboardData | null;
  handleRefresh: () => void;
  isRefreshing: boolean;
}> = ({ data, handleRefresh, isRefreshing }) => {
  const [theme] = useTheme();
  const userInfo = useUserInfo() as IUserInfo;
  const { t } = useTranslation();
  const [weatherData, setWeatherData] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(false);
  const [currentTime, setCurrentTime] = useState<string>('');
  const [isInitialLoad, setIsInitialLoad] = useState(true);

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

  const [configSystem] = useConfigSystem();
  const unitPreferences =
    configSystem && configSystem['system_default_formats'];
  const dateFormat = getDateFormatStringForDayjs(userInfo?.settings?.date_format__code ?? unitPreferences?.date_format ?? "YYYY/MM/DD");
  const timeFormat = getTimeFormatString2(userInfo?.settings?.time_format__code ?? unitPreferences?.time_format ?? "24");
  const { timeZoneFormat } = useConvertDate();

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

      const weatherInfo: WeatherData = {
        temperature: data.current_weather.temperature,
        wind_speed: data.current_weather.windspeed,
        temperature_unit: data?.current_weather_units?.temperature,
        wind_speed_unit: ` ${data?.current_weather_units?.windspeed}`,
        region: regionName || data.timezone,
        data_updated_at: dayjs().tz(timeZoneFormat).format(dateFormat + ' ' + timeFormat),
      };

      setWeatherData(weatherInfo);
      setIsInitialLoad(false);
    } catch (error) {
      console.error('Error fetching weather data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Update current time every second
  useEffect(() => {
    const updateTime = () => {
      setCurrentTime(dayjs().tz(timeZoneFormat).format(dateFormat + ' ' + timeFormat))
    };

    // Update immediately
    updateTime();

    // Update every second
    const interval = setInterval(updateTime, 1000);

    return () => clearInterval(interval);
  }, [dateFormat, timeFormat]);

  // Request location permission and fetch weather data when component mounts
  useEffect(() => {
    const requestLocationAndFetchWeather = async () => {
      try {
        const location = await getDashboardLocation();
        if (location && location.latitude && location.longitude) {
          await fetchWeatherData(location.latitude, location.longitude);
        }
      } catch (error) {
        console.log(
          'Location permission not granted or error occurred:',
          error,
        );
      }
    };

    requestLocationAndFetchWeather();
  }, [dateFormat, timeFormat]);

  const handleRefreshWeather = async () => {
    try {
      const location = await getDashboardLocation();
      if (location && location.latitude && location.longitude) {
        await fetchWeatherData(location.latitude, location.longitude);
      }
    } catch (error) {
      console.error('Error refreshing weather data:', error);
    }
  };

  const renderInfo = (
    Icon: React.ElementType,
    value: string | number,
    unit: string,
  ) => (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
      <Icon style={{ fontSize: '1.2rem' }} />
      <p style={{ fontSize: '1rem', lineHeight: '1', margin: 0 }}>
        {value}
        {unit}
      </p>
    </Box>
  );

  return (
    <>
      {loading && isInitialLoad ? (
        <WeatherInfoSkeleton />
      ) : (
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flex: 1,
            '@keyframes spin': {
              '0%': {
                transform: 'rotate(90deg)',
                color:
                  theme === 'dark'
                    ? 'var(--ga-primary-dark)'
                    : 'var(--ga-primary)',
              },
              '100%': {
                transform: 'rotate(450deg)',
                color:
                  theme === 'dark'
                    ? 'var(--ga-primary-dark)'
                    : 'var(--ga-primary)',
              },
            },
          }}
        >
          {/* Updated Section */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <p
                style={{
                  fontWeight: '600',
                  fontSize: '1rem',
                  lineHeight: '1',
                  margin: 0,
                }}
              >
                {t('Current Time')}
              </p>
              <p
                style={{
                  fontWeight: '500',
                  fontSize: '1rem',
                  lineHeight: '1',
                  margin: 0,
                }}
              >
                {currentTime}
              </p>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <p
                style={{
                  fontWeight: '600',
                  fontSize: '1rem',
                  lineHeight: '1',
                  margin: 0,
                }}
              >
                {t('Last Updated')}
              </p>
              <p
                style={{
                  fontWeight: '500',
                  fontSize: '1rem',
                  lineHeight: '1',
                  margin: 0,
                }}
              >
                {weatherData?.data_updated_at || data?.data_updated_at}
              </p>
            </Box>

            {/* Nút refresh */}
            <Box
              sx={{
                paddingLeft: '1rem',
                borderLeft: `1px solid ${borderColor[theme === 'dark' ? 'dark' : 'light']}`,
              }}
            >
              <Tooltip
                title={t('Refresh dashboard')}
                arrow
                placement="top"
              >
                <IconButton
                  size="small"
                  disabled={isRefreshing || loading}
                  sx={{
                    border: `1px solid ${borderColor[theme === 'dark' ? 'dark' : 'light']}`,
                    borderRadius: '0.5rem',
                    opacity: isRefreshing || loading ? 0.6 : 1,
                    color: textLabel[theme === 'dark' ? 'dark' : 'light'],
                    '&:hover': {
                      color:
                        theme === 'dark'
                          ? 'var(--ga-primary-dark)'
                          : 'var(--ga-primary)',
                    },
                  }}
                  onClick={() => {
                    handleRefresh();
                    handleRefreshWeather();
                  }}
                >
                  <FiRefreshCw
                    style={{
                      fontSize: '1.25rem',
                      animation:
                        isRefreshing || loading
                          ? 'spin 1s linear infinite'
                          : 'none',
                    }}
                  />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>

          {/* Weather Section */}
          {(weatherData?.temperature ||
            weatherData?.humidity ||
            weatherData?.wind_speed) && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                <p
                  style={{
                    fontWeight: '600',
                    fontSize: '1rem',
                    lineHeight: '1',
                    margin: 0,
                  }}
                >
                  {t('Weather')}
                </p>
                {weatherData?.temperature &&
                  renderInfo(
                    TiWeatherPartlySunny,
                    weatherData.temperature,
                    weatherData?.temperature_unit || '°C',
                  )}
                {weatherData?.humidity &&
                  renderInfo(WiHumidity, weatherData.humidity, '%')}
                {weatherData?.wind_speed &&
                  renderInfo(
                    FiWind,
                    weatherData.wind_speed,
                    weatherData?.wind_speed_unit || ' km/h',
                  )}
              </Box>
            )}

          {/* Region Section */}
          {weatherData?.region && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <p
                style={{
                  fontWeight: '600',
                  fontSize: '1rem',
                  lineHeight: '1',
                  margin: 0,
                }}
              >
                {t('Location')}
              </p>
              <p
                style={{
                  fontWeight: '500',
                  fontSize: '1rem',
                  lineHeight: '1',
                  margin: 0,
                }}
              >
                {weatherData?.region}
              </p>
            </Box>
          )}
        </Box>
      )}
    </>
  );
};

export default WeatherInfo;
