import React from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

const DeliveryReservations: React.FC = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  // Random data generation
  const todayReservations = Math.floor(Math.random() * 50) + 150; // 150-200
  const yesterdayReservations = Math.floor(Math.random() * 50) + 150; // 150-200

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
          {t('Today')}
        </div>
        <div
          style={{
            fontSize: 24,
            fontWeight: 'bold',
            color: theme === 'dark' ? Colors.Gray3 : '#333',
          }}
        >
          {todayReservations}
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
          {t('Yesterday')}
        </div>
        <div
          style={{
            fontSize: 24,
            fontWeight: 'bold',
            color: theme === 'dark' ? Colors.Gray3 : '#333',
          }}
        >
          {yesterdayReservations}
        </div>
      </div>
    </div>
  );
};

export default DeliveryReservations;
