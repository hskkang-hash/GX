// Types cho Route Export API

export interface ExportRouteParams {
  route_ids: string[];
}

export interface ExportRouteResponse {
  success: boolean;
  message: string;
}

export interface BackendFileResponse {
  file_url: string;
  file_name?: string;
}

export interface ExportRouteError {
  success: false;
  message: string;
}

export interface ExportRouteSuccess {
  success: true;
  message: string;
}

// Union type cho response
export type ExportRouteResult = ExportRouteSuccess | ExportRouteError;

// Types cho backend response
export interface BackendExportResponse {
  file_url?: string;
  file_name?: string;
  error?: string;
  message?: string;
}

// Types cho API configuration
export interface ApiConfig {
  responseType?: 'json' | 'blob' | 'text';
  headers?: Record<string, string>;
}

// Types cho download options
export interface DownloadOptions {
  fileName?: string;
  mimeType?: string;
  autoDownload?: boolean;
}
