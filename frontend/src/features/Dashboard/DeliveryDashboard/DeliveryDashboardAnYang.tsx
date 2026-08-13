import dayjs from 'dayjs';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Container,
  HeaderWithBtn,
  Main,
  useConfigSystem,
  useLoadingContext,
  useTheme,
} from 'rj-core';

import DroneIconHide from '@/assets/images/dashboard/drone-close.svg';
import DroneIcon from '@/assets/images/dashboard/drone.svg';
import HouseIcon from '@/assets/images/dashboard/house-door.svg';
import RouteIconHide from '@/assets/images/dashboard/route-close.svg';
import RouteIcon from '@/assets/images/dashboard/route.svg';
import HouseIconHide from '@/assets/images/dashboard/station-close.svg';
import DockingStationIcon from '@/assets/images/icon_hub.svg';
import Colors from '@/configs/Colors';

import MapAnYang from '../../../components/maps/MapAnYang';
import Panel from '../components/Panel';
import useDashboard from '../hooks/useDashboard';
import { DashboardData, Panel as PanelType } from '../types/IDashboard';
import DeliveryProgressAnYang from './componentsV2/DeliveryProgressAnYang';
import DeliveryProgressSkeletonAnYang from './componentsV2/DeliveryProgressSkeletonAnYang';
import OperationStatus from './componentsV2/OperationStatus';
import OperationStatusSkeleton from './componentsV2/OperationStatusSkeleton';
import WeatherInfoAngYang from './componentsV2/WeatherInfoAnYang';
import WeatherInfoSkeletonAnYang from './componentsV2/WeatherInfoSkeletonAnYang';
import { useAutoRefresh } from './componentsV2/autoRefresh';
import { useConvertDate } from '../utils/formatDateTime';


const controlOverlay = [
  { id: 'drone', active: DroneIcon, hide: DroneIconHide },
  { id: 'house', active: HouseIcon, hide: HouseIconHide },
  { id: 'route', active: RouteIcon, hide: RouteIconHide },
];

const DeliveryDashboardAnYang: React.FC = () => {
  const [theme] = useTheme();
  const headerPageRef = useRef(null);
  const { showLoading, hideLoading } = useLoadingContext();
  const { getDashboardDataAngYang, saveWeatherData, getDeviceLocation } =
    useDashboard();
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(
    null,
  );
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isInitialMount = useRef(true);
  const dashboardApiCalledRef = useRef(false);
  const dateRangeSetFromWeatherRef = useRef(false);
  const refreshLatLongDevice = 5;
  const [configSystem] = useConfigSystem();
  const { convertDateToUTCStartOfDay, convertDateToUTCEndOfDay } = useConvertDate();

  const [controlVisibility, setControlVisibility] = useState<{
    [key: string]: boolean;
  }>({
    drone: true,
    house: true,
    route: true,
  });
  const handleControlOverlay = (item: any) => {
    setControlVisibility((prev) => ({
      ...prev,
      [item.id]: !prev[item.id],
    }));
  };

  const formattedRoutes = (route: any) => {
    if (!Array.isArray(route)) return [];
    return route?.map((stop: any, index: number) => ({
      type: 'route',
      terminal_name: stop.name,
      lat: Number(stop.latitude),
      lng: Number(stop.longitude),
      for_robot: stop.for_robot || false,
    }));
  };

  const listRouteTerminals = React.useMemo(() => {
    return (
      dashboardData?.routes?.flatMap((item: any) => item?.route_terminals) ?? []
    );
  }, [dashboardData?.routes]);

  const listRouteForPolyline = React.useMemo(() => {
    return dashboardData?.routes?.map((item: any) => {
      return {
        route_terminals: item?.route_terminals,
        color: item?.is_active ? '#0CBA47' : '#9C9D9D',
      };
    });
  }, [dashboardData?.routes]);

  // const routeLocation = React.useMemo(
  //   () => formattedRoutes(listRouteTerminals),
  //   [listRouteTerminals],
  // );
  const routeForPolyline = React.useMemo(
    () =>
      listRouteForPolyline?.map(
        (item: { route_terminals: any[]; color: string }) => {
          return {
            route_terminals: formattedRoutes(item.route_terminals),
            color: item.color,
          };
        },
      ),
    [listRouteForPolyline],
  );


  const refreshTime = React.useMemo(
    () => configSystem?.['Dashboard']?.dashboard_refresh_interval || 0,
    [configSystem],
  );

  // this year get first day of the year
  const thisYearStartDate = useRef(
    dayjs().startOf('year').format('YYYY-MM-DD'),
  ).current;
  const thisYearEndDate = useRef(
    dayjs().endOf('year').format('YYYY-MM-DD'),
  ).current;

  const [dateRange, setDateRange] = useState<{
    start_date: string;
    end_date: string;
  }>({
    start_date: thisYearStartDate,
    end_date: thisYearEndDate,
  });

  const [searchLocationCenter, setSearchLocationCenter] = useState<{
    lat: number;
    lng: number;
  } | null>(null);



  const { shouldRefresh, consumeRefreshFlag } = useAutoRefresh({
    refreshTime: refreshTime,
    isActive: dashboardData ? true : false,
  });
  const {
    shouldRefresh: shouldRefreshLatLongDevice,
    consumeRefreshFlag: consumeRefreshFlagLatLongDevice,
  } = useAutoRefresh({
    refreshTime: refreshLatLongDevice,
    isActive: dashboardData ? true : false,
  });

  const onRefreshDashboardData = useCallback(async (): Promise<void> => {
    showLoading();
    // setIsLoading(true);
    setIsRefreshing(true);
    try {
      let apiResponse;
      if (dateRange?.start_date && dateRange?.end_date) {
        apiResponse = await getDashboardDataAngYang({
          start_date: convertDateToUTCStartOfDay(dateRange.start_date),
          end_date: convertDateToUTCEndOfDay(dateRange.end_date),
        });
      } else {
        apiResponse = await getDashboardDataAngYang();
      }

      const { success, data } = apiResponse;
      if (success) {
        setDashboardData(data);
      }
    } finally {
      setIsRefreshing(false);
      // setIsLoading(false);
      hideLoading();
    }
  }, [
    dateRange,
    getDashboardDataAngYang,
    hideLoading,
    setDashboardData,
    setIsRefreshing,
    showLoading,
  ]);

  const [updateDeviceLocation, setUpdateDeviceLocation] = useState<any[]>([]);

  const onRefreshLatLongDevice = useCallback(async (): Promise<void> => {
    const { success, data } = await getDeviceLocation();
    if (success) {
      const deviceLocation = data.map((item: any) => {
        return {
          type: item.type.toLowerCase(),
          name: item.device,
          lat: item.location.latitude || 0,
          lng: item.location.longitude || 0,
          icon:
            item.type == 'Drone'
              ? `data:image/svg+xml;utf8,<svg width="32" height="32" viewBox="0 0 22 22" xmlns="http://www.w3.org/2000/svg"><path d="m6 3a3 3 0 0 0 -3 3 3 3 0 0 0 3 3 3 3 0 0 0 1.0859375-.2070312c.5392711.8209481.9140625 1.6424172.9140625 2.2070312 0 .563623-.3724493 1.384498-.9101562 2.205078a3 3 0 0 0 -1.0898438-.205078 3 3 0 0 0 -3 3 3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0 -.2050781-1.080078c.8233483-.542436 1.6446221-.919922 2.2050781-.919922.55949 0 1.37815.375313 2.201172.916016a3 3 0 0 0 -.201172 1.083984 3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0 -3-3 3 3 0 0 0 -1.085938.207031c-.539273-.820943-.914062-1.642417-.914062-2.207031 0-.563623.372445-1.3844956.910156-2.2050781a3 3 0 0 0 .002.00195 3 3 0 0 0 1.087844.2031281 3 3 0 0 0 3-3 3 3 0 0 0 -3-3 3 3 0 0 0 -3 3 3 3 0 0 0 .205078 1.0800781c-.823351.5424443-1.644622.9199219-2.205078.9199219-.55949 0-1.3781473-.3753084-2.2011719-.9160156a3 3 0 0 0 .2011719-1.0839844 3 3 0 0 0 -3-3zm0 1a2 2 0 0 1 2 2 2 2 0 0 1 -.0527344.453125c-.4577913-.368834-.8926099-.7589139-1.2402344-1.1601562a1 1 0 0 0 -.6933593-.2929688 1 1 0 0 0 -.7207031.2929688 1 1 0 0 0 0 1.4140624 1 1 0 0 0 .058594.054688c.3824613.333788.7551689.7476371 1.1074216 1.1835933a2 2 0 0 1 -.4589844.0546875 2 2 0 0 1 -2-2 2 2 0 0 1 2-2zm10 0a2 2 0 0 1 2 2 2 2 0 0 1 -2 2 2 2 0 0 1 -.457031-.054687c.37051-.4592027.761959-.8951713 1.164062-1.2382813a1 1 0 0 0 0-1.4140624 1 1 0 0 0 -1.414062 0 1 1 0 0 0 -.05274.054687c-.337606.3818392-.750702.7543351-1.185541 1.1054687a2 2 0 0 1 -.054688-.453125 2 2 0 0 1 2-2zm-10 10a2 2 0 0 1 .4570312.05469c-.3705108.459203-.7619484.895165-1.1640624 1.238281a1 1 0 0 0 0 1.414062 1 1 0 0 0 1.4140624 0 1 1 0 0 0 .052734-.05469c.3376223-.381857.7507063-.754333.1855473-1.105468a2 2 0 0 1 .0546875.453125 2 2 0 0 1 -2 2 2 2 0 0 1 -2-2 2 2 0 0 1 2-2zm10 0a2 2 0 0 1 2 2 2 2 0 0 1 -2 2 2 2 0 0 1 -2-2 2 2 0 0 1 .05273-.453125c.457792.368835.892604.758903 1.240235 1.160156a1 1 0 0 0 1.414062 0 1 1 0 0 0 0-1.414062c-.01717-.01465-.0336-.03387-.05078-.04883a1 1 0 0 0 -.0078-.0059c-.382475-.333732-.755177-.747602-1.107431-1.183551a2 2 0 0 1 .458984-.054688z" style="fill:%23${item?.color?.replace('#', '') || '000000'};fill-opacity:1;stroke:none"/></svg>`
              : `data:image/svg+xml;utf8,<svg width="150" height="150" viewBox="0 0 150 150" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M150 77.2308V110.692C150 113.771 147.493 116.269 144.403 116.269H137.903C136.485 103.63 125.637 93.9615 112.873 93.9615C100.109 93.9615 89.2612 103.63 87.8433 116.269H62.1567C60.7612 103.736 50.0672 93.9615 37.1269 93.9615C24.1866 93.9615 13.4925 103.736 12.097 116.269H5.59701C2.50746 116.269 0 113.771 0 110.692V82.8077C0 79.7292 2.50746 77.2308 5.59701 77.2308H150Z" fill="%23${item?.color?.replace('#', '') || '000000'}"/><path d="M144.403 17H89.7201C85.4478 17 81.6881 17 74.8134 17C67.9437 17 63.9925 17 60.2798 17H5.59701C2.50746 17 0 19.4985 0 22.5769V48.2233C0 49.3387 0.335821 50.4281 0.962687 51.3501L10.9739 66.0769H150V22.5769C150 19.4985 147.493 17 144.403 17ZM107.09 43.0256C103.999 43.0256 101.493 40.5287 101.493 37.4487C101.493 34.3688 103.999 31.8718 107.09 31.8718C110.181 31.8718 112.687 34.3688 112.687 37.4487C112.687 40.5287 110.181 43.0256 107.09 43.0256ZM129.478 43.0256C126.387 43.0256 123.881 40.5287 123.881 37.4487C123.881 34.3688 126.387 31.8718 129.478 31.8718C132.569 31.8718 135.075 34.3688 135.075 37.4487C135.075 40.5287 132.569 43.0256 129.478 43.0256Z" fill="%23${item?.color?.replace('#', '') || '000000'}"/><path d="M37.1268 133C44.8547 133 51.1194 126.758 51.1194 119.058C51.1194 111.358 44.8547 105.115 37.1268 105.115C29.399 105.115 23.1343 111.358 23.1343 119.058C23.1343 126.758 29.399 133 37.1268 133Z" fill="%23${item?.color?.replace('#', '') || '000000'}"/><path d="M112.873 133C120.601 133 126.866 126.758 126.866 119.058C126.866 111.358 120.601 105.115 112.873 105.115C105.145 105.115 98.8806 111.358 98.8806 119.058C98.8806 126.758 105.145 133 112.873 133Z" fill="%23${item?.color?.replace('#', '') || '000000'}"/></svg>`,
        };
      });
      setUpdateDeviceLocation(deviceLocation);
    }
  }, [getDeviceLocation]);

  useEffect(() => {
    if (shouldRefresh) {
      onRefreshDashboardData();
      consumeRefreshFlag();
    }
  }, [shouldRefresh, onRefreshDashboardData, consumeRefreshFlag]);

  useEffect(() => {
    if (shouldRefreshLatLongDevice) {
      onRefreshLatLongDevice();
      consumeRefreshFlagLatLongDevice();
    }
  }, [
    shouldRefreshLatLongDevice,
    onRefreshLatLongDevice,
    consumeRefreshFlagLatLongDevice,
  ]);

  const saveWeatherSetting = useCallback(
    async (data: any) => {
      try {
        const { success, message } = await saveWeatherData({
          latitude: data?.latitude,
          longitude: data?.longitude,
          address: data?.address,
        });
        if (success) {
          console.log('Save weather setting success', message);
        } else {
          console.log('Save weather setting error', message);
        }
      } catch (error) {
        console.log('Error save weather setting', error);
      }
    },
    [saveWeatherData],
  );

  const fetchDashboardDataWithDateRange = async (
    dateRange: {
      start_date: string;
      end_date: string;
    } | null,
  ) => {
    try {
      showLoading();
      setError(null);
      setIsRefreshing(true);
      let apiResponse;
      if (dateRange?.start_date && dateRange?.end_date) {
        apiResponse = await getDashboardDataAngYang({
          start_date: convertDateToUTCStartOfDay(dateRange?.start_date),
          end_date: convertDateToUTCEndOfDay(dateRange?.end_date),
        });
      } else {
        apiResponse = await getDashboardDataAngYang();
      }
      const { success, data } = apiResponse;
      if (success) {
        setDashboardData(data);
        setError(null);
      } else {
        setError('Failed to fetch dashboard data');
      }
    } catch (error) {
      setError('Network error occurred');
    } finally {
      hideLoading();
      setIsRefreshing(false);
    }
  };

  // Call API when dateRange changes
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      const initialDateRange = {
        start_date: thisYearStartDate,
        end_date: thisYearEndDate,
      };
      fetchDashboardDataWithDateRange(initialDateRange);
      dashboardApiCalledRef.current = true;
      return;
    }

    if (dashboardApiCalledRef.current) {
      const isDefaultDateRange =
        dateRange?.start_date === thisYearStartDate &&
        dateRange?.end_date === thisYearEndDate;

      if (isDefaultDateRange && !dateRangeSetFromWeatherRef.current) {
        dateRangeSetFromWeatherRef.current = true;
        return;
      }

      if (dateRange === null) {
        fetchDashboardDataWithDateRange(null);
      } else if (dateRange && dateRange.start_date && dateRange.end_date) {
        fetchDashboardDataWithDateRange(dateRange);
      } else {
        console.log('DateRange is invalid, skipping API call');
      }
    }
  }, [dateRange]);

  // get panel by title
  const getPanelByTitle = useCallback(
    (title: string): PanelType | undefined => {
      return dashboardData?.panels?.find((p) => p.panel_title === title);
    },
    [dashboardData?.panels],
  );

  // get location for map
  const result = React.useMemo(() => {
    const dataForMap = getPanelByTitle('Operation Status')?.panel_data.data;
    if (!dataForMap) return [];
    return dataForMap.flatMap((item: any) => {
      const hasAnyDevice = Object.entries(item.devices || {}).some(
        ([, deviceData]: [string, any]) => {
          const hasDrones = deviceData?.drones?.length > 0;
          const hasRobots = deviceData?.robots?.length > 0;
          return hasDrones || hasRobots;
        },
      );
      const hasLinkedTerminals = (item?.linked_terminals || []).length > 0;
      if (!hasAnyDevice && !hasLinkedTerminals) {
        return [];
      }
      const itemResults: any[] = [];
      if (item?.docking_station && item.docking_station.active === true) {
        // docking station location
        if (item?.docking_station) {
          itemResults.push({
            type: 'docking_station',
            name: item.docking_station.name,
            lat: parseFloat(item.docking_station.latitude),
            lng: parseFloat(item.docking_station.longitude),
            icon: DockingStationIcon,
          });
        }
      }

      // linked terminals location
      if (item?.linked_terminals) {
        item?.linked_terminals
          .filter((terminal: any) => terminal.active !== false)
          .forEach((terminal: any) => {
            itemResults.push({
              type: 'linked_terminals',
              name: terminal.name,
              lat: parseFloat(terminal.latitude || 0),
              lng: parseFloat(terminal.longitude || 0),
              icon: 'data:image/svg+xml;utf8,<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%2369DC8A" opacity="0.85"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>',
            });
          });
      }

      // devices location
      if (item?.devices) {
        Object.entries(item.devices).forEach(
          ([weight, deviceData]: [string, any]) => {
            if (deviceData?.drones && Array.isArray(deviceData.drones)) {
              deviceData.drones
                .filter((device: any) => device.status !== 'inactive')
                .forEach((device: any) => {
                  if (
                    device.location &&
                    device.location.latitude !== 0 &&
                    device.location.longitude !== 0
                  ) {
                    itemResults.push({
                      type: 'drone',
                      name: device.device,
                      lat: device.location.latitude || 0,
                      lng: device.location.longitude || 0,
                      icon: `data:image/svg+xml;utf8,<svg width="32" height="32" viewBox="0 0 22 22" xmlns="http://www.w3.org/2000/svg"><path d="m6 3a3 3 0 0 0 -3 3 3 3 0 0 0 3 3 3 3 0 0 0 1.0859375-.2070312c.5392711.8209481.9140625 1.6424172.9140625 2.2070312 0 .563623-.3724493 1.384498-.9101562 2.205078a3 3 0 0 0 -1.0898438-.205078 3 3 0 0 0 -3 3 3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0 -.2050781-1.080078c.8233483-.542436 1.6446221-.919922 2.2050781-.919922.55949 0 1.37815.375313 2.201172.916016a3 3 0 0 0 -.201172 1.083984 3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0 -3-3 3 3 0 0 0 -1.085938.207031c-.539273-.820943-.914062-1.642417-.914062-2.207031 0-.563623.372445-1.3844956.910156-2.2050781a3 3 0 0 0 .002.00195 3 3 0 0 0 1.087844.2031281 3 3 0 0 0 3-3 3 3 0 0 0 -3-3 3 3 0 0 0 -3 3 3 3 0 0 0 .205078 1.0800781c-.823351.5424443-1.644622.9199219-2.205078.9199219-.55949 0-1.3781473-.3753084-2.2011719-.9160156a3 3 0 0 0 .2011719-1.0839844 3 3 0 0 0 -3-3zm0 1a2 2 0 0 1 2 2 2 2 0 0 1 -.0527344.453125c-.4577913-.368834-.8926099-.7589139-1.2402344-1.1601562a1 1 0 0 0 -.6933593-.2929688 1 1 0 0 0 -.7207031.2929688 1 1 0 0 0 0 1.4140624 1 1 0 0 0 .058594.054688c.3824613.333788.7551689.7476371 1.1074216 1.1835933a2 2 0 0 1 -.4589844.0546875 2 2 0 0 1 -2-2 2 2 0 0 1 2-2zm10 0a2 2 0 0 1 2 2 2 2 0 0 1 -2 2 2 2 0 0 1 -.457031-.054687c.37051-.4592027.761959-.8951713 1.164062-1.2382813a1 1 0 0 0 0-1.4140624 1 1 0 0 0 -1.414062 0 1 1 0 0 0 -.05274.054687c-.337606.3818392-.750702.7543351-1.185541 1.1054687a2 2 0 0 1 -.054688-.453125 2 2 0 0 1 2-2zm-10 10a2 2 0 0 1 .4570312.05469c-.3705108.459203-.7619484.895165-1.1640624 1.238281a1 1 0 0 0 0 1.414062 1 1 0 0 0 1.4140624 0 1 1 0 0 0 .052734-.05469c.3376223-.381857.7507063-.754333.1855473-1.105468a2 2 0 0 1 .0546875.453125 2 2 0 0 1 -2 2 2 2 0 0 1 -2-2 2 2 0 0 1 2-2zm10 0a2 2 0 0 1 2 2 2 2 0 0 1 -2 2 2 2 0 0 1 -2-2 2 2 0 0 1 .05273-.453125c.457792.368835.892604.758903 1.240235 1.160156a1 1 0 0 0 1.414062 0 1 1 0 0 0 0-1.414062c-.01717-.01465-.0336-.03387-.05078-.04883a1 1 0 0 0 -.0078-.0059c-.382475-.333732-.755177-.747602-1.107431-1.183551a2 2 0 0 1 .458984-.054688z" style="fill:%23${device?.color?.replace('#', '') || '000000'};fill-opacity:1;stroke:none"/></svg>`,
                    });
                  }
                });
            }
            // Robot location
            if (deviceData?.robots && Array.isArray(deviceData.robots)) {
              deviceData.robots
                .filter((device: any) => device.status !== 'inactive')
                .forEach((device: any) => {
                  if (
                    device.location &&
                    device.location.latitude !== 0 &&
                    device.location.longitude !== 0
                  ) {
                    itemResults.push({
                      type: 'robot',
                      name: device.device,
                      lat: device.location.latitude || 0,
                      lng: device.location.longitude || 0,
                      icon: `data:image/svg+xml;utf8,<svg width="150" height="150" viewBox="0 0 150 150" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M150 77.2308V110.692C150 113.771 147.493 116.269 144.403 116.269H137.903C136.485 103.63 125.637 93.9615 112.873 93.9615C100.109 93.9615 89.2612 103.63 87.8433 116.269H62.1567C60.7612 103.736 50.0672 93.9615 37.1269 93.9615C24.1866 93.9615 13.4925 103.736 12.097 116.269H5.59701C2.50746 116.269 0 113.771 0 110.692V82.8077C0 79.7292 2.50746 77.2308 5.59701 77.2308H150Z" fill="%23${device?.color?.replace('#', '') || '000000'}"/><path d="M144.403 17H89.7201C85.4478 17 81.6881 17 74.8134 17C67.9437 17 63.9925 17 60.2798 17H5.59701C2.50746 17 0 19.4985 0 22.5769V48.2233C0 49.3387 0.335821 50.4281 0.962687 51.3501L10.9739 66.0769H150V22.5769C150 19.4985 147.493 17 144.403 17ZM107.09 43.0256C103.999 43.0256 101.493 40.5287 101.493 37.4487C101.493 34.3688 103.999 31.8718 107.09 31.8718C110.181 31.8718 112.687 34.3688 112.687 37.4487C112.687 40.5287 110.181 43.0256 107.09 43.0256ZM129.478 43.0256C126.387 43.0256 123.881 40.5287 123.881 37.4487C123.881 34.3688 126.387 31.8718 129.478 31.8718C132.569 31.8718 135.075 34.3688 135.075 37.4487C135.075 40.5287 132.569 43.0256 129.478 43.0256Z" fill="%23${device?.color?.replace('#', '') || '000000'}"/><path d="M37.1268 133C44.8547 133 51.1194 126.758 51.1194 119.058C51.1194 111.358 44.8547 105.115 37.1268 105.115C29.399 105.115 23.1343 111.358 23.1343 119.058C23.1343 126.758 29.399 133 37.1268 133Z" fill="%23${device?.color?.replace('#', '') || '000000'}"/><path d="M112.873 133C120.601 133 126.866 126.758 126.866 119.058C126.866 111.358 120.601 105.115 112.873 105.115C105.145 105.115 98.8806 111.358 98.8806 119.058C98.8806 126.758 105.145 133 112.873 133Z" fill="%23${device?.color?.replace('#', '') || '000000'}"/></svg>`,
                    });
                  }
                });
            }
          },
        );
      }
      return itemResults;
    });
  }, [dashboardData]);

  const [dataForMap, setDataForMap] = useState<any[]>([]);

  useEffect(() => {
    if (result && updateDeviceLocation.length > 0) {
      const staticLocations = result.filter(
        (item: any) => item.type !== 'drone' && item.type !== 'robot',
      );
      const finalLocations = staticLocations
        .concat(updateDeviceLocation)
        .concat(listRouteTerminals);
      let dataForMapFinal = finalLocations;

      if (!controlVisibility.drone) {
        dataForMapFinal = dataForMapFinal.filter(
          (item: any) => item.type !== 'drone' && item.type !== 'robot',
        );
      }

      if (!controlVisibility.house) {
        dataForMapFinal = dataForMapFinal.filter(
          (item: any) => item.type !== 'docking_station',
        );
      }

      if (!controlVisibility.route) {
        dataForMapFinal = dataForMapFinal.filter(
          (item: any) => item.type !== 'route',
        );
      }
      setDataForMap(dataForMapFinal);
    } else {
      const finalLocationss = result.concat(listRouteTerminals);
      let dataForMapFinalSecond = finalLocationss;
      if (!controlVisibility.drone) {
        dataForMapFinalSecond = dataForMapFinalSecond.filter(
          (item: any) => item.type !== 'drone' && item.type !== 'robot',
        );
      }
      if (!controlVisibility.house) {
        dataForMapFinalSecond = dataForMapFinalSecond.filter(
          (item: any) => item.type !== 'docking_station',
        );
      }

      setDataForMap(dataForMapFinalSecond);
    }
  }, [
    result,
    controlVisibility.drone,
    controlVisibility.house,
    controlVisibility.route,
    updateDeviceLocation,
    listRouteTerminals,
  ]);

  return (
    <Container>
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[]}
      />
      <Main>
        {/* Weather Info */}
        <div
          style={{
            color: theme === 'dark' ? Colors.Gray3 : '#333',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
            paddingBottom: '1rem',
          }}
        >
          <Panel
            fullHeight
            shouldHaveAspectRatio={false}
            contentStyles={{
              paddingTop: '0.75rem',
              paddingBottom: '0.75rem',
            }}
          >
            {isLoading ? (
              <WeatherInfoSkeletonAnYang />
            ) : (
              <WeatherInfoAngYang
                data={dashboardData}
                handleRefresh={onRefreshDashboardData}
                isRefreshing={isRefreshing}
                setSearchLocation={(locationValue) => {
                  setSearchLocationCenter(
                    locationValue?.lat && locationValue?.lng
                      ? {
                        lat: Number(locationValue?.lat),
                        lng: Number(locationValue?.lng),
                      }
                      : null,
                  );

                  if (
                    locationValue?.lat &&
                    locationValue?.lng &&
                    locationValue?.type !== 'weather_setting'
                  ) {
                    saveWeatherSetting({
                      latitude: locationValue?.lat,
                      longitude: locationValue?.lng,
                      address:
                        locationValue?.structured_formatting?.secondary_text ||
                        '',
                    });
                  }
                }}
                setDateRange={(newDateRange) => {
                  setDateRange(newDateRange);
                }}
              />
            )}
          </Panel>
        </div>

        {/* Main content */}
        <div
          style={{
            display: 'flex',
            gap: '1.5rem',
            height: `calc(100vh - 130px)`,
            width: '100%',
          }}
        >
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              width: '50%',
              gap: '1.5rem',
            }}
          >
            <Panel
              shouldHaveAspectRatio={false}
              panelStyles={{ height: '32.333%', flexShrink: 0 }}
            >
              {isLoading ? (
                <DeliveryProgressSkeletonAnYang />
              ) : (
                <DeliveryProgressAnYang
                  panel={getPanelByTitle('Overall Delivery Service Status')}
                />
              )}
            </Panel>
            <Panel
              shouldHaveAspectRatio={false}
              panelStyles={{ height: '65.666%', flexShrink: 0 }}
            >
              {isLoading ? (
                <OperationStatusSkeleton />
              ) : (
                <OperationStatus panel={getPanelByTitle('Operation Status')} />
              )}
            </Panel>
          </div>
          <div style={{ width: '50%' }}>
            {dashboardData?.routes && dataForMap?.length > 0 && (
              <MapAnYang
                centerTerminal={searchLocationCenter}
                operatingMarkers={dataForMap?.length > 0 ? dataForMap : []}
                style={{ height: `calc(100vh - 130px)` }}
                polylines={controlVisibility.route ? routeForPolyline : []}
                routeColor="#fc6703"
                overlayContent={
                  <div
                    style={{
                      display: 'flex',
                      background: '#fff',
                      borderRadius: '0.5rem',
                      padding: '0.5rem',
                      flexDirection: 'column',
                      gap: '1rem',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {controlOverlay.map((item, index) => (
                      <div
                        key={index}
                        onClick={() => handleControlOverlay(item)}
                        style={{
                          cursor: 'pointer',
                          opacity: controlVisibility[item.id] ? 1 : 0.5,
                          transition: 'opacity 0.2s ease',
                        }}
                      >
                        <img
                          src={
                            controlVisibility[item.id] ? item.active : item.hide
                          }
                          alt={item.id}
                        />
                      </div>
                    ))}
                  </div>
                }
              />
            )}
          </div>
        </div>
      </Main>
    </Container>
  );
};

export default DeliveryDashboardAnYang;
