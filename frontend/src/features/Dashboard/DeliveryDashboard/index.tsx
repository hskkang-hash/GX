import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FaSync } from 'react-icons/fa';
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
import Cancellation from './components/Cancellation';
import ChartSkeleton from './components/ChartSkeleton';
import DeliveryItems from './components/DeliveryItems';
import DeliveryProgress from './components/DeliveryProgress';
import DeliveryProgressSkeleton from './components/DeliveryProgressSkeleton';
import DeliveryStats from './components/DeliveryStats';
import InTransitVsCompletion from './components/InTransitVsCompletion';
import InfoCardSkeleton from './components/InfoCardSkeleton';
import OrderStatsByWeight from './components/OrderStatsByWeight';
import ReceivedVsPendingShipment from './components/ReceivedVsPendingShipment';
import RegionalOrderStats from './components/RegionalOrderStats';
import WeatherInfo from './components/WeatherInfo';
import WeatherInfoSkeleton from './components/WeatherInfoSkeleton';

interface WeatherData extends DashboardData {
  temperature?: number;
  humidity?: number;
  wind_speed?: number;
  region?: string;
}

const DeliveryDashboard: React.FC = () => {
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
  console.log('spaceTableHeight', spaceTableHeight);

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
            // height: `${spaceTableHeight}px`,
            color: theme === 'dark' ? Colors.Gray3 : '#333',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
            paddingBottom: '1rem',
          }}
        >
          {/* Main Content Area */}
          {/* Row 1 */}
          <div style={{ display: 'flex', gap: '1rem', flex: 1 }}>
            {/* Left Column (1/4) */}
            <div style={{ flex: 1 }}>
              <Panel fullHeight>
                {isLoading ? (
                  <DeliveryProgressSkeleton />
                ) : (
                  <DeliveryProgress
                    panel={getPanelByTitle('Delivery Progress')}
                  />
                )}
              </Panel>
            </div>
            {/* Right Column (3/4) */}
            <div
              style={{
                flex: 3,
                display: 'flex',
                flexDirection: 'column',
                gap: '1rem',
              }}
            >
              <div>
                <Panel
                  fullHeight
                  contentStyles={{
                    paddingTop: '0.375rem',
                    paddingBottom: '0.375rem',
                  }}
                >
                  {isLoading ? (
                    <WeatherInfoSkeleton />
                  ) : (
                    <WeatherInfo
                      data={dashboardData}
                      handleRefresh={onRefreshDashboardData}
                      isRefreshing={isRefreshing}
                    />
                  )}
                </Panel>
              </div>
              <div style={{ display: 'flex', gap: '1rem', height: '100%' }}>
                <Panel
                  fullHeight
                  panelStyles={{ flex: 1 }}
                >
                  {isLoading ? (
                    <InfoCardSkeleton />
                  ) : (
                    <ReceivedVsPendingShipment
                      panel={getPanelByTitle(
                        'Receipt Completed vs Waiting for Delivery',
                      )}
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
                    <InTransitVsCompletion
                      panel={getPanelByTitle(
                        'In Delivery vs Delivery Completed',
                      )}
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
                    <Cancellation panel={getPanelByTitle('Cancellation')} />
                  )}
                </Panel>
              </div>
            </div>
          </div>
          <div
            style={{
              display: 'flex',
              gap: '1rem',
              flex: 1,
            }}
          >
            {/* Row 2 */}
            <div style={{ flex: 1 }}>
              <Panel
                fullHeight
                panelStyles={{ maxHeight: 'calc(59vh - 1.5rem)' }}
              >
                {isLoading ? (
                  <ChartSkeleton />
                ) : (
                  <DeliveryStats
                    panel={getPanelByTitle('Monthly Delivery Stats')}
                  />
                )}
              </Panel>
            </div>
            <div style={{ flex: 1 }}>
              <Panel
                fullHeight
                panelStyles={{
                  maxHeight: 'calc(59vh - 1.5rem)',
                }}
              >
                {isLoading ? (
                  <ChartSkeleton />
                ) : (
                  <DeliveryItems
                    panel={getPanelByTitle('Order Stats by Item Type')}
                    panelStyles={{
                      paddingTop: '1rem',
                      maxHeight:
                        'calc(59vh - 1.5rem - 64px - 1.25rem - 1.25rem - 2.5rem)',
                      overflowY: 'scroll',
                      paddingBottom: '1rem',
                    }}
                  />
                )}
              </Panel>
            </div>
            <div style={{ flex: 1 }}>
              <Panel
                fullHeight
                panelStyles={{
                  maxHeight: 'calc(59vh - 1.5rem)',
                }}
              >
                {isLoading ? (
                  <InfoCardSkeleton />
                ) : (
                  <RegionalOrderStats
                    panel={getPanelByTitle('Regional Order Stats')}
                    panelStyles={{
                      maxHeight:
                        'calc(59vh - 1.5rem - 64px - 1.25rem - 1.25rem - 3rem)',
                      overflowY: 'scroll',
                      paddingBottom: '1rem',
                    }}
                  />
                )}
              </Panel>
            </div>
            <div style={{ flex: 1 }}>
              <Panel
                fullHeight
                panelStyles={{ maxHeight: 'calc(59vh - 1.5rem)' }}
              >
                {isLoading ? (
                  <ChartSkeleton />
                ) : (
                  <OrderStatsByWeight
                    panel={getPanelByTitle('Order Stats by Weight')}
                  />
                )}
              </Panel>
            </div>
          </div>
        </div>
      </Main>
    </Container>
  );
};

export default DeliveryDashboard;
