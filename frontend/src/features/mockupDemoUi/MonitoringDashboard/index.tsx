import React from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../../configs/Colors';
import Panel from '../Dashboard/components/Panel';
import DroneStatus from './components/DroneStatus';
import EmergencyStatus from './components/EmergencyStatus';
import EventLog from './components/EventLog';
import FlightSchedule from './components/FlightSchedule';
import FlightTime from './components/FlightTime';
import KoreaMap from './components/KoreaMap';

const MonitoringDashboard: React.FC = () => {
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
          }}
        >
          {t('Monitoring Dashboard')}
        </h1>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1.5fr 1.5fr',
          gridTemplateRows: '1fr 1fr',
          gap: 10,
          padding: 20,
          height: 'calc(100vh - 60px)',
        }}
      >
        {/* Drone Status Panel */}
        <div
          className="drone-status"
          style={{ gridRow: 1, gridColumn: 1 }}
        >
          <Panel
            title={t('Drone Status') + ' 🛸'}
            fullHeight
          >
            <DroneStatus />
          </Panel>
        </div>

        {/* Event Log Panel */}
        <div
          className="event-log"
          style={{ gridRow: 1, gridColumn: 2 }}
        >
          <Panel
            title={t('Event') + ' 📊'}
            fullHeight
          >
            <EventLog />
          </Panel>
        </div>

        {/* Flight Schedule Panel */}
        <div
          className="flight-schedule"
          style={{ gridRow: '1 / span 2', gridColumn: 3 }}
        >
          <Panel title={t('Flight Schedule') + ' 📅'}>
            <FlightSchedule />
          </Panel>
        </div>

        {/* Flight Time Panel */}
        <div
          className="flight-time"
          style={{ gridRow: 2, gridColumn: 1 }}
        >
          <Panel
            title={t('Flight Time') + ' ⏱️'}
            fullHeight
          >
            <FlightTime />
          </Panel>
        </div>

        {/* Emergency Status Panel */}
        <div
          className="emergency-status"
          style={{ gridRow: 2, gridColumn: 2 }}
        >
          <Panel
            title={t('Emergency Status') + ' 🔧'}
            fullHeight
          >
            <EmergencyStatus />
          </Panel>
        </div>

        {/* Korea Map Panel */}
        <div
          className="korea-map"
          style={{ gridRow: '1 / span 2', gridColumn: 4 }}
        >
          <Panel title={t('Flight Map') + ' 🗺️'}>
            <KoreaMap height={'calc(100vh - 62px - 40px - 50px - 30px)'} />
          </Panel>
        </div>
      </div>
    </div>
  );
};

export default MonitoringDashboard;
