import React, { useEffect, useRef } from 'react';

interface DebugPanelProps {
  drones: any[];
  selectedDroneIds: Record<string, string>;
  routeDroneCache: Record<string, any[]>;
  currentOrderDetails: any;
  generateRouteKey: (order: any) => string;
}

export const DebugPanel: React.FC<DebugPanelProps> = ({
  drones,
  selectedDroneIds,
  routeDroneCache,
  currentOrderDetails,
  generateRouteKey,
}) => {
  const prevDronesRef = useRef(drones.length);
  const prevSelectedRef = useRef(Object.keys(selectedDroneIds).length);
  const prevCacheRef = useRef(Object.keys(routeDroneCache).length);

  useEffect(() => {
    if (prevDronesRef.current !== drones.length) {
      console.log('🚨 DRONES CHANGED:', {
        from: prevDronesRef.current,
        to: drones.length,
        stack: new Error().stack?.split('\n').slice(1, 4),
      });
      prevDronesRef.current = drones.length;
    }
  }, [drones.length]);

  useEffect(() => {
    const selectedCount = Object.keys(selectedDroneIds).length;
    if (prevSelectedRef.current !== selectedCount) {
      console.log('🚨 SELECTED DRONE IDS CHANGED:', {
        from: prevSelectedRef.current,
        to: selectedCount,
        selections: selectedDroneIds,
      });
      prevSelectedRef.current = selectedCount;
    }
  }, [selectedDroneIds]);

  useEffect(() => {
    const cacheCount = Object.keys(routeDroneCache).length;
    if (prevCacheRef.current !== cacheCount) {
      console.log('💾 ROUTE CACHE CHANGED:', {
        from: prevCacheRef.current,
        to: cacheCount,
        routes: Object.keys(routeDroneCache),
      });
      prevCacheRef.current = cacheCount;
    }
  }, [routeDroneCache]);

  const currentRoute = currentOrderDetails
    ? generateRouteKey(currentOrderDetails)
    : 'none';
  const cachedForCurrentRoute = routeDroneCache[currentRoute] || [];

  return (
    <div
      style={{
        display: 'none',
        position: 'fixed',
        top: '10px',
        left: '10px',
        width: '300px',
        padding: '16px',
        backgroundColor: 'white',
        border: '1px solid #ccc',
        borderRadius: '4px',
        zIndex: 9999,
        fontSize: '12px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      }}
    >
      <h4 style={{ margin: '0 0 8px 0' }}>🐛 Debug Panel</h4>

      <div style={{ marginBottom: '8px' }}>
        <strong>Current Route:</strong> {currentRoute}
      </div>

      <div style={{ marginBottom: '8px' }}>
        <strong>Active Drones:</strong> {drones.length}
      </div>

      <div style={{ marginBottom: '8px' }}>
        <strong>Selected Assignments:</strong>{' '}
        {Object.keys(selectedDroneIds).length}
      </div>

      <div style={{ marginBottom: '8px' }}>
        <strong>Cache Routes:</strong> {Object.keys(routeDroneCache).length}
      </div>

      <div style={{ marginBottom: '8px' }}>
        <strong>Cached for Current Route:</strong>{' '}
        {cachedForCurrentRoute.length}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {Object.entries(routeDroneCache).map(([route, drones]) => (
          <span
            key={route}
            style={{
              padding: '2px 6px',
              backgroundColor: route === currentRoute ? '#e3f2fd' : '#f5f5f5',
              color: route === currentRoute ? '#1976d2' : '#666',
              borderRadius: '4px',
              fontSize: '10px',
            }}
          >
            {route}: {drones.length} drones
          </span>
        ))}
      </div>

      {Object.keys(selectedDroneIds).length > 0 && (
        <div style={{ marginTop: '8px' }}>
          <strong>Current Selections:</strong>
          {Object.entries(selectedDroneIds).map(([pkg, drone]) => (
            <div
              key={pkg}
              style={{ fontSize: '10px' }}
            >
              Package {pkg} → Drone {drone}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
