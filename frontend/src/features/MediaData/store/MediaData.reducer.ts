import { MediaDataPageAction, MediaDataPageState } from '../types';

export const initialMediaDataState: MediaDataPageState = {
  detectionTypes: [],
  pageSize: null,
  currentPage: 1,
  breadcrumbItems: [],
  selectedRows: [],
  refreshTable: false,
  openOffcanvas: false,
  selectFolder: null,
  isOpenViewFile: false,
  viewFile: null,
  selectedRowForPreview: null,
  isLoadingPreview: false,
  videoAnalysisData: [],
  videoAnalysisId: null,
  isLoadingAnalysis: false,
  data: {
    data: [],
    totalItem: 0,
    totalPage: 0,
  },
};

export function MediaDataPageReducer(
  state: MediaDataPageState,
  action: MediaDataPageAction,
): MediaDataPageState {
  switch (action.type) {
    case 'SET_DETECTION_TYPES':
      return { ...state, detectionTypes: action.payload };
    case 'SET_PAGE_SIZE':
      return { ...state, pageSize: action.payload };
    case 'SET_CURRENT_PAGE':
      return { ...state, currentPage: action.payload };
    case 'SET_BREADCRUMB_ITEMS':
      return { ...state, breadcrumbItems: action.payload };
    case 'SET_SELECTED_ROWS':
      return { ...state, selectedRows: action.payload };
    case 'TOGGLE_REFRESH':
      return { ...state, refreshTable: action.payload || !state.refreshTable };
    case 'OPEN_OFFCANVAS':
      return {
        ...state,
        openOffcanvas: action.payload || !state.openOffcanvas,
      };
    case 'OPEN_VIEW_FILE':
      return {
        ...state,
        isOpenViewFile: action.payload || !state.isOpenViewFile,
      };
    case 'SET_VIEW_FILE':
      return {
        ...state,
        viewFile: action.payload,
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
    case 'SET_SELECTED_ROW_FOR_PREVIEW':
      return {
        ...state,
        selectedRowForPreview: action.payload,
      };
    case 'SET_LOADING_PREVIEW':
      return {
        ...state,
        isLoadingPreview: action.payload,
      };
    case 'SET_VIDEO_ANALYSIS_DATA':
      return {
        ...state,
        videoAnalysisData: action.payload,
      };
    case 'SET_VIDEO_ANALYSIS_ID':
      return {
        ...state,
        videoAnalysisId: action.payload,
      };
    case 'SET_LOADING_ANALYSIS':
      return {
        ...state,
        isLoadingAnalysis: action.payload,
      };
    default:
      return state;
  }
}
