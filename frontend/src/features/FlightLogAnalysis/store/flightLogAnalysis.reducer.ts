import {
  FlightLogAnalysisPage,
  FlightLogAnalysisPageAction,
} from '../types/flightLogAnalysis.types';

export const initialFlightLogAnalysisState: FlightLogAnalysisPage = {
  pageSize: null,
  currentPage: 1,
  selectedRows: [],
  selectedRow: null,
  refreshTable: false,
  openOffcanvas: false,
  modalDetail: false,
  data: {
    data: [],
    totalItem: 0,
    totalPage: 0,
  },
};

export function FlightLogAnalysisPageReducer(
  state: FlightLogAnalysisPage,
  action: FlightLogAnalysisPageAction,
): FlightLogAnalysisPage {
  switch (action.type) {
    case 'SET_PAGE_SIZE':
      return { ...state, pageSize: action.payload };
    case 'SET_CURRENT_PAGE':
      return { ...state, currentPage: action.payload };
    case 'SET_SELECTED_ROWS':
      return { ...state, selectedRows: action.payload };
    case 'SET_SELECTED_ROW':
      return { ...state, selectedRow: action.payload };
    case 'TOGGLE_REFRESH':
      return { ...state, refreshTable: action.payload || !state.refreshTable };
    case 'OPEN_OFFCANVAS':
      return {
        ...state,
        openOffcanvas: action.payload || !state.openOffcanvas,
      };
    case 'OPEN_MODAL_DETAIL':
      return {
        ...state,
        modalDetail:
          action.payload !== undefined ? action.payload : !state.modalDetail,
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
    default:
      return state;
  }
}
