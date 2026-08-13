import { Box } from '@mui/material';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import { ChartDataItem, SurveyMissionState } from '../AddNewProfile.d';

interface FlightChartProps {
  surveyMission: SurveyMissionState;
  chartData: ChartDataItem[];
  label: string;
}

const GeneralInformation = ({ surveyMission, label }: FlightChartProps) => {
  const GENERAL_DATA = {
    purpose__name: {
      label: 'SurveyMission.Purpose',
      type: 'string',
    },
    // return_to_home: {
    //   label: 'SurveyMission.Return',
    //   type: 'string',
    // },
    maximum_drones: {
      label: 'SurveyMission.Maximum Number of Drones',
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
  const { t } = useTranslation();
  const [theme] = useTheme();
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div>
        <div
          style={{
            fontWeight: 600,
            fontSize: '1.2rem',
            marginBottom: '1rem',
          }}
        >
          {label}
        </div>
        {Object.keys(GENERAL_DATA).map((item, index) => {
          const fieldKey = item as keyof typeof GENERAL_DATA;
          const fieldValue =
            surveyMission?.[fieldKey as keyof SurveyMissionState];
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
    </Box>
  );
};

export default GeneralInformation;
