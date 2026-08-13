import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { FormBlock, useTheme } from 'rj-core';

import i18n from '../../../i18n';
import { useDateTimeFormat } from '../../Handover/hooks/useDateFormat';
import { formatDateTime } from '../../Handover/utils/dateFormat';
import { FlightLogAnalysisState } from '../types/flightLogAnalysis.types';
import { CustomBadgeStatus } from './CustomBadgeStatus';

const generalDataManual = (
  data: FlightLogAnalysisState | null,
  dateFormat: string,
  timeFormat: string,
  timezoneCode: string | null,
) => {
  return [
    {
      label: 'Profile Name',
      value: data?.profile_drone__profile || '',
    },
    {
      label: 'Drone Name',
      value: data?.drone_name || '',
    },
    {
      label: 'Mission ID',
      value: data?.mission_id || '',
    },
    {
      label: 'Mission Name',
      value: data?.mission_name || '',
    },
    {
      label: 'Flight Start Time',
      value: data?.start_time
        ? formatDateTime(
            data?.start_time,
            dateFormat,
            timeFormat,
            i18n.language,
            timezoneCode,
          )
        : '',
    },
    {
      label: 'Flight End Time',
      value: data?.end_time
        ? formatDateTime(
            data?.end_time,
            dateFormat,
            timeFormat,
            i18n.language,
            timezoneCode,
          )
        : '',
    },
    {
      label: 'Total Distance',
      value: data?.total_distance || '',
    },
    {
      label: 'Start Point',
      value: data?.start_point__name || '',
    },
    {
      label: 'End Point',
      value: data?.end_point__name || '',
    },
    {
      label: 'Drone State Prediction',
      value: data?.drone_anomaly_prediction__name ? (
        <CustomBadgeStatus
          status={
            data?.drone_anomaly_prediction__code.toLowerCase() as
              | 'normal'
              | 'loading'
              | 'warning'
          }
          label={data?.drone_anomaly_prediction__name}
        />
      ) : (
        '-'
      ),
    },
  ];
};

export const InformationFlightLogDetail = ({
  detailInfo,
}: {
  detailInfo: FlightLogAnalysisState | null;
}) => {
  const [theme] = useTheme();
  const { t } = useTranslation();
  const { dateFormat, timeFormat, timezoneCode } = useDateTimeFormat();

  const generalData = useMemo(() => {
    return generalDataManual(detailInfo, dateFormat, timeFormat, timezoneCode);
  }, [detailInfo, dateFormat, timeFormat, timezoneCode]);

  return (
    <div>
      <FormBlock
        style={{
          backgroundColor: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
          padding: '1rem',
        }}
      >
        <div>
          {generalData.map((item, index) => {
            return (
              <div
                key={index}
                style={{
                  borderBottom:
                    index === generalData.length - 1
                      ? 'none'
                      : `1px solid ${theme === 'dark' ? '#444646' : '#DDDFE2'}`,
                  marginBottom: index === generalData.length - 1 ? '0' : '1rem',
                }}
              >
                <div
                  className={`d-flex  ${index === generalData.length - 1 ? 'mb-0' : 'mb-2'}`}
                >
                  <p
                    className="mb-0"
                    style={{
                      alignContent: 'center',
                    }}
                  >
                    {t(item.label)}
                  </p>
                  <p className="ms-auto mb-1">
                    {item.value !== undefined &&
                    item.value !== null &&
                    item.value !== '' ? (
                      item.value
                    ) : (
                      <span>-</span>
                    )}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </FormBlock>
    </div>
  );
};
