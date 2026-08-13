import React from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

const OperationLogs: React.FC = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  // Random data generation
  const droneLogs = Math.floor(Math.random() * 100) + 100; // 100-200
  const robotLogs = Math.floor(Math.random() * 100) + 300; // 300-400
  const droneLogSize = Math.floor(Math.random() * 30) + 40; // 40-70
  const robotLogSize = Math.floor(Math.random() * 20) + 60; // 60-80

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 15 }}>
      <div
        style={{
          background: theme === 'dark' ? Colors.Black : '#f8f8f8',
          padding: 15,
          borderRadius: 8,
          border: `1px solid ${theme === 'dark' ? Colors.Gray7 : '#e0e0e0'}`,
        }}
      >
        <div
          style={{
            color: theme === 'dark' ? Colors.Gray3 : '#666',
            fontSize: 14,
            marginBottom: 5,
          }}
        >
          {t('Drone Flight Logs')}
        </div>
        <div
          style={{
            fontSize: 24,
            fontWeight: 'bold',
            color: theme === 'dark' ? Colors.Gray3 : '#333',
            marginBottom: 5,
          }}
        >
          {droneLogs} {t('cases')}
        </div>
        <div
          style={{
            height: 8,
            background: theme === 'dark' ? Colors.Gray7 : '#e0e0e0',
            borderRadius: 4,
            marginTop: 5,
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${droneLogSize}%`,
              background: '#4169e1',
              borderRadius: 4,
            }}
          />
        </div>
        <div
          style={{
            color: theme === 'dark' ? Colors.Gray3 : '#666',
            fontSize: 12,
            marginTop: 5,
          }}
        >
          {t('Size')}: {droneLogSize} GB
        </div>
      </div>

      <div
        style={{
          background: theme === 'dark' ? Colors.Black : '#f8f8f8',
          padding: 15,
          borderRadius: 8,
          border: `1px solid ${theme === 'dark' ? Colors.Gray7 : '#e0e0e0'}`,
        }}
      >
        <div
          style={{
            color: theme === 'dark' ? Colors.Gray3 : '#666',
            fontSize: 14,
            marginBottom: 5,
          }}
        >
          {t('Robot Operation Logs')}
        </div>
        <div
          style={{
            fontSize: 24,
            fontWeight: 'bold',
            color: theme === 'dark' ? Colors.Gray3 : '#333',
            marginBottom: 5,
          }}
        >
          {robotLogs} {t('cases')}
        </div>
        <div
          style={{
            height: 8,
            background: theme === 'dark' ? Colors.Gray7 : '#e0e0e0',
            borderRadius: 4,
            marginTop: 5,
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${robotLogSize}%`,
              background: '#4169e1',
              borderRadius: 4,
            }}
          />
        </div>
        <div
          style={{
            color: theme === 'dark' ? Colors.Gray3 : '#666',
            fontSize: 12,
            marginTop: 5,
          }}
        >
          {t('Size')}: {robotLogSize} GB
        </div>
      </div>
    </div>
  );
};

export default OperationLogs;
