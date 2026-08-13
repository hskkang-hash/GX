// WeatherInfo component
import { Box, IconButton, Tooltip } from '@mui/material';
import React, { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { FiWind } from 'react-icons/fi';
import { FiRefreshCw } from 'react-icons/fi';
import { TiWeatherPartlySunny } from 'react-icons/ti';
import { WiHumidity } from 'react-icons/wi';
import { useTheme } from 'rj-core';

import { border as borderColor, textLabel } from '@/configs/Colors';
import { getDashboardLocation } from '@/utils/requestLocationPermission';

import { DashboardData } from '../../types/IDashboard';

interface WeatherData extends DashboardData {
  temperature?: number;
  humidity?: number;
  wind_speed?: number;
  region?: string;
}

const WeatherInfo: React.FC<{
  data: WeatherData | null;
  handleRefresh: () => void;
  isRefreshing: boolean;
}> = ({ data: weatherData, handleRefresh, isRefreshing }) => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  // Request location permission when component mounts
  useEffect(() => {
    const requestLocation = async () => {
      try {
        const location = await getDashboardLocation();
        if (location) {
          console.log('User location obtained:', location);
          // You can use this location data to get more accurate weather
          // or pass it to the parent component
        }
      } catch {
        console.log('Location permission not granted or error occurred');
      }
    };

    requestLocation();
  }, []);

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
              theme === 'dark' ? 'var(--ga-primary-dark)' : 'var(--ga-primary)',
          },
          '100%': {
            transform: 'rotate(450deg)',
            color:
              theme === 'dark' ? 'var(--ga-primary-dark)' : 'var(--ga-primary)',
          },
        },
      }}
    >
      {/* Updated Section */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <p
          style={{
            fontWeight: '600',
            fontSize: '1rem',
            lineHeight: '1',
            margin: 0,
          }}
        >
          {t('Updated')}
        </p>
        <p
          style={{
            fontWeight: '500',
            fontSize: '1rem',
            lineHeight: '1',
            margin: 0,
          }}
        >
          {weatherData?.data_updated_at}
        </p>
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
              disabled={isRefreshing}
              sx={{
                border: `1px solid ${borderColor[theme === 'dark' ? 'dark' : 'light']}`,
                borderRadius: '0.5rem',
                opacity: isRefreshing ? 0.6 : 1,
                color: textLabel[theme === 'dark' ? 'dark' : 'light'],
                '&:hover': {
                  color:
                    theme === 'dark'
                      ? 'var(--ga-primary-dark)'
                      : 'var(--ga-primary)',
                },
              }}
              onClick={handleRefresh}
            >
              <FiRefreshCw
                style={{
                  fontSize: '1.25rem',
                  animation: isRefreshing ? 'spin 1s linear infinite' : 'none',
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
            renderInfo(TiWeatherPartlySunny, weatherData.temperature, '°C')}
          {weatherData?.humidity &&
            renderInfo(WiHumidity, weatherData.humidity, '%')}
          {weatherData?.wind_speed &&
            renderInfo(FiWind, weatherData.wind_speed, ' m/s')}
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
            {t('Region')}
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
  );
};

export default WeatherInfo;
