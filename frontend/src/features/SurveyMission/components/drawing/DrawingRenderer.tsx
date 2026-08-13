import React, { JSX } from 'react';
import { MapMarker, Polygon, Polyline } from 'react-kakao-maps-sdk';

import { DrawingShape, DrawingPoint, DrawingMode } from './types';
import { generateCirclePoints } from './utils';

type DrawingRendererProps = {
  shapes: DrawingShape[];
  drawingMode: DrawingMode;
  drawingPoints: DrawingPoint[];
  isDrawingActive: boolean;
  dragStartPoint: DrawingPoint | null;
  dragCurrentPoint: DrawingPoint | null;
  markerData?: { lat: number; lng: number; name?: string; color?: string }[];
};

const smallMarkerImage = (color: string) => ({
  src: `data:image/svg+xml;utf8,<svg width='16' height='16' xmlns='http://www.w3.org/2000/svg'><circle cx='8' cy='8' r='7' fill='${encodeURIComponent(
    color,
  )}' stroke='white' stroke-width='2'/></svg>`,
  size: { width: 16, height: 16 },
  options: { offset: { x: 8, y: 8 } },
});

export const DrawingRenderer = ({
  shapes,
  drawingMode,
  drawingPoints,
  isDrawingActive,
  dragStartPoint,
  dragCurrentPoint,
  markerData = [],
}: DrawingRendererProps): JSX.Element => {
  return (
    <>
      {/* Drawing Points - Current drawing points */}
      {drawingPoints.map((point, index) => (
        <MapMarker
          key={`drawing-point-${index}`}
          position={point}
          image={smallMarkerImage('#ff9800')} // Orange for drawing points
          title={`Point ${index + 1}`}
        />
      ))}

      {/* TRACE Drawing Points - Show numbered points for TRACE */}
      {drawingMode === 'TRACE' &&
        isDrawingActive &&
        drawingPoints.map((point, index) => (
          <MapMarker
            key={`trace-point-${index}`}
            position={point}
            image={smallMarkerImage('#ff9800')} // Orange for trace points
            title={`Trace Point ${index + 1}`}
          />
        ))}

      {/* Drawing Lines - Current drawing line */}
      {drawingMode === 'LINE' && drawingPoints.length > 1 && (
        <Polyline
          path={drawingPoints}
          strokeWeight={3}
          strokeColor="#ff9800"
          strokeOpacity={0.8}
          strokeStyle="solid"
        />
      )}

      {/* LINE Drawing Points - Show numbered points for LINE */}
      {drawingMode === 'LINE' &&
        drawingPoints.map((point, index) => (
          <MapMarker
            key={`line-point-${index}`}
            position={point}
            image={smallMarkerImage('#ff9800')} // Orange for line points
            title={`Line Point ${index + 1}`}
          />
        ))}

      {/* Drawing Trace - Current drawing trace */}
      {drawingMode === 'TRACE' && drawingPoints.length > 1 && (
        <Polyline
          path={drawingPoints}
          strokeWeight={3}
          strokeColor="#ff9800"
          strokeOpacity={0.8}
          strokeStyle="solid"
        />
      )}

      {/* Drawing Rectangle Preview - Current drawing rectangle */}
      {drawingMode === 'POLYGON' &&
        isDrawingActive &&
        dragStartPoint &&
        dragCurrentPoint && (
          <Polyline
            path={[
              dragStartPoint,
              { lat: dragStartPoint.lat, lng: dragCurrentPoint.lng },
              dragCurrentPoint,
              { lat: dragCurrentPoint.lat, lng: dragStartPoint.lng },
              dragStartPoint, // Close the rectangle
            ]}
            strokeWeight={3}
            strokeColor="#ff9800"
            strokeOpacity={0.6}
            strokeStyle="dashed"
          />
        )}

      {/* Drawing Circle Preview - Current drawing circle */}
      {drawingMode === 'CIRCULAR' &&
        isDrawingActive &&
        dragStartPoint &&
        dragCurrentPoint && (
          <Polyline
            path={(() => {
              const center = dragStartPoint;
              const radius = Math.sqrt(
                Math.pow(dragCurrentPoint.lat - center.lat, 2) +
                  Math.pow(dragCurrentPoint.lng - center.lng, 2),
              );
              return generateCirclePoints(center, radius);
            })()}
            strokeWeight={3}
            strokeColor="#ff9800"
            strokeOpacity={0.6}
            strokeStyle="dashed"
          />
        )}

      {/* Drawing Trace Preview - Current drawing trace */}
      {drawingMode === 'TRACE' &&
        isDrawingActive &&
        drawingPoints.length > 0 && (
          <>
            {/* Show all connected points */}
            {drawingPoints.length > 1 && (
              <Polyline
                path={drawingPoints}
                strokeWeight={3}
                strokeColor="#ff9800"
                strokeOpacity={0.6}
                strokeStyle="dashed"
              />
            )}
            {/* Show preview line to current mouse position */}
            {dragCurrentPoint && (
              <Polyline
                path={[
                  drawingPoints[drawingPoints.length - 1],
                  dragCurrentPoint,
                ]}
                strokeWeight={2}
                strokeColor="#ff9800"
                strokeOpacity={0.4}
                strokeStyle="dashed"
              />
            )}
          </>
        )}

      {/* Completed Drawing Shapes */}
      {shapes.map((shape) => {
        if (shape.type === 'LINE') {
          return (
            <Polyline
              key={shape.id}
              path={shape.points}
              strokeWeight={4}
              strokeColor="#ff9800"
              strokeOpacity={0.8}
              strokeStyle="solid"
            />
          );
        } else if (shape.type === 'POLYGON') {
          return (
            <Polygon
              key={shape.id}
              path={shape.points}
              strokeWeight={0.2}
              strokeColor="#010f01"
              strokeOpacity={0.8}
              strokeStyle="solid"
              fillColor={shape.fillColor || '#4caf50'}
              fillOpacity={shape.fillOpacity || 0.3}
              zIndex={10}
            />
          );
        } else if (shape.type === 'TRACE') {
          const MAX_POLYGON_POINTS = 1000;
          const tracePoints = shape.points;
          
          if (tracePoints.length > MAX_POLYGON_POINTS) {
            return (
              <Polyline
                key={shape.id}
                path={tracePoints}
                strokeWeight={0.2}
                strokeColor="#010f01"
                strokeOpacity={0.8}
                strokeStyle="solid"
              />
            );
          }
          
          return (
            <Polygon
              key={shape.id}
              path={tracePoints}
              strokeWeight={0.2}
              strokeColor="#010f01"
              strokeOpacity={0.8}
              strokeStyle="solid"
              fillColor={shape.fillColor || '#4caf50'}
              fillOpacity={shape.fillOpacity || 0.3}
              zIndex={10}
            />
          );
        } else if (shape.type === 'CIRCULAR') {
          // For circular shapes, use points directly from API
          return (
            <Polygon
              key={shape.id}
              path={shape.points}
              strokeWeight={0.2}
              strokeColor="#010f01"
              strokeOpacity={0.8}
              strokeStyle="solid"
              fillColor={shape.fillColor || '#4caf50'}
              fillOpacity={shape.fillOpacity || 0.3}
              zIndex={10}
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
          <Polyline
            key={`${shapes[0].id}-return`}
            path={[markerData[markerData.length - 1], markerData[0]]}
            strokeWeight={4}
            strokeColor="#ff9800"
            strokeOpacity={0.8}
          />
        )}
    </>
  );
};
