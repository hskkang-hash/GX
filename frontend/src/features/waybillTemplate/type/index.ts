import { SelectOption } from '../../../components/selects/CustomSelect';

type FieldType =
  | 'number'
  | 'text'
  | 'boolean'
  | 'date'
  | 'foreign_key'
  | 'table';

export interface WaybillTemplateFormValues {
  name: string;
  group?: SelectOption | null;
  template?: string;
  css?: string;
  is_default?: boolean;
  is_enabled?: boolean;
}

export interface WaybillTemplateData {
  id: number;
  name: string;
  group__name: string;
  group__id: number;
  template: string;
  created_on: string;
  is_enabled: boolean;
  is_default: boolean;
  usage_count: number;
}

export interface Field {
  name: string;
  field_type: FieldType;
  label: string;
  is_required: boolean | null;
  fields: Field[] | null;
  data_example?: FieldType;
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
  dataExample?: Record<string, any>;
}

export type Result = {
  data: Record<string, any>;
  fieldTemplate: FieldTemplate[];
};
