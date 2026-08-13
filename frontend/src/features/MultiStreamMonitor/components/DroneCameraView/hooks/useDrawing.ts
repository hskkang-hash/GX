import { useRef, useCallback, useState, useEffect } from 'react';

import { DrawingPath, DrawingState } from '../types';

interface UseDrawingProps {
  streamId: string;
  userId: string;
  dimensions: { width: number; height: number };
  sendDrawingMessage: (message: any) => void;
  redrawAllPaths: () => void;
  canvasRef?: React.RefObject<HTMLCanvasElement | null>;
}

export const useDrawing = ({
  streamId,
  userId,
  dimensions,
  sendDrawingMessage,
  redrawAllPaths,
  canvasRef,
}: UseDrawingProps) => {
  const drawingStateRef = useRef<DrawingState>({
    isDrawing: false,
    lastX: 0,
    lastY: 0,
  });
  const currentPathRef = useRef<DrawingPath | null>(null);
  const animationFrameRef = useRef<number>();
  const shapeStartPointRef = useRef<{ x: number; y: number } | null>(null);
  const drawingStorageRef = useRef<Map<string, DrawingPath[]>>(new Map());

  const [brushSize, setBrushSize] = useState(3);
  const [brushColor, setBrushColor] = useState('#ff0000');
  const [drawingMode, setDrawingMode] = useState<'pen' | 'eraser' | 'shape'>(
    'pen',
  );
  const [shapeType, setShapeType] = useState<
    'rectangle' | 'circle' | 'oval' | 'line'
  >('rectangle');

  // Update canvas context when brush settings change
  useEffect(() => {
    const canvas =
      canvasRef?.current ||
      (document.querySelector('canvas[style*="z-index"]') as HTMLCanvasElement);
    const context = canvas?.getContext('2d');
    if (!context) return;

    console.log('🎨 Updating canvas context in useDrawing:', {
      mode: drawingMode,
      color: brushColor,
      size: brushSize,
    });

    if (drawingMode === 'pen' || drawingMode === 'shape') {
      context.globalCompositeOperation = 'source-over';
      context.strokeStyle = brushColor;
    } else {
      context.globalCompositeOperation = 'destination-out';
    }
    context.lineWidth = brushSize;
    context.lineCap = 'round';
    context.lineJoin = 'round';
  }, [drawingMode, brushColor, brushSize, canvasRef]);

  // Redraw canvas when drawing mode changes to ensure proper display
  useEffect(() => {
    // Small delay to ensure canvas context is updated
    const timer = setTimeout(() => {
      redrawAllPaths();
    }, 10);
    return () => clearTimeout(timer);
  }, [drawingMode, brushColor, brushSize, redrawAllPaths]);

  // Get stored drawings for this stream
  const getStoredDrawings = useCallback(() => {
    return drawingStorageRef.current.get(streamId) || [];
  }, [streamId]);

  // Save current drawings
  const saveDrawings = useCallback(
    (paths: DrawingPath[]) => {
      drawingStorageRef.current.set(streamId, paths);
    },
    [streamId],
  );

  // Convert canvas coordinates to percentage
  const pixelToPercentage = useCallback(
    (x: number, y: number) => {
      if (!dimensions.width || !dimensions.height) return { x: 0, y: 0 };
      return {
        x: (x / dimensions.width) * 100,
        y: (y / dimensions.height) * 100,
      };
    },
    [dimensions],
  );

  // Convert percentage coordinates to canvas pixels
  const percentageToPixel = useCallback(
    (x: number, y: number) => {
      if (!dimensions.width || !dimensions.height) return { x: 0, y: 0 };
      return {
        x: (x / 100) * dimensions.width,
        y: (y / 100) * dimensions.height,
      };
    },
    [dimensions],
  );

  // Get canvas coordinates
  const getCanvasCoordinates = useCallback(
    (
      e:
        | React.MouseEvent<HTMLCanvasElement>
        | React.TouchEvent<HTMLCanvasElement>,
    ) => {
      const rect = (
        e.currentTarget as HTMLCanvasElement
      ).getBoundingClientRect();

      let clientX, clientY;
      if ('touches' in e && e.touches.length > 0) {
        clientX = e.touches[0].clientX;
        clientY = e.touches[0].clientY;
      } else if ('clientX' in e) {
        clientX = e.clientX;
        clientY = e.clientY;
      } else {
        return { x: 0, y: 0 };
      }

      const x = clientX - rect.left;
      const y = clientY - rect.top;

      return { x, y };
    },
    [],
  );

  // Draw temporary shape preview
  const drawTemporaryShape = useCallback(
    (
      startPoint: { x: number; y: number },
      currentPoint: { x: number; y: number },
    ) => {
      const startX = startPoint.x;
      const startY = startPoint.y;
      const currentX = currentPoint.x;
      const currentY = currentPoint.y;

      // Use canvasRef if available, otherwise fallback to querySelector
      const canvas =
        canvasRef?.current ||
        (document.querySelector(
          'canvas[style*="z-index"]',
        ) as HTMLCanvasElement);
      const context = canvas?.getContext('2d');
      if (!context || !canvas) return;

      // Get all existing drawings and redraw them
      const drawings = getStoredDrawings();

      // Clear canvas
      context.clearRect(0, 0, canvas.width, canvas.height);

      // Redraw all existing drawings
      drawings.forEach((path) => {
        context.save();

        if (path.mode === 'draw' || path.mode === 'shape') {
          context.globalCompositeOperation = 'source-over';
          context.strokeStyle = path.color;
        } else {
          context.globalCompositeOperation = 'destination-out';
        }

        context.lineWidth = path.lineWidth;
        context.lineCap = 'round';
        context.lineJoin = 'round';

        if (path.userId && path.userId !== userId) {
          context.globalAlpha = 0.8;
        }

        if (path.mode === 'shape' && path.startPoint && path.endPoint) {
          const startPixel = percentageToPixel(
            path.startPoint.x,
            path.startPoint.y,
          );
          const endPixel = percentageToPixel(path.endPoint.x, path.endPoint.y);

          context.beginPath();

          switch (path.shapeType) {
            case 'rectangle': {
              const width = endPixel.x - startPixel.x;
              const height = endPixel.y - startPixel.y;
              context.strokeRect(startPixel.x, startPixel.y, width, height);
              break;
            }
            case 'circle': {
              const centerX = (startPixel.x + endPixel.x) / 2;
              const centerY = (startPixel.y + endPixel.y) / 2;
              const radius =
                Math.sqrt(
                  Math.pow(endPixel.x - startPixel.x, 2) +
                    Math.pow(endPixel.y - startPixel.y, 2),
                ) / 2;
              context.arc(centerX, centerY, radius, 0, 2 * Math.PI);
              context.stroke();
              break;
            }
            case 'oval': {
              const ovalCenterX = (startPixel.x + endPixel.x) / 2;
              const ovalCenterY = (startPixel.y + endPixel.y) / 2;
              const radiusX = Math.abs(endPixel.x - startPixel.x) / 2;
              const radiusY = Math.abs(endPixel.y - startPixel.y) / 2;
              context.ellipse(
                ovalCenterX,
                ovalCenterY,
                radiusX,
                radiusY,
                0,
                0,
                2 * Math.PI,
              );
              context.stroke();
              break;
            }
            case 'line': {
              context.moveTo(startPixel.x, startPixel.y);
              context.lineTo(endPixel.x, endPixel.y);
              context.stroke();
              break;
            }
          }
        } else if (path.points.length > 0) {
          context.beginPath();
          const firstPixel = percentageToPixel(
            path.points[0].x,
            path.points[0].y,
          );
          context.moveTo(firstPixel.x, firstPixel.y);

          for (let i = 1; i < path.points.length; i++) {
            const pixel = percentageToPixel(path.points[i].x, path.points[i].y);
            context.lineTo(pixel.x, pixel.y);
          }
          context.stroke();
        }

        context.restore();
      });

      // Reset context for temporary shape
      context.globalCompositeOperation = 'source-over';
      context.strokeStyle = brushColor;
      context.lineWidth = brushSize;
      context.globalAlpha = 0.7;
      context.setLineDash([]); // Remove dashed lines for solid shapes

      context.beginPath();
      switch (shapeType) {
        case 'rectangle': {
          const width = currentX - startX;
          const height = currentY - startY;
          context.strokeRect(startX, startY, width, height);
          break;
        }
        case 'circle': {
          const centerX = (startX + currentX) / 2;
          const centerY = (startY + currentY) / 2;
          const radius =
            Math.sqrt(
              Math.pow(currentX - startX, 2) + Math.pow(currentY - startY, 2),
            ) / 2;
          context.arc(centerX, centerY, radius, 0, 2 * Math.PI);
          context.stroke();
          break;
        }
        case 'oval': {
          const ovalCenterX = (startX + currentX) / 2;
          const ovalCenterY = (startY + currentY) / 2;
          const radiusX = Math.abs(currentX - startX) / 2;
          const radiusY = Math.abs(currentY - startY) / 2;
          context.ellipse(
            ovalCenterX,
            ovalCenterY,
            radiusX,
            radiusY,
            0,
            0,
            2 * Math.PI,
          );
          context.stroke();
          break;
        }
        case 'line': {
          context.moveTo(startX, startY);
          context.lineTo(currentX, currentY);
          context.stroke();
          break;
        }
      }

      context.restore();
    },
    [brushColor, brushSize, shapeType, redrawAllPaths],
  );

  // Drawing functions
  const startDrawing = useCallback(
    (x: number, y: number) => {
      if (drawingMode === 'shape') {
        const startPoint = { x, y };
        shapeStartPointRef.current = startPoint;
        drawingStateRef.current = {
          isDrawing: true,
          lastX: x,
          lastY: y,
        };
      } else {
        const percentageCoords = pixelToPercentage(x, y);
        currentPathRef.current = {
          points: [percentageCoords],
          color: drawingMode === 'eraser' ? 'transparent' : brushColor,
          lineWidth: brushSize,
          mode: drawingMode === 'eraser' ? 'erase' : 'draw',
          userId: String(userId),
          timestamp: Date.now(),
        };

        drawingStateRef.current = {
          isDrawing: true,
          lastX: x,
          lastY: y,
        };
      }
    },
    [brushColor, brushSize, drawingMode, userId, pixelToPercentage],
  );

  const draw = useCallback(
    (x: number, y: number) => {
      if (!drawingStateRef.current.isDrawing) return;

      if (drawingMode === 'shape') {
        if (shapeStartPointRef.current) {
          drawTemporaryShape(shapeStartPointRef.current, { x, y });
        }
        return;
      }

      // Use canvasRef if available, otherwise fallback to querySelector
      const canvas =
        canvasRef?.current ||
        (document.querySelector(
          'canvas[style*="z-index"]',
        ) as HTMLCanvasElement);
      const context = canvas?.getContext('2d');
      if (!context) return;

      // Ensure context is set with current brush settings
      if (drawingMode === 'eraser') {
        context.globalCompositeOperation = 'destination-out';
      } else {
        context.globalCompositeOperation = 'source-over';
        context.strokeStyle = brushColor;
      }
      context.lineWidth = brushSize;
      context.lineCap = 'round';
      context.lineJoin = 'round';

      const percentageCoords = pixelToPercentage(x, y);
      if (currentPathRef.current) {
        currentPathRef.current.points.push(percentageCoords);
      }

      context.beginPath();
      context.moveTo(
        drawingStateRef.current.lastX,
        drawingStateRef.current.lastY,
      );
      context.lineTo(x, y);
      context.stroke();

      drawingStateRef.current.lastX = x;
      drawingStateRef.current.lastY = y;
    },
    [drawingMode, drawTemporaryShape, pixelToPercentage, brushColor, brushSize],
  );

  const endDrawing = useCallback(
    (x?: number, y?: number) => {
      if (!drawingStateRef.current.isDrawing) return;

      if (
        drawingMode === 'shape' &&
        shapeStartPointRef.current &&
        x !== undefined &&
        y !== undefined
      ) {
        const startPoint = shapeStartPointRef.current;
        const endPoint = { x, y };

        const startPercentage = pixelToPercentage(startPoint.x, startPoint.y);
        const endPercentage = pixelToPercentage(endPoint.x, endPoint.y);

        let elementData: any = {};
        let elementType: string = '';

        switch (shapeType) {
          case 'rectangle':
            elementType = 'rectangle';
            elementData = {
              x: Math.min(startPoint.x, endPoint.x),
              y: Math.min(startPoint.y, endPoint.y),
              width: Math.abs(endPoint.x - startPoint.x),
              height: Math.abs(endPoint.y - startPoint.y),
              color: brushColor,
              lineWidth: brushSize,
            };
            break;
          case 'circle':
            const centerX = (startPoint.x + endPoint.x) / 2;
            const centerY = (startPoint.y + endPoint.y) / 2;
            const radius =
              Math.sqrt(
                Math.pow(endPoint.x - startPoint.x, 2) +
                  Math.pow(endPoint.y - startPoint.y, 2),
              ) / 2;
            elementType = 'circle';
            elementData = {
              cx: centerX,
              cy: centerY,
              radius: radius,
              color: brushColor,
              width: brushSize,
            };
            break;
          case 'oval':
            const ovalCenterX = (startPoint.x + endPoint.x) / 2;
            const ovalCenterY = (startPoint.y + endPoint.y) / 2;
            const radiusX = Math.abs(endPoint.x - startPoint.x) / 2;
            const radiusY = Math.abs(endPoint.y - startPoint.y) / 2;
            elementType = 'oval';
            elementData = {
              cx: ovalCenterX,
              cy: ovalCenterY,
              radiusX: radiusX,
              radiusY: radiusY,
              color: brushColor,
              width: brushSize,
            };
            break;
          case 'line':
            elementType = 'line';
            elementData = {
              points: [
                [startPoint.x, startPoint.y],
                [endPoint.x, endPoint.y],
              ],
              points_percentage: [
                [startPercentage.x, startPercentage.y],
                [endPercentage.x, endPercentage.y],
              ],
              color: brushColor,
              width: brushSize,
            };
            break;
        }

        sendDrawingMessage({
          type: 'draw_element',
          element_type: elementType as 'line' | 'circle' | 'rectangle' | 'oval',
          element_data: {
            ...elementData,
            startPoint: { x: startPoint.x, y: startPoint.y },
            endPoint: { x: endPoint.x, y: endPoint.y },
            start_point: [startPercentage.x, startPercentage.y],
            end_point: [endPercentage.x, endPercentage.y],
            stream_id: streamId,
            drone_code: streamId, // Use streamId as drone_code for consistency
            session_id: '1',
            user_id: String(userId),
            canvas_width: dimensions.width,
            canvas_height: dimensions.height,
          },
        });

        const drawings = getStoredDrawings();
        const newPath: DrawingPath = {
          points: [],
          color: brushColor,
          lineWidth: brushSize,
          mode: 'shape',
          userId: String(userId),
          timestamp: Date.now(),
          shapeType: shapeType,
          startPoint: startPercentage,
          endPoint: endPercentage,
        };
        drawings.push(newPath);
        saveDrawings(drawings);
      } else if (
        drawingMode !== 'shape' &&
        currentPathRef.current &&
        currentPathRef.current.points.length > 1
      ) {
        const serverPoints = currentPathRef.current.points.map((point) => {
          const pixel = percentageToPixel(point.x, point.y);
          return [pixel.x, pixel.y];
        });

        const percentagePoints = currentPathRef.current.points.map((point) => [
          point.x,
          point.y,
        ]);

        sendDrawingMessage({
          type: 'draw_element',
          element_type: 'line',
          element_data: {
            points: serverPoints,
            points_percentage: percentagePoints,
            color: currentPathRef.current.color,
            width: currentPathRef.current.lineWidth,
            stream_id: streamId,
            drone_code: streamId, // Use streamId as drone_code for consistency
            session_id: '1',
            user_id: String(userId),
            canvas_width: dimensions.width,
            canvas_height: dimensions.height,
          },
        });

        const drawings = getStoredDrawings();
        drawings.push(currentPathRef.current);
        saveDrawings(drawings);
      }

      currentPathRef.current = null;
      shapeStartPointRef.current = null;
      drawingStateRef.current.isDrawing = false;

      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    },
    [
      drawingMode,
      shapeType,
      brushColor,
      brushSize,
      sendDrawingMessage,
      getStoredDrawings,
      saveDrawings,
      streamId,
      userId,
      dimensions.width,
      dimensions.height,
      pixelToPercentage,
      percentageToPixel,
    ],
  );

  const clearCanvas = useCallback(() => {
    const canvas =
      canvasRef?.current ||
      (document.querySelector('canvas[style*="z-index"]') as HTMLCanvasElement);
    const context = canvas?.getContext('2d');
    if (!context || !canvas) return;

    console.log('🗑️ Clearing canvas and local storage for stream:', streamId);
    context.clearRect(0, 0, canvas.width, canvas.height);
    saveDrawings([]);

    sendDrawingMessage({
      type: 'clear_all',
      stream_id: streamId,
      drone_code: streamId,
      session_id: '1',
      sessionId: '1',
      userId: String(userId),
      element_data: {
        stream_id: streamId,
        drone_code: streamId, // Use streamId as drone_code for consistency
        session_id: '1',
        user_id: String(userId),
      },
    });
    console.log('📤 Sent clear_all message for stream:', streamId);
  }, [saveDrawings, sendDrawingMessage, streamId, userId, canvasRef]);

  return {
    drawingStateRef,
    currentPathRef,
    animationFrameRef,
    shapeStartPointRef,
    drawingStorageRef,
    brushSize,
    setBrushSize,
    brushColor,
    setBrushColor,
    drawingMode,
    setDrawingMode,
    shapeType,
    setShapeType,
    getStoredDrawings,
    saveDrawings,
    pixelToPercentage,
    percentageToPixel,
    getCanvasCoordinates,
    drawTemporaryShape,
    startDrawing,
    draw,
    endDrawing,
    clearCanvas,
  };
};
