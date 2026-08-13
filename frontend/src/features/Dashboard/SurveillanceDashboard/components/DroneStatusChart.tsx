import React from 'react';
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, XAxis, YAxis } from 'recharts';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';
import Colors from '@/configs/Colors';
import { DroneStatusOverview } from '../hooks/useSurveillanceDashboard';
import DroneStatusChartSkeleton from './DroneStatusChartSkeleton';

interface DroneStatusChartProps {
  data: DroneStatusOverview | null;
  isLoading?: boolean;
}

const DroneStatusChart: React.FC<DroneStatusChartProps> = ({ data, isLoading = false }) => {
  const { t } = useTranslation();
  const [theme] = useTheme();

  if (isLoading || !data) {
    return (
      <DroneStatusChartSkeleton />
    );
  }

  const chartData = [
    {
      label: t('Active'),
      value: data.active,
      color: '#4caf50',
    },
    {
      label: t('On Mission'),
      value: data.on_mission,
      color: '#ff9800',
    },
    {
      label: t('Warning'),
      value: data.warning,
      color: '#f44336',
    },
    {
      label: t('Inactive'),
      value: data.inactive,
      color: '#9e9e9e',
    },
  ];

  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
        overflow: 'hidden',
      }}
    >
      <h3
        style={{
          margin: '0 0 1.25rem 0',
          fontSize: '1.25rem',
          color: theme === 'dark' ? Colors.Gray3 : '#333',
          flexShrink: 0,
        }}
      >
        {t('SurveillanceDashboard.Drone Status Overview')}
      </h3>
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
        <ResponsiveContainer
          width="100%"
          height="100%"
        >
          <BarChart
            data={chartData}
            margin={{
              top: 16,
              right: 8,
              left: 0,
            }}
          >
            <CartesianGrid
              strokeDasharray="1 1"
              stroke={theme === 'dark' ? Colors.Gray6 : 'rgba(0,0,0,0.1)'}
              strokeWidth={1}
              strokeOpacity={1}
            />
            <XAxis
              dataKey="label"
              tickLine={false}
              fontSize={12}
              stroke={theme === 'dark' ? Colors.Gray8 : '#666'}
              tick={false}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              fontSize={12}
              domain={[0, 25]}
              ticks={[0, 10, 25]}
              stroke={theme === 'dark' ? Colors.Gray3 : '#666'}
              allowDecimals={false}
            />
            <Bar
              dataKey="value"
              radius={[4, 4, 0, 0]}
              maxBarSize={60}
            >
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.color}
                />
              ))}
              <LabelList
                dataKey="value"
                position="top"
                fontSize={12}
                fill={theme === 'dark' ? Colors.Gray3 : '#666'}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          gap: '1.25rem',
          flexWrap: 'wrap',
          flexShrink: 0,
        }}
      >
        {chartData.map((item) => (
          <div
            key={item.label}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <div
              style={{
                width: '0.5rem',
                height: '0.5rem',
                backgroundColor: item.color,
                borderRadius: '50%',
              }}
            />
            <span
              style={{
                fontSize: '1rem',
                color: theme === 'dark' ? Colors.Gray3 : '#666',
              }}
            >
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default DroneStatusChart;

