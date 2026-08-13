import { create } from 'zustand';

import { Waypoint } from '../../SurveyMission/types/surveyMission.types';
import { DrawingMode, DrawingShape } from '../components/drawing/types';

interface DrawingModeState {
  drawingMode: DrawingMode;
  setDrawingMode: (mode: DrawingMode) => void;
  setDrawingModeWithoutClear: (mode: DrawingMode) => void;
  currentShape: DrawingShape | null;
  setCurrentShape: (shape: DrawingShape | null) => void;
  clearCurrentShape: () => void;
  waypointsPreview: [number, number][];
  setWaypointsPreview: (waypoints: [number, number][]) => void;
  clearWaypointsPreview: () => void;
  waypointsList: Waypoint[];
  setWaypointsList: (waypoints: Waypoint[]) => void;
  clearWaypointsList: () => void;
  isEditable: boolean;
  setIsEditable: (editable: boolean) => void;
  clearAll: () => void;
  resetStore: () => void;
}

export const useDrawingModeStore = create<DrawingModeState>()((set) => ({
  drawingMode: 'NONE',
  setDrawingMode: (mode: DrawingMode) => set({ drawingMode: mode }),
  setDrawingModeWithoutClear: (mode: DrawingMode) =>
    set({
      drawingMode: mode,
    }),
  currentShape: null,
  setCurrentShape: (shape: DrawingShape | null) => set({ currentShape: shape }),
  clearCurrentShape: () => set({ currentShape: null }),
  waypointsPreview: [],
  setWaypointsPreview: (waypoints: [number, number][]) =>
    set({ waypointsPreview: waypoints }),
  clearWaypointsPreview: () => set({ waypointsPreview: [] }),
  waypointsList: [],
  setWaypointsList: (waypoints: Waypoint[]) =>
    set({ waypointsList: waypoints }),
  clearWaypointsList: () => set({ waypointsList: [] }),
  isEditable: false,
  setIsEditable: (editable: boolean) => set({ isEditable: editable }),
  clearAll: () =>
    set({
      drawingMode: 'NONE',
      currentShape: null,
      waypointsPreview: [],
      waypointsList: [],
      isEditable: false,
    }),
  resetStore: () =>
    set({
      drawingMode: 'NONE',
      currentShape: null,
      waypointsPreview: [],
      waypointsList: [],
      isEditable: false,
    }),
}));
