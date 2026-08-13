import { useEffect } from 'react';

interface UseBeforeUnloadWarningProps {
  hasFiles: boolean;
  onConfirm: () => void;
}

// Global flag để tạm thời disable cảnh báo
let isDownloading = false;

export const setDownloadingFlag = (downloading: boolean): void => {
  isDownloading = downloading;
};

export const useBeforeUnloadWarning = ({
  hasFiles,
  onConfirm,
}: UseBeforeUnloadWarningProps): void => {
  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent): string | void => {
      // Không hiển thị cảnh báo nếu đang trong quá trình download
      if (hasFiles && !isDownloading) {
        // Modern browsers ignore custom messages, but we still need to prevent default
        event.preventDefault();
        // Return empty string or any string - browser will show its own message
        return '';
      }
    };

    const handleUnload = () => {
      if (hasFiles && !isDownloading) {
        onConfirm();
      }
    };

    if (hasFiles) {
      window.addEventListener('beforeunload', handleBeforeUnload);
      window.addEventListener('unload', handleUnload);
    }

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      window.removeEventListener('unload', handleUnload);
    };
  }, [hasFiles]);
};
