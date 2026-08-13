import React from 'react';
import { useTranslation } from 'react-i18next';
import { useConfigGroupSystem } from 'rj-core';

import MapKakao from '@/components/maps/MapKakao';

import { MapGoogle } from '../../../../components/maps';
import { MAP_CONFIG } from '../../../../configs/Constant';

const cities = [
  { name: '서울', coords: [37.5665, 126.978] },
  { name: '부산', coords: [35.1796, 129.0756] },
  { name: '인천', coords: [37.4563, 126.7052] },
  { name: '대구', coords: [35.8714, 128.6014] },
  { name: '광주', coords: [35.1595, 126.8526] },
  { name: '대전', coords: [36.3504, 127.3845] },
];

// Tạo 1 path nối các thành phố lớn
const path = [
  { lat: 37.5665, lng: 126.978 }, // Seoul
  { lat: 37.4563, lng: 126.7052 }, // Incheon
  { lat: 36.3504, lng: 127.3845 }, // Daejeon
  { lat: 35.8714, lng: 128.6014 }, // Daegu
];

// Tính bounds bao trọn tất cả marker và path
function getBounds(points: { lat: number; lng: number }[]): {
  sw: { lat: number; lng: number };
  ne: { lat: number; lng: number };
} {
  let minLat = 90,
    maxLat = -90,
    minLng = 180,
    maxLng = -180;
  points.forEach((p: { lat: number; lng: number }) => {
    if (p.lat < minLat) minLat = p.lat;
    if (p.lat > maxLat) maxLat = p.lat;
    if (p.lng < minLng) minLng = p.lng;
    if (p.lng > maxLng) maxLng = p.lng;
  });
  return {
    sw: { lat: minLat, lng: minLng },
    ne: { lat: maxLat, lng: maxLng },
  };
}

const allPoints = [
  ...cities.map((c) => ({ lat: c.coords[0], lng: c.coords[1] })),
  ...path,
];
const bounds = getBounds(allPoints);

const KoreaMap: React.FC = ({ height }) => {
  const { t } = useTranslation();
  const { configGroupSystem } = useConfigGroupSystem();
  const isSystemUseGoogleMap =
    configGroupSystem?.use_map?.select_map?.google_map || false;
  const isEmptyConfigGroupSystem =
    !configGroupSystem || Object.keys(configGroupSystem).length === 0;
  if (isSystemUseGoogleMap || isEmptyConfigGroupSystem) {
    return (
      <MapGoogle
        center={{ lat: 36.5184, lng: 126.8 }}
        level={7}
        operatingMarkers={cities.map((c) => ({
          lat: c.coords[0],
          lng: c.coords[1],
          name: c.name,
        }))}
        polylines={[path]}
        smallMarker={true}
        bounds={bounds}
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
        style={{ height: height || 500, minHeight: 300, borderRadius: 5 }}
        apiKey={MAP_CONFIG.GOOGLE_MAPS_API_KEY}
      />
    );
  }

  return (
    <MapKakao
      center={{ lat: 36.5184, lng: 126.8 }}
      level={7}
      operatingMarkers={cities.map((c) => ({
        lat: c.coords[0],
        lng: c.coords[1],
        name: c.name,
      }))}
      polylines={[path]}
      smallMarker={true}
      bounds={bounds}
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
      style={{ height: height || 500, minHeight: 300, borderRadius: 5 }}
    />
  );
};

export default KoreaMap;
