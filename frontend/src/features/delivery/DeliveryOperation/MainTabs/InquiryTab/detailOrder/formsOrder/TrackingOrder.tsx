import Timeline from '@mui/lab/Timeline';
import TimelineSeparator from '@mui/lab/TimelineSeparator';
import { Box, styled } from '@mui/material';
import dayjs from 'dayjs';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme, FormBlock } from 'rj-core';

import DroneIcon from '@/assets/images/drone.svg';
import MapKakao from '@/components/maps/MapKakao';
import Colors from '@/configs/Colors';
import DetailDevice from '@/features/device/detailDevice/DetailDevice';
import MapForRoute from '@/features/routes/components/MapForRoute';

import { Map } from '../../../../../../../components/maps';
import {
  CustomTimelineConnector,
  CustomTimelineContent,
  CustomTimelineDot,
  CustomTimelineItem,
} from '../style';

const TrackingOrder = ({ dataDetail }: { dataDetail: any }) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  console.log({ dataDetail });
  const historyOrder = dataDetail?.history?.map((item: any, index: number) => {
    return {
      id: index + 1,
      date: item?.created_on ? item?.created_on : '-',
      description: item.description,
    };
  });

  console.log({ historyOrder });

  const dronePosition = {
    lat: dataDetail?.delivery_events[1]?.lat,
    lng: dataDetail?.delivery_events[1]?.lng,
  };

  const groupedData = useMemo(() => {
    return Object.values(
      dataDetail?.delivery_events.reduce((acc: any, event: any) => {
        if (!acc[event.package_id]) {
          acc[event.package_id] = {
            package_id: event.package_id,
            events: [],
          };
        }
        acc[event.package_id].events.push(event);
        return acc;
      }, {}),
    );
  }, [dataDetail]);
  const [mapCenter, setMapCenter] = useState<
    { lat: number; lng: number } | undefined
  >(undefined);
  const [mapBounds, setMapBounds] = useState<
    { lat: number; lng: number } | undefined
  >(undefined);

  useEffect(() => {
    if (groupedData.length === 0 || groupedData?.[0]?.events?.length === 0) {
      setMapBounds(undefined);
      setMapCenter({ lat: 37.5665, lng: 126.978 });
      return;
    }

    const points: { lat: number; lng: number }[] = [];

    // Add drone position if available

    // Add route terminals if available
    if (groupedData.length > 0 && groupedData?.[0]?.events?.length > 0) {
      points.push(...groupedData?.[0]?.events);
    }

    if (points.length > 0) {
      // Calculate bounds
      const lats = points.map((p) => p.lat);
      const lngs = points.map((p) => p.lng);

      const bounds = {
        sw: {
          lat: Math.min(...lats) - 0.01, // Add some padding
          lng: Math.min(...lngs) - 0.01,
        },
        ne: {
          lat: Math.max(...lats) + 0.01,
          lng: Math.max(...lngs) + 0.01,
        },
      };
      setMapBounds(bounds);

      // Calculate center
      const center = {
        lat: (bounds.sw.lat + bounds.ne.lat) / 2,
        lng: (bounds.sw.lng + bounds.ne.lng) / 2,
      };
      setMapCenter(center);
    }
  }, [groupedData]);

  console.log('groupedData', groupedData);
  return (
    <Box
      sx={{
        display: 'grid',
        gap: '24px',
        gridTemplateColumns: '8fr 4fr',
        alignItems: 'start',
      }}
    >
      {/* <MapForRoute
                dronePosition={dronePosition}
                iconDrone={DroneIcon}
                routeGroups={groupedData.map(group =>
                    group.events.map((stop: any) => ({
                        name: stop.terminal_stop,
                        lat: +stop.lat,
                        lng: +stop.lng,
                    }))
                )}
                height="650px"
            /> */}
      <Map
        center={mapCenter}
        operatingMarkers={
          groupedData.length > 0 && groupedData[0].events.length > 0
            ? groupedData[0].events.map((stop: any) => ({
                name: stop.terminal_stop,
                lat: stop.lat,
                lng: stop.lng,
              }))
            : []
        }
        polylines={
          groupedData.length > 0 && groupedData[0].events.length > 0
            ? [
                groupedData[0].events.map((stop: any) => ({
                  lat: stop.lat,
                  lng: stop.lng,
                })),
              ]
            : []
        }
        bounds={mapBounds}
        style={{ height: 650 }}
      />
      <FormBlock style={{ zIndex: 1000 }}>
        <div className="header-title">{t('History')}</div>

        <Timeline sx={{ padding: '10px 5px 2px' }}>
          {historyOrder.map((item: any, index: number) => (
            <CustomTimelineItem>
              <TimelineSeparator>
                <CustomTimelineDot />
                <CustomTimelineConnector />
              </TimelineSeparator>
              <CustomTimelineContent>
                <span style={{ color: Colors.Gray5 }}>{item.description}</span>

                <span
                  style={{
                    color: theme === 'dark' ? Colors.Gray3 : Colors.Gray6,
                  }}
                >
                  {item.date}
                </span>
              </CustomTimelineContent>
            </CustomTimelineItem>
          ))}
        </Timeline>
      </FormBlock>
    </Box>
  );
};
export default TrackingOrder;
