import { Box, Divider, IconButton, Tooltip } from '@mui/material';
import dayjs from 'dayjs';
import React, { useEffect, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { FiMapPin, FiRefreshCw, FiWind } from 'react-icons/fi';
import { TiWeatherPartlySunny } from 'react-icons/ti';
import { WiHumidity } from 'react-icons/wi';
import { useTheme, useUserInfo } from 'rj-core';
import QuickDateRangeBtn from '@/components/QuickDateRangeBtn';
import Colors, { border as borderColor, textLabel } from '@/configs/Colors';
import { getDashboardLocation } from '@/utils/requestLocationPermission';
import { SearchDeliveryDashBoard } from '../../components/SearchDeliveryDashBoard';
import { DashboardData } from '../../types/IDashboard';
import getDateTimeFormat, { useConvertDate } from '../../utils/formatDateTime';
import WeatherInfoSkeleton from '../components/WeatherInfoSkeleton';
import timezone from 'dayjs/plugin/timezone';
dayjs.extend(timezone);

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
    province?: string;
    quarter?: string;
    suburb?: string;
    county?: string;
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

const WeatherInfoAngYang: React.FC<{
  data: DashboardData | null;
  handleRefresh: () => void;
  isRefreshing: boolean;
  setSearchLocation: (location: any) => void;
  setDateRange: (dateRange: any) => void;
}> = ({
  data,
  handleRefresh,
  isRefreshing,
  setSearchLocation,
  setDateRange,
}) => {
    const [theme] = useTheme();
    const userInfo = useUserInfo();
    const { t } = useTranslation();
    const [weatherData, setWeatherData] = useState<WeatherData | null>(null);
    const [loading, setLoading] = useState(false);
    const [currentTime, setCurrentTime] = useState<string>('');
    const [openModalSearchLocation, setOpenModalSearchLocation] =
      useState<boolean>(false);
    const weatherApiCalledRef = useRef<{ lat: number; lng: number } | null>(null);
    const [dataLoaded, setDataLoaded] = useState(false);
    const { dateFormat, timeFormat, timeZoneFormat } = useConvertDate();

    // this year get first day of the year - use ISO format for form values
    const thisYearStartDateISO = useRef(
      dayjs().startOf('year').format('YYYY-MM-DD'),
    ).current;
    const thisYearEndDateISO = useRef(
      dayjs().endOf('year').format('YYYY-MM-DD'),
    ).current;

    const [locationFromOption, setLocationFromOption] = useState<any>(null);
    const [weatherFromOption, setWeatherFromOption] = useState<any>(null);
    const methods = useForm({
      defaultValues: {
        start_date: thisYearStartDateISO,
        end_date: thisYearEndDateISO,
      },
    });

    const { control, watch } = methods;

    const fetchRegionData = async (
      latitude: number,
      longitude: number,
    ): Promise<string | null> => {
      try {
        // Get language from userInfo
        const language =
          (userInfo as any)?.language__code === 'ko'
            ? 'ko'
            : (userInfo as any)?.language__code === 'th'
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
          data.address.quarter ||
          data.address.suburb ||
          data.address.county ||
          data.address.city ||
          data.address.town ||
          data.address.village ||
          data.address.province ||
          data.address.country ||
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

        const weatherApiData: OpenMeteoResponse = await weatherResponse.json();

        const weatherInfo: WeatherData = {
          temperature: weatherApiData.current_weather.temperature,
          wind_speed: weatherApiData.current_weather.windspeed,
          temperature_unit: weatherApiData?.current_weather_units?.temperature,
          wind_speed_unit: ` ${weatherApiData?.current_weather_units?.windspeed}`,
          region: regionName || weatherApiData.timezone,
          data_updated_at: dayjs().tz(timeZoneFormat).format(dateFormat + ' ' + timeFormat),
        };

        if (
          data?.weather_setting?.latitude &&
          data?.weather_setting?.longitude &&
          data?.weather_setting?.address
        ) {
          setSearchLocation({
            lat: data.weather_setting.latitude,
            lng: data.weather_setting.longitude,
            address: data.weather_setting.address,
            type: 'weather_setting',
          });

          setLocationFromOption(regionName);
        }

        setWeatherData(weatherInfo);

        weatherApiCalledRef.current = {
          lat: latitude,
          lng: longitude,
        };
      } catch (error) {
        console.error('Error fetching weather data:', error);
      } finally {
        setLoading(false);
      }
    };

    // Update current time every second
    useEffect(() => {
      const updateTime = () => {
        const userInfo = localStorage.getItem('userInfo');
        const time_format = userInfo
          ? JSON.parse(userInfo).settings?.time_format__code
          : null;
        const date_format = userInfo
          ? JSON.parse(userInfo).settings?.date_format__code
          : null;
        const formattedTime = getDateTimeFormat(date_format, time_format);
        setCurrentTime(formattedTime);
      };

      // Update immediately
      updateTime();

      // Update every second
      const interval = setInterval(updateTime, 1000);

      return () => clearInterval(interval);
    }, []);

    const requestLocationAndFetchWeather = async () => {
      try {
        const location = await getDashboardLocation();
        if (location && location.latitude && location.longitude) {
          await fetchWeatherData(location.latitude, location.longitude);
        }
      } catch (error) {
        console.log('Location permission not granted or error occurred:', error);
      }
    };

    const fetchWeatherDataBySetting = async () => {
      try {
        await fetchWeatherData(
          data?.weather_setting?.latitude || 0,
          data?.weather_setting?.longitude || 0,
        );
      } catch (error) {
        console.log('Error fetching weather data:', error);
      }
    };

    useEffect(() => {
      if (data) {
        setDataLoaded(true);

        if (data.weather_setting?.latitude && data.weather_setting?.longitude) {
          if (
            !weatherApiCalledRef.current ||
            (weatherApiCalledRef.current &&
              (data.weather_setting.latitude !==
                weatherApiCalledRef.current.lat ||
                data.weather_setting.longitude !==
                weatherApiCalledRef.current.lng))
          ) {
            weatherApiCalledRef.current = {
              lat: data.weather_setting.latitude,
              lng: data.weather_setting.longitude,
            };
            fetchWeatherDataBySetting();
          }
        } else if (!weatherApiCalledRef.current && dataLoaded) {
          weatherApiCalledRef.current = { lat: 0, lng: 0 };
          requestLocationAndFetchWeather();
        }
      }
    }, [data, dataLoaded]);

    const handleRefreshWeather = async () => {
      try {
        //Use weather setting if available
        if (data?.weather_setting?.latitude && data?.weather_setting?.longitude) {
          await fetchWeatherData(
            data.weather_setting.latitude,
            data.weather_setting.longitude,
          );
        } else {
          //Request location from browser
          const location = await getDashboardLocation();
          if (location && location.latitude && location.longitude) {
            await fetchWeatherData(location.latitude, location.longitude);
          }
        }
      } catch (error) {
        console.error('Error refreshing weather data:', error);
      }
    };

    useEffect(() => {
      if (isRefreshing) {
        handleRefreshWeather();
      }
    }, [isRefreshing]);

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

    const handleSearchLocation = () => {
      setOpenModalSearchLocation((prev) => !prev);
    };

    const prevStartDate = useRef<string | null>(null);
    const prevEndDate = useRef<string | null>(null);

    useEffect(() => {
      const startDate = watch('start_date');
      const endDate = watch('end_date');

      if (
        startDate !== prevStartDate.current ||
        endDate !== prevEndDate.current
      ) {
        prevStartDate.current = startDate;
        prevEndDate.current = endDate;

        if (startDate && endDate) {
          const newDateRange = {
            start_date: startDate,
            end_date: endDate,
          };
          setDateRange(newDateRange);
        } else if (!startDate && !endDate) {
          setDateRange(null);
        }
      } else {
        console.log('Dates unchanged, skipping setDateRange call');
      }
    }, [watch('start_date'), watch('end_date')]);

    return (
      <>
        {loading ? (
          <WeatherInfoSkeleton />
        ) : (
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flex: 1,
              zIndex: 500,
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
            {/* Date Range */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <p
                style={{
                  fontWeight: '600',
                  fontSize: '1rem',
                  lineHeight: '1',
                  margin: 0,
                }}
              >
                {t('Date Range')}
              </p>
              {watch('start_date') && watch('end_date') && (
                <p
                  style={{
                    fontWeight: '500',
                    fontSize: '1rem',
                    lineHeight: '1',
                    margin: 0,
                    marginLeft: '0.25rem',
                  }}
                >
                  {dayjs(watch('start_date'), 'YYYY-MM-DD').tz(timeZoneFormat).format(dateFormat)} - {dayjs(watch('end_date'), 'YYYY-MM-DD').tz(timeZoneFormat).format(dateFormat)}
                </p>
              )}
              <Divider
                orientation="vertical"
                flexItem
                sx={{
                  borderColor: theme === 'dark' ? '#444646' : '#DDDFE2',
                  margin: '0 0.5rem',
                }}
              />
              <QuickDateRangeBtn
                fromName="start_date"
                toName="end_date"
                control={control}
                format={dateFormat}
                heightForDashboard
              />
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              {/* Last Updated */}
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
              <Divider
                orientation="vertical"
                flexItem
                sx={{
                  borderColor: theme === 'dark' ? '#444646' : '#DDDFE2',
                  margin: '0 0.5rem',
                }}
              />
              {/* Nút refresh */}
              <Box>
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

            {/* Start Location Section */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
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
                    {locationFromOption || weatherData?.region}
                  </p>
                </Box>
              )}
              <Divider
                orientation="vertical"
                flexItem
                sx={{
                  borderColor: theme === 'dark' ? '#444646' : '#DDDFE2',
                  margin: '0 0.5rem',
                }}
              />
              {/* Location Icon */}
              <Box>
                <Tooltip
                  title={t('Search Location')}
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
                      handleSearchLocation();
                    }}
                  >
                    <FiMapPin
                      style={{ fontSize: '1.25rem' }}
                      color={
                        openModalSearchLocation
                          ? theme === 'dark'
                            ? 'var(--ga-primary-dark)'
                            : 'var(--ga-primary)'
                          : textLabel[theme === 'dark' ? 'dark' : 'light']
                      }
                    />
                  </IconButton>
                </Tooltip>
                {/* Modal Search Location */}
                {openModalSearchLocation && (
                  <div
                    style={{
                      position: 'absolute',
                      backgroundColor:
                        theme === 'dark' ? Colors.Secondary : 'white',
                      borderRadius: '8px',
                      top: '120%',
                      transform: 'translateX(-50%)',
                      width: '36rem',
                      zIndex: 1000,
                    }}
                  >
                    <SearchDeliveryDashBoard
                      isRequired
                      onSelect={(value, option) => {
                        setLocationFromOption(
                          option?.city ||
                          option?.administrative_area_level_2 ||
                          option?.administrative_area_level_1,
                        );
                        setWeatherFromOption(option?.weatherData);
                        setSearchLocation(option);
                      }}
                      onClear={() => { }}
                    />
                  </div>
                  // <div style={{ background: "red", width: "100%", height: "100%" }}>lalalalalala</div>
                )}
              </Box>
            </Box>
            {/* End Location Section */}
            {/* Weather Section */}
            {(weatherFromOption?.temperature ||
              weatherFromOption?.humidity ||
              weatherFromOption?.wind_speed ||
              weatherData?.temperature ||
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
                  {(weatherFromOption?.temperature || weatherData?.temperature) &&
                    renderInfo(
                      TiWeatherPartlySunny,
                      weatherFromOption?.temperature || weatherData?.temperature,
                      weatherFromOption?.temperature_unit ||
                      weatherData?.temperature_unit ||
                      '°C',
                    )}
                  {(weatherFromOption?.humidity || weatherData?.humidity) &&
                    renderInfo(
                      WiHumidity,
                      weatherFromOption?.humidity || weatherData?.humidity,
                      '%',
                    )}
                  {(weatherFromOption?.wind_speed || weatherData?.wind_speed) &&
                    renderInfo(
                      FiWind,
                      (() => {
                        const windSpeed =
                          weatherFromOption?.wind_speed ?? weatherData?.wind_speed;
                        if (windSpeed != null && !isNaN(windSpeed)) {
                          return (windSpeed * 0.27778).toFixed(2);
                        }
                        return '0.00';
                      })(),
                      ' m/s',
                    )}
                </Box>
              )}
          </Box>
        )}
      </>
    );
  };

export default WeatherInfoAngYang;
