export interface UnitInputProps {
  name: string;
  label?: string;
  required?: boolean;
  units?: string[];
  defaultValue?: {
    value: string;
    unit: string;
  };
  className?: string;
  style?: React.CSSProperties;
}

export interface UnitInputValue {
  value: string;
  unit: string;
}
export interface IUserInfo {
  id?: number;
  language__code?: string;
  settings?: {
    date_format__code?: string;
    time_format__code?: string;
    number_format__name?: string;
    decimal_places?: string | number;
  };
}
