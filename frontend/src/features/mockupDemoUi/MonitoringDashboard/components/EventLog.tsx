import React from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

const EventLog: React.FC = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  // Random data generation
  const gaugeValue = Math.floor(Math.random() * 41) + 50; // 50-90
  const eventCount = Math.floor(Math.random() * 5) + 1; // 1-5

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
      }}
    >
      <div
        style={{
          width: 150,
          height: 150,
          borderRadius: '50%',
          background: `conic-gradient(#4169e1 0% ${gaugeValue}%, #e0e0e0 ${gaugeValue}% 100%)`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
          marginBottom: 20,
          boxShadow: '0 0 15px rgba(65, 105, 225, 0.2)',
        }}
      >
        <div
          style={{
            position: 'absolute',
            width: 120,
            height: 120,
            borderRadius: '50%',
            backgroundColor: theme === 'dark' ? Colors.Black : '#ffffff',
          }}
        />
        <div
          style={{
            position: 'relative',
            zIndex: 1,
            fontSize: 24,
            fontWeight: 'bold',
            color: theme === 'dark' ? Colors.Gray3 : '#333',
          }}
        >
          {gaugeValue}%
        </div>
      </div>
      <div style={{ color: theme === 'dark' ? Colors.Gray3 : '#333' }}>
        {t('Event Rate')} - {eventCount}건
      </div>
    </div>
  );
};

export default EventLog;
