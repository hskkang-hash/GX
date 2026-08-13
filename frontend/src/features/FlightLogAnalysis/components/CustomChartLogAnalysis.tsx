import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartData,
  ChartOptions,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { useTheme } from 'rj-core';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
);

interface CustomChartLogAnalysisProps {
  id?: string;
  data: ChartData<'line'>;
  options?: ChartOptions<'line'>;
}

const getDefaultOptions = (theme: string): ChartOptions<'line'> => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'right' as const,
      display: true,
      labels: {
        usePointStyle: true,
        pointStyle: 'line',
        padding: 20,
        font: {
          size: 12,
        },
        color: theme === 'dark' ? '#ECECEF' : '#2D2E30',
      },
    },
    title: {
      display: false,
    },
    tooltip: {
      titleColor: theme === 'dark' ? '#ECECEF' : '#2D2E30',
      bodyColor: theme === 'dark' ? '#ECECEF' : '#2D2E30',
      backgroundColor: theme === 'dark' ? '#2D2E30' : '#FFFFFF',
      borderColor: theme === 'dark' ? '#3C3D3E' : '#DDDFE2',
      callbacks: {
        label: function(context) {
          // Return the exact value without rounding
          const value = context.parsed.y;
          // Check if value is null or undefined
          if (value === null || value === undefined) {
            return `${context.dataset.label}: N/A`;
          }
          // Return the full precision value as string
          return `${context.dataset.label}: ${value}`;
        },
      },
    },
  },
  scales: {
    x: {
      display: true,
      border: {
        display: true,
        width: 2,
        color: theme === 'dark' ? '#ECECEF' : '#2D2E30',
      },
      ticks: {
        display: false,
      },
      grid: {
        display: false,
      },
    },
    y: {
      display: true,
      ticks: {
        color: theme === 'dark' ? '#ECECEF' : '#2D2E30',
      },
      grid: {
        color: theme === 'dark' ? '#3C3D3E' : '#DDDFE2',
      },
    },
  },
});

export const CustomChartLogAnalysis = ({
  id,
  data,
  options,
}: CustomChartLogAnalysisProps): React.JSX.Element => {
  const [theme] = useTheme();

  const defaultOptions = getDefaultOptions(theme);
  const mergedOptions = options
    ? { ...defaultOptions, ...options }
    : defaultOptions;

  return (
    <div
      id={id}
      style={{ width: '100%', height: '250px' }}
    >
      <Line
        options={mergedOptions}
        data={data}
      />
    </div>
  );
};
