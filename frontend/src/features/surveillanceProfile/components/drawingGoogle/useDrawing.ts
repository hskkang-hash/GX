import { useState, useCallback } from 'react';

import { useDrawingModeStore } from '@/features/surveillanceProfile/stores/drawingModeStore';
import {
  DrawingMode,
  DrawingPoint,
  DrawingShape,
  DrawingState,
  DrawingActions,
} from './types';
import {
  convertPolygonToCircular,
  convertCircularToPolygon,
  canConvertDirectly,
} from './utils';

export const useDrawing = (): DrawingState & DrawingActions => {
  const [mode, setMode] = useState<DrawingMode>('NONE');
  const [points, setPoints] = useState<DrawingPoint[]>([]);
  const [currentShape, setCurrentShape] = useState<DrawingShape | null>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [isDrawingActive, setIsDrawingActive] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStartPoint, setDragStartPoint] = useState<DrawingPoint | null>(
    null,
  );
  const [dragCurrentPoint, setDragCurrentPoint] = useState<DrawingPoint | null>(
    null,
  );

  // Get clearWaypointsPreview from store
  const clearWaypointsPreview = useDrawingModeStore(
    (state) => state.clearWaypointsPreview,
  );

  const clearDrawing = useCallback(() => {
    setPoints([]);
    setCurrentShape(null);
    setMode('NONE');
    setIsDrawing(false);
    setIsDragging(false);
    setDragStartPoint(null);
    setDragCurrentPoint(null);
    setIsDrawingActive(false);
    clearWaypointsPreview(); // Clear waypointsPreview when clearing drawing
  }, [clearWaypointsPreview]);

  const convertShape = useCallback(
    (fromType: DrawingMode, toType: DrawingMode) => {
      if (!currentShape || !canConvertDirectly(fromType, toType)) {
        return;
      }

      try {
        let newShape: DrawingShape;

        if (fromType === 'POLYGON' && toType === 'CIRCULAR') {
          newShape = convertPolygonToCircular(currentShape);
        } else if (fromType === 'CIRCULAR' && toType === 'POLYGON') {
          newShape = convertCircularToPolygon(currentShape);
        } else {
          return;
        }

        setCurrentShape(newShape);
        setMode(toType);
        setPoints([]);
        setIsDrawingActive(false);
        setDragStartPoint(null);
        setDragCurrentPoint(null);
      } catch (error) {
        console.error('Error converting shape:', error);
      }
    },
    [currentShape],
  );

  const handleModeChange = useCallback(
    (newMode: DrawingMode) => {
      // Clear waypointsPreview when changing drawing mode
      clearWaypointsPreview();

      // Handle mode switching logic FIRST before clearing state
      if (newMode === 'NONE') {
        // Only clear drawing state, keep currentShape in store
        setPoints([]);
        setMode('NONE');
        setIsDrawing(false);
        setIsDragging(false);
        setDragStartPoint(null);
        setDragCurrentPoint(null);
        setIsDrawingActive(false);
        return;
      }

      // Toggle LINE mode - if already in LINE mode, turn it off
      if (newMode === 'LINE' && mode === 'LINE') {
        setPoints([]);
        setMode('NONE');
        setIsDrawing(false);
        setIsDragging(false);
        setDragStartPoint(null);
        setDragCurrentPoint(null);
        setIsDrawingActive(false);
        return;
      }

      // If switching from Polygon to Circular, keep the same shape but change type
      if (
        currentShape &&
        currentShape.type === 'POLYGON' &&
        newMode === 'CIRCULAR'
      ) {
        console.log('Converting Polygon to Circular', currentShape);
        convertShape('POLYGON', 'CIRCULAR');
        return;
      }

      // If switching from Circular to Polygon, keep the same shape but change type
      if (
        currentShape &&
        currentShape.type === 'CIRCULAR' &&
        newMode === 'POLYGON' &&
        currentShape.center &&
        currentShape.radius
      ) {
        convertShape('CIRCULAR', 'POLYGON');
        return;
      }

      // For other mode switches (LINE, TRACE, or switching to POLYGON/CIRCULAR from LINE/TRACE)
      // Only clear if switching to a different drawing mode, not if just changing mode
      setPoints([]);
      // Only clear current shape if switching to a completely different drawing mode
      if (currentShape && currentShape.type !== newMode) {
        setCurrentShape(null);
      }
      setMode(newMode);
      setIsDrawing(true);
      setIsDragging(false);
      setDragStartPoint(null);
      setDragCurrentPoint(null);
      // For TRACE mode, don't set isDrawingActive to false initially
      // It will be set to true on first click
      if (newMode !== 'TRACE') {
        setIsDrawingActive(false);
      }
    },
    [mode, currentShape, convertShape, clearWaypointsPreview],
  );

  return {
    // State
    mode,
    points,
    currentShape,
    isDrawing,
    isDrawingActive,
    isDragging,
    dragStartPoint,
    dragCurrentPoint,

    // Actions
    setMode: handleModeChange,
    setPoints,
    setCurrentShape,
    setIsDrawing,
    setIsDrawingActive,
    setIsDragging,
    setDragStartPoint,
    setDragCurrentPoint,
    clearDrawing,
  };
};
