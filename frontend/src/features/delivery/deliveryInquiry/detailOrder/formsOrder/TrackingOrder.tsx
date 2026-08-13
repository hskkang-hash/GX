import Timeline from '@mui/lab/Timeline';
import TimelineSeparator from '@mui/lab/TimelineSeparator';
import { Box } from '@mui/material';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FormBlock, useTheme } from 'rj-core';

import DeliveryLocationIcon from '@/assets/images/delivery_location.svg';
import { Map } from '@/components/maps';
import Colors from '@/configs/Colors';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';
import API, { endpoint } from '@/services/API';

import useCommonAPI from '../../../../useCommonAPI/useAPI';
import {
  CustomTimelineConnector,
  CustomTimelineContent,
  CustomTimelineDot,
  CustomTimelineItem,
} from '../style';

const TrackingOrder = ({ dataDetail }: { dataDetail: any }) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const { converRawDateToDateTimeFormat } = useConvertDate();

  const historyOrder = dataDetail?.history?.map((item: any, index: number) => {
    return {
      id: index + 1,
      date: item?.created_on
        ? converRawDateToDateTimeFormat(item?.created_on)
        : '-',
      description: item.description,
    };
  });
  const { getLatLongFromAddressGoogle } = useCommonAPI();

  const mapRef = useRef<HTMLDivElement>(null);

  const [routeMap, setRouteMap] = useState<
    { lat: number; lng: number; name: string }[]
  >([]);

  // Helper function to calculate distance between two lat/lng points using Haversine formula
  const calculateDistance = (
    lat1: number,
    lng1: number,
    lat2: number,
    lng2: number,
  ): number => {
    const R = 6371; // Radius of the Earth in km
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLng = ((lng2 - lng1) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((lat1 * Math.PI) / 180) *
        Math.cos((lat2 * Math.PI) / 180) *
        Math.sin(dLng / 2) *
        Math.sin(dLng / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c; // Distance in km
  };

  useEffect(() => {
    const fetchRouteDetail = async () => {
      setRouteMap([]);
      const { success: routeDetailSuccess, data: routeDetailData } =
        await API.get(endpoint.routes + `/${dataDetail?.route}`);

      if (routeDetailSuccess && routeDetailData) {
        let closestTerminalIndex: number | null = null;

        // If no delivery terminal, find the closest terminal to destination
        if (!dataDetail?.delivery_terminal__id) {
          const result = await getLatLongFromAddressGoogle(
            dataDetail?.destination || '',
          );

          console.log('result', result);

          if (
            result.data?.lat &&
            result.data?.lng &&
            routeDetailData?.route_terminals
          ) {
            const destinationLat = result.data.lat;
            const destinationLng = result.data.lng;
            let minDistance = Infinity;
            routeDetailData.route_terminals.forEach(
              (
                terminal: { latitude: number; longitude: number },
                index: number,
              ) => {
                const distance = calculateDistance(
                  destinationLat,
                  destinationLng,
                  terminal.latitude,
                  terminal.longitude,
                );
                if (distance < minDistance) {
                  minDistance = distance;
                  closestTerminalIndex = index;
                }
              },
            );
          }
        }

        const routesMapData =
          routeDetailData?.route_terminals?.map((item: any, index: number) => {
            if (
              dataDetail?.delivery_terminal__id &&
              item.terminal_id === dataDetail?.delivery_terminal__id
            ) {
              return {
                lat: item.latitude,
                lng: item.longitude,
                name: item.name,
                icon: DeliveryLocationIcon,
              };
            } else if (
              !dataDetail?.delivery_terminal__id &&
              closestTerminalIndex !== null &&
              index === closestTerminalIndex
            ) {
              return {
                lat: item.latitude,
                lng: item.longitude,
                name: item.name,
                icon: DeliveryLocationIcon,
              };
            } else {
              return {
                lat: item.latitude,
                lng: item.longitude,
                name: item.name,
              };
            }
          }) || [];

        setRouteMap(routesMapData);
      }
    };

    if (dataDetail?.route) {
      fetchRouteDetail();
    }
  }, []);

  console.log({ routeMap });

  return (
    <Box
      sx={{
        display: 'grid',
        gap: '24px',
        gridTemplateColumns: '8fr 4fr',
        alignItems: 'start',
      }}
    >
      <div ref={mapRef}>
        <Map
          operatingMarkers={routeMap}
          polylines={routeMap.length > 0 ? [routeMap] : []}
          style={{ height: 650 }}
        />
      </div>
      <FormBlock style={{ zIndex: 1000 }}>
        <div className="header-title">{t('History')}</div>
        <Timeline sx={{ padding: '10px 5px 2px' }}>
          {historyOrder.map((item: any, index: number) => (
            <CustomTimelineItem key={index}>
              <TimelineSeparator>
                <CustomTimelineDot />
                <CustomTimelineConnector />
              </TimelineSeparator>
              <CustomTimelineContent>
                <span style={{ color: Colors.Gray5 }}>{item.date}</span>
                <span
                  style={{
                    color: theme === 'dark' ? Colors.Gray3 : Colors.PrimaryText,
                  }}
                >
                  {item.description}
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
