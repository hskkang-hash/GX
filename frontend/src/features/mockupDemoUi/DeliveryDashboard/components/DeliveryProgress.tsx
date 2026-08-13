import React from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

const DeliveryProgress: React.FC = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  // Random data generation
  const scheduledDeliveries = Math.floor(Math.random() * 50) + 50; // 50-100
  const completedDeliveries = Math.floor(Math.random() * 50) + 100; // 100-150

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 15,
      }}
    >
      <div
        style={{
          background: theme === 'dark' ? Colors.Black : '#f8f8f8',
          padding: 15,
          borderRadius: 8,
          textAlign: 'center',
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
          {t('Scheduled')}
        </div>
        <div
          style={{
            fontSize: 24,
            fontWeight: 'bold',
            color: '#f39c12', // Warning color
          }}
        >
          {scheduledDeliveries}
        </div>
      </div>
      <div
        style={{
          background: theme === 'dark' ? Colors.Black : '#f8f8f8',
          padding: 15,
          borderRadius: 8,
          textAlign: 'center',
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
          {t('Completed')}
        </div>
        <div
          style={{
            fontSize: 24,
            fontWeight: 'bold',
            color: '#2ecc71', // Success color
          }}
        >
          {completedDeliveries}
        </div>
      </div>
    </div>
  );
};

export default DeliveryProgress;
