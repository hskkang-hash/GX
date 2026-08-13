import React from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../../configs/Colors';
import Panel from '../Dashboard/components/Panel';
import DeliveryApprovals from './components/DeliveryApprovals';
import DeliveryItems from './components/DeliveryItems';
import DeliveryProgress from './components/DeliveryProgress';
import DeliveryReservations from './components/DeliveryReservations';
import DeliveryStats from './components/DeliveryStats';
import DeliveryStatus from './components/DeliveryStatus';
import DeviceStatus from './components/DeviceStatus';
import MemberApprovals from './components/MemberApprovals';
import OperationLogs from './components/OperationLogs';
import WeatherInfo from './components/WeatherInfo';

const DeliveryDashboard: React.FC = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  return (
    <div
      style={{
        fontFamily: 'Inter, sans-serif',
        background: theme === 'dark' ? Colors.Black : '#f5f5f5',
        minHeight: '100vh',
        color: theme === 'dark' ? Colors.Gray3 : '#333',
      }}
    >
      <div
        className="header"
        style={{
          padding: '15px 20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: `1px solid ${theme === 'dark' ? Colors.Gray7 : '#e0e0e0'}`,
          background: theme === 'dark' ? Colors.Black : '#fff',
        }}
      >
        <h1
          style={{
            margin: 0,
            fontWeight: 'bold',
            fontSize: 24,
            color: theme === 'dark' ? Colors.Gray3 : '#333',
            flex: '1',
          }}
        >
          {t('Delivery Dashboard')}
        </h1>
        <WeatherInfo />
      </div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 20,
          padding: 20,
        }}
      >
        {/* Delivery Status Panel */}
        <div className="delivery-status">
          <Panel
            title={t('Delivery Status')}
            fullHeight
          >
            <DeliveryStatus />
          </Panel>
        </div>

        {/* Delivery Reservations Panel */}
        <div className="delivery-reservations">
          <Panel
            title={t('Delivery Reservations')}
            fullHeight
          >
            <DeliveryReservations />
          </Panel>
        </div>

        {/* Delivery Progress Panel */}
        <div className="delivery-progress">
          <Panel
            title={t('Delivery Progress')}
            fullHeight
          >
            <DeliveryProgress />
          </Panel>
        </div>

        {/* Delivery Approvals Panel */}
        <div className="delivery-approvals">
          <Panel
            title={t('Delivery Approvals')}
            fullHeight
          >
            <DeliveryApprovals />
          </Panel>
        </div>

        {/* Delivery Stats Panel */}
        <div className="delivery-stats">
          <Panel
            title={t('Delivery Statistics')}
            fullHeight
          >
            <DeliveryStats />
          </Panel>
        </div>

        {/* Delivery Items Panel */}
        <div className="delivery-items">
          <Panel
            title={t('Delivery Items')}
            fullHeight
          >
            <DeliveryItems />
          </Panel>
        </div>

        {/* Operation Logs Panel */}
        <div className="operation-logs">
          <Panel
            title={t('Operation Logs')}
            fullHeight
          >
            <OperationLogs />
          </Panel>
        </div>

        {/* Member Approvals Panel */}
        <div className="member-approvals">
          <Panel
            title={t('Member Approvals')}
            fullHeight
          >
            <MemberApprovals />
          </Panel>
        </div>

        {/* Device Status Panel */}
        <div className="device-status">
          <Panel
            title={t('Drone/Robot Algebra')}
            fullHeight
          >
            <DeviceStatus />
          </Panel>
        </div>

        {/* Device Status Panel */}
        <div className="device-status">
          <Panel
            title={t('Control drone/robot status')}
            fullHeight
          >
            <DeviceStatus />
          </Panel>
        </div>
      </div>
    </div>
  );
};

export default DeliveryDashboard;
