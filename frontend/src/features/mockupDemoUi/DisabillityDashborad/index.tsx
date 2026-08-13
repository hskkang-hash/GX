import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import CustomSelectControlled from '@/components/selects/CustomSelectControlled';
import Colors from '@/configs/Colors';

import Panel from '../Dashboard/components/Panel';
import AltitudePanel from './components/AltitudePanel';
import AttitudePanel from './components/AttitudePanel';
import BatteryBar from './components/BatteryBar';
import DroneStatusTable from './components/DroneStatusTable';
import SensorAxisGrid from './components/SensorAxisGrid';
import SensorChartPanel from './components/SensorChartPanel';
import SensorStatusTable from './components/SensorStatusTable';

const droneOptions = [
  { value: '', label: 'Drone Selection' },
  { value: 'drone1', label: 'X05-1' },
  { value: 'drone2', label: 'X05-2' },
  { value: 'drone3', label: 'X05-3' },
  { value: 'drone4', label: 'X05-4' },
  { value: 'drone5', label: 'X05-5' },
];

const getRandomInt = (min: number, max: number) =>
  Math.floor(Math.random() * (max - min + 1)) + min;
const getRandomFloat = (min: number, max: number, decimals = 2) =>
  (Math.random() * (max - min) + min).toFixed(decimals);

const DisabillityDashborad: React.FC = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();
  const [selectedDrone, setSelectedDrone] = useState('');

  // Random data
  const statusCounts = {
    normal: getRandomInt(5, 8),
    warning: getRandomInt(2, 4),
    danger: getRandomInt(1, 3),
  };
  const sensorData = {
    roll: getRandomFloat(-2, 2),
    pitch: getRandomFloat(-1, 1),
    yaw: getRandomFloat(178, 182),
    gyroX: getRandomFloat(0, 0.02),
    gyroY: getRandomFloat(0.01, 0.03),
    gyroZ: getRandomFloat(0, 0.01),
    accelX: getRandomFloat(0.05, 0.12),
    accelY: getRandomFloat(0.03, 0.09),
    accelZ: getRandomFloat(9.78, 9.82),
    magX: getRandomFloat(22.8, 24.2),
    magY: getRandomFloat(44.5, 45.8),
    magZ: getRandomFloat(12.2, 13.4),
    vibX: getRandomFloat(0.01, 0.03),
    vibY: getRandomFloat(0.01, 0.02),
    vibZ: getRandomFloat(0.02, 0.04),
  };
  const altitude = getRandomInt(100, 150);
  const batteryLevel = getRandomInt(60, 90);

  return (
    <div
      style={{
        fontFamily: 'Inter, sans-serif',
        background: theme === 'dark' ? Colors.Black : '#f5f5f5',
        minHeight: '100vh',
        color: theme === 'dark' ? Colors.Gray3 : '#333',
      }}
    >
      {/* Header */}
      <div
        className="header"
        style={{
          padding: '15px 20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: `1px solid ${theme === 'dark' ? '#444' : '#e0e0e0'}`,
          background: theme === 'dark' ? Colors.Black : '#fff',
        }}
      >
        <h1
          style={{
            fontWeight: 'bold',
            fontSize: 24,
            color: theme === 'dark' ? Colors.Gray3 : '#333',
          }}
        >
          {t('Disability Dashboard')}
        </h1>
        <div
          className="dropdown-container"
          style={{ display: 'flex', alignItems: 'center' }}
        >
          <CustomSelectControlled
            options={droneOptions}
            value={
              droneOptions.find((opt) => opt.value === selectedDrone) ||
              undefined
            }
            setValue={(opt) => setSelectedDrone(opt ? String(opt.value) : '')}
            isClearable={false}
            isSearchable={false}
            placeholder={t('Drone Selection')}
            menuPlacement="auto"
            menuPortalTarget={document.body}
            disabled={false}
          />
        </div>
      </div>
      {/* Main content */}
      <div
        style={{
          padding: 20,
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 20,
        }}
      >
        <div
          style={{
            gridColumn: '1 / span 3',
            display: 'flex',
            flexDirection: 'column',
            gap: 20,
          }}
        >
          <div style={{ display: 'flex', gap: 20 }}>
            <DroneStatusTable statusCounts={statusCounts} />
            <SensorStatusTable sensorData={sensorData} />
          </div>
          <div style={{ display: 'flex', gap: 20 }}>
            <div style={{ flex: 1 }}>
              <AttitudePanel
                data={{
                  roll: sensorData.roll,
                  pitch: sensorData.pitch,
                  yaw: sensorData.yaw,
                }}
              />
            </div>
            <div
              style={{
                flex: 2,
                display: 'flex',
                flexDirection: 'column',
                gap: 20,
              }}
            >
              <SensorChartPanel
                title={t('Gyro sensor')}
                chartData={[10, 15, 20, 15, 10, 5, 10, 15, 10, 5]}
                axisData={[
                  {
                    label: `X${t('axisLabel')}`,
                    icon: '↔',
                    value: `${sensorData.gyroX} ~ ${(
                      parseFloat(sensorData.gyroX) + 0.02
                    ).toFixed(2)}`,
                  },
                  {
                    label: `Y${t('axisLabel')}`,

                    icon: '↕',
                    value: `${sensorData.gyroY} ~ ${(
                      parseFloat(sensorData.gyroY) + 0.02
                    ).toFixed(2)}`,
                  },
                  {
                    label: `Z${t('axisLabel')}`,
                    icon: '⊙',
                    value: `${sensorData.gyroZ} ~ ${(
                      parseFloat(sensorData.gyroZ) + 0.01
                    ).toFixed(2)}`,
                  },
                ]}
              />
              <SensorChartPanel
                title={t('Geomagnetic sensor')}
                chartData={[50, 52, 48, 51, 53, 49, 50, 52, 51, 50]}
                axisData={[
                  {
                    label: `X${t('axisLabel')}`,
                    icon: '🧭',
                    value: `${sensorData.magX} ~ ${(parseFloat(sensorData.magX) + 1.4).toFixed(2)}`,
                  },
                  {
                    label: `Y${t('axisLabel')}`,
                    icon: '🧭',
                    value: `${sensorData.magY} ~ ${(parseFloat(sensorData.magY) + 1.3).toFixed(2)}`,
                  },
                  {
                    label: `Z${t('axisLabel')}`,
                    icon: '🧭',
                    value: `${sensorData.magZ} ~ ${(parseFloat(sensorData.magZ) + 1.2).toFixed(2)}`,
                  },
                ]}
              />
            </div>
          </div>
        </div>
        <div
          style={{
            gridColumn: '4 / span 1',
            display: 'flex',
            flexDirection: 'column',
            gap: 20,
          }}
        >
          <Panel>
            <h3
              style={{
                fontSize: 18,
                margin: 0,
                marginBottom: 10,
                color: theme === 'dark' ? Colors.Gray3 : '#333',
                textAlign: 'left',
              }}
            >
              <span
                style={{
                  display: 'inline-block',
                  width: 24,
                  height: 24,
                  background: theme === 'dark' ? '#2D2E30' : '#f8f8f8',
                  borderRadius: '50%',
                  marginRight: 5,
                  verticalAlign: 'middle',
                  position: 'relative',
                }}
              >
                <span
                  style={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%,-50%)',
                    width: 12,
                    height: 12,
                    background: '#1D9BE2',
                    borderRadius: '50%',
                  }}
                />
              </span>
              {t('Drone altitude')} 🛸
            </h3>
            <AltitudePanel altitude={altitude} />
            <BatteryBar batteryLevel={batteryLevel} />
            <SensorAxisGrid
              label={t('Accelerometer sensor')}
              axisData={[
                {
                  label: `X${t('axisLabel')}`,
                  icon: '⇉',
                  value: `${sensorData.accelX} ~ ${(
                    parseFloat(sensorData.accelX) + 0.07
                  ).toFixed(2)}`,
                },
                {
                  label: `Y${t('axisLabel')}`,
                  icon: '⇊',
                  value: `${sensorData.accelY} ~ ${(
                    parseFloat(sensorData.accelY) + 0.06
                  ).toFixed(2)}`,
                },
                {
                  label: `Z${t('axisLabel')}`,

                  icon: '⥯',
                  value: `${sensorData.accelZ} ~ ${(
                    parseFloat(sensorData.accelZ) + 0.04
                  ).toFixed(2)}`,
                },
              ]}
            />
            <SensorAxisGrid
              label={t('Vibration sensor')}
              axisData={[
                {
                  label: `X${t('axisLabel')}`,
                  icon: '↯',
                  value: `${sensorData.accelX} ~ ${(
                    parseFloat(sensorData.accelX) + 0.07
                  ).toFixed(2)}`,
                },
                {
                  label: `Y${t('axisLabel')}`,
                  icon: '↯',
                  value: `${sensorData.accelY} ~ ${(
                    parseFloat(sensorData.accelY) + 0.06
                  ).toFixed(2)}`,
                },
                {
                  label: `Z${t('axisLabel')}`,
                  icon: '↯',
                  value: `${sensorData.accelZ} ~ ${(
                    parseFloat(sensorData.accelZ) + 0.04
                  ).toFixed(2)}`,
                },
              ]}
            />
          </Panel>
        </div>
      </div>
    </div>
  );
};

export default DisabillityDashborad;
