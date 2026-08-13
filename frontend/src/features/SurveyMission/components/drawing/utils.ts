import { DrawingPoint, DrawingShape, DrawingMode } from './types';

/**
 * Calculate center and radius from polygon bounds
 */
export const calculatePolygonBounds = (
  points: DrawingPoint[],
): {
  center: DrawingPoint;
  radius: number;
} => {
  const minLat = Math.min(...points.map((p) => p.lat));
  const maxLat = Math.max(...points.map((p) => p.lat));
  const minLng = Math.min(...points.map((p) => p.lng));
  const maxLng = Math.max(...points.map((p) => p.lng));

  const center = {
    lat: (minLat + maxLat) / 2,
    lng: (minLng + maxLng) / 2,
  };

  // Use the larger dimension as radius
  const latRadius = (maxLat - minLat) / 2;
  const lngRadius = (maxLng - minLng) / 2;
  const radius = Math.max(latRadius, lngRadius);

  return { center, radius };
};

/**
 * Generate circle points from center and radius
 */
export const generateCirclePoints = (
  center: DrawingPoint,
  radius: number,
  segments = 16,
): DrawingPoint[] => {
  const circlePoints: DrawingPoint[] = [];
  for (let i = 0; i < segments; i++) {
    const angle = (i * 2 * Math.PI) / segments;
    const lat = center.lat + radius * Math.cos(angle);
    const lng = center.lng + radius * Math.sin(angle);
    circlePoints.push({ lat, lng });
  }
  return circlePoints;
};

/**
 * Generate rectangle points from center and radius
 */
export const generateRectanglePoints = (
  center: DrawingPoint,
  radius: number,
): DrawingPoint[] => {
  return [
    { lat: center.lat - radius, lng: center.lng - radius },
    { lat: center.lat - radius, lng: center.lng + radius },
    { lat: center.lat + radius, lng: center.lng + radius },
    { lat: center.lat + radius, lng: center.lng - radius },
  ];
};

/**
 * Convert polygon to circular shape
 */
export const convertPolygonToCircular = (
  polygon: DrawingShape,
): DrawingShape => {
  const { center, radius } = calculatePolygonBounds(polygon.points);
  const circlePoints = generateCirclePoints(center, radius);

  return {
    id: `circle-${Date.now()}`,
    type: 'CIRCULAR',
    points: circlePoints,
    center,
    radius,
    fillColor: polygon.fillColor || '#4caf50',
    fillOpacity: polygon.fillOpacity || 0.3,
  };
};

/**
 * Convert circular to polygon shape
 */
export const convertCircularToPolygon = (
  circular: DrawingShape,
): DrawingShape => {
  if (!circular.center || !circular.radius) {
    throw new Error('Circular shape must have center and radius');
  }

  const rectanglePoints = generateRectanglePoints(
    circular.center,
    circular.radius,
  );

  return {
    id: `polygon-${Date.now()}`,
    type: 'POLYGON',
    points: rectanglePoints,
    fillColor: circular.fillColor || '#4caf50',
    fillOpacity: circular.fillOpacity || 0.3,
  };
};

/**
 * Check if two drawing modes can be converted directly
 */
export const canConvertDirectly = (
  fromType: DrawingMode,
  toType: DrawingMode,
): boolean => {
  return (
    (fromType === 'POLYGON' && toType === 'CIRCULAR') ||
    (fromType === 'CIRCULAR' && toType === 'POLYGON')
  );
};

/**
 * Validate coordinate values
 */
export const validateCoordinate = (
  value: number | string | undefined,
): number | null => {
  const num = typeof value === 'number' ? value : Number(value);
  return num && !isNaN(num) && num !== 0 ? num : null;
};

/**
 * Check if coordinates are valid
 */
export const isValidCoordinate = (
  lat: number | string | undefined,
  lng: number | string | undefined,
): boolean => {
  const latNum = validateCoordinate(lat);
  const lngNum = validateCoordinate(lng);
  return latNum !== null && lngNum !== null;
};
