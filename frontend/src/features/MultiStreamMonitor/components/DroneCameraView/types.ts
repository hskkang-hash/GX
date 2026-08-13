export interface DroneCameraViewProps {
  index?: number;
  camera?: any;
  videoUrl?: string;
  droneName?: string;
  droneCode?: string;
  width?: number | string;
  height?: number | string;
  isHls?: boolean;
  isRtsp?: boolean;
  streamId?: string;
  socketUrl?: string;
  userId?: string;
  sessionId?: string;
  ratio?: '16:9' | '4:3' | '1:1' | '21:9' | '3:2' | '5:4';
  onSaveSuccess?: () => void;
  isStreamingAI?: boolean;
  gridColumn?: number;
  droneColor?: string;
  isExternal?: boolean;
}

export interface DrawingState {
  isDrawing: boolean;
  lastX: number;
  lastY: number;
}

export interface DrawingPath {
  id?: string;
  points: Array<{ x: number; y: number }>;
  color: string;
  lineWidth: number;
  mode: 'draw' | 'erase' | 'shape';
  userId?: string;
  timestamp?: number;
  shapeType?: 'rectangle' | 'circle' | 'oval' | 'line';
  startPoint?: { x: number; y: number };
  endPoint?: { x: number; y: number };
}

export interface DrawingMessage {
  type:
    | 'draw_element'
    | 'cursor_position'
    | 'clear_all'
    | 'connected'
    | 'element_added'
    | 'drawing_cleared'
    | 'participant_joined'
    | 'participant_left'
    | 'participants_list'
    | 'join'
    | 'leave'
    | 'request_drawing'
    | 'drawings_request'
    | 'send_drawings'
    | 'drawings_sync';

  element_type?: 'line' | 'circle' | 'rectangle' | 'oval';
  element_data?: {
    points?: number[][];
    color?: string;
    width?: number;
    cx?: number;
    cy?: number;
    radius?: number;
    x?: number;
    y?: number;
    height?: number;
    stream_id?: string;
    drone_code?: string;
    session_id?: string;
    user_id?: string;
    canvas_width?: number;
    canvas_height?: number;
    points_percentage?: number[][];
    start_point?: number[];
    end_point?: number[];
    startPoint?: { x: number; y: number };
    endPoint?: { x: number; y: number };
    target_channel?: string; // For sending messages to specific channel/user
    drawings?: DrawingElement[]; // For drawings_sync messages
  };

  cursor_data?: {
    x: number;
    y: number;
  };

  message?: string;
  element?: DrawingElement;
  cleared_by?: string;
  user?: string;

  session_id?: string;
  stream_id?: string;
  drone_code?: string;
  drone_id?: string;

  sessionId?: string;
  userId?: string | number;
  participants?: Array<{
    user: string;
    joined_at?: string;
    last_activity?: string;
    is_online?: boolean;
  }>;
  drawings?: DrawingElement[]; // For send_drawings and drawings_sync messages
}

export interface DrawingElement {
  type: string;
  data: {
    points?: number[][];
    points_percentage?: number[][];
    color?: string;
    width?: number;
    cx?: number;
    cy?: number;
    radius?: number;
    x?: number;
    y?: number;
    height?: number;
    stream_id?: string;
    drone_code?: string;
    session_id?: string;
    user_id?: string;
    created_by_id?: string;
    canvas_width?: number;
    canvas_height?: number;
    // Shape-specific properties
    start_point?: number[];
    end_point?: number[];
    startPoint?: { x: number; y: number };
    endPoint?: { x: number; y: number };
  };
  created_by?: string;
  session_id?: string;
  drone_id?: string;
}
