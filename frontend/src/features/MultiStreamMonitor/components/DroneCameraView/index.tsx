import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { ToastTopHelper } from 'rj-core';

import API, { endpoint } from '@/services/API';

import { useDynamicStream } from '../../hooks/useDynamicStream';
import { useWebRTC } from '../../hooks/useWebRTC';
import { StreamControls } from '../StreamControls';
import { ActionControls } from './components/ActionControls';
import { CaptureFlash } from './components/CaptureFlash';
import { DrawingModal } from './components/DrawingModal';
import { RecordingOverlay } from './components/RecordingOverlay';
import { StatusInfo } from './components/StatusInfo';
import { useDrawing } from './hooks/useDrawing';
import { useMemoryOptimization } from './hooks/useMemoryOptimization';
import { useRecording } from './hooks/useRecording';
import { useVideo } from './hooks/useVideo';
import { useWebSocket } from './hooks/useWebSocket';
import {
  DrawingElement,
  DrawingMessage,
  DrawingPath,
  DroneCameraViewProps,
} from './types';

const DroneCameraView: React.FC<DroneCameraViewProps> = ({
  index,
  camera,
  videoUrl,
  droneCode = 'SM_ALPHA_001',
  droneName = 'Drone 1',
  droneColor = '#0CBA47',
  gridColumn = 1,
  width = '100%',
  height = '100%',
  isHls = false,
  isRtsp = false,
  streamId = 'default',
  socketUrl = 'ws://localhost:8000/ws/drawing/session/1/',
  userId,
  sessionId = '1',
  ratio = '16:9',
  onSaveSuccess,
  isStreamingAI = false,
  isExternal = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const videoContainerRef = useRef<HTMLDivElement>(null);
  const modalVideoContainerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const controlsPanelRef = useRef<HTMLDivElement>(null);
  const [isDrawingEnabled, setIsDrawingEnabled] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [showShapeOptions, setShowShapeOptions] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [activeUsers, setActiveUsers] = useState<
    Set<{
      user: string;
      joined_at?: string;
      last_activity?: string;
      is_online?: boolean;
    }>
  >(new Set());
  const [currentMode, setCurrentMode] = useState<
    'draw' | 'capture' | 'record' | 'ai' | null
  >(null);
  const [showCaptureFlash, setShowCaptureFlash] = useState(false);
  const [showStreamControls, setShowStreamControls] = useState(false);
  const renderCountRef = useRef(0);

  // Calculate aspect ratio dimensions
  const getAspectRatioDimensions = useCallback(
    (containerWidth: number, containerHeight: number) => {
      const [widthRatio, heightRatio] = ratio.split(':').map(Number);
      const aspectRatio = widthRatio / heightRatio;

      let videoWidth, videoHeight;

      if (containerWidth / containerHeight > aspectRatio) {
        // Container is wider than video ratio - fit to height
        videoHeight = containerHeight;
        videoWidth = containerHeight * aspectRatio;
      } else {
        // Container is taller than video ratio - fit to width
        videoWidth = containerWidth;
        videoHeight = containerWidth / aspectRatio;
      }

      return { width: videoWidth, height: videoHeight };
    },
    [ratio],
  );

  // Debug: Log the props being used (with render count)
  useEffect(() => {
    renderCountRef.current += 1;
  }, [socketUrl, sessionId, userId, streamId]);

  // Memoize stream URLs to prevent unnecessary re-renders
  const streamUrls = useMemo(
    () => ({
      hlsUrl: isHls ? videoUrl : undefined,
      rtspUrl: isRtsp ? videoUrl : undefined,
      webrtcUrl: isRtsp ? videoUrl : undefined, // WebRTC can use RTSP URL
    }),
    [isHls, isRtsp, videoUrl],
  );

  // Memoize callbacks to prevent re-renders
  const onProtocolSwitch = useCallback(
    (from: string, to: string) => {
      console.log(
        `📡 Protocol switched from ${from} to ${to} for stream ${streamId}`,
      );
    },
    [streamId],
  );

  const onQualityChange = useCallback(
    (quality: string) => {
      console.log(`📊 Quality changed to ${quality} for stream ${streamId}`);
    },
    [streamId],
  );

  // Dynamic stream management with memoized props
  const dynamicStream = useDynamicStream({
    streamId,
    ...streamUrls,
    initialProtocol: isRtsp ? 'webrtc' : 'hls', // Use WebRTC if RTSP stream is available
    autoSwitch: false, // Disable auto-switch for now to reduce re-renders
    onProtocolSwitch,
    onQualityChange,
  });

  // Memoize video configuration to prevent unnecessary re-renders
  const videoConfig = useMemo(() => {
    const config = {
      hlsVideoUrl: dynamicStream.isHls ? dynamicStream.streamUrl || '' : '',
      webrtcUrl: dynamicStream.isWebRTC ? dynamicStream.streamUrl || '' : '',
      isHlsActive: dynamicStream.isHls,
      isWebRTCActive: dynamicStream.isWebRTC && !!dynamicStream.streamUrl,
    };

    return config;
  }, [dynamicStream.isHls, dynamicStream.isWebRTC, dynamicStream.streamUrl]);

  // WebRTC error and success callbacks (memoized)
  const onWebRTCError = useCallback(
    (error: Error) => {
      console.error('WebRTC error:', error);
      dynamicStream.handleConnectionError(error);
    },
    [dynamicStream],
  );

  const onWebRTCSuccess = useCallback(() => {
    dynamicStream.handleConnectionSuccess();
  }, [dynamicStream]);

  const onWebRTCStatusChange = useCallback((status: string, type: string) => {
    console.log(`WebRTC ${type}:`, status);
  }, []);

  // Video setup for HLS streams
  const { videoRef } = useVideo({
    videoUrl: videoConfig.hlsVideoUrl,
    isHls: videoConfig.isHlsActive,
  });

  // WebRTC setup for RTSP streams
  const {
    videoRef: webrtcVideoRef,
    isConnected: isWebRTCConnected,
    isLoading: isWebRTCLoading,
    error: webrtcError,
  } = useWebRTC({
    rtspUrl: videoConfig.webrtcUrl,
    isActive: videoConfig.isWebRTCActive,
    onError: onWebRTCError,
    onSuccess: onWebRTCSuccess,
    onStatusChange: onWebRTCStatusChange,
  });

  // Use the appropriate video ref based on stream type
  const activeVideoRef = dynamicStream.isWebRTC ? webrtcVideoRef : videoRef;

  // Memory optimization for HLS streams
  const { forceCleanup } = useMemoryOptimization({
    isActive: !!dynamicStream.streamUrl && dynamicStream.isHls,
    streamId,
  });

  // Recording setup
  const {
    isRecording: recordingState,
    isLoading: isLoadingRecording,
    isPaused: recordingPaused,
    formattedTime: recordingTime,
    startRecording,
    stopRecording,
    togglePause,
  } = useRecording(droneCode);

  // Placeholder redrawAllPaths function (will be updated after drawing hook)
  const redrawAllPaths = useCallback(() => {
    console.log('🎨 RedrawAllPaths called (placeholder)');
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Force memory cleanup when component unmounts
      if (dynamicStream.streamUrl && dynamicStream.isHls) {
        forceCleanup();
      }
      // Reset dynamic stream state
      dynamicStream.reset();
    };
  }, [dynamicStream, forceCleanup]);

  // WebSocket setup
  const handleRemoteDrawEvent = useCallback(
    (message: DrawingMessage) => {
      // For element_added, we can process without canvas since we're just saving data
      if (message.type === 'element_added') {
        if (message.element) {
          const elementStreamId =
            message.element?.data?.stream_id || message.element?.session_id;
          const elementDroneCode =
            message.element?.data?.drone_code || message.element?.drone_id;
          const elementUserId =
            message.element?.data?.user_id || message.element?.created_by;
          const currentStreamId = streamId;

          if (elementUserId && elementUserId === String(userId)) {
            return;
          }

          // Strict stream matching - only accept if stream_id matches exactly
          const isSameStream = elementStreamId === currentStreamId;

          if (!isSameStream) {
            return;
          }

          // Convert and save the drawing
          const drawings = drawingGetStoredDrawings();
          let newPath: DrawingPath;

          if (message.element.data.points_percentage) {
            // Determine mode based on color
            const isEraser = message.element.data.color === 'transparent';

            newPath = {
              points: message.element.data.points_percentage.map(
                (point: number[]) => ({
                  x: point[0],
                  y: point[1],
                }),
              ),
              color: message.element.data.color || '#000000',
              lineWidth: message.element.data.width || 2,
              mode: isEraser ? 'erase' : 'draw',
              userId: message.element.data?.created_by_id,
              timestamp: Date.now(),
            };
          } else if (message.element.data.points) {
            const senderCanvasWidth =
              message.element.data.canvas_width || dimensions.width;
            const senderCanvasHeight =
              message.element.data.canvas_height || dimensions.height;

            // Determine mode based on color
            const isEraser = message.element.data.color === 'transparent';

            newPath = {
              points: message.element.data.points.map((point: number[]) => ({
                x: (point[0] / senderCanvasWidth) * 100,
                y: (point[1] / senderCanvasHeight) * 100,
              })),
              color: message.element.data.color || '#000000',
              lineWidth: message.element.data.width || 2,
              mode: isEraser ? 'erase' : 'draw',
              userId: message.element.data?.created_by_id,
              timestamp: Date.now(),
            };
          } else {
            // Handle shape data
            const shapeData = message.element.data;
            let startPoint, endPoint;

            if (shapeData.start_point && shapeData.end_point) {
              // If start and end points are provided as percentages
              startPoint = {
                x: shapeData.start_point[0],
                y: shapeData.start_point[1],
              };
              endPoint = {
                x: shapeData.end_point[0],
                y: shapeData.end_point[1],
              };
            } else if (shapeData.startPoint && shapeData.endPoint) {
              // If start and end points are provided as pixel coordinates
              const senderCanvasWidth =
                shapeData.canvas_width || dimensions.width;
              const senderCanvasHeight =
                shapeData.canvas_height || dimensions.height;

              startPoint = {
                x: (shapeData.startPoint.x / senderCanvasWidth) * 100,
                y: (shapeData.startPoint.y / senderCanvasHeight) * 100,
              };
              endPoint = {
                x: (shapeData.endPoint.x / senderCanvasWidth) * 100,
                y: (shapeData.endPoint.y / senderCanvasHeight) * 100,
              };
            } else {
              // Fallback: create dummy points (should not happen in normal cases)
              startPoint = { x: 0, y: 0 };
              endPoint = { x: 10, y: 10 };
            }

            newPath = {
              points: [],
              color: message.element.data.color || '#000000',
              lineWidth: message.element.data.width || 2,
              mode: 'shape',
              userId: message.element.data?.created_by_id,
              timestamp: Date.now(),
              shapeType: message.element.type as
                | 'rectangle'
                | 'circle'
                | 'oval'
                | 'line',
              startPoint,
              endPoint,
            };
          }

          drawings.push(newPath);
          drawingSaveDrawings(drawings);

          // Schedule redraw for next frame to ensure canvas is ready
          // setTimeout(() => {
          updatedRedrawAllPaths();
          // }, 0);
          return;
        }
      }

      // For other message types, check canvas availability
      const canvas = canvasRef.current;
      const context = canvas?.getContext('2d');
      if (!context || !canvas) {
        return;
      }

      switch (message.type) {
        case 'connected':
          // Clear local drawings when connected to avoid duplicates

          drawingSaveDrawings([]);
          setTimeout(() => {
            const canvas = canvasRef.current;
            const context = canvas?.getContext('2d');
            if (context && canvas) {
              context.clearRect(0, 0, canvas.width, canvas.height);
            }
          }, 100);
          break;

        case 'element_added':
          // Already handled above - no need to process again
          break;

        case 'clear_all':
        case 'drawing_cleared': {
          const clearStreamId =
            message.element_data?.stream_id ||
            message.session_id ||
            message.stream_id;
          const clearDroneCode =
            message.element_data?.drone_code ||
            message.drone_code ||
            message.drone_id;

          // For drawing_cleared messages without stream info, assume they apply to current stream
          // This handles server responses that don't include stream identification
          const shouldClear =
            (clearStreamId && clearStreamId === streamId) ||
            (clearDroneCode && clearDroneCode === droneCode) ||
            (message.type === 'drawing_cleared' &&
              !clearStreamId &&
              !clearDroneCode);

          if (!shouldClear) {
            return;
          }

          context.clearRect(0, 0, canvas.width, canvas.height);

          // Also clear local storage for this stream
          drawingSaveDrawings([]);

          break;
        }

        case 'participant_joined': {
          const joinUser = message.user || String(message.userId);

          if (message.participants) {
            setActiveUsers(
              new Set(
                message.participants
                  .filter((p) => p.user !== String(userId))
                  .map((p) => ({
                    user: p.user,
                    joined_at: p.joined_at,
                    last_activity: p.last_activity,
                    is_online: p.is_online,
                  })),
              ),
            );
          } else {
            setActiveUsers((prev) => new Set([...prev, { user: joinUser }]));
          }

          break;
        }

        case 'participant_left': {
          const leaveUser = message.user || String(message.userId);
          if (message.participants) {
            setActiveUsers(
              new Set(
                message.participants
                  .filter((p) => p.user !== String(userId))
                  .map((p) => ({
                    user: p.user,
                    joined_at: p.joined_at,
                    last_activity: p.last_activity,
                    is_online: p.is_online,
                  })),
              ),
            );
          } else {
            setActiveUsers((prev) => {
              const newSet = new Set(prev);
              // Find and remove the user object with matching user property
              for (const userObj of newSet) {
                if (userObj.user === leaveUser) {
                  newSet.delete(userObj);
                  break;
                }
              }
              return newSet;
            });
          }
          break;
        }

        case 'participants_list': {
          if (message.participants && Array.isArray(message.participants)) {
            setActiveUsers(
              new Set(
                message.participants
                  .filter((p) => p.user !== String(userId))
                  .map((p) => ({
                    user: p.user,
                    joined_at: p.joined_at,
                    last_activity: p.last_activity,
                    is_online: p.is_online,
                  })),
              ),
            );
          }
          break;
        }
        case 'drawing_request':
        case 'request_drawing': {
          // Strategy: Only respond if I'm the "first" user alphabetically among active users
          // This ensures only one user responds to avoid duplicates
          const allUsers = Array.from(activeUsers)
            .map((u) => u.user)
            .concat(String(userId))
            .sort();
          const firstUser = allUsers[0];
          const isMyTurnToRespond = String(userId) === firstUser;

          if (!isMyTurnToRespond) {
            break;
          }

          // Get current drawings and convert to DrawingElement format
          const currentDrawings = drawingGetStoredDrawings();
          const drawingElements: DrawingElement[] = currentDrawings
            .map((drawing) => {
              if (
                drawing.mode === 'shape' &&
                drawing.startPoint &&
                drawing.endPoint
              ) {
                return {
                  type: drawing.shapeType || 'rectangle',
                  data: {
                    start_point: [drawing.startPoint.x, drawing.startPoint.y],
                    end_point: [drawing.endPoint.x, drawing.endPoint.y],
                    color: drawing.color,
                    width: drawing.lineWidth,
                    stream_id: streamId, // ✅ Ensure stream_id is set
                    drone_code: droneCode,
                    session_id: sessionId,
                    user_id: drawing.userId || String(userId),
                    canvas_width: dimensions.width,
                    canvas_height: dimensions.height,
                  },
                  created_by: drawing.userId || String(userId),
                } as DrawingElement;
              } else if (drawing.points && drawing.points.length > 0) {
                const serverPoints = drawing.points.map((point) => {
                  const pixel = drawingPercentageToPixel(point.x, point.y);
                  return [pixel.x, pixel.y];
                });

                return {
                  type: 'line',
                  data: {
                    points: serverPoints,
                    points_percentage: drawing.points.map((point) => [
                      point.x,
                      point.y,
                    ]),
                    color: drawing.color,
                    width: drawing.lineWidth,
                    stream_id: streamId, // ✅ Ensure stream_id is set
                    drone_code: droneCode,
                    session_id: sessionId,
                    user_id: drawing.userId || String(userId),
                    canvas_width: dimensions.width,
                    canvas_height: dimensions.height,
                  },
                  created_by: drawing.userId || String(userId),
                } as DrawingElement;
              }
              return null;
            })
            .filter((item): item is DrawingElement => item !== null);

          sendMessage({
            type: 'send_drawings',
            drawings: drawingElements,
            target_channel: message?.requester_channel,
          });
          break;
        }

        case 'drawings_sync': {
          if (message.drawings && Array.isArray(message.drawings)) {
            // Filter drawings by current stream
            const streamDrawings = message.drawings.filter(
              (serverDrawing: DrawingElement) => {
                const elementStreamId = serverDrawing.data?.stream_id;
                const isForCurrentStream = elementStreamId === streamId;

                return isForCurrentStream;
              },
            );

            // Clear current drawings and apply server drawings
            const existingDrawings: DrawingPath[] = [];

            streamDrawings.forEach((serverDrawing: DrawingElement) => {
              let newPath: DrawingPath;

              if (serverDrawing.data?.points_percentage) {
                newPath = {
                  points: serverDrawing.data.points_percentage.map(
                    (point: number[]) => ({
                      x: point[0],
                      y: point[1],
                    }),
                  ),
                  color: serverDrawing.data.color || '#000000',
                  lineWidth: serverDrawing.data.width || 2,
                  mode: 'draw',
                  userId:
                    serverDrawing.data?.user_id || serverDrawing.created_by,
                  timestamp: Date.now(),
                };
              } else if (
                serverDrawing.data?.start_point &&
                serverDrawing.data?.end_point
              ) {
                newPath = {
                  points: [],
                  color: serverDrawing.data.color || '#000000',
                  lineWidth: serverDrawing.data.width || 2,
                  mode: 'shape',
                  userId:
                    serverDrawing.data?.user_id || serverDrawing.created_by,
                  timestamp: Date.now(),
                  shapeType: serverDrawing.type as
                    | 'rectangle'
                    | 'circle'
                    | 'oval'
                    | 'line',
                  startPoint: {
                    x: serverDrawing.data.start_point[0],
                    y: serverDrawing.data.start_point[1],
                  },
                  endPoint: {
                    x: serverDrawing.data.end_point[0],
                    y: serverDrawing.data.end_point[1],
                  },
                };
              } else {
                return;
              }

              existingDrawings.push(newPath);
            });

            // Save all drawings and redraw
            drawingSaveDrawings(existingDrawings);
            setTimeout(() => {
              updatedRedrawAllPaths();
            }, 100);
          }
          break;
        }

        default:
          console.warn('❓ Unknown message type:', message.type);
      }
    },
    [userId, streamId, droneCode, dimensions],
  );

  const { isConnected, sendMessage } = useWebSocket({
    socketUrl,
    sessionId,
    userId: String(userId),
    streamId,
    droneCode,
    onMessage: handleRemoteDrawEvent,
  });

  // Update the drawing hook with the correct sendMessage function
  const {
    brushSize: drawingBrushSize,
    setBrushSize: setDrawingBrushSize,
    brushColor: drawingBrushColor,
    setBrushColor: setDrawingBrushColor,
    drawingMode: drawingDrawingMode,
    setDrawingMode: setDrawingDrawingMode,
    shapeType: drawingShapeType,
    setShapeType: setDrawingShapeType,
    getStoredDrawings: drawingGetStoredDrawings,
    saveDrawings: drawingSaveDrawings,
    percentageToPixel: drawingPercentageToPixel,
    getCanvasCoordinates: drawingGetCanvasCoordinates,
    startDrawing: drawingStartDrawing,
    draw: drawingDraw,
    endDrawing: drawingEndDrawing,
    clearCanvas: drawingClearCanvas,
  } = useDrawing({
    streamId,
    userId: String(userId),
    dimensions,
    sendDrawingMessage: sendMessage,
    redrawAllPaths,
    canvasRef,
  });

  // Update redrawAllPaths with the actual implementation
  const updatedRedrawAllPaths = useCallback(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext('2d');
    if (!context || !canvas) {
      return;
    }

    context.clearRect(0, 0, canvas.width, canvas.height);

    // Get all stored drawings
    const drawings = drawingGetStoredDrawings();

    drawings.forEach((path, index) => {
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
        const startPixel = drawingPercentageToPixel(
          path.startPoint.x,
          path.startPoint.y,
        );
        const endPixel = drawingPercentageToPixel(
          path.endPoint.x,
          path.endPoint.y,
        );

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
        const firstPixel = drawingPercentageToPixel(
          path.points[0].x,
          path.points[0].y,
        );
        context.moveTo(firstPixel.x, firstPixel.y);

        for (let i = 1; i < path.points.length; i++) {
          const pixel = drawingPercentageToPixel(
            path.points[i].x,
            path.points[i].y,
          );
          context.lineTo(pixel.x, pixel.y);
        }
        context.stroke();
      }

      context.restore();
    });

    context.globalCompositeOperation = 'source-over';
    context.strokeStyle = drawingBrushColor;
    context.lineWidth = drawingBrushSize;
  }, [
    drawingGetStoredDrawings,
    drawingBrushColor,
    drawingBrushSize,
    userId,
    drawingPercentageToPixel,
  ]);

  // Video setup with container switching
  useEffect(() => {
    const video = activeVideoRef.current;
    const canvas = canvasRef.current;
    if (!video || !dynamicStream.streamUrl) return;

    const targetContainer = isDrawingEnabled
      ? modalVideoContainerRef.current?.querySelector('.video-wrapper')
      : videoContainerRef.current;

    if (targetContainer) {
      if (video.parentNode !== targetContainer) {
        targetContainer.appendChild(video);
      }
      if (canvas && canvas.parentNode !== targetContainer) {
        targetContainer.appendChild(canvas);
      }
    }
  }, [
    dynamicStream.streamUrl,
    dynamicStream.isHls,
    dynamicStream.isWebRTC,
    isDrawingEnabled,
    activeVideoRef,
  ]);

  // Separate effect to ensure canvas is moved when drawing mode changes
  useEffect(() => {
    const canvas = canvasRef.current;
    const video = activeVideoRef.current;

    if (!canvas || !video) return;

    const timer = setTimeout(() => {
      const targetContainer = isDrawingEnabled
        ? modalVideoContainerRef.current?.querySelector('.video-wrapper')
        : videoContainerRef.current;

      if (targetContainer) {
        // Store canvas content before moving
        const imageData = canvas
          .getContext('2d')
          ?.getImageData(0, 0, canvas.width, canvas.height);

        if (canvas.parentNode !== targetContainer) {
          targetContainer.appendChild(canvas);

          // Restore canvas content after moving and force redraw
          if (imageData) {
            const context = canvas.getContext('2d');
            if (context) {
              context.putImageData(imageData, 0, 0);
            }
          }

          // Additional redraw after a short delay to ensure stability
          setTimeout(() => {
            updatedRedrawAllPaths();
          }, 50);
        }
        if (video.parentNode !== targetContainer) {
          targetContainer.appendChild(video);
        }
      }
    }, 50);

    return () => clearTimeout(timer);
  }, [isDrawingEnabled, updatedRedrawAllPaths]);

  // Update container size
  useEffect(() => {
    const updateContainerSize = () => {
      const container = isDrawingEnabled
        ? (modalVideoContainerRef.current?.querySelector(
            '.video-wrapper',
          ) as HTMLElement)
        : videoContainerRef.current;
      if (!container) return;

      const rect = container.getBoundingClientRect();
      const containerWidth = rect.width;
      const containerHeight = rect.height;

      if (containerWidth > 0 && containerHeight > 0) {
        const videoDimensions = getAspectRatioDimensions(
          containerWidth,
          containerHeight,
        );
        setDimensions(videoDimensions);
      }
    };

    setTimeout(() => {
      updateContainerSize();
    }, 100);

    const resizeObserver = new ResizeObserver(updateContainerSize);

    if (isDrawingEnabled && modalVideoContainerRef.current) {
      resizeObserver.observe(modalVideoContainerRef.current);
    } else if (!isDrawingEnabled && videoContainerRef.current) {
      resizeObserver.observe(videoContainerRef.current);
    }

    window.addEventListener('resize', updateContainerSize);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener('resize', updateContainerSize);
    };
  }, [isDrawingEnabled, getAspectRatioDimensions]);

  // Update dimensions when ratio changes
  useEffect(() => {
    const updateDimensionsForRatio = () => {
      const container = isDrawingEnabled
        ? (modalVideoContainerRef.current?.querySelector(
            '.video-wrapper',
          ) as HTMLElement)
        : videoContainerRef.current;
      if (!container) return;

      const rect = container.getBoundingClientRect();
      const containerWidth = rect.width;
      const containerHeight = rect.height;

      if (containerWidth > 0 && containerHeight > 0) {
        const videoDimensions = getAspectRatioDimensions(
          containerWidth,
          containerHeight,
        );
        setDimensions(videoDimensions);
      }
    };

    // Small delay to ensure container is ready
    const timer = setTimeout(updateDimensionsForRatio, 50);
    return () => clearTimeout(timer);
  }, [ratio, isDrawingEnabled, getAspectRatioDimensions]);

  // Restore drawings when container changes (layout change)
  useEffect(() => {
    const restoreDrawings = () => {
      const canvas = canvasRef.current;
      const context = canvas?.getContext('2d');
      if (!context || !canvas) return;

      // Small delay to ensure canvas is ready
      setTimeout(() => {
        updatedRedrawAllPaths();
      }, 50);
    };

    // Call restore when dimensions change (indicating layout change)
    if (dimensions.width > 0 && dimensions.height > 0) {
      restoreDrawings();
    }
  }, [dimensions.width, dimensions.height, updatedRedrawAllPaths]);

  // Initialize canvas with proper scaling
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const context = canvas.getContext('2d');
    if (!context) return;

    canvas.width = dimensions.width;
    canvas.height = dimensions.height;
    canvas.style.width = dimensions.width + 'px';
    canvas.style.height = dimensions.height + 'px';

    // Ensure context is set correctly after resize
    if (drawingDrawingMode === 'pen' || drawingDrawingMode === 'shape') {
      context.globalCompositeOperation = 'source-over';
      context.strokeStyle = drawingBrushColor;
    } else {
      context.globalCompositeOperation = 'destination-out';
    }
    context.lineWidth = drawingBrushSize;
    context.lineCap = 'round';
    context.lineJoin = 'round';

    // Redraw all paths after a small delay to ensure canvas is ready
    setTimeout(() => {
      updatedRedrawAllPaths();
    }, 10);
  }, [
    dimensions,
    drawingDrawingMode,
    drawingBrushColor,
    drawingBrushSize,
    updatedRedrawAllPaths,
  ]);

  // Update canvas context when drawing settings change
  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext('2d');
    if (!context) return;

    if (drawingDrawingMode === 'pen' || drawingDrawingMode === 'shape') {
      context.globalCompositeOperation = 'source-over';
      context.strokeStyle = drawingBrushColor;
    } else {
      context.globalCompositeOperation = 'destination-out';
    }
    context.lineWidth = drawingBrushSize;
  }, [drawingBrushColor, drawingBrushSize, drawingDrawingMode]);

  // Ensure canvas context is set correctly when entering drawing mode
  useEffect(() => {
    if (!isDrawingEnabled) return;

    const canvas = canvasRef.current;
    const context = canvas?.getContext('2d');
    if (!context) return;

    if (drawingDrawingMode === 'pen' || drawingDrawingMode === 'shape') {
      context.globalCompositeOperation = 'source-over';
      context.strokeStyle = drawingBrushColor;
    } else {
      context.globalCompositeOperation = 'destination-out';
    }
    context.lineWidth = drawingBrushSize;
    context.lineCap = 'round';
    context.lineJoin = 'round';
  }, [
    isDrawingEnabled,
    drawingBrushColor,
    drawingBrushSize,
    drawingDrawingMode,
  ]);

  // Drawing event handlers
  const handleStart = useCallback(
    (
      e:
        | React.MouseEvent<HTMLCanvasElement>
        | React.TouchEvent<HTMLCanvasElement>,
    ) => {
      if (!isDrawingEnabled) {
        return;
      }

      e.preventDefault();
      e.stopPropagation();

      const coords = drawingGetCanvasCoordinates(e);

      drawingStartDrawing(coords.x, coords.y);
    },
    [
      isDrawingEnabled,
      drawingDrawingMode,
      drawingGetCanvasCoordinates,
      drawingStartDrawing,
    ],
  );

  const handleMove = useCallback(
    (
      e:
        | React.MouseEvent<HTMLCanvasElement>
        | React.TouchEvent<HTMLCanvasElement>,
    ) => {
      if (!isDrawingEnabled) return;

      e.preventDefault();
      const coords = drawingGetCanvasCoordinates(e);

      drawingDraw(coords.x, coords.y);
    },
    [isDrawingEnabled, drawingGetCanvasCoordinates, drawingDraw],
  );

  const handleEnd = useCallback(
    (
      e?:
        | React.MouseEvent<HTMLCanvasElement>
        | React.TouchEvent<HTMLCanvasElement>,
    ) => {
      if (e && drawingDrawingMode === 'shape') {
        const coords = drawingGetCanvasCoordinates(e);
        drawingEndDrawing(coords.x, coords.y);
      } else {
        drawingEndDrawing();
      }
    },
    [drawingDrawingMode, drawingGetCanvasCoordinates, drawingEndDrawing],
  );

  // Auto-hide shape options when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        controlsPanelRef.current &&
        !controlsPanelRef.current.contains(event.target as Node)
      ) {
        setShowShapeOptions(false);
      }
    };

    if (showShapeOptions) {
      document.addEventListener('mousedown', handleClickOutside);
      return () =>
        document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showShapeOptions]);

  // Utility functions
  const toggleDrawing = useCallback(() => {
    setIsDrawingEnabled(!isDrawingEnabled);

    if (isDrawingEnabled) {
      // Increased delay to ensure canvas move operation completes first
      setTimeout(() => {
        updatedRedrawAllPaths();
      }, 150);
    }
  }, [isDrawingEnabled, updatedRedrawAllPaths]);

  // Handle ESC key to exit drawing mode
  useEffect(() => {
    const handleEsc = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isDrawingEnabled) {
        setIsDrawingEnabled(false);

        setTimeout(() => {
          updatedRedrawAllPaths();
        }, 150);
      }
    };

    if (isDrawingEnabled) {
      document.addEventListener('keydown', handleEsc);
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'auto';
    }

    return () => {
      document.removeEventListener('keydown', handleEsc);
      document.body.style.overflow = 'auto';
    };
  }, [isDrawingEnabled, updatedRedrawAllPaths]);

  const captureFrame = useCallback(() => {
    console.log('Capture frame with annotations');
  }, []);

  const toggleRecording = useCallback(() => {
    setIsRecording(!isRecording);
  }, [isRecording]);

  // Handle mode changes
  const handleModeChange = useCallback(
    (mode: 'draw' | 'capture' | 'record' | 'ai' | null) => {
      setCurrentMode(mode);

      // Handle specific mode logic
      if (mode === 'draw') {
        setIsDrawingEnabled(true);
      } else {
        setIsDrawingEnabled(false);
      }
    },
    [],
  );

  // Handle close drawing modal (same as ESC key)
  const handleCloseDrawingModal = useCallback(() => {
    setIsDrawingEnabled(false);

    setTimeout(() => {
      updatedRedrawAllPaths();
    }, 150);
  }, [updatedRedrawAllPaths]);

  // Handle capture flash effect
  const handleCaptureFlash = useCallback(() => {
    setShowCaptureFlash(true);
  }, []);

  const handleFlashComplete = useCallback(() => {
    setShowCaptureFlash(false);
  }, []);

  const handleDeleteExternalStream = useCallback(async () => {
    const response = await API.delete(
      endpoint.deleteExternalStream(Number(streamId)),
    );
    if (response.success) {
      ToastTopHelper.success(response.message);
      onSaveSuccess?.();
    } else {
      ToastTopHelper.error(response.message);
    }
  }, [streamId, onSaveSuccess]);

  return (
    <>
      {/* Single Video Element - Will be moved between containers */}
      <video
        ref={activeVideoRef}
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: `100%`,
          height: `100%`,
          objectFit: 'contain',
          objectPosition: 'center',
          zIndex: 1,
        }}
        autoPlay
        muted
        loop={!isRtsp}
        playsInline
        crossOrigin="anonymous"
      />
      {/* Canvas Overlay - Always present and moved between containers */}
      <canvas
        ref={canvasRef}
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: `${dimensions.width}px`,
          height: `${dimensions.height}px`,
          cursor: isDrawingEnabled
            ? drawingDrawingMode === 'eraser'
              ? 'grab'
              : 'crosshair'
            : 'default',
          zIndex: isDrawingEnabled ? 1000 : 10,
          touchAction: 'none',
          pointerEvents: isDrawingEnabled ? 'auto' : 'none',
        }}
        onMouseDown={isDrawingEnabled ? handleStart : undefined}
        onMouseMove={isDrawingEnabled ? handleMove : undefined}
        onMouseUp={isDrawingEnabled ? handleEnd : undefined}
        onMouseLeave={isDrawingEnabled ? handleEnd : undefined}
        onTouchStart={isDrawingEnabled ? handleStart : undefined}
        onTouchMove={isDrawingEnabled ? handleMove : undefined}
        onTouchEnd={isDrawingEnabled ? handleEnd : undefined}
      />
      {/* Normal View - When drawing is disabled */}
      {!isDrawingEnabled && (
        <div
          ref={containerRef}
          style={{
            position: 'relative',
            width: width,
            height: height,
            backgroundColor: '#000',
            overflow: 'hidden',
            fontFamily: 'system-ui, -apple-system, sans-serif',
          }}
        >
          {/* Video and Canvas Container */}
          <div
            ref={videoContainerRef}
            style={{
              position: 'relative',
              width: '100%',
              height: '100%',
              overflow: 'hidden',
            }}
          >
            {/* Capture Flash Effect */}
            <CaptureFlash
              isVisible={showCaptureFlash}
              onComplete={handleFlashComplete}
            />
          </div>

          {/* Stream Controls Toggle Button */}
          <button
            style={{
              position: 'absolute',
              top: '10px',
              right: '10px',
              background: 'rgba(0, 0, 0, 0.7)',
              border: 'none',
              borderRadius: '4px',
              color: 'white',
              padding: '8px',
              cursor: 'pointer',
              fontSize: '12px',
              zIndex: 100,
            }}
            onClick={() => setShowStreamControls(!showStreamControls)}
            title="Toggle stream controls"
          >
            📡
          </button>

          {/* Dynamic Stream Controls */}
          {showStreamControls && (
            <div
              style={{
                position: 'absolute',
                top: '50px',
                right: '10px',
                zIndex: 100,
              }}
            >
              <StreamControls
                currentProtocol={dynamicStream.currentProtocol}
                currentQuality={dynamicStream.currentQuality}
                isConnected={dynamicStream.isConnected}
                isLoading={dynamicStream.isLoading}
                connectionMetrics={dynamicStream.connectionMetrics}
                canSwitchToWebRTC={dynamicStream.canSwitchToWebRTC}
                canSwitchToHLS={dynamicStream.canSwitchToHLS}
                onProtocolSwitch={dynamicStream.switchProtocol}
                onQualityChange={dynamicStream.adjustQuality}
              />
            </div>
          )}

          {/* Only show StatusInfo and ActionControls when not recording */}
          {!recordingState && (
            <>
              <StatusInfo
                isDrawingEnabled={isDrawingEnabled}
                isConnected={isConnected}
                activeUsers={activeUsers}
                isRecording={isRecording}
                droneCode={droneCode}
                droneName={droneName}
                droneColor={droneColor}
                gridColumn={gridColumn}
              />
              <ActionControls
                index={index}
                camera={camera}
                currentMode={currentMode}
                isLoadingRecording={isLoadingRecording}
                recordingState={recordingState}
                startRecording={startRecording}
                stopRecording={stopRecording}
                streamMonitorCode={droneCode}
                onModeChange={handleModeChange}
                onCaptureFlash={handleCaptureFlash}
                onSaveSuccess={onSaveSuccess}
                isStreamingAI={isStreamingAI}
                onDeleteExternalStream={
                  isExternal ? handleDeleteExternalStream : undefined
                }
              />
            </>
          )}

          {/* Recording overlay */}
          <RecordingOverlay
            isRecording={recordingState}
            isPaused={recordingPaused}
            recordingTime={recordingTime}
            droneCode={droneCode}
            onTogglePause={togglePause}
            onStopRecording={stopRecording}
          />
        </div>
      )}
      {/* Drawing Modal Overlay - When drawing is enabled */}
      {isDrawingEnabled && (
        <DrawingModal
          isDrawingEnabled={isDrawingEnabled}
          drawingMode={drawingDrawingMode}
          shapeType={drawingShapeType}
          brushSize={drawingBrushSize}
          brushColor={drawingBrushColor}
          showShapeOptions={showShapeOptions}
          isRecording={isRecording}
          isConnected={isConnected}
          activeUsers={activeUsers}
          droneCode={droneCode}
          droneName={droneName}
          onToggleDrawing={toggleDrawing}
          onDrawingModeChange={setDrawingDrawingMode}
          onShapeTypeChange={setDrawingShapeType}
          onBrushSizeChange={setDrawingBrushSize}
          onBrushColorChange={setDrawingBrushColor}
          onShowShapeOptionsChange={setShowShapeOptions}
          onToggleRecording={toggleRecording}
          onCaptureFrame={captureFrame}
          onClearCanvas={drawingClearCanvas}
          onClose={handleCloseDrawingModal}
        >
          <div
            ref={modalVideoContainerRef}
            style={{
              position: 'relative',
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {/* Video Stream Container */}
            <div
              className="video-wrapper"
              style={{
                position: 'relative',
                width: '100%',
                height: '100%',
                borderRadius: '16px',
                backgroundColor: '#000',
                overflow: 'hidden',
                boxShadow: '0 20px 60px rgba(0, 0, 0, 0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {/* Capture Flash Effect in Drawing Modal */}
              <CaptureFlash
                isVisible={showCaptureFlash}
                onComplete={handleFlashComplete}
              />
            </div>
          </div>
        </DrawingModal>
      )}
      <style>{`
        @keyframes pulse {
          0%,
          100% {
            opacity: 1;
          }
          50% {
            opacity: 0.5;
          }
        }

        input[type='range']::-webkit-slider-thumb {
          appearance: none;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #3B82F6;
          cursor: pointer;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }

        input[type='range']::-moz-range-thumb {
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #3B82F6;
          cursor: pointer;
          border: none;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }

        input[type='range']::-ms-thumb {
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #3B82F6;
          cursor: pointer;
          border: none;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }

        input[type='color']::-webkit-color-swatch-wrapper {
          padding: 0;
          border: none;
          border-radius: 8px;
          overflow: hidden;
        }

        input[type='color']::-webkit-color-swatch {
          border: none;
          border-radius: 6px;
        }
      `}</style>
    </>
  );
};

export default React.memo(DroneCameraView);
