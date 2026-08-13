export interface OperationalNotice {
  id: number;
  title: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface NoticeSliderProps {
  items: OperationalNotice[];
  onCompleteNotice: (id: number) => void;
  onDeleteNotice: (id: number) => void;
}

export interface HandoverShiftState {
  handover_shift: number;
  id: number;
  name: string;
}

export interface HandoverManagementState {
  id: number;
  shift_id: number;
  data: HandoverShiftState[];
  created_time: string;
  date: string;
  total_content: number;
  shift__name: string;
  group__name: string;
  creator__full_name: string;
  editor__full_name: string;
}

export interface NoticeManagementState {
  id: number;
  created_time: string;
  creator__full_name: string;
  updated_time: string;
  editor__full_name: string;
  content_text: string;
  files: File[];
  deleted?: boolean;
}

export interface CompletedNoticeState {
  id: number;
  title: string;
  description: string;
  created_time: string;
  updated_time: string;
}

export interface HandoverNoticeState {
  id: number;
  handover_doc_id: number;
  content: string;
  is_notice: boolean;
  created_time: string;
  updated_time: string;
  creator_full_name: string;
  editor: string;
  editor_full_name: string;
  is_edit: boolean;
  handover_doc__id?: number;
  handover_doc__date_create_shift?: string;
  shift_name?: string;
  [key: string]: unknown;
}

export interface HandoverDutyDetailGrouped {
  handover_doc_id: number;
  shift_name: string;
  data: HandoverNoticeState[];
  date: string;
}
