import React from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';
import Colors, { cardBg, infoBg } from '@/configs/Colors';
import { AbnormalSignsOverview as AbnormalSignsOverviewType } from '../hooks/useSurveillanceDashboard';
import { Box } from '@mui/material';
import Truncate from '@/components/truncate/Truncate';
import QuickDateRangeBtn from '@/components/QuickDateRangeBtn';
import { Control, useFormContext } from 'react-hook-form';
import AbnormalSignsOverviewSkeleton from './AbnormalSignsOverviewSkeleton';
import { useConvertDate } from '../../utils/formatDateTime';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

dayjs.extend(utc);
dayjs.extend(timezone);

interface AbnormalSignsOverviewProps {
  data: AbnormalSignsOverviewType | null;
  isLoading?: boolean;
  formatDate: string;
  control: Control<any>;
}

const AbnormalSignsOverview: React.FC<AbnormalSignsOverviewProps> = ({
  data,
  isLoading = false,
  formatDate,
  control: controlForm
}) => {
  const { watch } = useFormContext();
  const { t } = useTranslation();
  const [theme] = useTheme();


  const { dateFormat, timeZoneFormat } = useConvertDate();

  const formatDateDisplay = (dateValue: string | undefined): string => {
    if (!dateValue) return '';
    let parsed = dayjs(dateValue);
    if (!parsed.isValid()) {
      parsed = dayjs(dateValue, dateFormat);
    }
    if (!parsed.isValid()) return dateValue;
    return parsed.tz(timeZoneFormat).format(dateFormat);
  };

  if (isLoading || !data) {
    return (
      <AbnormalSignsOverviewSkeleton />
    );
  }

  const signsList = [
    {
      label: t('SurveillanceDashboard.Fire Smoke'),
      value: data.fire_smoke,
      color: '#f44336',
    },
    {
      label: t('SurveillanceDashboard.Animals'),
      value: data.animals,
      color: '#ff9800',
    },
    {
      label: t('SurveillanceDashboard.Human'),
      value: data.human,
      color: '#2196f3',
    },
    {
      label: t('SurveillanceDashboard.Vehicle'),
      value: data.vehicle,
      color: '#9c27b0',
    },
    {
      label: t('SurveillanceDashboard.Anomaly'),
      value: data.anomaly,
      color: '#ff5722',
    },
  ];

  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
        minHeight: 0,
        overflow: 'hidden',
      }}
    >
      {/* HEADER */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',

          flexWrap: 'wrap',
          gap: '0.75rem',
          flexShrink: 0,
        }}
      >
        <h3
          style={{
            margin: 0,
            fontSize: '1.25rem',
            color: theme === 'dark' ? Colors.Gray3 : '#333',
            flex: 1,
            minWidth: '12.5rem',
          }}
        >
          {t('SurveillanceDashboard.Abnormal Signs Overview')}
        </h3>
      </div>
      {/* DATE PICKER */}
      <Box sx={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        width: '100%',
      }}>
        <Box sx={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.5rem',
          border: `1px solid ${theme === 'dark' ? Colors.Gray6 : Colors.Gray4}`,
          borderRadius: '0.5rem',
          padding: '0.35rem',
        }}>
          {watch('start_date') && watch('end_date') && (
            <p
              style={{
                fontWeight: '500',
                fontSize: '1rem',
                lineHeight: '1',
                margin: 0,
                marginLeft: '0.25rem',
              }}
            >
              {formatDateDisplay(watch('start_date'))} - {formatDateDisplay(watch('end_date'))}
            </p>
          )}
          <QuickDateRangeBtn
            fromName="start_date"
            toName="end_date"
            control={controlForm}
            format={formatDate}
            heightForDashboard
            positionForDashboard
          />
        </Box>
      </Box>
      <div
        style={{
          flex: 1,
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          columnGap: '1rem',
          rowGap: '1.5rem',
          minHeight: 0,
          overflowY: 'auto',
          paddingTop: "1rem"
        }}
      >
        {signsList.map((sign) => (
          <Box
            key={sign.label}
            style={{
              position: 'relative',
              background: infoBg[theme === 'dark' ? 'dark' : 'light'],
              borderRadius: 8,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
            }}
          >
            <span
              style={{
                position: 'absolute',
                top: '0',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                background: cardBg[theme === 'dark' ? 'dark' : 'light'],
                padding: '2px 4px',
                borderRadius: 4,
                fontSize: `calc( (14 / 1920) * 100vw)`,
                textAlign: 'center',
                whiteSpace: 'nowrap',
              }}
            >
              <Truncate
                content={t(sign.label)}
                maxLengthContent={13}
              />
            </span>
            <span
              style={{
                fontWeight: 'bold',
                fontSize: `calc( (24 / 1920) * 100vw)`,
                color: '#2EB4FFE5',
              }}
            >
              {sign.value}
            </span>
          </Box>
        ))}
      </div>
    </div >
  );
};

export default AbnormalSignsOverview;
