import {
  OperationalNoticeState,
  OperationalNoticePageState,
} from '../types/operationalNotice.types';

export type OperationalNoticePageAction =
  | { type: 'SET_PAGE_SIZE'; payload: number }
  | { type: 'SET_CURRENT_PAGE'; payload: number }
  | { type: 'SET_SELECTED_ROWS'; payload: OperationalNoticeState[] }
  | { type: 'TOGGLE_REFRESH'; payload?: boolean }
  | { type: 'OPEN_OFFCANVAS'; payload?: boolean }
  | {
      type: 'SET_DATA';
      payload: {
        data: OperationalNoticeState[];
        totalItem: number;
        totalPage: number;
      };
    };

export const initialReportTemplatePageState: OperationalNoticePageState = {
  pageSize: 0,
  currentPage: 1,
  selectedRows: [],
  refreshTable: false,
  openOffcanvas: false,
  data: {
    data: [],
    totalItem: 0,
    totalPage: 0,
  },
};

export function OperatinalNoticePageReducer(
  state: OperationalNoticePageState,
  action: OperationalNoticePageAction,
): OperationalNoticePageState {
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
