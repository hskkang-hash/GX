import React from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

interface SensorData {
  roll: string;
  pitch: string;
  yaw: string;
  gyroX: string;
  gyroY: string;
  gyroZ: string;
  accelX: string;
  accelY: string;
  accelZ: string;
  magX: string;
  magY: string;
  magZ: string;
  vibX: string;
  vibY: string;
  vibZ: string;
}

interface SensorStatusTableProps {
  sensorData: SensorData;
}

const SensorStatusTable: React.FC<SensorStatusTableProps> = ({
  sensorData,
}) => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  return (
    <table
      style={{
        width: '78%',
        border: '1px solid #e0e0e0',
        borderCollapse: 'collapse',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
      }}
    >
      <thead>
        <tr>
          <th
            colSpan={15}
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
              {t('Sensor status monitoring')}
            </label>
          </th>
        </tr>
        <tr>
          <th
            colSpan={3}
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 8,
              textAlign: 'center',
              fontWeight: 'bold',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            {t('Aircraft attitude')}
          </th>
          <th
            colSpan={3}
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 8,
              textAlign: 'center',
              fontWeight: 'bold',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            {t('Gyro sensor')}
          </th>
          <th
            colSpan={3}
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 8,
              textAlign: 'center',
              fontWeight: 'bold',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            {t('Acceleration sensor')}
          </th>
          <th
            colSpan={3}
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 8,
              textAlign: 'center',
              fontWeight: 'bold',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            {t('Geomagnetic sensor')}
          </th>
          <th
            colSpan={3}
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 8,
              textAlign: 'center',
              fontWeight: 'bold',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            {t('Vibration sensor')}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td
            style={{
              width: '6.66%',
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
              textAlign: 'center',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            Roll
          </td>
          <td
            style={{
              width: '6.66%',
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
              textAlign: 'center',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            Pitch
          </td>
          <td
            style={{
              width: '6.66%',
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
              textAlign: 'center',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            Yaw
          </td>
          <td
            style={{
              width: '6.66%',
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
              textAlign: 'center',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            X{t('axisLabel')}
          </td>
          <td
            style={{
              width: '6.66%',
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
              textAlign: 'center',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            Y{t('axisLabel')}
          </td>
          <td
            style={{
              width: '6.66%',
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
              textAlign: 'center',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            Z{t('axisLabel')}
          </td>
          <td
            style={{
              width: '6.66%',
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
              textAlign: 'center',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            X{t('axisLabel')}
          </td>
          <td
            style={{
              width: '6.66%',
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
              textAlign: 'center',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            Y{t('axisLabel')}
          </td>
          <td
            style={{
              width: '6.66%',
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
              textAlign: 'center',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            Z{t('axisLabel')}
          </td>
          <td
            style={{
              width: '6.66%',
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
              textAlign: 'center',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            X축{t('axisLabel')}
          </td>
          <td
            style={{
              width: '6.66%',
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
              textAlign: 'center',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            Y{t('axisLabel')}
          </td>
          <td
            style={{
              width: '6.66%',
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
              textAlign: 'center',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            Z{t('axisLabel')}
          </td>
          <td
            style={{
              width: '6.66%',
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
              textAlign: 'center',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            X{t('axisLabel')}
          </td>
          <td
            style={{
              width: '6.66%',
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
              textAlign: 'center',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            Y{t('axisLabel')}
          </td>
          <td
            style={{
              width: '6.66%',
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
              textAlign: 'center',
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            Z{t('axisLabel')}
          </td>
        </tr>
        <tr>
          <td
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
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
              }}
            />
          </td>
          <td
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
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
              }}
            />
          </td>
          <td
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
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
              }}
            />
          </td>
          <td
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
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
              }}
            />
          </td>
          <td
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
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
              }}
            />
          </td>
          <td
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
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
              }}
            />
          </td>
          <td
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
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
              }}
            />
          </td>
          <td
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
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
              }}
            />
          </td>
          <td
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
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
              }}
            />
          </td>
          <td
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
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
              }}
            />
          </td>
          <td
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
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
              }}
            />
          </td>
          <td
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
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
              }}
            />
          </td>
          <td
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
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
              }}
            />
          </td>
          <td
            style={{
              border: '1px solid #e0e0e0',
              background: theme === 'dark' ? '#2D2E30' : '#fff',
              padding: 6,
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
              }}
            />
          </td>
        </tr>
      </tbody>
    </table>
  );
};

export default SensorStatusTable;
