import { useMap } from '@vis.gl/react-google-maps';
import React, { useCallback, useEffect, useRef } from 'react';
import { Marker } from './drawingGoogle/types';

interface DroneRoute {
  route_path?: Array<{
    latitude: number;
    longitude: number;
    name?: string;
  }>;
  device?: {
    id: number;
    name: string;
    color?: string;
  };
}

interface RoutePolylineProps {
  markerData: Marker[];
  strokeColor?: string;
  strokeWeight?: number;
  strokeOpacity?: number;
  geodesic?: boolean;
  isLineMode?: boolean;
  onMarkerClick?: (marker: Marker) => void;
  droneRoutes?: DroneRoute[];
}



const createLocationPinIcon = (
  fillColor: string,
  scale: number,
): google.maps.Symbol => {
  const pinPath =
    'M 0,0 C -2,-10 -10,-12 -10,-20 A 10,10 0 1,1 10,-20 C 10,-12 2,-10 0,0 z M -2,-20 A 2,2 0 1,1 2,-20 2,2 0 1,1 -2,-20 z';
  return {
    path: pinPath,
    scale: scale,
    fillColor: fillColor,
    fillOpacity: 1,
    strokeColor: '#ffffff',
    strokeWeight: 2,
    anchor: new google.maps.Point(0, 0), // Anchor at bottom point of pin
  };
};

const RoutePolyline: React.FC<RoutePolylineProps> = ({
  markerData,
  strokeColor = '#2378d9',
  strokeWeight = 3,
  strokeOpacity = 0.8,
  geodesic = true,
  isLineMode = false,
  onMarkerClick,
  droneRoutes = [],
}) => {


  const map = useMap();
  const polylineRef = useRef<google.maps.Polyline | null>(null);
  const markersRef = useRef<google.maps.Marker[]>([]);
  const arrowsRef = useRef<google.maps.Marker[]>([]);
  const dronePolylinesRef = useRef<google.maps.Polyline[]>([]);
  const droneMarkersRef = useRef<google.maps.Marker[]>([]);


  // Helper function to create arrow marker
  const createArrowMarker = useCallback(
    (position: google.maps.LatLng, rotation: number): google.maps.Marker => {
      const arrowSymbol = {
        path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
        scale: 4,
        strokeColor: strokeColor,
        fillColor: strokeColor,
        fillOpacity: strokeOpacity,
        rotation: rotation,
      };

      return new google.maps.Marker({
        position: position,
        icon: arrowSymbol,
        map: map,
        clickable: false,
        zIndex: 2,
      });
    },
    [map, strokeColor, strokeOpacity],
  );

  // Helper function to calculate bearing between two points
  const calculateBearing = useCallback(
    (from: google.maps.LatLng, to: google.maps.LatLng): number => {
      const lat1 = (from.lat() * Math.PI) / 180;
      const lat2 = (to.lat() * Math.PI) / 180;
      const deltaLng = ((to.lng() - from.lng()) * Math.PI) / 180;

      const y = Math.sin(deltaLng) * Math.cos(lat2);
      const x =
        Math.cos(lat1) * Math.sin(lat2) -
        Math.sin(lat1) * Math.cos(lat2) * Math.cos(deltaLng);

      return (Math.atan2(y, x) * 180) / Math.PI;
    },
    [],
  );
  useEffect(() => {
    if (!map || !markerData || markerData.length < 2) {
      // Clean up existing elements if no valid data
      if (polylineRef.current) {
        polylineRef.current.setMap(null);
        polylineRef.current = null;
      }
      markersRef.current.forEach((marker) => marker.setMap(null));
      markersRef.current = [];
      arrowsRef.current.forEach((arrow) => arrow.setMap(null));
      arrowsRef.current = [];
      dronePolylinesRef.current.forEach((polyline) => polyline.setMap(null));
      dronePolylinesRef.current = [];
      droneMarkersRef.current.forEach((marker) => marker.setMap(null));
      droneMarkersRef.current = [];
      return;
    }

    // Clean up existing elements first
    if (polylineRef.current) {
      polylineRef.current.setMap(null);
      polylineRef.current = null;
    }
    markersRef.current.forEach((marker) => marker.setMap(null));
    markersRef.current = [];
    arrowsRef.current.forEach((arrow) => arrow.setMap(null));
    arrowsRef.current = [];
    dronePolylinesRef.current.forEach((polyline) => polyline.setMap(null));
    dronePolylinesRef.current = [];
    droneMarkersRef.current.forEach((marker) => marker.setMap(null));
    droneMarkersRef.current = [];

    // Convert markerData to path format for Google Maps Polyline
    // Handle comma decimal separators and filter out invalid coordinates
    const path = markerData
      .map((marker) => {
        // Convert comma decimal separators to dots and parse as numbers
        const lat = Number(String(marker.lat).replace(',', '.'));
        const lng = Number(String(marker.lng).replace(',', '.'));
        return { lat, lng };
      })
      .filter((point) => {
        // Filter out invalid coordinates (NaN, 0,0, or out of valid range)
        return (
          !isNaN(point.lat) &&
          !isNaN(point.lng) &&
          !(point.lat === 0 && point.lng === 0) &&
          point.lat >= -90 &&
          point.lat <= 90 &&
          point.lng >= -180 &&
          point.lng <= 180
        );
      });

    // Create new polyline
    const polyline = new google.maps.Polyline({
      path: path,
      geodesic: geodesic,
      strokeColor: strokeColor,
      strokeOpacity: strokeOpacity,
      strokeWeight: strokeWeight,
      clickable: false,
      zIndex: 1,
    });

    // Add polyline to map
    polyline.setMap(map);
    polylineRef.current = polyline;

    if (isLineMode) {
      const pointMarkers = path.map((point, index) => {
        const isStart = index === 0;
        const isEnd = index === path.length - 1;
        let fillColor = strokeColor;
        let scale = 1;

        if (isStart) {
          fillColor = '#00ff00';
          scale = 1.2;
        } else if (isEnd) {
          fillColor = '#ff0000';
          scale = 1.2;
        }
        const marker = new google.maps.Marker({
          position: point,
          map: map,
          title: isStart ? 'Start Point' : isEnd ? 'End Point' : `Waypoint ${index + 1}`,
          icon: createLocationPinIcon(fillColor, scale),
          zIndex: 2,
        });
        if (onMarkerClick) {
          marker.addListener('click', () => {
            const originalMarker = markerData[index];
            if (originalMarker) {
              onMarkerClick(originalMarker);
            }
          });
        }
        return marker;
      });

      markersRef.current = pointMarkers;
    } else {
      // Create markers for all waypoints
      const waypointMarkers = path.map((point, index) => {
        const isStart = index === 0;
        const isEnd = index === path.length - 1;

        let fillColor = strokeColor;
        let scale = 1;

        if (isStart) {
          fillColor = '#00ff00';
          scale = 1.2;
        } else if (isEnd) {
          fillColor = '#ff0000';
          scale = 1.2;
        }

        const marker = new google.maps.Marker({
          position: point,
          map: map,
          title: isStart ? 'Start Point' : isEnd ? 'End Point' : `Waypoint ${index + 1}`,
          icon: createLocationPinIcon(fillColor, scale),
          zIndex: 3,
        });

        // Add click event listener
        if (onMarkerClick) {
          marker.addListener('click', () => {
            const originalMarker = markerData[index];
            if (originalMarker) {
              onMarkerClick(originalMarker);
            }
          });
        }
        return marker;
      });

      markersRef.current = waypointMarkers;

      // Add arrow markers along the path to show direction
      const arrowCount = Math.min(Math.max(2, Math.floor(path.length / 3)), 5); // 2-5 arrows
      const step = Math.max(1, Math.floor(path.length / (arrowCount + 1)));

      for (let i = step; i < path.length - 1; i += step) {
        const currentPoint = new google.maps.LatLng(path[i].lat, path[i].lng);
        const nextPoint = new google.maps.LatLng(
          path[i + 1].lat,
          path[i + 1].lng,
        );
        // Calculate midpoint between current and next point
        const midLat = (currentPoint.lat() + nextPoint.lat()) / 2;
        const midLng = (currentPoint.lng() + nextPoint.lng()) / 2;
        const midPoint = new google.maps.LatLng(midLat, midLng);
        const bearing = calculateBearing(currentPoint, nextPoint);
        const arrowMarker = createArrowMarker(midPoint, bearing);
        arrowsRef.current.push(arrowMarker);
      }
    }

    // Draw polyline and markers for each drone route with different colors
    droneRoutes.forEach((droneRoutes, index) => {
      if (!droneRoutes.route_path || droneRoutes.route_path.length < 1) {
        return;
      }
      const dronePath = droneRoutes.route_path
        .map((point) => ({
          lat: Number(point.lat),
          lng: Number(point.lng),
          name: point.name,
          altitude: point.altitude ?? 0,
          command: point.command ?? "WAYPOINT",
          frame: point.frame ?? "FRAME",
          param_1: point.param_1 ?? 0,
          param_2: point.param_2 ?? 0,
          param_3: point.param_3 ?? 0,
          param_4: point.param_4 ?? 0,
        }))
        .filter((point) => {
          // Filter out invalid coordinates
          return (
            !isNaN(point.lat) &&
            !isNaN(point.lng) &&
            !(point.lat === 0 && point.lng === 0) &&
            point.lat >= -90 &&
            point.lat <= 90 &&
            point.lng >= -180 &&
            point.lng <= 180
          );
        });
      if (dronePath.length < 1) {
        return;
      }

      const droneColor = droneRoutes.device?.color || '#ce0ef0';

      // Create polyline for this drone
      const dronePolyline = new google.maps.Polyline({
        path: dronePath,
        geodesic: geodesic,
        strokeColor: droneColor,
        strokeOpacity: strokeOpacity,
        strokeWeight: strokeWeight + 1, // Slightly thicker than main polyline
        clickable: false,
        zIndex: 7, // Below markers but above main polyline
      });

      dronePolyline.setMap(map);
      dronePolylinesRef.current.push(dronePolyline);

      // Create markers for drone route points (especially when isLineMode)
      // if (isLineMode) {
      const droneRouteMarkers = dronePath.map((point, pointIndex) => {

        const marker = new google.maps.Marker({
          position: point,
          map: map,
          title: droneRoutes.route_path?.[pointIndex]?.name || `Point ${pointIndex + 1}`,
          icon: createLocationPinIcon(droneColor, 1),
          zIndex: 100, // Above main markers
        });

        // Add click event listener if needed
        if (onMarkerClick) {
          marker.addListener('click', () => {
            const markerData: Marker = {
              lat: point.lat,
              lng: point.lng,
              name: point.name || `WAYPOINT`,
              command: point.command,
              frame: point.frame,
              param_1: point.param_1 ?? 0,
              param_2: point.param_2 ?? 0,
              param_3: point.param_3 ?? 0,
              param_4: point.param_4 ?? 0,
              altitude: point.altitude ?? 0,
            };
            onMarkerClick(markerData);
          });
        }

        return marker;
      });

      droneMarkersRef.current.push(...droneRouteMarkers);

    });

    // Cleanup function
    return () => {
      if (polylineRef.current) {
        polylineRef.current.setMap(null);
        polylineRef.current = null;
      }
      markersRef.current.forEach((marker) => marker.setMap(null));
      markersRef.current = [];
      arrowsRef.current.forEach((arrow) => arrow.setMap(null));
      arrowsRef.current = [];
      dronePolylinesRef.current.forEach((polyline) => polyline.setMap(null));
      dronePolylinesRef.current = [];
      droneMarkersRef.current.forEach((marker) => marker.setMap(null));
      droneMarkersRef.current = [];
    };
  }, [
    map,
    markerData,
    strokeColor,
    strokeWeight,
    strokeOpacity,
    geodesic,
    isLineMode,
    createArrowMarker,
    onMarkerClick,
    droneRoutes,
  ]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (polylineRef.current) {
        polylineRef.current.setMap(null);
        polylineRef.current = null;
      }
      markersRef.current.forEach((marker) => marker.setMap(null));
      markersRef.current = [];
      arrowsRef.current.forEach((arrow) => arrow.setMap(null));
      arrowsRef.current = [];
      dronePolylinesRef.current.forEach((polyline) => polyline.setMap(null));
      dronePolylinesRef.current = [];
      droneMarkersRef.current.forEach((marker) => marker.setMap(null));
      droneMarkersRef.current = [];
    };
  }, []);

  return null;
};

export default React.memo(RoutePolyline);
