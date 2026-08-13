import { t } from 'i18next';

// Configuration for different analysis types
const analysisConfig = {
  roll_analysis: {
    charts: [
      {
        name: 'Roll Analysis',
        datasets: [
          { field: 'roll', label: 'Roll', color: '#7086FD' },
          { field: 'desired_roll', label: 'Desired Roll', color: '#6FD195' },
        ],
      }
    ],
  },
  rollspeed_analysis: {
    charts: [
      {
        name: 'Rollspeed Analysis',
        datasets: [
          { field: 'rollspeed', label: 'Rollspeed', color: '#7086FD' },
        ],
      }
    ],
  },
  pitch_analysis: {
    charts: [
      {
        name: 'Pitch Analysis',
        datasets: [
          { field: 'pitch', label: 'Pitch', color: '#7086FD' },
          { field: 'desired_pitch', label: 'Desired Pitch', color: '#6FD195' },
        ],
      }
    ],
  },
  pitchspeed_analysis: {
    charts: [
      {
        name: 'Pitchspeed Analysis',
        datasets: [
          { field: 'pitchspeed', label: 'Pitchspeed', color: '#7086FD' },
        ],
      }
    ],
  },
  yaw_analysis: {
    charts: [
      {
        name: 'Yaw Analysis',
        datasets: [
          { field: 'yaw', label: 'Yaw', color: '#7086FD' },
        ],
      }
    ],
  },
  yawspeed_analysis: {
    charts: [
      {
        name: 'Yawspeed Analysis',
        datasets: [
          { field: 'yawspeed', label: 'Yawspeed', color: '#7086FD' },
        ],
      }
    ],
  },
};

export const convertDataChart = (data: any, language: string) => {
  // eslint-disable-line
  const items: {
    label: string;
    data: {
      labels: string[];
      datasets: {
        label: string;
        data: number[];
        borderColor: string;
        backgroundColor: string;
        borderWidth: number;
        tension: number;
      }[];
    }[];
  }[] = [];

  if (!data || typeof data !== 'object') {
    return items;
  }

  Object.entries(data).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      // Convert key to label (remove underscores and capitalize)
      const label = key
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (l) => l.toUpperCase());

      // Format timestamps to date format
      const labels = value.map((item: any) => {
        // eslint-disable-line
        const date = new Date(item.timestamp);
        return date.toLocaleString(language === 'en' ? 'en-US' : 'ko-KR', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        });
      });

      // Get configuration for this analysis type
      const config = analysisConfig[key as keyof typeof analysisConfig];

      if (config) {
        // Create charts based on configuration
        const charts = config.charts.map((chartConfig) => ({
          labels,
          datasets: chartConfig.datasets.map((datasetConfig) => ({
            label: t(datasetConfig.label),
            data: value.map((item: any) => item[datasetConfig.field]), // eslint-disable-line
            borderColor: datasetConfig.color,
            backgroundColor: datasetConfig.color,
            borderWidth: 2,
            tension: 0.8,
          })),
        }));

        // Add item with array of charts
        items.push({
          label,
          data: charts,
        });
      }
    }
  });

  return items;
};
