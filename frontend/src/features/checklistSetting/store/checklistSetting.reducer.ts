import {
  ChecklistSettingPageState,
  ChecklistSettingState,
  SettingCategoryState,
} from '../types/checklistSetting.types';

export type ChecklistSettingPageAction =
  | { type: 'SET_PAGE_SIZE'; payload: number }
  | { type: 'SET_CURRENT_PAGE'; payload: number }
  | { type: 'SET_SELECTED_ROWS'; payload: ChecklistSettingState[] }
  | { type: 'SET_SELECTED_ROW'; payload: ChecklistSettingState | null }
  | { type: 'TOGGLE_REFRESH'; payload?: boolean }
  | { type: 'OPEN_OFFCANVAS'; payload?: boolean }
  | { type: 'SET_OFFCANVAS_CREATE'; payload: boolean }
  | { type: 'SET_OFFCANVAS_EDIT'; payload: boolean }
  | { type: 'SET_SETTING_CATEGORY'; payload: SettingCategoryState[] }
  | {
      type: 'SET_DATA';
      payload: {
        data: ChecklistSettingState[];
        totalItem: number;
        totalPage: number;
      };
    };

export const initialChecklistSettingPageState: ChecklistSettingPageState = {
  pageSize: null,
  currentPage: 1,
  selectedRows: [],
  selectedRow: null,
  refreshTable: false,
  openOffcanvas: false,
  offcanvasCreate: false,
  offcanvasEdit: false,
  settingCategory: [],
  data: {
    data: [],
    totalItem: 0,
    totalPage: 0,
  },
};

export function ChecklistSettingPageReducer(
  state: ChecklistSettingPageState,
  action: ChecklistSettingPageAction,
): ChecklistSettingPageState {
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
      console.log('action.payload', action.payload);
      return {
        ...state,
        openOffcanvas:
          action.payload !== undefined ? action.payload : !state.openOffcanvas,
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
    case 'SET_SETTING_CATEGORY':
      return { ...state, settingCategory: action.payload };
    default:
      return state;
  }
}
