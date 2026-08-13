import { SearchObject } from '@/types/paramAPI';

export interface LibraryData {
  id: number;
  name?: string;
  created_on?: string;
  main_type__name?: string;
  note?: string;
  active?: boolean;
  in_use?: boolean;
}

export interface LibraryListResponse {
  data: LibraryData[];
  totalItem: number;
  totalPage: number;
}

export interface LibraryListRequest {
  pageSize: number;
  currentPage: number;
  objSearch?: SearchObject;
}

// Define types for form data
export interface FormData {
  data: Record<string, any>;
  avatar: any;
  files: any[];
  dronesData: any;
  remove_files: any;
  remove_avatar: boolean;
}

export interface FormLibraryProps {
  initialData?: FormData;
  onSubmit: (data: FormData) => Promise<void>;
  onCancel: () => void;
  title?: string;
  breadcrumbItems?: { url?: string; text: string }[];
  loading?: boolean;
}
