import React from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

interface StatusCounts {
  normal: number;
  warning: number;
  danger: number;
}

interface DroneStatusTableProps {
  statusCounts: StatusCounts;
}

const DroneStatusTable: React.FC<DroneStatusTableProps> = ({
  statusCounts,
}) => {
  const [theme] = useTheme();
  const { t } = useTranslation();
  return (
    <table
      style={{
        width: '20%',
        marginRight: '2%',
        border: '1px solid #e0e0e0',
        borderCollapse: 'collapse',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
      }}
    >
      <thead>
        <tr>
          <th
            colSpan={3}
            style={{
              padding: 8,
              textAlign: 'left',
              background: theme === 'dark' ? '#2D2E30' : '#f5f5f5',
              borderBottom: '1px solid #e0e0e0',
            }}
          >
            <label
              style={{
                fontWeight: 'bold',
                color: theme === 'dark' ? Colors.Gray3 : '#333',
              }}
            >
              {t('Drone Status Diagnosis Status')}
            </label>
          </th>
        </tr>
        <tr>
          <th
            colSpan={3}
            style={{
              padding: 8,
              textAlign: 'center',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              borderBottom: '1px solid #e0e0e0',
            }}
          >
            <label
              style={{
                fontWeight: 'bold',
                color: theme === 'dark' ? Colors.Gray3 : '#333',
              }}
            >
              {t('Condition Diagnosis')}
            </label>
          </th>
        </tr>
        <tr>
          <th
            style={{
              width: '33.33%',
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 8,
              textAlign: 'center',
              fontWeight: 'bold',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            {t('Situation')}
          </th>
          <th
            style={{
              width: '33.33%',
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 8,
              textAlign: 'center',
              fontWeight: 'bold',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            {t('Caution')}
          </th>
          <th
            style={{
              width: '33.33%',
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 8,
              textAlign: 'center',
              fontWeight: 'bold',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            {t('Danger')}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 8,
              textAlign: 'center',
            }}
          >
            <span
              style={{
                display: 'inline-block',
                width: 20,
                height: 20,
                borderRadius: '50%',
                background: '#1D9BE2',
                boxShadow: '0 0 5px rgba(0,0,0,0.1)',
              }}
            />
            <div style={{ marginTop: 4 }}>{statusCounts.normal}</div>
          </td>
          <td
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 8,
              textAlign: 'center',
            }}
          >
            <span
              style={{
                display: 'inline-block',
                width: 20,
                height: 20,
                borderRadius: '50%',
                background: '#808080',
                boxShadow: '0 0 5px rgba(0,0,0,0.1)',
              }}
            />
            <div style={{ marginTop: 4 }}>{statusCounts.warning}</div>
          </td>
          <td
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 8,
              textAlign: 'center',
            }}
          >
            <span
              style={{
                display: 'inline-block',
                width: 20,
                height: 20,
                borderRadius: '50%',
                background: '#cc0000',
                boxShadow: '0 0 5px rgba(0,0,0,0.1)',
              }}
            />
            <div style={{ marginTop: 4 }}>{statusCounts.danger}</div>
          </td>
        </tr>
      </tbody>
    </table>
  );
};

export default DroneStatusTable;
