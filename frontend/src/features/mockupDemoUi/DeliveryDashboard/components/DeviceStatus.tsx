import React from 'react';
import { useTranslation } from 'react-i18next';
import { FaRobot } from 'react-icons/fa';
import { TbDrone } from 'react-icons/tb';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

const DeviceStatus: React.FC = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  // Random data generation
  const deviceCounts = {
    [t('Under 25kg')]: Math.floor(Math.random() * 10) + 30, // 30-40
    [t('Under 40kg')]: Math.floor(Math.random() * 10) + 20, // 20-30
    [t('Over 40kg')]: Math.floor(Math.random() * 10) + 10, // 10-20
  };

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 15,
        textAlign: 'center',
      }}
    >
      {Object.entries(deviceCounts).map(([label, count], index) => (
        <div
          key={label}
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 10,
          }}
        >
          <div
            style={{
              color: '#4169e1',
              fontSize: 24,
            }}
          >
            {index === 2 ? (
              <FaRobot />
            ) : (
              <TbDrone
                width={32}
                height={32}
              />
            )}
          </div>
          <div
            style={{
              color: theme === 'dark' ? Colors.Gray3 : '#666',
              fontSize: 12,
            }}
          >
            {label}
          </div>
          <div
            style={{
              fontSize: 20,
              fontWeight: 'bold',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            {count}
            {t('units')}
          </div>
        </div>
      ))}
    </div>
  );
};

export default DeviceStatus;
