import { OperatingTimeData } from "@/components/HelperCellOperatingTime";

interface SelectOption {
  value: string;
  label: string;
  code?: string;
}

interface FormData {
  code: string;
  name: string;
  terminal_type_ids: SelectOption[] | null;
  manufacturer: string;
  year_of_manufacture: string;
  url: string;
  note: string;
  time_stops: {
    value: number | null;
    unit: string;
  };
  group_id: SelectOption | null;
  address_type: 'geographic_coordinates' | 'address';
  latitude: number | null;
  longitude: number | null;
  city_province: string | null;
  city_county_district: string | null;
  ward_town_township: string | null;
  street_address: string;
  full_address: string;
  manager_name: string;
  postal_code: string;
  function_ids: [] | null;
  delete_avatar: false;
  terminal_purpose_id?: SelectOption | null;
  purpose_type_id?: SelectOption | null;
  group?: SelectOption | null;
  exceptions?: Array<{
    id?: number;
    exception_date: string | null;
    start_time: string | null;
    end_time: string | null;
    is_all_day: boolean;
    reason: string | null;
  }>;
  operating_times?: OperatingTimeData[];
}

interface FormTerminalsProps {
  initialData?: FormData;
  onSubmit: (data: FormData) => Promise<void>;
  onCancel: () => void;
  loading?: boolean;
  title?: string;
  breadcrumbItems?: { url?: string; text?: string }[];
  isDirtyEdit?: boolean;
  setIsDirtyEdit?: (isDirtyEdit: boolean) => void;
  editMode?: boolean;
}

export { FormTerminalsProps, FormData, SelectOption };
