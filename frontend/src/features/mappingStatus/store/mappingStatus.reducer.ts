import {
  MappingStatusPageAction,
  MappingStatusPageState,
} from '../types/mappingStatus.types';

export const initialMappingStatusState: MappingStatusPageState = {
  pageSize: null,
  currentPage: 1,
  selectedRows: [],
  selectedRow: null,
  refreshTable: false,
  openOffcanvas: false,
  offcanvasCreate: false,
  offcanvasEdit: false,
  data: {
    data: [],
    totalItem: 0,
    totalPage: 0,
  },
};

export function MappingStatusPageReducer(
  state: MappingStatusPageState,
  action: MappingStatusPageAction,
): MappingStatusPageState {
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
    case 'SET_OFFCANVAS_CREATE':
      return { ...state, offcanvasCreate: action.payload };
    case 'SET_OFFCANVAS_EDIT':
      return { ...state, offcanvasEdit: action.payload };
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
