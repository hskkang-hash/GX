import { TFunction } from 'i18next';
import { useTranslation } from 'react-i18next';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { FormBlock, useTheme } from 'rj-core';

import { textLabel } from '../../../configs/Colors';
import { SurveyMissionState } from '../types/surveyMission.types';

const GENERAL_DATA = {
  name: {
    label: 'SurveyMission.Name',
    code: 'string',
  },
  // return_to_home: {
  //   label: 'SurveyMission.Return',
  //   type: 'string',
  // },
  maximum_drones: {
    label: 'SurveyMission.Maximum Number of Drones',
    type: 'string',
  },
  purpose__name: {
    label: 'SurveyMission.Purpose',
    type: 'string',
  },
  log_collection: {
    label: 'SurveyMission.Log Collection',
    type: 'string',
  },
  video_recording: {
    label: 'SurveyMission.Video Recording',
    type: 'string',
  },
  video_analysis: {
    label: 'SurveyMission.Video Analysis',
    type: 'string',
  },
  altitude: {
    label: 'SurveyMission.Capture Altitude',
    type: 'unit',
  },
  total_distance: {
    label: 'SurveyMission.Total Distance',
    type: 'unit',
  },
  estimated_time: {
    label: 'SurveyMission.Total Estimated Time',
    type: 'unit',
  },
  region: {
    label: 'Region',
    type: 'string',
  },
  note: {
    label: 'Note',
    type: 'string',
  },
};

interface LeftDetailSurveyMissionProps {
  detailSurveyMission: SurveyMissionState;
  chartData: {
    waypointName: string;
    cruise_speed: number;
    operating_altitude: number;
    cumulativeDistance: number;
    order: number;
  }[];
}

// Custom tooltip component
const CustomTooltip = ({
  active,
  payload,
  t,
}: {
  active?: boolean;
  payload?: {
    payload: {
      waypointName: string;
      cruise_speed: number;
      operating_altitude: number;
    };
  }[];
  t: TFunction;
}) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div
        style={{
          backgroundColor: 'white',
          border: '1px solid #ccc',
          borderRadius: '4px',
          padding: '10px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        }}
      >
        <p
          style={{
            margin: '0 0 5px 0',
            fontWeight: 'bold',
            color: '#000000',
          }}
        >
          {data.waypointName}
        </p>
        <p style={{ margin: '0 0 3px 0', color: '#7086FD' }}>
          {t('Cruise Speed')}: {data.cruise_speed} m/s
        </p>
        <p style={{ margin: '0', color: '#6FD195' }}>
          {t('Operating Altitude')}: {data.operating_altitude} m
        </p>
      </div>
    );
  }
  return null;
};

export const LeftDetailSurveyMission: React.FC<
  LeftDetailSurveyMissionProps
> = ({ detailSurveyMission, chartData }) => {
  const { t } = useTranslation();
  const [theme] = useTheme();

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
        height: '68rem',
      }}
    >
      <FormBlock>
        <div>
          <div
            style={{
              fontWeight: 600,
              fontSize: '1.2rem',
              marginBottom: '1rem',
            }}
          >
            {t('General')}
          </div>
          {Object.keys(GENERAL_DATA).map((item, index) => {
            const fieldKey = item as keyof typeof GENERAL_DATA;
            const fieldValue =
              detailSurveyMission[fieldKey as keyof SurveyMissionState];
            const fieldConfig = GENERAL_DATA[fieldKey];

            return (
              <div
                key={index}
                className="d-flex"
                style={{
                  borderBottom:
                    index === Object.keys(GENERAL_DATA).length - 1
                      ? 'none'
                      : `1px solid ${theme === 'dark' ? '#444646' : '#DDDFE2'}`,
                  marginBottom: '1rem',
                }}
              >
                <p className="mb-1">{t(fieldConfig.label)}</p>
                <p className="ms-auto mb-1">
                  {fieldValue !== undefined &&
                  fieldValue !== null &&
                  fieldValue !== '' ? (
                    (() => {
                      // Handle boolean values for specific fields
                      if (
                        fieldKey === 'log_collection' ||
                        fieldKey === 'video_recording' ||
                        fieldKey === 'video_analysis'
                      ) {
                        return fieldValue === true
                          ? t('SurveyMission.Allow')
                          : t('SurveyMission.Not Allow');
                      }
                      // Handle boolean values for other fields
                      if (typeof fieldValue === 'boolean') {
                        return fieldValue ? t('Yes') : t('No');
                      }
                      return String(fieldValue);
                    })()
                  ) : (
                    <span>-</span>
                  )}
                </p>
              </div>
            );
          })}
        </div>
      </FormBlock>
      <FormBlock>
        <div>
          <div
            style={{
              fontWeight: 600,
              fontSize: '1.2rem',
              marginBottom: '1rem',
            }}
          >
            {t('Flight speed and altitude chart')}
          </div>
          <div
            style={{
              flex: 1,
              width: '100%',
              height: '29.2rem',
            }}
          >
            <ResponsiveContainer
              width="100%"
              height="100%"
            >
              <LineChart
                data={chartData}
                margin={{
                  top: 10,
                  right: 30,
                  left: 0,
                  bottom: 0,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="cumulativeDistance"
                  stroke={textLabel[theme === 'dark' ? 'dark' : 'light']}
                  label={{
                    position: 'insideBottom',
                    offset: -5,
                  }}
                />
                <YAxis
                  stroke={textLabel[theme === 'dark' ? 'dark' : 'light']}
                />
                <Tooltip content={<CustomTooltip t={t} />} />
                <Legend />
                <Line
                  type="linear"
                  dataKey="cruise_speed"
                  stroke="#7086FD"
                  activeDot={{ r: 8 }}
                  name={t('Cruise Speed (m/s)')}
                />
                <Line
                  type="linear"
                  dataKey="operating_altitude"
                  stroke="#6FD195"
                  activeDot={{ r: 8 }}
                  name={t('Altitude/Z')}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </FormBlock>
    </div>
  );
};
