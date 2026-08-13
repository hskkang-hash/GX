import { DeliveryHubsState } from '../types/IDeliveryHubs';

interface DeliveryHubsPageState {
  pageSize: number | null;
  currentPage: number;
  selectedRows: DeliveryHubsState[] | [];
  refreshTable: boolean | false;
  openOffcanvas: boolean | false;
  data: {
    data: DeliveryHubsState[] | null;
    totalItem: number | 0;
    totalPage: number | 0;
  };
}

export type DeliveryHubsPageAction =
  | { type: 'SET_PAGE_SIZE'; payload: number }
  | { type: 'SET_CURRENT_PAGE'; payload: number }
  | { type: 'SET_SELECTED_ROWS'; payload: DeliveryHubsState[] }
  | { type: 'TOGGLE_REFRESH'; payload?: boolean }
  | { type: 'OPEN_OFFCANVAS'; payload?: boolean }
  | {
      type: 'SET_DATA';
      payload: {
        data: DeliveryHubsState[];
        totalItem: number;
        totalPage: number;
      };
    };

export const initialDeliveryHubsPageState: DeliveryHubsPageState = {
  pageSize: null,
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

export function DeliveryHubsPageReducer(
  state: DeliveryHubsPageState,
  action: DeliveryHubsPageAction,
): DeliveryHubsPageState {
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
      return { ...state, data: action.payload };
    default:
      return state;
  }
}
