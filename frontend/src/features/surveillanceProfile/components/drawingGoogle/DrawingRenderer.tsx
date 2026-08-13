import { AdvancedMarker, Pin, useMap } from '@vis.gl/react-google-maps';
import React, { Fragment, useEffect, useRef } from 'react';

import { DrawingShape, DrawingPoint, DrawingMode } from './types';

// Helper function to validate and filter coordinates
const validateCoordinates = (
  path: { lat: number; lng: number }[],
): { lat: number; lng: number }[] => {
  if (!path || path.length === 0) {
    return [];
  }

  return path
    .map((point) => ({
      lat: Number(point.lat),
      lng: Number(point.lng),
    }))
    .filter(
      (point) =>
        !isNaN(point.lat) &&
        !isNaN(point.lng) &&
        !(point.lat === 0 && point.lng === 0) &&
        point.lat >= -90 &&
        point.lat <= 90 &&
        point.lng >= -180 &&
        point.lng <= 180,
    );
};

// Drawing Polyline component for Google Maps
const GoogleDrawingPolyline = React.memo(
  ({
    path,
    color,
    strokeWeight = 3,
    strokeOpacity = 0.8,
  }: {
    path: { lat: number; lng: number }[];
    color: string;
    strokeWeight?: number;
    strokeOpacity?: number;
  }) => {
    const map = useMap();
    const polylineRef = useRef<google.maps.Polyline | null>(null);

    useEffect(() => {
      if (!map) return;

      // Clean up existing polyline first
      const currentPolyline = polylineRef.current;
      if (currentPolyline) {
        currentPolyline.setMap(null);
        polylineRef.current = null;
      }

      // Validate and filter coordinates before using them
      const validatedPath = validateCoordinates(path);

      // If no valid path, don't create polyline
      if (validatedPath.length === 0) {
        return;
      }

      // Create polyline with optimized settings for smooth rendering
      const polyline = new google.maps.Polyline({
        path: validatedPath,
        geodesic: true,
        strokeColor: color,
        strokeOpacity: strokeOpacity,
        strokeWeight: strokeWeight,
        // Optimize for smooth rendering
        clickable: false,
        zIndex: 1,
      });

      polyline.setMap(map);
      polylineRef.current = polyline;

      return () => {
        if (polylineRef.current) {
          polylineRef.current.setMap(null);
          polylineRef.current = null;
        }
      };
    }, [map, path, color, strokeWeight, strokeOpacity]);

    return null;
  },
);

// Drawing Polygon component for Google Maps
const GoogleDrawingPolygon = React.memo(
  ({
    path,
    strokeColor,
    fillColor,
    strokeWeight = 2,
    strokeOpacity = 0.8,
    fillOpacity = 0.5,
  }: {
    path: { lat: number; lng: number }[];
    strokeColor: string;
    fillColor: string;
    strokeWeight?: number;
    strokeOpacity?: number;
    fillOpacity?: number;
  }) => {
    const map = useMap();
    const polygonRef = useRef<google.maps.Polygon | null>(null);

    useEffect(() => {
      if (!map) return;

      // Clean up existing polygon first
      const currentPolygon = polygonRef.current;
      if (currentPolygon) {
        currentPolygon.setMap(null);
        polygonRef.current = null;
      }

      // Validate and filter coordinates before using them
      const validatedPath = validateCoordinates(path);

      // If no valid path, don't create polygon
      if (validatedPath.length === 0) {
        return;
      }

      // Create polygon with optimized settings for smooth rendering
      const polygon = new google.maps.Polygon({
        paths: [validatedPath],
        strokeColor: strokeColor,
        strokeOpacity: strokeOpacity,
        strokeWeight: strokeWeight,
        fillColor: fillColor,
        fillOpacity: fillOpacity,
        clickable: false,
        zIndex: 10,
      });

      polygon.setMap(map);
      polygonRef.current = polygon;

      return () => {
        if (polygonRef.current) {
          polygonRef.current.setMap(null);
          polygonRef.current = null;
        }
      };
    }, [
      map,
      path,
      strokeColor,
      fillColor,
      strokeWeight,
      strokeOpacity,
      fillOpacity,
    ]);

    return null;
  },
);

type DrawingRendererProps = {
  shapes: DrawingShape[];
  drawingMode: DrawingMode;
  drawingPoints: DrawingPoint[];
  isDrawingActive: boolean;
  dragStartPoint: DrawingPoint | null;
  dragCurrentPoint: DrawingPoint | null;
  markerData?: { lat: number; lng: number; name?: string; color?: string }[];
};

export const DrawingRenderer = ({
  shapes,
  drawingMode,
  drawingPoints,
  isDrawingActive,
  dragStartPoint,
  dragCurrentPoint,
  markerData = [],
}: DrawingRendererProps) => {
  console.log('DrawingRenderer received shapes:', shapes);
  console.log('DrawingRenderer drawingMode:', drawingMode);
  console.log('DrawingRenderer shapes length:', shapes.length);

  if (shapes.length > 0) {
    shapes.forEach((shape, index) => {
      console.log(`Shape ${index}:`, {
        id: shape.id,
        type: shape.type,
        pointsLength: shape.points.length,
        center: shape.center,
        radius: shape.radius,
        fillColor: shape.fillColor,
        fillOpacity: shape.fillOpacity,
      });
    });
  }

  return (
    <Fragment>
      {/* Drawing Points - Current drawing points */}
      {drawingPoints.map((point, index) => (
        <AdvancedMarker
          key={`drawing-point-${index}`}
          position={point}
          title={`Point ${index + 1}`}
        >
          <Pin
            background="#ff9800"
            glyphColor="#ffffff"
            borderColor="#ffffff"
            scale={0.8}
          />
        </AdvancedMarker>
      ))}

      {/* TRACE Drawing Points - Show numbered points for TRACE */}
      {drawingMode === 'TRACE' &&
        isDrawingActive &&
        drawingPoints.map((point, index) => (
          <AdvancedMarker
            key={`trace-point-${index}`}
            position={point}
          >
            <Pin
              background="#ff9800"
              glyphColor="#ffffff"
              borderColor="#ffffff"
              scale={0.8}
            />
          </AdvancedMarker>
        ))}

      {/* Drawing Lines - Current drawing line */}
      {drawingMode === 'LINE' && drawingPoints.length > 1 && (
        <GoogleDrawingPolyline
          path={drawingPoints}
          color="#ff9800"
          strokeWeight={3}
          strokeOpacity={0.8}
        />
      )}

      {/* LINE Drawing Points - Show numbered points for LINE */}
      {drawingMode === 'LINE' &&
        drawingPoints.map((point, index) => (
          <AdvancedMarker
            key={`line-point-${index}`}
            position={point}
            title={`Line Point ${index + 1}`}
          >
            <Pin
              background="#ff9800"
              glyphColor="#ffffff"
              borderColor="#ffffff"
              scale={0.8}
            />
          </AdvancedMarker>
        ))}

      {/* Drawing Trace - Current drawing trace */}
      {drawingMode === 'TRACE' && drawingPoints.length > 1 && (
        <GoogleDrawingPolyline
          path={drawingPoints}
          color="#ff9800"
          strokeWeight={3}
          strokeOpacity={0.8}
        />
      )}

      {/* Drawing Rectangle Preview - Current drawing rectangle */}
      {drawingMode === 'POLYGON' &&
        isDrawingActive &&
        dragStartPoint &&
        dragCurrentPoint && (
          <GoogleDrawingPolyline
            path={[
              dragStartPoint,
              { lat: dragStartPoint.lat, lng: dragCurrentPoint.lng },
              dragCurrentPoint,
              { lat: dragCurrentPoint.lat, lng: dragStartPoint.lng },
              dragStartPoint, // Close the rectangle
            ]}
            color="#ff9800"
            strokeWeight={3}
            strokeOpacity={0.6}
          />
        )}

      {/* Drawing Circle Preview - Current drawing circle */}
      {drawingMode === 'CIRCULAR' &&
        isDrawingActive &&
        dragStartPoint &&
        dragCurrentPoint && (
          <GoogleDrawingPolyline
            path={(() => {
              const center = dragStartPoint;
              const radius = Math.sqrt(
                Math.pow(dragCurrentPoint.lat - center.lat, 2) +
                  Math.pow(dragCurrentPoint.lng - center.lng, 2),
              );
              const circlePoints: DrawingPoint[] = [];
              // Create 16 points around the circle
              for (let i = 0; i < 16; i++) {
                const angle = (i * 2 * Math.PI) / 16;
                const lat = center.lat + radius * Math.cos(angle);
                const lng = center.lng + radius * Math.sin(angle);
                circlePoints.push({ lat, lng });
              }
              return circlePoints;
            })()}
            color="#ff9800"
            strokeWeight={3}
            strokeOpacity={0.6}
          />
        )}

      {/* Drawing Trace Preview - Current drawing trace */}
      {drawingMode === 'TRACE' &&
        isDrawingActive &&
        drawingPoints.length > 0 && (
          <>
            {/* Show all connected points as polyline (not polygon) */}
            {drawingPoints.length > 1 && (
              <GoogleDrawingPolyline
                path={drawingPoints}
                color="#ff9800"
                strokeWeight={3}
                strokeOpacity={0.6}
              />
            )}
            {/* Show preview line to current mouse position */}
            {dragCurrentPoint && (
              <GoogleDrawingPolyline
                path={[
                  drawingPoints[drawingPoints.length - 1],
                  dragCurrentPoint,
                ]}
                color="#ff9800"
                strokeWeight={2}
                strokeOpacity={0.4}
              />
            )}
          </>
        )}

      {/* Completed Drawing Shapes */}
      {shapes.map((shape) => {
        if (shape.type === 'LINE') {
          return (
            <GoogleDrawingPolyline
              key={shape.id}
              path={shape.points}
              color="#ff9800"
              strokeWeight={4}
              strokeOpacity={0.8}
            />
          );
        } else if (shape.type === 'POLYGON') {
          console.log('Rendering POLYGON shape (Google):', shape);
          return (
            <GoogleDrawingPolygon
              key={shape.id}
              path={shape.points}
              strokeColor="#010f01"
              fillColor={shape.fillColor || '#4caf50'}
              strokeWeight={0.2}
              strokeOpacity={0.8}
              fillOpacity={shape.fillOpacity || 0.3}
            />
          );
        } else if (shape.type === 'TRACE') {
          console.log('Rendering TRACE shape (Google):', shape);
          // For TRACE, render as polygon with proper closing
          const tracePoints = shape.points;
          if (tracePoints.length < 3) {
            // If less than 3 points, render as polyline
            console.log('TRACE has less than 3 points, rendering as polyline');
            return (
              <GoogleDrawingPolyline
                key={shape.id}
                path={tracePoints}
                color="#010f01"
                strokeWeight={0.2}
                strokeOpacity={0.8}
              />
            );
          }

          // Create closed polygon - ensure it's properly closed
          const closedPoints = [...tracePoints];

          // Add the first point at the end to close the polygon
          if (closedPoints.length > 0) {
            const firstPoint = closedPoints[0];
            const lastPoint = closedPoints[closedPoints.length - 1];

            // Only add if not already closed
            if (
              firstPoint.lat !== lastPoint.lat ||
              firstPoint.lng !== lastPoint.lng
            ) {
              closedPoints.push({
                lat: firstPoint.lat,
                lng: firstPoint.lng,
              });
            }
          }

          return (
            <GoogleDrawingPolygon
              key={shape.id}
              path={closedPoints}
              strokeColor="#010f01"
              fillColor={shape.fillColor || '#4caf50'}
              strokeWeight={0.2}
              strokeOpacity={0.8}
              fillOpacity={shape.fillOpacity || 0.3}
            />
          );
        } else if (shape.type === 'CIRCULAR') {
          // For circular shapes, use points directly from API
          return (
            <GoogleDrawingPolygon
              key={shape.id}
              path={shape.points}
              strokeColor="#010f01"
              fillColor={shape.fillColor || '#4caf50'}
              strokeWeight={0.2}
              strokeOpacity={0.8}
              fillOpacity={shape.fillOpacity || 0.3}
            />
          );
        }
        return null;
      })}

      {/* Return line - Draw line from last marker to first marker if shape.return is true and shape is POLYGON, CIRCULAR, or TRACE */}
      {shapes.length > 0 &&
        markerData.length > 1 &&
        shapes[0].return &&
        (shapes[0].type === 'POLYGON' ||
          shapes[0].type === 'CIRCULAR' ||
          shapes[0].type === 'TRACE') && (
          <GoogleDrawingPolyline
            key={`${shapes[0].id}-return`}
            path={[markerData[markerData.length - 1], markerData[0]]}
            color="#ff9800"
            strokeWeight={4}
            strokeOpacity={0.8}
          />
        )}
    </Fragment>
  );
};
