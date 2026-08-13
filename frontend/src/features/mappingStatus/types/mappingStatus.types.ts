export interface MappingStatusGroupState {
  status_guardianx: {
    id: number;
    name: string;
  };
  status_anyang: number[];
}

export interface MappingStatusState {
  id?: number | null;
  group__name: string;
  group__id: number;
}

export interface MappingStatusResponse {
  id: number;
  name: string;
  created_on: string;
  group__name: string;
  group__id: number;
  delivery_status__id: number;
  delivery_status__name: string;
  external_order_statuses_ids: number[];
}

export interface MappingStatusPageState {
  pageSize: number | null;
  currentPage: number;
  selectedRows: MappingStatusState[];
  selectedRow: MappingStatusState | null;
  refreshTable: boolean;
  openOffcanvas: boolean;
  offcanvasCreate: boolean;
  offcanvasEdit: boolean;
  data: {
    data: MappingStatusResponse[];
    totalItem: number;
    totalPage: number;
  };
}

export type MappingStatusPageAction =
  | { type: 'SET_PAGE_SIZE'; payload: number }
  | { type: 'SET_CURRENT_PAGE'; payload: number }
  | { type: 'SET_SELECTED_ROWS'; payload: MappingStatusState[] }
  | { type: 'SET_SELECTED_ROW'; payload: MappingStatusState | null }
  | { type: 'TOGGLE_REFRESH'; payload?: boolean }
  | { type: 'OPEN_OFFCANVAS'; payload?: boolean }
  | { type: 'SET_OFFCANVAS_CREATE'; payload: boolean }
  | { type: 'SET_OFFCANVAS_EDIT'; payload: boolean }
  | {
      type: 'SET_DATA';
      payload: {
        data: MappingStatusResponse[];
        totalItem: number;
        totalPage: number;
      };
    };

export interface MappingStatusFormValues {
  id?: number | null;
  group_id: number;
  mappings?:
    | {
        delivery_status_id: number;
        external_order_statuses: number[];
      }[]
    | null
    | [];
}
