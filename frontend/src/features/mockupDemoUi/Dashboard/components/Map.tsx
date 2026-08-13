import React from 'react';
import { useTranslation } from 'react-i18next';
import { useConfigGroupSystem } from 'rj-core';

import MapKakao from '@/components/maps/MapKakao';

import { MAP_CONFIG, MapGoogle } from '../../../../components/maps';

interface Marker {
  name: string;
  coords: [number, number];
  type: 'operating' | 'standby';
}

interface MapProps {
  operatingMarkers: Marker[];
  standbyMarkers: Marker[];
}

const Map: React.FC<MapProps> = ({ operatingMarkers, standbyMarkers }) => {
  const { t } = useTranslation();
  const { configGroupSystem } = useConfigGroupSystem();
  const isSystemUseGoogleMap =
    configGroupSystem?.use_map?.select_map?.google_map || false;
  const isEmptyConfigGroupSystem =
    !configGroupSystem || Object.keys(configGroupSystem).length === 0;

  // Tạo polyline đỏ nối các marker operating
  const polyline = operatingMarkers.map((m) => ({
    lat: m.coords[0],
    lng: m.coords[1],
  }));

  // Tính bounds từ tất cả marker
  const allPoints = [
    ...operatingMarkers.map((m) => m.coords),
    ...standbyMarkers.map((m) => m.coords),
  ];
  const bounds = allPoints.length
    ? {
        sw: {
          lat: Math.min(...allPoints.map((p) => p[0])) - 0.01,
          lng: Math.min(...allPoints.map((p) => p[1])) - 0.01,
        },
        ne: {
          lat: Math.max(...allPoints.map((p) => p[0])) + 0.01,
          lng: Math.max(...allPoints.map((p) => p[1])) + 0.01,
        },
      }
    : undefined;
  if (isSystemUseGoogleMap || isEmptyConfigGroupSystem) {
    return (
      <MapGoogle
        center={{ lat: 36.5184, lng: 126.8 }}
        operatingMarkers={operatingMarkers.map((m) => ({
          lat: m.coords[0],
          lng: m.coords[1],
          name: m.name,
        }))}
        standbyMarkers={standbyMarkers.map((m) => ({
          lat: m.coords[0],
          lng: m.coords[1],
          name: m.name,
        }))}
        polylines={[polyline]}
        bounds={bounds}
        smallMarker={true}
        style={{
          height: 500,
          minHeight: 300,
          borderRadius: 5,
          overflow: 'hidden',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
        }}
        overlayContent={
          <div style={{ fontSize: 12, color: '#666' }}>
            <div
              style={{ display: 'flex', alignItems: 'center', marginBottom: 5 }}
            >
              <div
                style={{
                  width: 10,
                  height: 10,
                  backgroundColor: '#4169e1',
                  borderRadius: '50%',
                  marginRight: 5,
                }}
              />
              <span style={{ fontSize: 12 }}>{t('도시')}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <div
                style={{
                  width: 10,
                  height: 2,
                  backgroundColor: '#e74c3c',
                  marginRight: 5,
                }}
              />
              <span style={{ fontSize: 12 }}>{t('드론 경로')}</span>
            </div>
          </div>
        }
        apiKey={MAP_CONFIG.GOOGLE_MAPS_API_KEY}
      />
    );
  }

  return (
    <MapKakao
      center={{ lat: 36.5184, lng: 126.8 }}
      operatingMarkers={operatingMarkers.map((m) => ({
        lat: m.coords[0],
        lng: m.coords[1],
        name: m.name,
      }))}
      standbyMarkers={standbyMarkers.map((m) => ({
        lat: m.coords[0],
        lng: m.coords[1],
        name: m.name,
      }))}
      polylines={[polyline]}
      bounds={bounds}
      smallMarker={true}
      style={{
        height: 500,
        minHeight: 300,
        borderRadius: 5,
        overflow: 'hidden',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
      }}
      overlayContent={
        <div style={{ fontSize: 12, color: '#666' }}>
          <div
            style={{ display: 'flex', alignItems: 'center', marginBottom: 5 }}
          >
            <div
              style={{
                width: 10,
                height: 10,
                backgroundColor: '#4169e1',
                borderRadius: '50%',
                marginRight: 5,
              }}
            />
            <span style={{ fontSize: 12 }}>{t('도시')}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <div
              style={{
                width: 10,
                height: 2,
                backgroundColor: '#e74c3c',
                marginRight: 5,
              }}
            />
            <span style={{ fontSize: 12 }}>{t('드론 경로')}</span>
          </div>
        </div>
      }
    />
  );
};

export default Map;
