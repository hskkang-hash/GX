import { useEffect, useMemo, useRef } from 'react';

import { useFileManagementStore } from '../store/FileManagement.store';

export const useAutoClearFiles = (): void => {
  const { fileManagement, downloadFileManagement } = useFileManagementStore();
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Memoize the check to avoid unnecessary recalculations
  const shouldClear = useMemo(() => {
    const allFiles = [...fileManagement, ...downloadFileManagement];
    return (
      allFiles.length > 0 && allFiles.every((item) => item.status === 'done')
    );
  }, [fileManagement, downloadFileManagement]);

  useEffect((): (() => void) | undefined => {
    // Clear existing timeout if any
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    if (shouldClear) {
      timeoutRef.current = setTimeout(() => {
        useFileManagementStore.setState({
          fileManagement: [],
          downloadFileManagement: [],
          isVisible: true,
        });
        timeoutRef.current = null;
      }, 7000);
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
  }, [shouldClear]);
};
