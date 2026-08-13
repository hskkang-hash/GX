// WeatherInfo component
import React, { useEffect, useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { FaCloud } from 'react-icons/fa';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

const WeatherInfo: React.FC = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();
  const [currentTime, setCurrentTime] = useState<string>('');
  const [windSpeed, setWindSpeed] = useState<number>(
    Math.floor(Math.random() * 9) + 1,
  );

  const weatherData = useRef({
    temperature: Math.floor(Math.random() * 20) + 5, // 5-25°C
    humidity: Math.floor(Math.random() * 80) + 10, // 10-90%
  });

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const formattedTime = now
        .toLocaleString('ko-KR', {
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false,
        })
        .replace(/\//g, '/');
      setCurrentTime(formattedTime);
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const updateWindSpeed = () => {
      setWindSpeed(Math.floor(Math.random() * 9) + 1); // 1-10 m/s
    };

    const interval = setInterval(updateWindSpeed, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div
      style={{
        display: 'flex',
        flex: '2',
        alignItems: 'center',
      }}
    >
      <div
        className="timestamp"
        style={{
          color: theme === 'dark' ? Colors.Gray3 : '#666',
          flex: '1',
          display: 'flex',
          justifyContent: 'center',
        }}
      >
        <span>
          {t('Current')}: {currentTime}
        </span>
        <span style={{ marginLeft: 15 }}>
          {t('Last Update')}: 04.13 17:42:55
        </span>
      </div>
      <div
        className="weather-info"
        style={{
          display: 'flex',
          justifyContent: 'flex-end',
          alignItems: 'center',
          gap: 10,
          flex: '1',
        }}
      >
        <span style={{ color: theme === 'dark' ? Colors.Gray3 : '#666' }}>
          {t('Weather Info')}
        </span>
        <FaCloud style={{ color: '#4169e1', fontSize: 20 }} />
        <span style={{ color: theme === 'dark' ? Colors.Gray3 : '#666' }}>
          {weatherData.current.temperature}°C
        </span>
        <span style={{ color: theme === 'dark' ? Colors.Gray3 : '#666' }}>
          {weatherData.current.humidity}%
        </span>
        <span style={{ color: theme === 'dark' ? Colors.Gray3 : '#666' }}>
          {windSpeed} m/s
        </span>
      </div>
    </div>
  );
};

export default WeatherInfo;
