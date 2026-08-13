export interface ChecklistSettingPageState {
  pageSize: number | null;
  currentPage: number;
  selectedRows: ChecklistSettingState[] | null;
  selectedRow: ChecklistSettingState | null;
  refreshTable: boolean | false;
  openOffcanvas: boolean | false;
  offcanvasCreate: boolean | false;
  offcanvasEdit: boolean | false;
  settingCategory: SettingCategoryState[] | [];
  data: {
    data: ChecklistSettingState[] | null;
    totalItem: number;
    totalPage: number;
  };
}

export interface ChecklistSettingState {
  id: number;
  item_name?: string;
  created_on?: string;
  category_id?: number;
  category__name?: string;
  group__name?: string;
  group__id?: number;
  is_active?: boolean;
  item_name_translations?: {
    en: string;
    ko: string;
    th: string;
  };
}

export interface ChecklistSettingFormValues {
  id?: number;
  item_name: {
    en: string;
    ko: string;
    th: string;
  };
  category?:
    | {
        value?: number;
        label?: string;
      }
    | number
    | null
    | undefined;
  group?: {
    value?: number;
    label?: string;
  };
}

export interface SettingCategoryState {
  id: number;
  name: string;
  code: string;
}

export interface BodyRequestChecklistSetting {
  item_name: {
    en: string;
    ko: string;
    th: string;
  };
  category: number;
  group_id?: number;
}
