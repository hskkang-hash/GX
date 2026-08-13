import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Container,
  HeaderWithBtn,
  Main,
  useCalculateHeight,
  useTheme,
} from 'rj-core';

import MapKakao, { MarkerData } from '@/components/maps/MapKakao';
import Colors from '@/configs/Colors';
import { CustomRoutes } from '@/services/API';
import { remToPx } from '@/utils/utils';

import { Map } from '../../../components/maps';
import Panel from '../components/Panel';
import useDashboard from '../hooks/useDashboard';
import { DashboardData, Panel as PanelType } from '../types/IDashboard';
import DeliveryProgressV2 from './componentsV2/DeliveryProgressV2';
import OperationStatus from './componentsV2/OperationStatus';
import WeatherInfoAngYang from './componentsV2/WeatherInfoAnYang';

interface WeatherData extends DashboardData {
  temperature?: number;
  humidity?: number;
  wind_speed?: number;
  region?: string;
}

const fakeData = [
  {
    devices: {
      '0 kg': {
        drones: [],
        robots: [
          {
            type: 'Robot',
            color: '#ff09ef',
            device: 'D-12345678103',
            status: 'inactive',
            location: {
              latitude: 35.8714,
              longitude: 128.6014,
            },
          },
          {
            type: 'Robot',
            color: null,
            device: '4_3139613665613332_UDP:0.0.0.0:14556',
            status: 'inactive',
            location: {
              latitude: 33.4996,
              longitude: 126.5312,
            },
          },
        ],
      },
      '45.0 kg': {
        drones: [
          {
            type: 'Drone',
            color: '#ff09ef',
            device: 'D-12345678103',
            status: 'inactive',
            location: {
              latitude: 35.1796,
              longitude: 129.0756,
            },
          },
          {
            type: 'Drone',
            color: null,
            device: '4_3139613665613332_UDP:0.0.0.0:14556',
            status: 'inactive',
            location: {
              latitude: 35.1595,
              longitude: 126.8526,
            },
          },
        ],
        robots: [],
      },
    },
    docking_station: {
      name: 'test',
      latitude: '37.3770106054899', // gần Seoul
      longitude: '127.112728549656',
    },
    linked_terminals: [
      { name: 'ewrwer', active: true },
      { name: 'Huy Nguyen Khac', active: true },
      { name: 'Huy Nguyen Khac', active: true },
      { name: 'Huy Nguyen Khac', active: true },
      { name: 'Public', active: true },
      { name: 'rin_test_terminal4', active: true },
      { name: 'Samdeok Park (삼덕공원)', active: true },
      { name: 'Sammak Dog Park (삼막견공원)', active: true },
      { name: 'Seoksu Sports Park (석수체육공원)', active: true },
      { name: 'test docking-stations', active: true },
    ],
  },
];

const DeliveryDashboard: React.FC = () => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const headerPageRef = useRef(null);
  const { getDashboardDataAngYang, refreshDashboardData } = useDashboard();

  const [dashboardData, setDashboardData] = useState<WeatherData | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [markerData, setMarkerData] = useState<MarkerData[]>([]);
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(10)],
  });
  const [dateRange, setDateRange] = useState<{
    start_date: string;
    end_date: string;
  } | null>(null);

  const fetchDashboardData = async () => {
    setIsLoading(true);
    try {
      const { success, data } = await getDashboardDataAngYang();
      if (success) {
        setDashboardData(data);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const onRefreshDashboardData = async () => {
    setDateRange(null);
    setIsRefreshing(true);
    try {
      const { success, data } = await getDashboardDataAngYang();
      if (success) {
        setDashboardData(data);
      }
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardDataWithDateRange = async (dateRange: {
    start_date: string;
    end_date: string;
  }) => {
    setIsRefreshing(true);
    try {
      const { success, data } = await getDashboardDataAngYang({
        start_date: dateRange.start_date,
        end_date: dateRange.end_date,
      });
      if (success) {
        setDashboardData(data);
      }
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    if (dateRange?.start_date && dateRange?.end_date) {
      fetchDashboardDataWithDateRange({
        start_date: dateRange.start_date,
        end_date: dateRange.end_date,
      });
    }
  }, [dateRange]);

  const getPanelByTitle = (title: string): PanelType | undefined => {
    return dashboardData?.panels.find((p) => p.panel_title === title);
  };

  const result = React.useMemo(() => {
    const dataForMap = getPanelByTitle('Operation Status')?.panel_data.data;
    console.log({ dataForMap });
    if (!dataForMap) return [];
    return dataForMap.flatMap((item: any) => {
      const arr = [];
      // Add docking station
      if (item?.docking_station) {
        arr.push({
          type: 'docking_station',
          name: item.docking_station.name,
          lat: parseFloat(item.docking_station.latitude),
          lng: parseFloat(item.docking_station.longitude),
          icon: 'data:image/svg+xml;utf8,<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%23fd0000" opacity="0.85"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>',
        });
      }

      // Add devices
      if (item?.devices) {
        Object.entries(item.devices).forEach(
          ([weight, deviceData]: [string, any]) => {
            if (deviceData?.drones && Array.isArray(deviceData.drones)) {
              deviceData.drones.forEach((device: any) => {
                if (
                  device.location &&
                  device.location.latitude !== 0 &&
                  device.location.longitude !== 0
                ) {
                  arr.push({
                    name: device.device,
                    lat: device.location.latitude,
                    lng: device.location.longitude,
                    icon: `data:image/svg+xml;utf8,<svg width="32" height="32" viewBox="0 0 22 22" xmlns="http://www.w3.org/2000/svg"><path d="m6 3a3 3 0 0 0 -3 3 3 3 0 0 0 3 3 3 3 0 0 0 1.0859375-.2070312c.5392711.8209481.9140625 1.6424172.9140625 2.2070312 0 .563623-.3724493 1.384498-.9101562 2.205078a3 3 0 0 0 -1.0898438-.205078 3 3 0 0 0 -3 3 3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0 -.2050781-1.080078c.8233483-.542436 1.6446221-.919922 2.2050781-.919922.55949 0 1.37815.375313 2.201172.916016a3 3 0 0 0 -.201172 1.083984 3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0 -3-3 3 3 0 0 0 -1.085938.207031c-.539273-.820943-.914062-1.642417-.914062-2.207031 0-.563623.372445-1.3844956.910156-2.2050781a3 3 0 0 0 .002.00195 3 3 0 0 0 1.087844.2031281 3 3 0 0 0 3-3 3 3 0 0 0 -3-3 3 3 0 0 0 -3 3 3 3 0 0 0 .205078 1.0800781c-.823351.5424443-1.644622.9199219-2.205078.9199219-.55949 0-1.3781473-.3753084-2.2011719-.9160156a3 3 0 0 0 .2011719-1.0839844 3 3 0 0 0 -3-3zm0 1a2 2 0 0 1 2 2 2 2 0 0 1 -.0527344.453125c-.4577913-.368834-.8926099-.7589139-1.2402344-1.1601562a1 1 0 0 0 -.6933593-.2929688 1 1 0 0 0 -.7207031.2929688 1 1 0 0 0 0 1.4140624 1 1 0 0 0 .058594.054688c.3824613.333788.7551689.7476371 1.1074216 1.1835933a2 2 0 0 1 -.4589844.0546875 2 2 0 0 1 -2-2 2 2 0 0 1 2-2zm10 0a2 2 0 0 1 2 2 2 2 0 0 1 -2 2 2 2 0 0 1 -.457031-.054687c.37051-.4592027.761959-.8951713 1.164062-1.2382813a1 1 0 0 0 0-1.4140624 1 1 0 0 0 -1.414062 0 1 1 0 0 0 -.05274.054687c-.337606.3818392-.750702.7543351-1.185541 1.1054687a2 2 0 0 1 -.054688-.453125 2 2 0 0 1 2-2zm-10 10a2 2 0 0 1 .4570312.05469c-.3705108.459203-.7619484.895165-1.1640624 1.238281a1 1 0 0 0 0 1.414062 1 1 0 0 0 1.4140624 0 1 1 0 0 0 .052734-.05469c.3376223-.381857.7507063-.754333 1.1855473-1.105468a2 2 0 0 1 .0546875.453125 2 2 0 0 1 -2 2 2 2 0 0 1 -2-2 2 2 0 0 1 2-2zm10 0a2 2 0 0 1 2 2 2 2 0 0 1 -2 2 2 2 0 0 1 -2-2 2 2 0 0 1 .05273-.453125c.457792.368835.892604.758903 1.240235 1.160156a1 1 0 0 0 1.414062 0 1 1 0 0 0 0-1.414062c-.01717-.01465-.0336-.03387-.05078-.04883a1 1 0 0 0 -.0078-.0059c-.382475-.333732-.755177-.747602-1.107431-1.183551a2 2 0 0 1 .458984-.054688z" style="fill:%23${device?.color?.replace('#', '') || '000000'};fill-opacity:1;stroke:none"/></svg>`,
                  });
                }
              });
            }
            if (deviceData?.robots && Array.isArray(deviceData.robots)) {
              deviceData.robots.forEach((device: any) => {
                if (
                  device.location &&
                  device.location.latitude !== 0 &&
                  device.location.longitude !== 0
                ) {
                  arr.push({
                    name: device.device,
                    lat: device.location.latitude,
                    lng: device.location.longitude,
                    icon: `data:image/svg+xml;utf8,<svg width="150" height="150" viewBox="0 0 150 150" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M150 77.2308V110.692C150 113.771 147.493 116.269 144.403 116.269H137.903C136.485 103.63 125.637 93.9615 112.873 93.9615C100.109 93.9615 89.2612 103.63 87.8433 116.269H62.1567C60.7612 103.736 50.0672 93.9615 37.1269 93.9615C24.1866 93.9615 13.4925 103.736 12.097 116.269H5.59701C2.50746 116.269 0 113.771 0 110.692V82.8077C0 79.7292 2.50746 77.2308 5.59701 77.2308H150Z" fill="%231F1F20"/><path d="M144.403 17H89.7201C85.4478 17 81.6881 17 74.8134 17C67.9437 17 63.9925 17 60.2798 17H5.59701C2.50746 17 0 19.4985 0 22.5769V48.2233C0 49.3387 0.335821 50.4281 0.962687 51.3501L10.9739 66.0769H150V22.5769C150 19.4985 147.493 17 144.403 17ZM107.09 43.0256C103.999 43.0256 101.493 40.5287 101.493 37.4487C101.493 34.3688 103.999 31.8718 107.09 31.8718C110.181 31.8718 112.687 34.3688 112.687 37.4487C112.687 40.5287 110.181 43.0256 107.09 43.0256ZM129.478 43.0256C126.387 43.0256 123.881 40.5287 123.881 37.4487C123.881 34.3688 126.387 31.8718 129.478 31.8718C132.569 31.8718 135.075 34.3688 135.075 37.4487C135.075 40.5287 132.569 43.0256 129.478 43.0256Z" fill="%231F1F20"/><path d="M37.1268 133C44.8547 133 51.1194 126.758 51.1194 119.058C51.1194 111.358 44.8547 105.115 37.1268 105.115C29.399 105.115 23.1343 111.358 23.1343 119.058C23.1343 126.758 29.399 133 37.1268 133Z" fill="%231F1F20"/><path d="M112.873 133C120.601 133 126.866 126.758 126.866 119.058C126.866 111.358 120.601 105.115 112.873 105.115C105.145 105.115 98.8806 111.358 98.8806 119.058C98.8806 126.758 105.145 133 112.873 133Z" fill="%231F1F20"/></svg>`,
                  });
                }
              });
            }
          },
        );
      }
      return arr;
    });
  }, [dashboardData]);
  console.log({ result });

  const [searchLocationCenter, setSearchLocationCenter] = useState<{
    lat: number;
    lng: number;
  } | null>(null);
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
            {/* {isLoading ? (
              <WeatherInfoSkeleton />
            ) : ( */}
            <WeatherInfoAngYang
              data={dashboardData}
              handleRefresh={onRefreshDashboardData}
              isRefreshing={isRefreshing}
              setSearchLocation={(locationValue) => {
                console.log('Location value:', { locationValue });
                setSearchLocationCenter({
                  lat: locationValue.lat,
                  lng: locationValue.lng,
                });
              }}
              setDateRange={(dateRange) => {
                console.log('Date range:', { dateRange });
                setDateRange(dateRange);
              }}
            />
            {/* )} */}
          </Panel>
        </div>
        {/* Main content */}
        <div
          style={{
            // display: 'grid',
            // gridTemplateColumns: '1fr 1fr',
            display: 'flex',
            gap: '1.5rem',
            height: `calc(100vh - 140px)`,
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
              panelStyles={{ height: '278px', flexShrink: 0 }}
            >
              {/* {isLoading ? (
                <DeliveryProgressSkeleton />
              ) : ( */}
              <DeliveryProgressV2
                panel={getPanelByTitle('Overall Delivery Service Status')}
              />
              {/* )} */}
            </Panel>
            <Panel
              shouldHaveAspectRatio={false}
              panelStyles={{
                minHeight: '150px',
                height: '100%',
                width: '100%',
              }}
            >
              {/* {isLoading ? (
                <DeliveryProgressSkeleton />
              ) : ( */}
              <OperationStatus panel={getPanelByTitle('Operation Status')} />
              {/* )} */}
            </Panel>
          </div>
          <div style={{ width: '50%' }}>
            <Map
              center={
                searchLocationCenter
                  ? searchLocationCenter
                  : result && result.length > 0
                    ? { lat: result[0].lat, lng: result[0].lng }
                    : undefined
              }
              operatingMarkers={result?.length > 0 ? result : []}
              // polylines={result?.length > 0 ? [result] : []}
              // bounds={mapBounds || undefined}
              style={{ height: `calc(100vh - 140px)` }}
              polylines={[]}
            />
          </div>
        </div>
      </Main>
    </Container>
  );
};

export default DeliveryDashboard;
