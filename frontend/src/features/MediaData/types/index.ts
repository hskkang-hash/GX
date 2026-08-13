export interface MediaDataState {
  id: number | string; // Can be full_object_name when BE doesn't return id
  full_object_name: string;
  object_name: string;
  type: 'folder' | 'video' | 'image' | 'bucket' | 'document';
  size: string;
  group__name: string;
  last_modified: string;
}

export interface VideoAnalysisItem {
  object: string;
  object_count: number | string;
  detected_image_path: string;
  detect_time: string;
  timestamp?: number | null; // Video timestamp in seconds (e.g., 0.5, 1, 3.5)
}

export interface MediaDataPageState {
  detectionTypes: { value: string; label: string }[];
  pageSize?: number | null;
  currentPage: number;
  breadcrumbItems: { url?: string; text?: string; func?: () => void }[];
  selectedRows: MediaDataState[] | [];
  refreshTable: boolean | false;
  openOffcanvas: boolean | false;
  selectFolder: MediaDataState | null;
  isOpenViewFile: boolean | false;
  viewFile: { url: string; type: string; analysisId?: number | null } | null;
  selectedRowForPreview: MediaDataState | null;
  isLoadingPreview: boolean;
  videoAnalysisData: VideoAnalysisItem[];
  videoAnalysisId: number | null;
  isLoadingAnalysis: boolean;
  data: {
    data: MediaDataState[];
    totalItem: number;
    totalPage: number;
  };
}

export type MediaDataPageAction =
  | {
      type: 'SET_DETECTION_TYPES';
      payload: { value: string; label: string }[];
    }
  | {
      type: 'SET_PAGE_SIZE';
      payload: number;
    }
  | {
      type: 'SET_CURRENT_PAGE';
      payload: number;
    }
  | {
      type: 'SET_BREADCRUMB_ITEMS';
      payload: { url?: string; text?: string; func?: () => void }[];
    }
  | {
      type: 'SET_SELECTED_ROWS';
      payload: MediaDataState[];
    }
  | {
      type: 'TOGGLE_REFRESH';
      payload?: boolean;
    }
  | {
      type: 'OPEN_OFFCANVAS';
      payload?: boolean;
    }
  | {
      type: 'SET_SELECT_FOLDER';
      payload: MediaDataState | null;
    }
  | {
      type: 'SET_DATA';
      payload: {
        data: MediaDataState[];
        totalItem: number;
        totalPage: number;
      };
    }
  | {
      type: 'OPEN_VIEW_FILE';
      payload?: boolean;
    }
  | {
      type: 'SET_VIEW_FILE';
      payload: { url: string; type: string; analysisId?: number | null } | null;
    }
  | {
      type: 'SET_SELECTED_ROW_FOR_PREVIEW';
      payload: MediaDataState | null;
    }
  | {
      type: 'SET_LOADING_PREVIEW';
      payload: boolean;
    }
  | {
      type: 'SET_VIDEO_ANALYSIS_DATA';
      payload: VideoAnalysisItem[];
    }
  | {
      type: 'SET_VIDEO_ANALYSIS_ID';
      payload: number | null;
    }
  | {
      type: 'SET_LOADING_ANALYSIS';
      payload: boolean;
    };
