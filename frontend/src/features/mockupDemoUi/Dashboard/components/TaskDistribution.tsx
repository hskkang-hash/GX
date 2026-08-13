import React from 'react';
import { Bar } from 'react-chartjs-2';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

interface TaskDistributionProps {
  taskDistribution: number[];
}

const TaskDistribution: React.FC<TaskDistributionProps> = ({
  taskDistribution,
}) => {
  const [theme] = useTheme();

  const barData = {
    labels: ['배송', '감시/정찰', '기타'],
    datasets: [
      {
        data: taskDistribution,
        backgroundColor: ['#4cc9f0', '#4169e1', '#a78bfa'],
        barPercentage: 0.6,
      },
    ],
  };

  return (
    <div
      className="bar-chart"
      style={{ height: 250 }}
    >
      <Bar
        data={barData}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          indexAxis: 'y',
          plugins: { legend: { display: false } },
          scales: {
            x: {
              beginAtZero: true,
              max: 100,
              grid: {
                color: theme === 'dark' ? Colors.Gray7 : 'rgba(0,0,0,0.1)',
              },
              ticks: {
                color: theme === 'dark' ? Colors.Gray3 : '#666',
              },
            },
            y: {
              grid: { display: false },
              ticks: {
                color: theme === 'dark' ? Colors.Gray3 : '#666',
              },
            },
          },
        }}
      />
    </div>
  );
};

export default TaskDistribution;
