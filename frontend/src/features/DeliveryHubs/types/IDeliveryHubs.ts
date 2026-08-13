import { ExceptionData, OperatingTimeData } from "@/components/HelperCellOperatingTime";

export interface DeliveryHubsState {
  id: string;
  code: string;
  avatar__file_url?: string;
  avatar_id?: string;
  name: string;
  active?: boolean;
  created_on?: string;
  terminal_base_type: string;
  full_address: string;
  address?: string;
  latitude: number;
  longitude: number;
  postal_code?: number | null | undefined;
  url?: string;
  manager?: string;
  manager_name?: string;
  note?: string;
  terminal_base_type__name?: string;
}

export interface DeliveryHubsStateResponse {
  data: DeliveryHubsState[];
  totalItem: 0;
  totalPage: 0;
}

export interface DeliveryHubsStateRequest {
  pageSize: number;
  currentPage: number;
  objSearch?: {
    searchParams?: {
      id: string;
      value: string;
    }[];
    sortParams?: {
      id: string;
      value: string;
    }[];
    filters?: {
      [key: string]: string | number | boolean;
    };
    startDate?: string;
    endDate?: string;
  };
}

export interface DeliveryHubsStore {
  deliveryHubDetail: DeliveryHubsState | null;
  setDeliveryHub: (deliveryHub: DeliveryHubsState) => void;
}

export interface Marker {
  lat: number | null | undefined;
  lng: number | null | undefined;
}

export interface FormOption {
  label: string;
  value: number;
  function_type?: string;
  code?: string;
}

export interface FormRegisterData {
  group?: {
    value: number | null;
    label: string | null;
    code: string | null;
  } | null;
  code: string | null;
  name: string | null;
  avatar?: File | null;
  terminal_type_ids?: FormOption[] | null;
  temp_terminal_type_ids?: FormOption[] | null;
  terminal_type_ids_docking?: FormOption[] | null;
  manager?: string | null;
  address?: string | null;
  city_province?: string | null;
  city_county_district?: string | null;
  ward_town_township?: string | null;
  street_address?: string | null;
  latitude: number | null;
  longitude: number | null;
  postal_code?: number | null;
  url?: string | null;
  note?: string | null;
  address_note?: string | null;
  delete_avatar?: boolean | null;
  is_docking_station?: boolean | null;
  function_ids?: FormOption | null;
  function_ids_docking?: FormOption | null;
  temp_function_ids?: FormOption[] | null;
  time_stops: {
    value: number | null;
    unit: string;
  };
  exceptions?: ExceptionData[];
  operating_times?: OperatingTimeData[];
}
