import React from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

const DeliveryItems: React.FC = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  // Random data generation
  const deliveryItems = {
    [t('Medicine')]: Math.floor(Math.random() * 200) + 400, // 400-600
    [t('Daily Necessities')]: Math.floor(Math.random() * 200) + 200, // 200-400
    [t('Agricultural Products')]: Math.floor(Math.random() * 100) + 300, // 300-400
    [t('Military Supplies')]: Math.floor(Math.random() * 100) + 100, // 100-200
    [t('Food Delivery')]: Math.floor(Math.random() * 100) + 500, // 500-600
    [t('Others')]: Math.floor(Math.random() * 100) + 400, // 400-500
  };

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 10,
      }}
    >
      {Object.entries(deliveryItems).map(([label, value]) => (
        <div
          key={label}
          style={{
            background: theme === 'dark' ? Colors.Black : '#f8f8f8',
            padding: 10,
            borderRadius: 8,
            textAlign: 'center',
            border: `1px solid ${theme === 'dark' ? Colors.Gray7 : '#e0e0e0'}`,
          }}
        >
          <div
            style={{
              color: theme === 'dark' ? Colors.Gray3 : '#666',
              fontSize: 12,
              marginBottom: 5,
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
            {value}
          </div>
        </div>
      ))}
    </div>
  );
};

export default DeliveryItems;
