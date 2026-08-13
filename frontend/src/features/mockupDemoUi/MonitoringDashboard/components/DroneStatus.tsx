import React from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

const DroneStatus: React.FC = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  // Random data generation
  const totalFlights = Math.floor(Math.random() * 6) + 3; // 3-8
  const totalFlightTime = Math.floor(Math.random() * 5) + 1; // 1-5
  const totalFlightDistance = Math.floor(Math.random() * 11) + 5; // 5-15

  return (
    <div>
      <div
        style={{
          marginBottom: 10,
          padding: 10,
          background: theme === 'dark' ? Colors.Black : '#f8f8f8',
          borderRadius: 5,
          display: 'flex',
          justifyContent: 'space-between',
          borderLeft: '3px solid #4169e1',
        }}
      >
        <span style={{ color: theme === 'dark' ? Colors.Gray3 : '#666' }}>
          {t('Total Flights')}
        </span>
        <span
          style={{
            color: theme === 'dark' ? Colors.Gray3 : '#333',
            fontWeight: 'bold',
          }}
        >
          - {totalFlights}회
        </span>
      </div>
      <div
        style={{
          marginBottom: 10,
          padding: 10,
          background: theme === 'dark' ? Colors.Black : '#f8f8f8',
          borderRadius: 5,
          display: 'flex',
          justifyContent: 'space-between',
          borderLeft: '3px solid #4169e1',
        }}
      >
        <span style={{ color: theme === 'dark' ? Colors.Gray3 : '#666' }}>
          {t('Total Flight Time')}
        </span>
        <span
          style={{
            color: theme === 'dark' ? Colors.Gray3 : '#333',
            fontWeight: 'bold',
          }}
        >
          - {totalFlightTime}시간
        </span>
      </div>
      <div
        style={{
          padding: 10,
          background: theme === 'dark' ? Colors.Black : '#f8f8f8',
          borderRadius: 5,
          display: 'flex',
          justifyContent: 'space-between',
          borderLeft: '3px solid #4169e1',
        }}
      >
        <span style={{ color: theme === 'dark' ? Colors.Gray3 : '#666' }}>
          {t('Total Flight Distance')}
        </span>
        <span
          style={{
            color: theme === 'dark' ? Colors.Gray3 : '#333',
            fontWeight: 'bold',
          }}
        >
          - {totalFlightDistance}km
        </span>
      </div>
    </div>
  );
};

export default DroneStatus;
