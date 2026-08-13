import React from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

const EmergencyStatus: React.FC = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  // Random data generation
  const emergencyCounts = {
    drone: Math.floor(Math.random() * 4), // 0-3
    station: Math.floor(Math.random() * 3), // 0-2
    gcs: Math.floor(Math.random() * 2), // 0-1
  };

  // Random emergency items
  const emergencyTypes = [
    '배터리 과열',
    '통신 불안정',
    '전원 불안정',
    'GPS 오류',
    '모터 이상',
  ];
  const severityLevels = ['high', 'medium', 'low'];
  const severityLabels = ['심각', '경고', '주의'];

  const generateRandomTime = () => {
    const hours = Math.floor(Math.random() * 24)
      .toString()
      .padStart(2, '0');
    const minutes = Math.floor(Math.random() * 60)
      .toString()
      .padStart(2, '0');
    return `${hours}:${minutes}`;
  };

  const emergencies = Array.from(
    { length: Math.floor(Math.random() * 4) + 1 },
    () => {
      const severity =
        severityLevels[Math.floor(Math.random() * severityLevels.length)];
      const label = severityLabels[severityLevels.indexOf(severity)];
      const type =
        emergencyTypes[Math.floor(Math.random() * emergencyTypes.length)];
      const device = Math.random() > 0.5 ? '드론' : '스테이션';
      const id = Math.floor(Math.random() * 201) + 100; // 100-300

      return {
        severity,
        label,
        description: `${device} #${id} ${type}`,
        time: generateRandomTime(),
      };
    },
  );

  return (
    <div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 10,
          marginBottom: 15,
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
            }}
          >
            {t('Drone')}
          </div>
          <div
            style={{
              color: theme === 'dark' ? Colors.Gray3 : '#333',
              fontSize: 28,
              fontWeight: 'bold',
            }}
          >
            {emergencyCounts.drone}
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
            }}
          >
            {t('Station')}
          </div>
          <div
            style={{
              color: theme === 'dark' ? Colors.Gray3 : '#333',
              fontSize: 28,
              fontWeight: 'bold',
            }}
          >
            {emergencyCounts.station}
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
            }}
          >
            {t('GCS')}
          </div>
          <div
            style={{
              color: theme === 'dark' ? Colors.Gray3 : '#333',
              fontSize: 28,
              fontWeight: 'bold',
            }}
          >
            {emergencyCounts.gcs}
          </div>
        </div>
      </div>

      <div style={{ marginTop: 15 }}>
        {emergencies.map((emergency, index) => (
          <div
            key={index}
            style={{
              background: theme === 'dark' ? Colors.Black : '#f8f8f8',
              padding: 10,
              borderRadius: 5,
              marginBottom: 10,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div
              style={{
                padding: '5px 10px',
                borderRadius: 3,
                fontSize: 12,
                fontWeight: 'bold',
                backgroundColor:
                  emergency.severity === 'high'
                    ? '#e74c3c'
                    : emergency.severity === 'medium'
                      ? '#f39c12'
                      : '#2ecc71',
                color: '#ffffff',
              }}
            >
              {emergency.label}
            </div>
            <div
              style={{
                color: theme === 'dark' ? Colors.Gray3 : '#333',
                fontSize: 14,
              }}
            >
              {emergency.description}
            </div>
            <div
              style={{
                color: theme === 'dark' ? Colors.Gray3 : '#666',
                fontSize: 12,
              }}
            >
              {emergency.time}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default EmergencyStatus;
