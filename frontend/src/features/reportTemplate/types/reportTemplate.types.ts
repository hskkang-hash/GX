export interface ReportTemplateState {
  id: string;
  notShowCheckbox?: boolean;
  name?: string;
  is_enabled?: boolean;
  is_default?: boolean;
  template?: string;
  usage_count?: number;
  created_on?: string;
  group__name?: string;
}

export interface ReportTemplatePageState {
  pageSize: number | null;
  currentPage: number;
  selectedRows: ReportTemplateState[] | [];
  refreshTable: boolean | false;
  openOffcanvas: boolean | false;
  data: {
    data: ReportTemplateState[] | null;
    totalItem: number | 0;
    totalPage: number | 0;
  };
}

export interface FieldTemplate {
  label: string;
  value: string;
}

export interface CustomTiptapProps {
  content?: string;
  onChange?: (value: string) => void;
  label?: string;
  heightContent?: string;
  includeStyles?: boolean;
  fieldsTemplate?: FieldTemplate[];
}

export interface ReportTemplateFormValues {
  name: string;
  is_enabled?: boolean;
  is_default?: boolean;
  template?: string;
  group?: {
    value?: number | null;
    label?: string;
  } | null;
}

export interface BodyRequestReportTemplate {
  name: string;
  is_enabled?: boolean;
  is_default?: boolean;
  template?: string;
  group_id?: number | null;
}
