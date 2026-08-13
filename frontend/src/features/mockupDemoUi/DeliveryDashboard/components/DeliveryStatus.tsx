import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  ChartData,
} from 'chart.js';
import React from 'react';
import { Doughnut } from 'react-chartjs-2';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

ChartJS.register(ArcElement, Tooltip, Legend);

const DeliveryStatus: React.FC = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  // Random data generation
  const totalOrders = Math.floor(Math.random() * 100) + 200; // 200-300
  const completedOrders = Math.floor(Math.random() * 50) + 150; // 150-200
  const completionRate = ((completedOrders / totalOrders) * 100).toFixed(1);

  const data: ChartData<'doughnut'> = {
    labels: [t('Completed'), t('Pending')],
    datasets: [
      {
        data: [completedOrders, totalOrders - completedOrders],
        backgroundColor: ['#4169e1', '#e0e0e0'],
        borderWidth: 0,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '70%',
    plugins: {
      legend: {
        display: false,
      },
    },
  };

  return (
    <div style={{ position: 'relative', height: 300 }}>
      <div style={{ position: 'relative', width: '100%', height: '100%' }}>
        <Doughnut
          data={data}
          options={options}
        />
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            textAlign: 'center',
          }}
        >
          <div
            style={{
              fontSize: 24,
              fontWeight: 'bold',
              color: '#4169e1',
            }}
          >
            {completionRate}%
          </div>
          <div
            style={{
              fontSize: 14,
              color: theme === 'dark' ? Colors.Gray3 : '#666',
            }}
          >
            {t('Total')} {totalOrders}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DeliveryStatus;
