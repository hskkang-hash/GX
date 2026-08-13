export interface SearchParam {
  id: string;
  value: string | number | boolean;
}

// Define interface for sort params
export interface SortParam {
  id: string;
  desc: boolean;
}

export interface SearchObject {
  searchParams?: SearchParam[];
  filters?: Record<string, unknown>;
  sortParams?: SortParam[];
  mapped_status?: string;
  endDate?: string;
  startDate?: string;
  start_date_time?: string;
  end_date_time?: string;
}
