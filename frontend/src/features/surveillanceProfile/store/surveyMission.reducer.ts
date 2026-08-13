import {
  SurveyMissionPageState,
  SurveyMissionState,
} from '../types/surveyMission.types';

export type SurveyMissionPageAction =
  | { type: 'SET_PAGE_SIZE'; payload: number }
  | { type: 'SET_CURRENT_PAGE'; payload: number }
  | { type: 'SET_SELECTED_ROWS'; payload: SurveyMissionState[] }
  | { type: 'TOGGLE_REFRESH'; payload?: boolean }
  | { type: 'OPEN_OFFCANVAS'; payload?: boolean }
  | { type: 'OPEN_APPROVE_MISSION_MODAL'; payload?: boolean }
  | { type: 'OPEN_REJECT_MISSION_MODAL'; payload?: boolean }
  | {
      type: 'SET_DATA';
      payload: {
        data: SurveyMissionState[];
        totalItem: number;
        totalPage: number;
      };
    }
  | {
      type: 'SET_MISSION_ID';
      payload: number | null;
    }
  | {
      type: 'SET_HAS_PERMISSION_ACTION_SURVEY_MISSION';
      payload: boolean;
    };

export const initialSurveyMissionPageState: SurveyMissionPageState = {
  pageSize: null,
  currentPage: 1,
  selectedRows: [],
  hasPermissionActionSurveyMission: false,
  refreshTable: false,
  openOffcanvas: false,
  showApproveMissionModal: false,
  showRejectMissionModal: false,
  data: {
    data: [],
    totalItem: 0,
    totalPage: 0,
  },
  missionId: null,
};

export function SurveyMissionPageReducer(
  state: SurveyMissionPageState,
  action: SurveyMissionPageAction,
): SurveyMissionPageState {
  switch (action.type) {
    case 'SET_PAGE_SIZE':
      return { ...state, pageSize: action.payload };
    case 'SET_CURRENT_PAGE':
      return { ...state, currentPage: action.payload };
    case 'SET_SELECTED_ROWS':
      return { ...state, selectedRows: action.payload };
    case 'TOGGLE_REFRESH':
      return { ...state, refreshTable: action.payload || !state.refreshTable };
    case 'OPEN_OFFCANVAS':
      return {
        ...state,
        openOffcanvas: action.payload || !state.openOffcanvas,
      };
    case 'OPEN_APPROVE_MISSION_MODAL':
      return {
        ...state,
        showApproveMissionModal:
          action.payload || !state.showApproveMissionModal,
      };
    case 'OPEN_REJECT_MISSION_MODAL':
      return {
        ...state,
        showRejectMissionModal: action.payload || !state.showRejectMissionModal,
      };
    case 'SET_DATA':
      return {
        ...state,
        data: {
          data: action.payload.data,
          totalItem: action.payload.totalItem,
          totalPage: action.payload.totalPage,
        },
      };
    case 'SET_MISSION_ID':
      return { ...state, missionId: action.payload };
    case 'SET_HAS_PERMISSION_ACTION_SURVEY_MISSION':
      return { ...state, hasPermissionActionSurveyMission: action.payload };
    default:
      return state;
  }
}
