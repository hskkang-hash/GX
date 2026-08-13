import { useMap } from '@vis.gl/react-google-maps';
import React, { useCallback, useEffect, useMemo, useRef } from 'react';

import { Marker } from './drawingGoogle/types';

interface RoutePolylineProps {
  markerData: Marker[];
  strokeColor?: string;
  strokeWeight?: number;
  strokeOpacity?: number;
  geodesic?: boolean;
  isLineMode?: boolean;
  onMarkerClick?: (marker: Marker) => void;
}

const RoutePolyline: React.FC<RoutePolylineProps> = ({
  markerData,
  strokeColor: baseStrokeColor = '#ffffff',
  strokeWeight = 3,
  strokeOpacity = 0.8,
  geodesic = true,
  isLineMode = false,
  onMarkerClick,
}) => {
  const map = useMap();
  const polylineRefs = useRef<google.maps.Polyline[]>([]);
  const markersRef = useRef<google.maps.Marker[]>([]);
  const arrowsRef = useRef<google.maps.Marker[]>([]);

  // Helper function to create arrow marker
  const createArrowMarker = useCallback(
    (
      position: google.maps.LatLng,
      rotation: number,
      color: string,
    ): google.maps.Marker => {
      const arrowSymbol = {
        path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
        scale: 4,
        strokeColor: color,
        fillColor: color,
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
    [map, strokeOpacity],
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

  const processedMarkers = useMemo(() => {
    return markerData
      .map((marker, index) => {
        const lat = Number(String(marker.lat).replace(',', '.'));
        const lng = Number(String(marker.lng).replace(',', '.'));

        if (
          Number.isNaN(lat) ||
          Number.isNaN(lng) ||
          (lat === 0 && lng === 0) ||
          lat < -90 ||
          lat > 90 ||
          lng < -180 ||
          lng > 180
        ) {
          return null;
        }

        return {
          position: { lat, lng } as google.maps.LatLngLiteral,
          original: marker,
          index,
        };
      })
      .filter(
        (
          entry,
        ): entry is {
          position: google.maps.LatLngLiteral;
          original: Marker;
          index: number;
        } => entry !== null,
      );
  }, [markerData]);

  const processedPath = useMemo(() => {
    return processedMarkers.map((entry) => entry.position);
  }, [processedMarkers]);

  const { segments, segmentColors } = useMemo(() => {
    if (processedPath.length < 2) {
      return {
        segments: [] as Array<{
          startIndex: number;
          path: google.maps.LatLngLiteral[];
          color: string;
        }>,
        segmentColors: [] as (string | undefined)[],
      };
    }

    const resultSegments: Array<{
      startIndex: number;
      path: google.maps.LatLngLiteral[];
      color: string;
    }> = [];
    const colors: Array<string | undefined> = [];

    for (let index = 0; index < processedPath.length - 1; index += 1) {
      const currentEntry = processedMarkers[index];
      const nextEntry = processedMarkers[index + 1];
      const currentRouteId = currentEntry?.original.routeId ?? '__default__';
      const nextRouteId = nextEntry?.original.routeId ?? currentRouteId;

      if (currentRouteId !== nextRouteId) {
        colors[index] = undefined;
        continue;
      }

      let segmentColor = currentEntry?.original.color;
      if (!segmentColor || segmentColor.length === 0) {
        segmentColor = nextEntry?.original.color ?? baseStrokeColor;
      }

      resultSegments.push({
        startIndex: index,
        path: [processedPath[index], processedPath[index + 1]],
        color: segmentColor,
      });
      colors[index] = segmentColor;
    }

    return { segments: resultSegments, segmentColors: colors };
  }, [processedPath, processedMarkers, baseStrokeColor]);

  const fallbackStrokeColor =
    segmentColors.find((color) => color && color.length > 0) ?? baseStrokeColor;

  useEffect(() => {
    if (!map) {
      if (polylineRefs.current.length > 0) {
        polylineRefs.current.forEach((polyline) => polyline.setMap(null));
        polylineRefs.current = [];
      }
      markersRef.current.forEach((marker) => marker.setMap(null));
      markersRef.current = [];
      arrowsRef.current.forEach((arrow) => arrow.setMap(null));
      arrowsRef.current = [];
      return;
    }

    if (processedPath.length < 2) {
      if (polylineRefs.current.length > 0) {
        polylineRefs.current.forEach((polyline) => polyline.setMap(null));
        polylineRefs.current = [];
      }
      markersRef.current.forEach((marker) => marker.setMap(null));
      markersRef.current = [];
      arrowsRef.current.forEach((arrow) => arrow.setMap(null));
      arrowsRef.current = [];
      return;
    }

    polylineRefs.current.forEach((polyline) => polyline.setMap(null));
    polylineRefs.current = [];
    markersRef.current.forEach((marker) => marker.setMap(null));
    markersRef.current = [];
    arrowsRef.current.forEach((arrow) => arrow.setMap(null));
    arrowsRef.current = [];

    segments.forEach((segment) => {
      const polyline = new google.maps.Polyline({
        path: segment.path,
        geodesic,
        strokeColor: segment.color,
        strokeOpacity,
        strokeWeight,
        clickable: false,
        zIndex: 1,
      });
      polyline.setMap(map);
      polylineRefs.current.push(polyline);
    });

    if (isLineMode) {
      const pointMarkers = processedMarkers.map((entry, index) => {
        const markerColor = entry.original.color ?? fallbackStrokeColor;
        const markerTitle = entry.original.name ?? `Point ${index + 1}`;
        const marker = new google.maps.Marker({
          position: entry.position,
          map,
          title: markerTitle,
          icon: {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 6,
            fillColor: markerColor,
            fillOpacity: strokeOpacity,
            strokeColor: '#ffffff',
            strokeWeight: 2,
          },
          zIndex: 3,
        });

        if (onMarkerClick) {
          marker.addListener('click', () => {
            onMarkerClick(entry.original);
          });
        }

        return marker;
      });

      markersRef.current = pointMarkers;
    } else {
      const startEntry = processedMarkers[0];
      const endEntry = processedMarkers[processedMarkers.length - 1];

      const startMarker = new google.maps.Marker({
        position: startEntry.position,
        map,
        title: startEntry.original.name ?? 'Start Point',
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 8,
          fillColor: startEntry.original.color ?? '#00ff00',
          fillOpacity: 1,
          strokeColor: '#ffffff',
          strokeWeight: 2,
        },
        zIndex: 3,
      });

      const endMarker = new google.maps.Marker({
        position: endEntry.position,
        map,
        title: endEntry.original.name ?? 'End Point',
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 8,
          fillColor: endEntry.original.color ?? '#ff0000',
          fillOpacity: 1,
          strokeColor: '#ffffff',
          strokeWeight: 2,
        },
        zIndex: 3,
      });

      if (onMarkerClick) {
        startMarker.addListener('click', () => {
          onMarkerClick(startEntry.original);
        });

        endMarker.addListener('click', () => {
          onMarkerClick(endEntry.original);
        });
      }

      markersRef.current = [startMarker, endMarker];

      const arrowCount = Math.min(
        Math.max(2, Math.floor(processedPath.length / 3)),
        5,
      );
      const step = Math.max(
        1,
        Math.floor(processedPath.length / (arrowCount + 1)),
      );

      for (let index = step; index < processedPath.length - 1; index += step) {
        const segmentColor = segmentColors[index];
        if (!segmentColor) {
          continue;
        }

        const currentPoint = new google.maps.LatLng(
          processedPath[index].lat,
          processedPath[index].lng,
        );
        const nextPoint = new google.maps.LatLng(
          processedPath[index + 1].lat,
          processedPath[index + 1].lng,
        );
        const midLat = (currentPoint.lat() + nextPoint.lat()) / 2;
        const midLng = (currentPoint.lng() + nextPoint.lng()) / 2;
        const midPoint = new google.maps.LatLng(midLat, midLng);
        const bearing = calculateBearing(currentPoint, nextPoint);
        const arrowMarker = createArrowMarker(midPoint, bearing, segmentColor);
        arrowsRef.current.push(arrowMarker);
      }
    }
  }, [
    map,
    processedPath,
    processedMarkers,
    segments,
    segmentColors,
    geodesic,
    strokeOpacity,
    strokeWeight,
    isLineMode,
    onMarkerClick,
    createArrowMarker,
    calculateBearing,
    fallbackStrokeColor,
  ]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (polylineRefs.current.length > 0) {
        polylineRefs.current.forEach((polyline) => polyline.setMap(null));
        polylineRefs.current = [];
      }
      markersRef.current.forEach((marker) => marker.setMap(null));
      markersRef.current = [];
      arrowsRef.current.forEach((arrow) => arrow.setMap(null));
      arrowsRef.current = [];
    };
  }, []);

  return null;
};

// Custom comparison function for memoization
const areMarkerDataEqual = (
  prevProps: RoutePolylineProps,
  nextProps: RoutePolylineProps,
): boolean => {
  // Compare all props except markerData
  if (
    prevProps.strokeColor !== nextProps.strokeColor ||
    prevProps.strokeWeight !== nextProps.strokeWeight ||
    prevProps.strokeOpacity !== nextProps.strokeOpacity ||
    prevProps.geodesic !== nextProps.geodesic ||
    prevProps.isLineMode !== nextProps.isLineMode
  ) {
    return false;
  }

  // Deep compare markerData
  if (prevProps.markerData.length !== nextProps.markerData.length) {
    return false;
  }

  return prevProps.markerData.every((marker, index) => {
    const nextMarker = nextProps.markerData[index];
    return (
      nextMarker &&
      Math.abs(marker.lat - nextMarker.lat) < 0.000001 &&
      Math.abs(marker.lng - nextMarker.lng) < 0.000001
    );
  });
};

export default React.memo(RoutePolyline, areMarkerDataEqual);
