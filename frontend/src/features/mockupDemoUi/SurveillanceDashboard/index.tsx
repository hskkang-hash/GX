import React from 'react';
import { useTranslation } from 'react-i18next';
import {
  FaRoute,
  FaExclamationTriangle,
  FaBatteryThreeQuarters,
  FaExclamationCircle,
  FaArrowUp,
  FaArrowDown,
} from 'react-icons/fa';
import { TbDrone } from 'react-icons/tb';
import { useTheme } from 'rj-core';

import { Map } from '@/components/maps';

import Colors from '../../../configs/Colors';
import Panel from '../Dashboard/components/Panel';

const getRandomInt = (min: number, max: number) =>
  Math.floor(Math.random() * (max - min + 1)) + min;

const SurveillanceDashboard: React.FC = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  // Random data
  const operatingDrones = getRandomInt(8, 15);
  const operatingRate = getRandomInt(70, 90);
  const todayDistance = getRandomInt(200, 300);
  const yesterdayDistance = getRandomInt(150, 250);
  const distanceChange = Number(
    (((todayDistance - yesterdayDistance) / yesterdayDistance) * 100).toFixed(
      1,
    ),
  );
  const totalDetections = getRandomInt(15, 25);
  const completedDetections = getRandomInt(10, totalDetections);
  const pendingDetections = totalDetections - completedDetections;
  const goodBatteries = getRandomInt(5, 10);
  const chargingBatteries = getRandomInt(2, 5);
  const lowBatteries = getRandomInt(1, 3);

  // Map data
  const operatingLocations = [
    [37.5665, 126.978],
    [37.533, 127.021],
    [37.588, 127.006],
    [37.527, 126.923],
    [37.607, 126.933],
    [37.549, 127.075],
    [37.579, 126.977],
    [37.512, 126.94],
  ];
  const standbyLocations = [
    [37.556, 126.865],
    [37.654, 127.047],
    [37.496, 127.127],
    [37.466, 126.9],
  ];

  // Surveillance paths
  const surveillancePaths = [
    // Path 1
    [
      [37.5665, 126.978],
      [37.533, 127.021],
      [37.588, 127.006],
      [37.527, 126.923],
    ],
    // Path 2
    [
      [37.607, 126.933],
      [37.549, 127.075],
      [37.579, 126.977],
      [37.512, 126.94],
    ],
    // Path 3
    [
      [37.556, 126.865],
      [37.654, 127.047],
      [37.496, 127.127],
      [37.466, 126.9],
    ],
  ];

  // Calculate bounds to fit all markers and paths
  const allPoints = [
    ...operatingLocations,
    ...standbyLocations,
    ...surveillancePaths.flat(),
  ];

  const bounds = {
    sw: {
      lat: Math.min(...allPoints.map((p) => p[0])) - 0.01,
      lng: Math.min(...allPoints.map((p) => p[1])) - 0.01,
    },
    ne: {
      lat: Math.max(...allPoints.map((p) => p[0])) + 0.01,
      lng: Math.max(...allPoints.map((p) => p[1])) + 0.01,
    },
  };

  // Alerts
  const alerts = [
    { msg: 'Zone A-7 Intruder Detection', time: `10 ${t('minutes ago')}` },
    { msg: 'Drone #5 Low Battery Warning', time: `15 ${t('minutes ago')}` },
    { msg: 'Activity detected above Zone C-3', time: `25 ${t('minutes ago')}` },
    {
      msg: 'Zone B-2 Suspicious movement detected',
      time: `30 ${t('minutes ago')}`,
    },
    {
      msg: 'Drone #3 Communication connection unstable',
      time: `45 ${t('minutes ago')}`,
    },
  ];

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
          justifyContent: 'flex-start',
          alignItems: 'center',
          borderBottom: `1px solid ${theme === 'dark' ? Colors.Gray7 : '#e0e0e0'}`,
          background: theme === 'dark' ? Colors.Black : '#fff',
        }}
      >
        <h1
          style={{
            fontSize: 24,
            fontWeight: 'bold',
            color: theme === 'dark' ? Colors.Gray3 : '#333',
          }}
        >
          {t('Drone Reconnaissance Dashboard')}
        </h1>
      </div>
      <div
        className="dashboard"
        style={{
          padding: 20,
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 20,
        }}
      >
        {/* 실시간 운영 현황 */}
        <Panel fullHeight>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 20,
            }}
          >
            <div
              style={{
                fontSize: 16,
                color: theme === 'dark' ? Colors.Gray3 : '#333',
              }}
            >
              {t('Real-time operating status')}
            </div>
            <div
              style={{
                width: 40,
                height: 40,
                background: '#1D9BE2',
                borderRadius: 10,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
              }}
            >
              <TbDrone size={24} />
            </div>
          </div>
          <div
            className="stat-value"
            style={{ fontSize: 32, fontWeight: 'bold', margin: '10px 0' }}
          >
            {operatingDrones}
            <span style={{ fontSize: 18 }}> {t('drones')}</span>
          </div>
          <div
            className="stat-label"
            style={{ fontSize: 14, color: '#666' }}
          >
            {t('Drones in operation')}
          </div>
          <div
            className="progress-container"
            style={{ marginTop: 10 }}
          >
            <div
              className="progress-bar"
              style={{ height: 6, background: '#e0e0e0', borderRadius: 3 }}
            >
              <div
                className="progress-fill"
                style={{
                  height: '100%',
                  background: '#1D9BE2',
                  borderRadius: 3,
                  width: `${operatingRate}%`,
                  transition: 'width 0.3s',
                }}
              />
            </div>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginTop: 5,
              }}
            >
              <span style={{ fontSize: 12, color: '#999' }}>
                {t('Operating rate')}
              </span>
              <span style={{ fontSize: 12, color: '#1D9BE2' }}>
                {operatingRate}%
              </span>
            </div>
          </div>
        </Panel>

        <Panel fullHeight>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 20,
            }}
          >
            <div
              style={{
                fontSize: 16,
                color: theme === 'dark' ? Colors.Gray3 : '#333',
              }}
            >
              {t("Today's reconnaissance results")}
            </div>
            <div
              style={{
                width: 40,
                height: 40,
                background: '#1D9BE2',
                borderRadius: 10,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
              }}
            >
              <FaRoute size={20} />
            </div>
          </div>
          <div
            className="stat-value"
            style={{ fontSize: 32, fontWeight: 'bold', margin: '10px 0' }}
          >
            {todayDistance}
            <span style={{ fontSize: 18 }}> km</span>
          </div>
          <div
            className="stat-label"
            style={{ fontSize: 14, color: '#666' }}
          >
            {t('Total reconnaissance range')}
          </div>
          <div
            className={distanceChange > 0 ? 'trend-up' : 'trend-down'}
            style={{
              color: distanceChange > 0 ? '#2ecc71' : '#e74c3c',
              marginTop: 8,
            }}
          >
            {distanceChange > 0 ? <FaArrowUp /> : <FaArrowDown />}{' '}
            {t('Compared to the previous day')} {Math.abs(distanceChange)}%{' '}
            {distanceChange > 0 ? t('increase') : t('decrease')}
          </div>
        </Panel>

        <Panel fullHeight>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 20,
            }}
          >
            <div
              style={{
                fontSize: 16,
                color: theme === 'dark' ? Colors.Gray3 : '#333',
              }}
            >
              {t('Detecting abnormal signs')}
            </div>
            <div
              style={{
                width: 40,
                height: 40,
                background: '#1D9BE2',
                borderRadius: 10,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
              }}
            >
              <FaExclamationTriangle size={20} />
            </div>
          </div>
          <div
            className="stat-value"
            style={{ fontSize: 32, fontWeight: 'bold', margin: '10px 0' }}
          >
            {totalDetections}
            <span style={{ fontSize: 18 }}> {t('cases')}</span>
          </div>
          <div
            className="stat-label"
            style={{
              fontSize: 14,
              color: theme === 'dark' ? Colors.Gray5 : '#666',
            }}
          >
            {t('Number of cases detected today')}
          </div>
          <div
            className="status-grid"
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 10,
              marginTop: 10,
            }}
          >
            <div
              className="status-item"
              style={{
                background: theme === 'dark' ? '#232325' : '#f8f8f8',
                padding: 15,
                borderRadius: 8,
                textAlign: 'center',
                border: `1px solid ${theme === 'dark' ? '#232325' : '#e0e0e0'}`,
              }}
            >
              <div
                style={{ fontSize: 20, fontWeight: 'bold', color: '#2ecc71' }}
              >
                {completedDetections}
              </div>
              <div
                style={{
                  fontSize: 12,
                  color: theme === 'dark' ? Colors.Gray5 : '#999',
                }}
              >
                {t('Processing complete')}
              </div>
            </div>
            <div
              className="status-item"
              style={{
                background: theme === 'dark' ? '#232325' : '#f8f8f8',
                padding: 15,
                borderRadius: 8,
                textAlign: 'center',
                border: `1px solid ${theme === 'dark' ? '#232325' : '#e0e0e0'}`,
              }}
            >
              <div
                style={{ fontSize: 20, fontWeight: 'bold', color: '#e74c3c' }}
              >
                {pendingDetections}
              </div>
              <div
                style={{
                  fontSize: 12,
                  color: theme === 'dark' ? Colors.Gray5 : '#999',
                }}
              >
                {t('Processing')}
              </div>
            </div>
          </div>
        </Panel>

        <Panel fullHeight>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 20,
            }}
          >
            <div
              style={{
                fontSize: 16,
                color: theme === 'dark' ? Colors.Gray3 : '#333',
              }}
            >
              {t('Real-time operating status')}
            </div>
            <div
              style={{
                width: 40,
                height: 40,
                background: '#1D9BE2',
                borderRadius: 10,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
              }}
            >
              <FaBatteryThreeQuarters size={20} />
            </div>
          </div>
          <div
            className="drone-stats"
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 10,
              marginTop: 10,
            }}
          >
            <div
              className="drone-stat"
              style={{
                textAlign: 'center',
                padding: 10,
                background: theme === 'dark' ? '#232325' : '#f8f8f8',
                borderRadius: 5,
                border: `1px solid ${theme === 'dark' ? '#232325' : '#e0e0e0'}`,
              }}
            >
              <div style={{ fontSize: 24, fontWeight: 'bold' }}>
                {goodBatteries}
              </div>
              <div
                style={{
                  fontSize: 12,
                  color: theme === 'dark' ? Colors.Gray5 : '#999',
                }}
              >
                {t('Good')}
              </div>
            </div>
            <div
              className="drone-stat"
              style={{
                textAlign: 'center',
                padding: 10,
                background: theme === 'dark' ? '#232325' : '#f8f8f8',
                borderRadius: 5,
                border: `1px solid ${theme === 'dark' ? '#232325' : '#e0e0e0'}`,
              }}
            >
              <div style={{ fontSize: 24, fontWeight: 'bold' }}>
                {chargingBatteries}
              </div>
              <div
                style={{
                  fontSize: 12,
                  color: theme === 'dark' ? Colors.Gray5 : '#999',
                }}
              >
                {t('Charging')}
              </div>
            </div>
            <div
              className="drone-stat"
              style={{
                textAlign: 'center',
                padding: 10,
                background: theme === 'dark' ? '#232325' : '#f8f8f8',
                borderRadius: 5,
                border: `1px solid ${theme === 'dark' ? '#232325' : '#e0e0e0'}`,
              }}
            >
              <div
                style={{ fontSize: 24, fontWeight: 'bold', color: '#e74c3c' }}
              >
                {lowBatteries}
              </div>
              <div
                style={{
                  fontSize: 12,
                  color: theme === 'dark' ? Colors.Gray5 : '#999',
                }}
              >
                {t('Need to replace')}
              </div>
            </div>
          </div>
        </Panel>

        {/* (Map) */}
        <div style={{ gridColumn: '1 / span 2' }}>
          <Panel title={t('Reconnaissance Area Status')}>
            <Map
              center={{ lat: 37.5665, lng: 126.978 }}
              operatingMarkers={operatingLocations.map((loc) => ({
                lat: loc[0],
                lng: loc[1],
              }))}
              standbyMarkers={standbyLocations.map((loc) => ({
                lat: loc[0],
                lng: loc[1],
              }))}
              // polylines={surveillancePaths.map((path) =>
              //   path.map((point) => ({
              //     lat: point[0],
              //     lng: point[1],
              //   }))
              // )}
              bounds={bounds}
              smallMarker={true}
              overlayContent={
                <>
                  <div style={{ marginBottom: 10 }}>
                    <span style={{ color: '#1D9BE2' }}>●</span> 운영 중 (
                    {operatingLocations.length})
                  </div>
                  <div>
                    <span style={{ color: '#e74c3c' }}>●</span> 대기 중 (
                    {standbyLocations.length})
                  </div>
                </>
              }
            />
          </Panel>
        </div>

        <div style={{ gridColumn: '3 / span 2' }}>
          <Panel title={t('Real-time notifications')}>
            <div className="alert-list">
              {alerts.map((alert, idx) => (
                <div
                  className="alert-item"
                  key={idx}
                  style={{
                    padding: 10,
                    background: theme === 'dark' ? '#232325' : '#f8f8f8',
                    borderRadius: 5,
                    marginBottom: 10,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    border: `1px solid ${theme === 'dark' ? '#232325' : '#e0e0e0'}`,
                    fontSize: '1.125rem',
                  }}
                >
                  <div
                    className="alert-icon"
                    style={{ color: '#e74c3c' }}
                  >
                    <FaExclamationCircle size={24} />
                  </div>
                  <div
                    className="alert-info"
                    style={{ flex: 1 }}
                  >
                    <div>{t(alert.msg)}</div>
                    <div
                      className="alert-time"
                      style={{ color: '#666', fontSize: 12 }}
                    >
                      {alert.time}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
};

export default SurveillanceDashboard;
