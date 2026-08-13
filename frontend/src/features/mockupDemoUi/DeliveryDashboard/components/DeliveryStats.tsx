import React from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

const DeliveryStats: React.FC = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  // Random data generation
  const totalMonthlyDeliveries = Math.floor(Math.random() * 10000) + 10000; // 10000-20000

  return (
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
        {t('Total')}
      </div>
      <div
        style={{
          fontSize: 24,
          fontWeight: 'bold',
          color: '#2ecc71', // Success color
        }}
      >
        {totalMonthlyDeliveries.toLocaleString()}
      </div>
    </div>
  );
};

export default DeliveryStats;
