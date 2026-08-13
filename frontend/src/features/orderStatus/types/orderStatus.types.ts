export interface OrderStatusState {
  id: number;
  name: string;
  value: string | null;
  created_on: string | null;
  text_color: string | null;
  background_color: string | null;
  border_color: string | null;
  group__name: string | null;
  group__id: number | null;
  no_background_color?: boolean;
  no_border_color?: boolean;
  name_en_translation: string | null;
  name_ko_translation: string | null;
  name_th_translation: string | null;
}

export interface OrderStatusResponse {
  id: number;
  name: string;
  name_en_translation: string | null;
  name_ko_translation: string | null;
  name_th_translation: string | null;
  group__name: string | null;
  group__id: number | null;
  value: string | null;
  created_on: string | null;
  text_color: string | null;
  background_color: string | null;
  border_color: string | null;
}

export interface OrderStatusPageState {
  pageSize: number | null;
  currentPage: number;
  selectedRows: OrderStatusState[];
  selectedRow: OrderStatusState | null;
  refreshTable: boolean;
  openOffcanvas: boolean;
  offcanvasCreate: boolean;
  offcanvasEdit: boolean;
  data: {
    data: OrderStatusState[];
    totalItem: number;
    totalPage: number;
  };
}

export type OrderStatusPageAction =
  | { type: 'SET_PAGE_SIZE'; payload: number }
  | { type: 'SET_CURRENT_PAGE'; payload: number }
  | { type: 'SET_SELECTED_ROWS'; payload: OrderStatusState[] }
  | { type: 'SET_SELECTED_ROW'; payload: OrderStatusState | null }
  | { type: 'TOGGLE_REFRESH'; payload?: boolean }
  | { type: 'OPEN_OFFCANVAS'; payload?: boolean }
  | { type: 'SET_OFFCANVAS_CREATE'; payload: boolean }
  | { type: 'SET_OFFCANVAS_EDIT'; payload: boolean }
  | {
      type: 'SET_DATA';
      payload: {
        data: OrderStatusState[];
        totalItem: number;
        totalPage: number;
      };
    };

export interface OrderStatusFormValues {
  id?: number | null;
  name: {
    en: string;
    ko: string;
    th: string;
  };
  value: string;
  text_color?: string | null;
  background_color?: string | null;
  border_color?: string | null;
  group_id?: number | null;
}
