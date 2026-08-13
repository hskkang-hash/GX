import React from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

const MemberApprovals: React.FC = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  // Random data generation
  const pendingApprovals = Math.floor(Math.random() * 10) + 10; // 10-20
  const completedApprovals = Math.floor(Math.random() * 10) + 10; // 10-20
  const rejectedApprovals = Math.floor(Math.random() * 4) + 1; // 1-5

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 15 }}>
      <div
        style={{
          background: '#4169e1',
          color: '#fff',
          padding: 10,
          borderRadius: 8,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '1.125rem',
        }}
      >
        <span>{t('Pending Approval')}</span>
        <span style={{ fontWeight: 'bold' }}>{pendingApprovals}</span>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 10,
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
            {t('Completed')}
          </div>
          <div
            style={{
              fontSize: 24,
              fontWeight: 'bold',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            {completedApprovals}
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
            {t('Rejected')}
          </div>
          <div
            style={{
              fontSize: 24,
              fontWeight: 'bold',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            {rejectedApprovals}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MemberApprovals;
