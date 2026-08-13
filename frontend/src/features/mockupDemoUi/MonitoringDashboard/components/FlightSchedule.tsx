import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

const FlightSchedule: React.FC = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();
  const [selectedDate, setSelectedDate] = useState<number | null>(null);

  // Calendar data
  const weekdays = ['월', '화', '수', '목', '금', '토', '일'];
  const days = Array.from({ length: 31 }, (_, i) => i + 1);

  // Random flight data
  const flights = [
    {
      id: 'DRN-001',
      start: '공주시 스테이션',
      end: '금강 감시구역',
      distance: 12.5,
      status: '운행 중',
    },
    {
      id: 'DRN-003',
      start: '공주시 스테이션',
      end: '산림 감시구역',
      distance: 8.7,
      status: '완료',
    },
    {
      id: 'DRN-005',
      start: '공주시 스테이션',
      end: '배송지점 A',
      distance: 5.2,
      status: '대기 중',
    },
  ];

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Calendar Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 15,
          color: theme === 'dark' ? Colors.Gray3 : '#333',
        }}
      >
        <span>◀</span>
        <div style={{ fontSize: 18 }}>2025-03</div>
        <span>▶</span>
      </div>

      {/* Weekdays */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(7, 1fr)',
          textAlign: 'center',
          marginBottom: 10,
        }}
      >
        {weekdays.map((day) => (
          <div
            key={day}
            style={{
              padding: 5,
              color: theme === 'dark' ? Colors.Gray3 : '#666',
              fontSize: 14,
            }}
          >
            {day}
          </div>
        ))}
      </div>

      {/* Calendar Days */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(7, 1fr)',
          gap: 5,
          marginBottom: 15,
        }}
      >
        {days.map((day) => (
          <div
            key={day}
            onClick={() => setSelectedDate(day)}
            style={{
              padding: 10,
              textAlign: 'center',
              background: theme === 'dark' ? Colors.Black : '#f8f8f8',
              borderRadius: 5,
              cursor: 'pointer',
              fontSize: 14,
              border: selectedDate === day ? '1px solid #4169e1' : 'none',
              backgroundColor:
                selectedDate === day
                  ? '#4169e1'
                  : theme === 'dark'
                    ? Colors.Black
                    : '#f8f8f8',
              color:
                selectedDate === day
                  ? '#fff'
                  : theme === 'dark'
                    ? Colors.Gray3
                    : '#333',
            }}
          >
            {day}
          </div>
        ))}
      </div>

      {/* Flight Info */}
      <div style={{ marginTop: 'auto' }}>
        <div
          style={{
            marginBottom: 10,
            fontSize: 16,
            color: theme === 'dark' ? Colors.Gray3 : '#333',
          }}
        >
          {t('Flight Rate')}
        </div>
        <div
          style={{
            background: theme === 'dark' ? Colors.Black : '#f8f8f8',
            padding: 10,
            borderRadius: 5,
            borderLeft: '3px solid #4169e1',
          }}
        >
          <table
            style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}
          >
            <thead>
              <tr>
                <th
                  style={{
                    textAlign: 'left',
                    padding: 8,
                    color: theme === 'dark' ? Colors.Gray3 : '#666',
                  }}
                >
                  {t('Drone ID')}
                </th>
                <th
                  style={{
                    textAlign: 'left',
                    padding: 8,
                    color: theme === 'dark' ? Colors.Gray3 : '#666',
                  }}
                >
                  {t('Start')}
                </th>
                <th
                  style={{
                    textAlign: 'left',
                    padding: 8,
                    color: theme === 'dark' ? Colors.Gray3 : '#666',
                  }}
                >
                  {t('End')}
                </th>
                <th
                  style={{
                    textAlign: 'left',
                    padding: 8,
                    color: theme === 'dark' ? Colors.Gray3 : '#666',
                  }}
                >
                  {t('Distance')} (km)
                </th>
                <th
                  style={{
                    textAlign: 'left',
                    padding: 8,
                    color: theme === 'dark' ? Colors.Gray3 : '#666',
                  }}
                >
                  {t('Status')}
                </th>
              </tr>
            </thead>
            <tbody>
              {flights.map((flight) => (
                <tr key={flight.id}>
                  <td
                    style={{
                      padding: 8,
                      color: theme === 'dark' ? Colors.Gray3 : '#333',
                    }}
                  >
                    {flight.id}
                  </td>
                  <td
                    style={{
                      padding: 8,
                      color: theme === 'dark' ? Colors.Gray3 : '#333',
                    }}
                  >
                    {flight.start}
                  </td>
                  <td
                    style={{
                      padding: 8,
                      color: theme === 'dark' ? Colors.Gray3 : '#333',
                    }}
                  >
                    {flight.end}
                  </td>
                  <td
                    style={{
                      padding: 8,
                      color: theme === 'dark' ? Colors.Gray3 : '#333',
                    }}
                  >
                    {flight.distance}
                  </td>
                  <td
                    style={{
                      padding: 8,
                      color: theme === 'dark' ? Colors.Gray3 : '#333',
                    }}
                  >
                    {flight.status}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default FlightSchedule;
