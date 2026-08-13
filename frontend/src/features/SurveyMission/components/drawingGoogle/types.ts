export type DrawingMode = 'NONE' | 'LINE' | 'POLYGON' | 'CIRCULAR' | 'TRACE';

export type DrawingPoint = {
  lat: number;
  lng: number;
};

export type DrawingShape = {
  id: string;
  type: DrawingMode;
  points: DrawingPoint[];
  center?: DrawingPoint;
  radius?: number;
  fillColor?: string;
  fillOpacity?: number;
  return?: boolean;
};

export type Marker = {
  lat: number;
  lng: number;
  name?: string;
  for_robot?: boolean;
  color?: string;
  routeId?: string | number;
};

export type DrawingState = {
  mode: DrawingMode;
  points: DrawingPoint[];
  currentShape: DrawingShape | null;
  isDrawing: boolean;
  isDrawingActive: boolean;
  isDragging: boolean;
  dragStartPoint: DrawingPoint | null;
  dragCurrentPoint: DrawingPoint | null;
};

export type DrawingActions = {
  setMode: (mode: DrawingMode) => void;
  setPoints: (points: DrawingPoint[]) => void;
  setCurrentShape: (shape: DrawingShape | null) => void;
  setIsDrawing: (isDrawing: boolean) => void;
  setIsDrawingActive: (isActive: boolean) => void;
  setIsDragging: (isDragging: boolean) => void;
  setDragStartPoint: (point: DrawingPoint | null) => void;
  setDragCurrentPoint: (point: DrawingPoint | null) => void;
  clearDrawing: () => void;
};
