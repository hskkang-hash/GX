export interface OperationalNoticeState {
  id?: string;
  name?: string;
  active?: boolean;
  notShowCheckbox?: boolean;
  created_on?: string;
  content1?: string;
  content2?: string;
  content3?: string;
  group__name?: string;
  group__id?: number;
}

export interface OperationalNoticePageState {
  pageSize: number | null;
  currentPage: number;
  selectedRows: OperationalNoticeState[] | [];
  refreshTable: boolean | false;
  openOffcanvas: boolean | false;
  data: {
    data: OperationalNoticeState[] | null;
    totalItem: number | 0;
    totalPage: number | 0;
  };
}

export interface FieldOperationalNotice {
  label: string;
  value: string;
}

export interface CustomTiptapProps {
  content?: string;
  onChange?: (value: string) => void;
  label?: string;
  heightContent?: string;
  includeStyles?: boolean;
  fieldsTemplate?: FieldOperationalNotice[];
}

export interface ContentSection {
  id: string;
  title: string;
  content?: string;
  content1?: string;
  content2?: string;
  content3?: string;
}

export interface OperationalNoticeFormValues {
  group?: {
    value: number;
    label: string;
  };
  name: string;
  active?: boolean;
  contentSections?: ContentSection[];
}
