import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Container,
  HeaderWithBtn,
  Main,
  useCalculateHeight,
  useTheme,
} from 'rj-core';

import Colors from '@/configs/Colors';
import { remToPx } from '@/utils/utils';

import Panel from '../components/Panel';
import useDashboard from '../hooks/useDashboard';
import { DashboardData, Panel as PanelType } from '../types/IDashboard';
import ChartSkeleton from './componentsV2/ChartSkeleton';
import DeliveryItemSkeleton from './componentsV2/DeliveryItemSkeleton';
import DeliveryItems from './componentsV2/DeliveryItems';
import DeliveryProgress from './componentsV2/DeliveryProgress';
import DeliveryProgressSkeleton from './componentsV2/DeliveryProgressSkeleton';
import DeliveryStats from './componentsV2/DeliveryStats';
import DeviceItems from './componentsV2/DeviceItems';
import DeviceSkeleton from './componentsV2/DeviceSkeleton';
import InfoCardSkeleton from './componentsV2/InfoCardSkeleton';
import LogDataCollection from './componentsV2/LogDataCollection';
import LogDataSkeleton from './componentsV2/LogDataSkeleton';
import PendingSignUps from './componentsV2/PendingSignUps';
import PendingSignUpsSkeleton from './componentsV2/PendingSignUpsSkeleton';
import StatusCard from './componentsV2/StatusCard';
import WeatherInfo from './componentsV2/WeatherInfo';

interface WeatherData extends DashboardData {
  temperature?: number;
  humidity?: number;
  wind_speed?: number;
  region?: string;
}

const DeliveryDashboard: React.FC = () => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const headerPageRef = useRef(null);
  const { getDashboardData, refreshDashboardData } = useDashboard();

  const [dashboardData, setDashboardData] = useState<WeatherData | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(10)],
  });

  const fetchDashboardData = async () => {
    setIsLoading(true);
    try {
      const { success, data } = await getDashboardData();
      if (success) {
        setDashboardData(data);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const onRefreshDashboardData = async () => {
    setIsRefreshing(true);
    try {
      const { success, data } = await refreshDashboardData();
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

  const getPanelByTitle = (title: string): PanelType | undefined => {
    return dashboardData?.panels.find((p) => p.panel_title === title);
  };
  return (
    <Container>
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[]}
      />
      <Main>
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
              paddingTop: '0.5rem',
              paddingBottom: '0.5rem',
            }}
          >
            {/* {isLoading ? (
              <WeatherInfoSkeleton />
            ) : ( */}
            <WeatherInfo
              data={dashboardData}
              handleRefresh={onRefreshDashboardData}
              isRefreshing={isRefreshing}
            />
            {/* )} */}
          </Panel>
        </div>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: '1.5rem',
            height: '100%',
            width: '100%',
          }}
        >
          <Panel fullHeight>
            {isLoading ? (
              <DeliveryProgressSkeleton />
            ) : (
              <DeliveryProgress
                panel={getPanelByTitle('Last Mile Delivery Progress')}
              />
            )}
          </Panel>
          <Panel
            fullHeight
            panelStyles={{ flex: 1 }}
          >
            {isLoading ? (
              <InfoCardSkeleton />
            ) : (
              <StatusCard panel={getPanelByTitle('Delivery Booking Status')} />
            )}
          </Panel>
          <Panel
            fullHeight
            panelStyles={{ flex: 1 }}
          >
            {isLoading ? (
              <InfoCardSkeleton />
            ) : (
              <StatusCard panel={getPanelByTitle('Delivery Approval')} />
            )}
          </Panel>
          <Panel
            fullHeight
            panelStyles={{ flex: 1 }}
          >
            {isLoading ? (
              <InfoCardSkeleton />
            ) : (
              <StatusCard panel={getPanelByTitle('Delivery Status')} />
            )}
          </Panel>
          <Panel fullHeight>
            {isLoading ? (
              <ChartSkeleton />
            ) : (
              <DeliveryStats
                panel={getPanelByTitle('Monthly Delivery Statistics')}
              />
            )}
          </Panel>
          <Panel
            fullHeight
            panelStyles={{}}
          >
            {isLoading ? (
              <DeliveryItemSkeleton />
            ) : (
              <DeliveryItems
                panel={getPanelByTitle('Delivered Items')}
                panelStyles={{
                  paddingTop: '1.25rem',
                  maxHeight: 'clamp(14rem, 40vh, 18rem)',
                  overflowY: 'scroll',
                  paddingBottom: '1rem',
                }}
              />
            )}
          </Panel>
          <Panel
            fullHeight
            panelStyles={{ flex: 1 }}
          >
            {isLoading ? (
              <DeviceSkeleton />
            ) : (
              <DeviceItems panel={getPanelByTitle('Number of Drones/Robots')} />
            )}
          </Panel>
          <Panel
            fullHeight
            panelStyles={{ flex: 1 }}
          >
            {isLoading ? (
              <DeviceSkeleton />
            ) : (
              <DeviceItems
                panel={getPanelByTitle('Last Mile Infrastructure Status')}
              />
            )}
          </Panel>
          <Panel
            fullHeight
            panelStyles={{ flex: 1 }}
          >
            {isLoading ? (
              <DeviceSkeleton />
            ) : (
              <DeviceItems
                panel={getPanelByTitle('Controlled Drones/Robots')}
              />
            )}
          </Panel>
          <Panel
            fullHeight
            panelStyles={{ flex: 1 }}
          >
            {isLoading ? (
              <DeviceSkeleton />
            ) : (
              <DeviceItems
                panel={getPanelByTitle('Uncontrolled Drones/Robots')}
              />
            )}
          </Panel>
          <Panel
            fullHeight
            panelStyles={{ flex: 1 }}
          >
            {isLoading ? (
              <LogDataSkeleton />
            ) : (
              <LogDataCollection
                lableEtri={t('Go to Drones/Robots and Infrastructure')}
                panel={getPanelByTitle('Log Data Collection')}
              />
            )}
          </Panel>
          <Panel
            fullHeight
            panelStyles={{ flex: 1 }}
          >
            {isLoading ? (
              <PendingSignUpsSkeleton />
            ) : (
              <PendingSignUps
                lableEtri={t('Go to User Management')}
                panel={getPanelByTitle('Pending Sign-ups')}
              />
            )}
          </Panel>
        </div>
      </Main>
    </Container>
  );
};

export default DeliveryDashboard;
