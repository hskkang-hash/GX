import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

import { MediaDataState } from '../types';

/**
 * Store for tracking files currently being detected (no persistence needed)
 * Survives navigation between pages but resets on page refresh
 */
interface MediaDataDetectionState {
  // Set of full_object_name paths currently being detected
  detectingFiles: Set<string>;

  // Actions
  addDetectingFile: (filePath: string) => void;
  addDetectingFiles: (filePaths: string[]) => void;
  removeDetectingFile: (filePath: string) => void;
  clearDetectingFiles: () => void;
  isFileDetecting: (filePath: string) => boolean;
  hasDetectingFiles: () => boolean;
}

export const useMediaDataDetectionStore = create<MediaDataDetectionState>()(
  (set, get): MediaDataDetectionState => ({
    detectingFiles: new Set(),

    addDetectingFile: (filePath: string): void => {
      set((state) => ({
        detectingFiles: new Set(state.detectingFiles).add(filePath),
      }));
    },

    addDetectingFiles: (filePaths: string[]): void => {
      set((state) => {
        const newSet = new Set(state.detectingFiles);
        filePaths.forEach((path) => newSet.add(path));
        return { detectingFiles: newSet };
      });
    },

    removeDetectingFile: (filePath: string): void => {
      set((state) => {
        const newSet = new Set(state.detectingFiles);
        newSet.delete(filePath);
        return { detectingFiles: newSet };
      });
    },

    clearDetectingFiles: (): void => {
      set({ detectingFiles: new Set() });
    },

    isFileDetecting: (filePath: string): boolean => {
      return get().detectingFiles.has(filePath);
    },

    hasDetectingFiles: (): boolean => {
      return get().detectingFiles.size > 0;
    },
  }),
);

interface MediaDataNavigationState {
  // Navigation state for back navigation and reload persistence
  selectedRowForPreview: MediaDataState | null;
  currentPrefix: string | undefined;
  breadcrumbPath: string | undefined;

  // Actions
  setSelectedRowForPreview: (row: MediaDataState | null) => void;
  setCurrentPrefix: (prefix: string | undefined) => void;
  setBreadcrumbPath: (path: string | undefined) => void;
  clearNavigationState: () => void;
}

export const useMediaDataNavigationStore = create<MediaDataNavigationState>()(
  persist<MediaDataNavigationState>(
    (set): MediaDataNavigationState => ({
      selectedRowForPreview: null,
      currentPrefix: undefined,
      breadcrumbPath: undefined,

      setSelectedRowForPreview: (row: MediaDataState | null): void => {
        set({ selectedRowForPreview: row });
      },
      setCurrentPrefix: (prefix: string | undefined): void => {
        set({ currentPrefix: prefix });
      },
      setBreadcrumbPath: (path: string | undefined): void => {
        set({ breadcrumbPath: path });
      },
      clearNavigationState: (): void => {
        set({
          selectedRowForPreview: null,
          currentPrefix: undefined,
          breadcrumbPath: undefined,
        });
      },
    }),
    {
      name: 'guardianx-media-data-navigation',
      storage: createJSONStorage((): Storage => sessionStorage),
    },
  ),
);
