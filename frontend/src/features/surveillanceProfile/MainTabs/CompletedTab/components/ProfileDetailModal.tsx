import { Skeleton } from '@mui/material';
import React, {
  JSX,
  lazy,
  Suspense,
  useCallback,
  useMemo,
  useState,
} from 'react';
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
import {
  CenterBtn,
  CustomizableTable,
  CustomModal,
  FormBlock,
  useTheme,
} from 'rj-core';

import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';
import i18n from '@/i18n';

import { Tabs } from '../../../../../components/Form/Tabs';
import { textLabel } from '../../../../../configs/Colors';
import {
  WaypointDetails,
  WaypointDetailsProps,
} from '../../../components/WaypointDetails';
import { useDrawingModeStore } from '../../../stores/drawingModeStore';
import { DroneAssignment, SurveillanceProfileState } from '../../../types';
import { CustomTooltip } from './LeftProfileDetail';
import {
  COLUMNS_DRONE_LIST,
  COLUMNS_DRONE_LIST_GCS,
} from './LeftProfileDetail.constants';

const MapForRouteUnifiedLazy = lazy(
  () => import('../../../components/MapForRouteUnified'),
);

const InformationTab = React.memo(
  ({
    detailData,
  }: {
    detailData: SurveillanceProfileState | null;
  }): JSX.Element => {
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
        label: 'Capture Altitude',
        value: data?.altitude || '',
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
        label: 'Region',
        value: data?.region || '',
      },
      {
        label: 'Note',
        value: data?.note || '',
      },
    ];

    return (
      <FormBlock
        style={{ backgroundColor: theme === 'dark' ? '#2D2E30' : '#F6F7F8' }}
      >
        {generalDataManual(detailData).map((item, index) => {
          return (
            <div
              key={index}
              className="d-flex"
              style={{
                borderBottom:
                  index === generalDataManual(detailData).length - 1
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
      </FormBlock>
    );
  },
);

type MapTabProps = {
  markerData?: {
    lat: number;
    lng: number;
    name?: string;
    color?: string;
    id?: number;
  }[];
};

const MapTab = React.memo(
  ({ markerData = [], droneRoutes = [] }: MapTabProps): JSX.Element => {
    const [waypointDetails, setWaypointDetails] =
      useState<WaypointDetailsProps | null>(null);

    const currentShape = useDrawingModeStore((state) => state.currentShape);
    const isLineMode = useMemo(
      () => currentShape?.type === 'LINE',
      [currentShape],
    );
    const handleMarkerClick = useCallback(
      (marker: { lat: number; lng: number; name?: string; color?: string }) => {
        // Create waypoint details from marker data
        const waypointDetails: WaypointDetailsProps = {
          command: marker.command ?? 'WAYPOINT',
          frame: marker.frame ?? 'FRAME',
          param_1: marker?.param_1 ?? 0,
          param_2: marker?.param_2 ?? 0,
          param_3: marker?.param_3 ?? 0,
          param_4: marker?.param_4 ?? 0,
          latitude: marker.lat.toString() || '0',
          longitude: marker.lng.toString() || '0',
          altitude: marker?.altitude?.toString() || '0',
        };
        setWaypointDetails(waypointDetails);
      },
      [],
    );

    return (
      <div>
        <Suspense fallback={null}>
          <MapForRouteUnifiedLazy
            notUseActionButtons
            isLineMode={isLineMode}
            markerData={markerData.length > 0 ? markerData : []}
            style={{ height: '42rem' }}
            droneRoutes={droneRoutes}
            overlayContent={
              <WaypointDetails
                waypointDetails={waypointDetails}
                setWaypointDetails={setWaypointDetails}
              />
            }
            onMarkerClick={handleMarkerClick}
          />
        </Suspense>
      </div>
    );
  },
);

const DroneListTab = React.memo(
  ({
    showActualStartTime,
    chartData = [],
    droneAssignments = [],
    actualStartTime,
  }: {
    showActualStartTime?: boolean;
    chartData: {
      waypointName: string;
      cruise_speed: number;
      operating_altitude: number;
      cumulativeDistance: number;
      order: number;
    }[];
    droneAssignments: DroneAssignment[];
    actualStartTime?: string;
  }): JSX.Element => {
    console.log('actualStartTime', actualStartTime);
    const { t } = useTranslation();
    const [theme] = useTheme();
    const { converRawDateToTimeFormat } = useConvertDate();

    const data = useMemo(() => {
      return droneAssignments.map((assignment) => {
        return {
          ...assignment,
          start_time: converRawDateToTimeFormat(assignment.start_time),
          actual_start_time: converRawDateToTimeFormat(actualStartTime),
        };
      });
    }, [droneAssignments, converRawDateToTimeFormat, actualStartTime]);

    return (
      <div
        className="d-flex flex-column gap-3"
        style={{
          height: '42rem',
          overflowY: 'auto',
        }}
      >
        <div>
          <div
            style={{
              fontWeight: 600,
              fontSize: '1.2rem',
            }}
          >
            {t('Drones List')}
          </div>
          <div
            style={{
              flex: 1,
              width: '100%',
              height: '100%',
              marginBottom: '1rem',
            }}
          >
            <CustomizableTable
              columns={
                showActualStartTime
                  ? COLUMNS_DRONE_LIST_GCS
                  : COLUMNS_DRONE_LIST
              }
              data={{
                data: data,
              }}
              hasPagination={false}
              notUseGroupColumn
              useSystemSetting
              subTable
              notShowSelectRow
            />
          </div>
        </div>
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
      </div>
    );
  },
);

const ProfileDetailSkeleton = React.memo((): JSX.Element => {
  const tabPlaceholderIndices = Array.from({ length: 3 }, (_, index) => index);
  const infoRowPlaceholderIndices = Array.from(
    { length: 6 },
    (_, index) => index,
  );

  return (
    <>
      <div className="d-flex flex-column gap-3 flex-grow-1">
        <div className="d-flex gap-2">
          {tabPlaceholderIndices.map((item) => (
            <Skeleton
              key={`profile-detail-tab-skeleton-${item}`}
              variant="rounded"
              width="10rem"
              height="3rem"
              animation="wave"
            />
          ))}
        </div>
        <div className="d-flex gap-3 flex-grow-1">
          <div
            className="d-flex flex-column gap-2"
            style={{ flex: 1 }}
          >
            {infoRowPlaceholderIndices.map((item) => (
              <Skeleton
                key={`profile-detail-info-skeleton-${item}`}
                variant="rounded"
                height="3.5rem"
                animation="wave"
              />
            ))}
          </div>
          <div
            className="d-flex flex-column gap-3"
            style={{ flex: 1 }}
          >
            <Skeleton
              variant="rounded"
              height="20rem"
              animation="wave"
            />
            <Skeleton
              variant="rounded"
              height="18rem"
              animation="wave"
            />
          </div>
        </div>
      </div>
      <div className="d-flex justify-content-center">
        <Skeleton
          variant="rounded"
          width="8rem"
          height="3rem"
          animation="wave"
        />
      </div>
    </>
  );
});

export const ProfileDetailModal = React.memo(
  ({
    show,
    onHide,
    detailData,
    markerData,
    droneRoutes,
    showActualStartTime = false,
  }: {
    show: boolean;
    onHide: () => void;
    detailData: SurveillanceProfileState | null;
    markerData: { lat: number; lng: number }[];
    droneRoutes: {
      route_path: {
        latitude: number;
        longitude: number;
        name?: string;
      }[];
      device: {
        id: number;
        name: string;
        color?: string;
      };
    }[];
    showActualStartTime?: boolean;
  }): JSX.Element => {
    const { t } = useTranslation();
    const isLoading = detailData === null;

    return (
      <CustomModal
        id="profile-detail-modal"
        title={t('Profile Detail')}
        show={show}
        onHide={onHide}
      >
        <div
          className="mb-2 d-flex flex-column"
          style={{ width: '56.25rem', height: '50rem' }}
        >
          {isLoading ? (
            <ProfileDetailSkeleton />
          ) : (
            <>
              <Tabs
                items={[
                  {
                    label: t('Information'),
                    content: <InformationTab detailData={detailData} />,
                  },
                  {
                    label: t('Map'),
                    content: (
                      <MapTab
                        markerData={markerData}
                        droneRoutes={droneRoutes}
                      />
                    ),
                  },
                  {
                    label: t('Drone List'),
                    content: (
                      <DroneListTab
                        showActualStartTime={showActualStartTime}
                        chartData={detailData?.chart_data || []}
                        droneAssignments={detailData?.drone_assignments || []}
                        actualStartTime={detailData?.actual_start_time || null}
                      />
                    ),
                  },
                ]}
              />
              <CenterBtn
                type="button"
                variant="outline"
                color="secondary"
                size="lg"
                onClick={onHide}
                label={t('Close')}
              />
            </>
          )}
        </div>
      </CustomModal>
    );
  },
);
