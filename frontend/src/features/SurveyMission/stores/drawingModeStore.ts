import { create } from 'zustand';

import { DrawingMode, DrawingShape } from '../components/drawing/types';
import { Waypoint } from '../types/surveyMission.types';

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
  isNotReviewing: boolean;
  setIsNotReviewing: (notReviewing: boolean) => void;
  isEditable: boolean;
  setIsEditable: (editable: boolean) => void;
  qgcMissionData: any | null;
  setQgcMissionData: (data: any | null) => void;
  clearAll: () => void;
  resetStore: () => void; // New method for explicit reset
  isDebouncedReviewPending: boolean;
  setIsDebouncedReviewPending: (pending: boolean) => void;
}

export const useDrawingModeStore = create<DrawingModeState>()((set) => ({
  drawingMode: 'NONE',
  setDrawingMode: (mode: DrawingMode) => set({ drawingMode: mode }),
  setDrawingModeWithoutClear: (mode: DrawingMode) =>
    set({
      drawingMode: mode,
    }),
  isNotReviewing: false,
  setIsNotReviewing: (notReviewing: boolean) =>
    set({ isNotReviewing: notReviewing }),
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
  qgcMissionData: null,
  setQgcMissionData: (data: any | null) => set({ qgcMissionData: data }),
  clearAll: () =>
    set({
      drawingMode: 'NONE',
      currentShape: null,
      waypointsPreview: [],
      waypointsList: [],
      isNotReviewing: false,
      isEditable: false,
      qgcMissionData: null,
      isDebouncedReviewPending: false,
    }),
  resetStore: () =>
    set({
      drawingMode: 'NONE',
      currentShape: null,
      waypointsPreview: [],
      waypointsList: [],
      isNotReviewing: false,
      isEditable: false,
      qgcMissionData: null,
      isDebouncedReviewPending: false,
    }),
  isDebouncedReviewPending: false,
  setIsDebouncedReviewPending: (pending: boolean) =>
    set({ isDebouncedReviewPending: pending }),
}));
