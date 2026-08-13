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

import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';
import i18n from '@/i18n';

import { textLabel } from '../../../../../configs/Colors';
import { SurveillanceProfileState } from '../../../types';

// import { INFORMATION_DATA } from './LeftProfileDetail.constants';

// Custom tooltip component
export const CustomTooltip = ({
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

export const LeftProfileDetail = ({
  detailSurveyMission,
  chartData = [],
}: {
  detailSurveyMission?: SurveillanceProfileState | null;
  chartData?: {
    waypointName: string;
    cruise_speed: number;
    operating_altitude: number;
    cumulativeDistance: number;
    order: number;
  }[];
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const { converRawDateToDateTimeFormat, converRawDateToDateFormat } =
    useConvertDate();

  const generalDataManual = (data: SurveillanceProfileState | null) => [
    {
      label: 'Name',
      value: data?.name || '',
    },
    {
      label: 'Mission',
      value: data?.mission || '',
    },
    {
      label: 'Start Time',
      value: converRawDateToDateTimeFormat(data?.start_time || ''),
    },
    {
      label: 'Repeat',
      value:
        data?.repeat_type__code == null
          ? i18n.t('None_Survey')
          : data?.repeat_type__code === 'none'
            ? i18n.t('None_Survey')
            : data?.repeat_until_type__code === 'never'
              ? `${data?.repeat_type__name} - ${i18n.t('No end date')}`
              : data?.repeat_until_type__code === 'on_date'
                ? `${data?.repeat_type__name} - ${i18n.t('Until {{date}}', { date: converRawDateToDateFormat(data?.repeat_until_date || '') })}`
                : `${data?.repeat_type__name} - ${i18n.t('times {{count}}', { count: data?.repeat_occurrences ?? 0 })}`,
    },
    {
      label: 'Operator',
      value: data?.operator || '',
    },
    {
      label: 'Purpose',
      value: data?.purpose || '',
    },
    // {
    //   label: 'Return',
    //   value: data?.return || '',
    // },
    {
      label: 'Maximum number of drones',
      value: data?.maximum_number_of_drones || '',
    },
    {
      label: 'Total Distance',
      value: data?.total_distance || '',
    },
    {
      label: 'Total Estimated Time',
      value: data?.total_estimated_time || '',
    },
    {
      label: 'Note',
      value: data?.note || '',
    },
  ];

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
        height: '67rem',
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
            {t('Information')}
          </div>
          {generalDataManual(
            detailSurveyMission as SurveillanceProfileState | null,
          ).map((item, index) => {
            return (
              <div
                key={index}
                className="d-flex"
                style={{
                  borderBottom:
                    index ===
                    generalDataManual(
                      detailSurveyMission as SurveillanceProfileState | null,
                    ).length -
                      1
                      ? 'none'
                      : `1px solid ${theme === 'dark' ? '#444646' : '#DDDFE2'}`,
                  marginBottom: '1rem',
                }}
              >
                <p className="mb-1">{t(item.label)}</p>
                <p className="ms-auto mb-1">
                  {item.value !== undefined &&
                  item.value !== null &&
                  item.value !== '' ? (
                    (() => {
                      // Handle boolean values for other fields
                      if (typeof item.value === 'boolean') {
                        return item.value ? t('Yes') : t('No');
                      }
                      return String(item.value);
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
              height: '28.2rem',
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
