import { Box } from '@mui/material';
import { Chart, registerables } from 'chart.js';
import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  FaChartLine,
  FaRoute,
  FaShippingFast,
  FaTasks,
  FaTools,
} from 'react-icons/fa';
import { useTheme } from 'rj-core';

import Colors from '@/configs/Colors';

import Map from './components/Map';
import MissionChart from './components/MissionChart';
import Panel from './components/Panel';
import StatBox from './components/StatBox';
import TaskDistribution from './components/TaskDistribution';

// Đăng ký chart.js
Chart.register(...registerables);

const cities = [
  { name: '천안시', coords: [36.8151, 127.1139] as [number, number] },
  { name: '공주시', coords: [36.4465, 127.1186] as [number, number] },
  { name: '보령시', coords: [36.3333, 126.6167] as [number, number] },
  { name: '아산시', coords: [36.7847, 127.0] as [number, number] },
  { name: '서산시', coords: [36.7817, 126.4522] as [number, number] },
  { name: '논산시', coords: [36.1877, 127.0987] as [number, number] },
  { name: '계룡시', coords: [36.2747, 127.2489] as [number, number] },
  { name: '당진시', coords: [36.8937, 126.6284] as [number, number] },
];

function getRandomInt(min: number, max: number) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function generateRandomData(length: number, min: number, max: number) {
  return Array.from({ length }, () => getRandomInt(min, max));
}

function generateRandomPercentages() {
  const total = 100;
  const delivery = getRandomInt(30, 70);
  const surveillance = getRandomInt(0, 30);
  const other = total - delivery - surveillance;
  return [delivery, surveillance, other];
}

const DashboardPage: React.FC = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  // Random data
  const totalDrones = getRandomInt(15, 25);
  const operatingDrones = getRandomInt(5, totalDrones - 5);
  const standbyDrones = totalDrones - operatingDrones;
  const totalMissions = getRandomInt(40, 60);
  const totalDistance = getRandomInt(60, 90);
  const totalDeliveries = getRandomInt(30, 50);
  const totalRevenue = getRandomInt(100, 200);
  const totalTerminals = getRandomInt(3, 6);
  const totalDeliveryPoints = getRandomInt(12, 20);

  const missionData = {
    missionCount: generateRandomData(12, 0, 30),
    distance: generateRandomData(12, 0, 25),
  };
  const taskDistribution = generateRandomPercentages();

  // Map markers
  const operatingMarkers = Array.from({ length: getRandomInt(1, 3) }, () => {
    const city = cities[getRandomInt(0, cities.length - 1)];
    return { ...city, type: 'operating' as const };
  });
  const standbyMarkers = Array.from({ length: getRandomInt(1, 3) }, () => {
    const city = cities[getRandomInt(0, cities.length - 1)];
    return { ...city, type: 'standby' as const };
  });

  // Status values
  const statusValues = Array.from({ length: 4 }, () => getRandomInt(0, 5));

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
          {t('Dashboard')}
        </h1>
      </div>

      <div
        className="dashboard"
        style={{ padding: 20 }}
      >
        {/* Stats */}
        <div
          className="stats-container"
          style={{ display: 'flex', gap: 10, marginBottom: 20 }}
        >
          <StatBox
            icon={FaTools}
            title={t('Total Drones')}
            value={
              <Box
                display="flex"
                gap={1}
              >
                <div>
                  {totalDrones}
                  <div
                    style={{
                      fontWeight: '400',
                      fontSize: 14,
                      color: theme === 'dark' ? Colors.Gray3 : '#666',
                    }}
                  >
                    {t('Operating')}
                  </div>
                </div>
                <div>
                  {standbyDrones}
                  <div
                    style={{
                      fontWeight: '400',
                      fontSize: 14,
                      color: theme === 'dark' ? Colors.Gray3 : '#666',
                    }}
                  >
                    {t('Standby')}
                  </div>
                </div>
              </Box>
              // <>
              //   {totalDrones}{" "}
              //   <span style={{ color: "#4169e1" }}>{standbyDrones}</span>
              // </>
            }
          />
          <StatBox
            icon={FaTasks}
            title={t('Total Missions')}
            value={
              <Box>
                {totalMissions}
                <span style={{ fontSize: 16 }}> {t('count')}</span>
              </Box>
            }
          />
          <StatBox
            icon={FaRoute}
            title={t('Total Distance')}
            value={
              <Box>
                {totalDistance}
                <span style={{ fontSize: 16 }}> {t('km')}</span>
              </Box>
            }
          />
          <StatBox
            icon={FaChartLine}
            title={t('Total Deliveries')}
            value={
              <Box
                display="flex"
                gap={1}
              >
                <Box>
                  {totalDeliveries}
                  <span style={{ fontSize: 16 }}> {t('orders')}</span>
                </Box>
                <Box>
                  {totalRevenue}
                  <span style={{ fontSize: 16 }}> {t('KRW')}</span>
                </Box>
              </Box>
            }
          />
          <StatBox
            icon={FaShippingFast}
            title={t('Total Terminals')}
            value={
              <Box
                display="flex"
                gap={1}
              >
                <div>
                  {totalTerminals}
                  <div
                    style={{
                      fontWeight: '400',
                      fontSize: 14,
                      color: theme === 'dark' ? Colors.Gray3 : '#666',
                    }}
                  >
                    {t('Terminal')}
                  </div>
                </div>
                <div>
                  {totalDeliveryPoints}
                  <div
                    style={{
                      fontWeight: '400',
                      fontSize: 14,
                      color: theme === 'dark' ? Colors.Gray3 : '#666',
                    }}
                  >
                    {t('Delivery Point')}
                  </div>
                </div>
              </Box>
            }
          />
        </div>

        {/* Main content */}
        <div
          className="content-container"
          style={{ display: 'flex', gap: 20 }}
        >
          {/* Left */}
          <div
            className="left-section"
            style={{ width: '33%' }}
          >
            <Panel title={t('Mission Status')}>
              <MissionChart missionData={missionData} />
            </Panel>
            <Panel title={t('Task Distribution')}>
              <TaskDistribution taskDistribution={taskDistribution} />
            </Panel>
          </div>
          {/* Center */}
          <div
            className="center-section"
            style={{ width: '33%' }}
          >
            <Panel title={t('Chungcheongnam-do')}>
              <Map
                cities={cities}
                operatingMarkers={operatingMarkers}
                standbyMarkers={standbyMarkers}
              />
            </Panel>
          </div>
          {/* Right */}
          <div
            className="right-section"
            style={{ width: '33%' }}
          >
            <Panel title={t('Task Distribution')}>
              <TaskDistribution taskDistribution={taskDistribution} />
            </Panel>
            <Panel title={t('Fault Status')}>
              <div
                className="status-grid"
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: 10,
                }}
              >
                {[t('Drone'), t('Station'), t('GCS'), t('Server')].map(
                  (label, idx) => (
                    <div
                      className="status-box"
                      key={label}
                      style={{
                        background: theme === 'dark' ? Colors.Black : '#f8f8f8',
                        border: `1px solid ${theme === 'dark' ? Colors.Gray7 : '#e0e0e0'}`,
                        padding: 15,
                        textAlign: 'center',
                      }}
                    >
                      <div
                        className="status-label"
                        style={{
                          fontSize: 14,
                          marginBottom: 10,
                          color: theme === 'dark' ? Colors.Gray3 : '#666',
                        }}
                      >
                        {label}
                      </div>
                      <div
                        className="status-value"
                        style={{
                          fontSize: 28,
                          fontWeight: 'bold',
                          color: theme === 'dark' ? Colors.Gray3 : '#333',
                        }}
                      >
                        {statusValues[idx]}
                      </div>
                    </div>
                  ),
                )}
              </div>
            </Panel>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
