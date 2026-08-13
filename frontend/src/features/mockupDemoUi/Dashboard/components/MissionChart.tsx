import React from 'react';
import { Line } from 'react-chartjs-2';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

interface MissionChartProps {
  missionData: {
    missionCount: number[];
    distance: number[];
  };
}

const MissionChart: React.FC<MissionChartProps> = ({ missionData }) => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  const lineData = {
    labels: ['4', '5', '6', '7', '8', '9', '10', '11', '12', '9', '10', '11'],
    datasets: [
      {
        label: '임무횟수',
        data: missionData.missionCount,
        borderColor: '#4169e1',
        backgroundColor: 'rgba(65, 105, 225, 0.1)',
        tension: 0.4,
        fill: true,
      },
      {
        label: '이동거리',
        data: missionData.distance,
        borderColor: '#4cc9f0',
        backgroundColor: 'rgba(76, 201, 240, 0.1)',
        tension: 0.4,
        fill: true,
      },
    ],
  };

  return (
    <div
      className="chart-container"
      style={{ height: 250 }}
    >
      <Line
        data={lineData}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: {
              beginAtZero: true,
              grid: {
                color: theme === 'dark' ? Colors.Gray7 : 'rgba(0,0,0,0.1)',
              },
              ticks: {
                color: theme === 'dark' ? Colors.Gray3 : '#666',
              },
            },
            x: {
              grid: {
                color: theme === 'dark' ? Colors.Gray7 : 'rgba(0,0,0,0.1)',
              },
              ticks: {
                color: theme === 'dark' ? Colors.Gray3 : '#666',
              },
            },
          },
        }}
      />
      <div
        className="legend"
        style={{
          display: 'flex',
          justifyContent: 'center',
          gap: 20,
          marginTop: 10,
        }}
      >
        <div
          className="legend-item"
          style={{
            display: 'flex',
            alignItems: 'center',
            fontSize: 12,
            color: theme === 'dark' ? Colors.Gray3 : '#666',
          }}
        >
          <div
            className="legend-color"
            style={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              background: '#4169e1',
              marginRight: 5,
            }}
          />
          <span>{t('Mission Count')}</span>
        </div>
        <div
          className="legend-item"
          style={{
            display: 'flex',
            alignItems: 'center',
            fontSize: 12,
            color: theme === 'dark' ? Colors.Gray3 : '#666',
          }}
        >
          <div
            className="legend-color"
            style={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              background: '#4cc9f0',
              marginRight: 5,
            }}
          />
          <span>{t('Distance')}</span>
        </div>
      </div>
    </div>
  );
};

export default MissionChart;
