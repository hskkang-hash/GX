import { DrawingPoint, DrawingShape } from './types';

export const validateCoordinate = (
  value: number | string | undefined,
): number | null => {
  const num = typeof value === 'number' ? value : Number(value);
  return num && !isNaN(num) && num !== 0 ? num : null;
};

export const isValidCoordinate = (
  lat: number | string | undefined,
  lng: number | string | undefined,
): boolean => {
  const latNum = validateCoordinate(lat);
  const lngNum = validateCoordinate(lng);
  return latNum !== null && lngNum !== null;
};

/**
 * Calculate center and radius from polygon bounds
 */
export const calculatePolygonBounds = (
  points: DrawingPoint[],
): {
  center: DrawingPoint;
  radius: number;
} => {
  if (points.length === 0) {
    throw new Error('Cannot calculate bounds for empty polygon');
  }

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
): DrawingPoint[] => {
  const circlePoints: DrawingPoint[] = [];
  for (let i = 0; i < 16; i++) {
    const angle = (i * 2 * Math.PI) / 16;
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

export const exportDrawingDataAsJSON = (
  currentShape: DrawingShape | null,
): string => {
  if (!currentShape) return JSON.stringify([], null, 2);

  let shapeWithPoints = currentShape;
  if (
    currentShape.type === 'CIRCULAR' &&
    currentShape.center &&
    currentShape.radius
  ) {
    const circlePoints: DrawingPoint[] = [];
    for (let i = 0; i < 16; i++) {
      const angle = (i * 2 * Math.PI) / 16;
      const lat =
        currentShape.center!.lat + currentShape.radius! * Math.cos(angle);
      const lng =
        currentShape.center!.lng + currentShape.radius! * Math.sin(angle);
      circlePoints.push({ lat, lng });
    }

    shapeWithPoints = {
      ...currentShape,
      points: circlePoints,
    };
  }

  return JSON.stringify([shapeWithPoints], null, 2);
};

export const exportDrawingDataAsGeoJSON = (
  currentShape: DrawingShape | null,
): Record<string, unknown> => {
  if (!currentShape) {
    return {
      type: 'FeatureCollection',
      features: [],
    };
  }

  const shape = currentShape;
  let feature = null;

  if (shape.type === 'LINE') {
    feature = {
      type: 'Feature',
      properties: {
        id: shape.id,
        type: shape.type,
        fillColor: shape.fillColor,
        fillOpacity: shape.fillOpacity,
      },
      geometry: {
        type: 'LineString',
        coordinates: shape.points.map((point) => [point.lng, point.lat]),
      },
    };
  } else if (shape.type === 'POLYGON' || shape.type === 'TRACE') {
    feature = {
      type: 'Feature',
      properties: {
        id: shape.id,
        type: shape.type,
        fillColor: shape.fillColor,
        fillOpacity: shape.fillOpacity,
      },
      geometry: {
        type: 'Polygon',
        coordinates: [shape.points.map((point) => [point.lng, point.lat])],
      },
    };
  } else if (shape.type === 'CIRCULAR' && shape.center && shape.radius) {
    const circlePoints: DrawingPoint[] = [];
    for (let i = 0; i < 16; i++) {
      const angle = (i * 2 * Math.PI) / 16;
      const lat = shape.center!.lat + shape.radius! * Math.cos(angle);
      const lng = shape.center!.lng + shape.radius! * Math.sin(angle);
      circlePoints.push({ lat, lng });
    }
    circlePoints.push(circlePoints[0]);

    feature = {
      type: 'Feature',
      properties: {
        id: shape.id,
        type: shape.type,
        center: shape.center,
        radius: shape.radius,
        fillColor: shape.fillColor,
        fillOpacity: shape.fillOpacity,
        points: circlePoints,
      },
      geometry: {
        type: 'Polygon',
        coordinates: [circlePoints.map((point) => [point.lng, point.lat])],
      },
    };
  }

  return {
    type: 'FeatureCollection',
    features: feature ? [feature] : [],
  };
};
