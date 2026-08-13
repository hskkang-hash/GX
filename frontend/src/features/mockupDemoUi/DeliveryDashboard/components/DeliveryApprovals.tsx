import React from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

const DeliveryApprovals: React.FC = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  // Random data generation
  const rejectedDeliveries = Math.floor(Math.random() * 30) + 20; // 20-50
  const approvedDeliveries = Math.floor(Math.random() * 50) + 100; // 100-150

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
          {t('Rejected')}
        </div>
        <div
          style={{
            fontSize: 24,
            fontWeight: 'bold',
            color: '#e74c3c', // Alert color
          }}
        >
          {rejectedDeliveries}
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
          {t('Approved')}
        </div>
        <div
          style={{
            fontSize: 24,
            fontWeight: 'bold',
            color: '#2ecc71', // Success color
          }}
        >
          {approvedDeliveries}
        </div>
      </div>
    </div>
  );
};

export default DeliveryApprovals;
