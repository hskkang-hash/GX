import type { UploadFile } from 'antd';
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export type GXFileType =
  | 'uploadFileDrone'
  | 'uploadFileRobot'
  | 'uploadVideoDrone'
  | 'uploadVideoRobot'
  | 'downloadFileDrone'
  | 'downloadFileRobot'
  | 'downloadFileAll'
  | 'importMission'
  | 'importFileAll'
  | 'downloadSurveillanceAnalysis';

export interface GXUploadFile extends UploadFile {
  gxId: number;
  gxType: GXFileType;
  taskId?: string;
  userId?: number | string;
  onUploadSuccess?: (file: GXUploadFile) => void | Promise<void>;
  /** When true, use checkTaskOperationalData endpoint instead of checkTaskSocket */
  useOperationalDataEndpoint?: boolean;
  /** Progress percentage from API (0-100) */
  progress?: number;
}

export interface GXDownloadFile extends UploadFile {
  gxId: string;
  gxType: GXFileType;
  taskId?: string;
  userId?: number | string;
  /** When true, use checkTaskOperationalData endpoint instead of checkTaskSocket */
  useOperationalDataEndpoint?: boolean;
  /** Progress percentage from API (0-100) */
  progress?: number;
}

interface FileManagementStore {
  isVisible: boolean;
  setIsVisible: (isVisible: boolean) => void;
  fileManagement: GXUploadFile[];
  setFileManagement: (fileManagement: GXUploadFile[]) => void;
  downloadFileManagement: GXDownloadFile[];
  setDownloadFileManagement: (downloadFileManagement: GXDownloadFile[]) => void;
  clearAllFiles: () => void;
  /** Remove files with status 'done' or 'error', keep only in-progress files */
  clearCompletedFiles: () => void;
}

export const useFileManagementStore = create<FileManagementStore>()(
  persist<FileManagementStore>(
    (set): FileManagementStore => ({
      isVisible: true,
      setIsVisible: (isVisible: boolean): void => {
        set({ isVisible });
      },
      fileManagement: [],
      setFileManagement: (fileManagement: GXUploadFile[]): void => {
        set({ fileManagement });
      },
      downloadFileManagement: [],
      setDownloadFileManagement: (
        downloadFileManagement: GXDownloadFile[],
      ): void => {
        set({ downloadFileManagement });
      },
      clearAllFiles: (): void => {
        set({ fileManagement: [], downloadFileManagement: [] });
      },
      clearCompletedFiles: (): void => {
        set((state) => ({
          fileManagement: state.fileManagement.filter(
            (f) => f.status !== 'done' && f.status !== 'error',
          ),
          downloadFileManagement: state.downloadFileManagement.filter(
            (f) => f.status !== 'done' && f.status !== 'error',
          ),
        }));
      },
    }),
    {
      name: 'guardianx-file-management',
      storage: createJSONStorage((): Storage => localStorage),
      partialize: (state) =>
        ({
          isVisible: state.isVisible,
          // Không persist callback trong file objects
          fileManagement: state.fileManagement.map((file) => {
            const { onUploadSuccess, ...fileWithoutCallback } = file;
            return fileWithoutCallback;
          }),
          downloadFileManagement: state.downloadFileManagement,
        }) as unknown as FileManagementStore,
    },
  ),
);
