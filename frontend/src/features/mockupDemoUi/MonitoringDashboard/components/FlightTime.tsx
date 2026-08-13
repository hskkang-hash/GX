import React from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

const FlightTime: React.FC = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  // Random data generation
  const totalFlightHours = (Math.random() * 50 + 100).toFixed(1); // 100-150
  const todayFlightHours = (Math.random() * 4 + 2).toFixed(1); // 2-6
  const avgFlightHours = (Math.random() * 2 + 3).toFixed(1); // 3-5

  return (
    <div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 10,
        }}
      >
        <div
          style={{
            background: theme === 'dark' ? Colors.Black : '#f8f8f8',
            padding: 15,
            borderRadius: 5,
            textAlign: 'center',
            borderLeft: '3px solid #4169e1',
          }}
        >
          <div
            style={{
              color: theme === 'dark' ? Colors.Gray3 : '#666',
              fontSize: 14,
              marginBottom: 5,
            }}
          >
            {t('Total Flight Time')}
          </div>
          <div
            style={{
              color: theme === 'dark' ? Colors.Gray3 : '#333',
              fontSize: 24,
              fontWeight: 'bold',
              marginBottom: 5,
            }}
          >
            {totalFlightHours}
          </div>
          <div
            style={{
              color: theme === 'dark' ? Colors.Gray3 : '#666',
              fontSize: 12,
            }}
          >
            {t('hours')}
          </div>
        </div>
        <div
          style={{
            background: theme === 'dark' ? Colors.Black : '#f8f8f8',
            padding: 15,
            borderRadius: 5,
            textAlign: 'center',
            borderLeft: '3px solid #4169e1',
          }}
        >
          <div
            style={{
              color: theme === 'dark' ? Colors.Gray3 : '#666',
              fontSize: 14,
              marginBottom: 5,
            }}
          >
            {t("Today's Flight Time")}
          </div>
          <div
            style={{
              color: theme === 'dark' ? Colors.Gray3 : '#333',
              fontSize: 24,
              fontWeight: 'bold',
              marginBottom: 5,
            }}
          >
            {todayFlightHours}
          </div>
          <div
            style={{
              color: theme === 'dark' ? Colors.Gray3 : '#666',
              fontSize: 12,
            }}
          >
            {t('hours')}
          </div>
        </div>
        <div
          style={{
            background: theme === 'dark' ? Colors.Black : '#f8f8f8',
            padding: 15,
            borderRadius: 5,
            textAlign: 'center',
            borderLeft: '3px solid #4169e1',
          }}
        >
          <div
            style={{
              color: theme === 'dark' ? Colors.Gray3 : '#666',
              fontSize: 14,
              marginBottom: 5,
            }}
          >
            {t('Average Flight Time')}
          </div>
          <div
            style={{
              color: theme === 'dark' ? Colors.Gray3 : '#333',
              fontSize: 24,
              fontWeight: 'bold',
              marginBottom: 5,
            }}
          >
            {avgFlightHours}
          </div>
          <div
            style={{
              color: theme === 'dark' ? Colors.Gray3 : '#666',
              fontSize: 12,
            }}
          >
            {t('hours/day')}
          </div>
        </div>
      </div>
    </div>
  );
};

export default FlightTime;
