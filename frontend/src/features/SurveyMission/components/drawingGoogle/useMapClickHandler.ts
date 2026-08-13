import { useCallback } from 'react';

import { DrawingMode, DrawingPoint, DrawingShape } from './types';

type UseMapClickHandlerProps = {
  drawingMode: DrawingMode;
  drawingPoints: DrawingPoint[];
  isDrawingActive: boolean;
  dragStartPoint: DrawingPoint | null;
  setDrawingPoints: (points: DrawingPoint[]) => void;
  setCurrentShape: (shape: DrawingShape | null) => void;
  setDrawingMode: (mode: DrawingMode) => void;
  setIsDrawingActive: (isActive: boolean) => void;
  setDragStartPoint: (point: DrawingPoint | null) => void;
  setDragCurrentPoint: (point: DrawingPoint | null) => void;
};

export const useMapClickHandler = ({
  drawingMode,
  drawingPoints,
  isDrawingActive,
  dragStartPoint,
  setDrawingPoints,
  setCurrentShape,
  setDrawingMode,
  setIsDrawingActive,
  setDragStartPoint,
  setDragCurrentPoint,
}: UseMapClickHandlerProps) => {
  const handleMapClick = useCallback(
    (event: google.maps.MapMouseEvent) => {
      if (drawingMode === 'NONE' || !event.latLng) {
        return;
      }

      const lat = event.latLng.lat();
      const lng = event.latLng.lng();
      const newPoint: DrawingPoint = {
        lat,
        lng,
      };

      if (drawingMode === 'LINE') {
        // Clear current shape when starting new line
        if (drawingPoints.length === 0) {
          setCurrentShape(null);
        }
        const updatedPoints = [...drawingPoints, newPoint];
        setDrawingPoints(updatedPoints);

        // Create or update line shape with all points (even with 1 point for real-time saving)
        if (updatedPoints.length >= 1) {
          const newShape: DrawingShape = {
            id: `line-${Date.now()}`,
            type: 'LINE',
            points: updatedPoints,
          };

          setCurrentShape(newShape);
        }
      } else if (drawingMode === 'POLYGON') {
        // For polygon, we'll use a different approach - double click to start/end
        if (!isDrawingActive) {
          // Start drawing mode - first click
          setCurrentShape(null); // Clear current shape when starting new polygon
          setIsDrawingActive(true);
          setDragStartPoint(newPoint);
          setDragCurrentPoint(newPoint);
        } else {
          // Complete the rectangle - second click
          if (dragStartPoint) {
            const rectanglePoints = [
              dragStartPoint,
              { lat: dragStartPoint.lat, lng: newPoint.lng },
              newPoint,
              { lat: newPoint.lat, lng: dragStartPoint.lng },
            ];

            const newShape: DrawingShape = {
              id: `polygon-${Date.now()}`,
              type: 'POLYGON',
              points: rectanglePoints,
              fillColor: '#4caf50',
              fillOpacity: 0.5,
            };

            setCurrentShape(newShape);
            setIsDrawingActive(false);
            setDragStartPoint(null);
            setDragCurrentPoint(null);
            // Auto-exit drawing mode after completing the polygon
            setDrawingMode('NONE');
          }
        }
      } else if (drawingMode === 'CIRCULAR') {
        // For circular, we'll use the same approach as polygon
        if (!isDrawingActive) {
          // Start drawing mode - first click
          setCurrentShape(null); // Clear current shape when starting new circle
          setIsDrawingActive(true);
          setDragStartPoint(newPoint);
          setDragCurrentPoint(newPoint);
        } else {
          // Complete the circle - second click
          if (dragStartPoint) {
            const center = dragStartPoint;
            const radius = Math.sqrt(
              Math.pow(newPoint.lat - center.lat, 2) +
                Math.pow(newPoint.lng - center.lng, 2),
            );

            // Create 16 points around the circle
            const circlePoints: DrawingPoint[] = [];
            for (let i = 0; i < 16; i++) {
              const angle = (i * 2 * Math.PI) / 16;
              const lat = center.lat + radius * Math.cos(angle);
              const lng = center.lng + radius * Math.sin(angle);
              circlePoints.push({ lat, lng });
            }

            const newShape: DrawingShape = {
              id: `circle-${Date.now()}`,
              type: 'CIRCULAR',
              points: circlePoints,
              center,
              radius,
              fillColor: '#4caf50',
              fillOpacity: 0.5,
            };

            setCurrentShape(newShape);
            setIsDrawingActive(false);
            setDragStartPoint(null);
            setDragCurrentPoint(null);
            // Auto-exit drawing mode after completing the circle
            setDrawingMode('NONE');
          }
        }
      } else if (drawingMode === 'TRACE') {
        // For trace, add points continuously
        if (!isDrawingActive) {
          // Start drawing mode - first click
          setCurrentShape(null); // Clear current shape when starting new trace
          setIsDrawingActive(true);
          setDrawingPoints([newPoint]);
          setDragStartPoint(newPoint);
          setDragCurrentPoint(newPoint);
        } else {
          // Add new point to trace
          const updatedPoints = [...drawingPoints, newPoint];
          setDrawingPoints(updatedPoints);
          setDragCurrentPoint(newPoint);

          // Update currentShape in real-time when we have at least 2 points
          if (updatedPoints.length >= 2) {
            const newShape: DrawingShape = {
              id: `trace-${Date.now()}`,
              type: 'TRACE',
              points: updatedPoints,
              fillColor: '#4caf50',
              fillOpacity: 0.5,
            };

            setCurrentShape(newShape);
          }
        }
      }
    },
    [
      drawingMode,
      drawingPoints,
      isDrawingActive,
      dragStartPoint,
      setDrawingPoints,
      setCurrentShape,
      setDrawingMode,
      setIsDrawingActive,
      setDragStartPoint,
      setDragCurrentPoint,
    ],
  );

  const handleMapRightClick = useCallback(() => {
    if (drawingMode === 'LINE' && drawingPoints.length >= 2) {
      // Complete the line drawing
      setDrawingPoints([]);
      setDrawingMode('NONE');
    } else if (
      drawingMode === 'TRACE' &&
      isDrawingActive &&
      drawingPoints.length >= 2
    ) {
      // Complete the trace by connecting first and last points
      const closedPoints = [...drawingPoints];

      const newShape: DrawingShape = {
        id: `trace-${Date.now()}`,
        type: 'TRACE',
        points: closedPoints,
        fillColor: '#4caf50',
        fillOpacity: 0.5,
      };

      setCurrentShape(newShape);
      setIsDrawingActive(false);
      setDragStartPoint(null);
      setDragCurrentPoint(null);
      setDrawingPoints([]);
      // Auto-exit drawing mode after completing the trace
      setDrawingMode('NONE');
    }
  }, [
    drawingMode,
    isDrawingActive,
    drawingPoints,
    setCurrentShape,
    setIsDrawingActive,
    setDragStartPoint,
    setDragCurrentPoint,
    setDrawingPoints,
    setDrawingMode,
  ]);

  return {
    handleMapClick,
    handleMapRightClick,
  };
};
