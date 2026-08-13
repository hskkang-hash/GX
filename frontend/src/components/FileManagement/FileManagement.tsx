import { DownOutlined } from '@ant-design/icons';
import { Collapse, ConfigProvider, Upload, UploadFile } from 'antd';
import { JSX, useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AiOutlineClose } from 'react-icons/ai';
import { useTheme, useUserInfo } from 'rj-core';

import { useAutoClearFiles } from '../../hooks/useAutoClearFiles';
// import { useFileMessageHandler } from '../../hooks/useFileMessageHandler'; // No longer needed - WebSocket removed
import { useFileStatusChecker } from '../../hooks/useFileStatusChecker';
// import { useWebSocket } from '../../hooks/useWebSocket'; // No longer used - polling is used instead
import {
  GXUploadFile,
  useFileManagementStore,
} from '../../store/FileManagement.store';
import { FileItemRenderer } from './FileItemRenderer';
import './FileManagement.scss';

interface FileManagementProps {
  label?: string;
}

export const FileManagement = ({
  label = 'Upload & Download Files',
}: FileManagementProps): JSX.Element | null => {
  const { t } = useTranslation();
  const {
    fileManagement,
    downloadFileManagement,
    isVisible,
    setIsVisible,
    clearCompletedFiles,
  } = useFileManagementStore();
  const [theme] = useTheme();
  const userInfo = useUserInfo();
  // const { handleMessage } = useFileMessageHandler(); // No longer needed - WebSocket removed
  const [isExpanded, setIsExpanded] = useState(true);

  // NOTE: WebSocket is no longer used. The system now uses polling via useFileStatusChecker
  // const socketUrl = `${import.meta.env.VITE_STREAMING_WS}/ws/operational-data/notifications/`;
  // const { isConnected } = useWebSocket({
  //   url: socketUrl,
  //   onMessage: handleMessage,
  // });

  useAutoClearFiles();
  useFileStatusChecker();

  // Lấy userId hiện tại từ userInfo
  const currentUserId = useMemo(() => {
    if (!userInfo) return null;
    return (
      (userInfo as { user_id?: number | string })?.user_id ||
      (userInfo as { id?: number | string })?.id ||
      null
    );
  }, [userInfo]);

  // Filter files chỉ hiển thị files của user hiện tại
  const allFiles = useMemo(() => {
    const allFilesList = [...fileManagement, ...downloadFileManagement];
    if (currentUserId === null) {
      // Nếu không có userId, hiển thị tất cả (backward compatibility)
      return allFilesList;
    }
    return allFilesList.filter(
      (file) =>
        !file.userId ||
        file.userId === currentUserId ||
        file.userId === String(currentUserId),
    );
  }, [fileManagement, downloadFileManagement, currentUserId]);

  const hasFiles = useMemo(() => allFiles.length > 0, [allFiles]);

  // const hasProcessingFiles = useMemo(
  //   () => allFiles.some((file) => file.status === 'uploading'),
  //   [allFiles],
  // );

  // useBeforeUnloadWarning({
  //   hasFiles: hasProcessingFiles,
  //   onConfirm: clearAllFiles,
  // });

  const shouldRender = useMemo(() => {
    console.log('🟢 FileManagement shouldRender check:', {
      hasFiles,
      isVisible,
      fileCount: allFiles.length,
      fileManagementCount: fileManagement.length,
      downloadFileManagementCount: downloadFileManagement.length,
    });
    return hasFiles && isVisible;
  }, [hasFiles, isVisible, allFiles.length, fileManagement.length, downloadFileManagement.length]);

  const renderItem = useCallback(
    (originNode: React.ReactNode, gxFile: UploadFile) => (
      <FileItemRenderer
        originNode={originNode}
        gxFile={gxFile as unknown as GXUploadFile}
      />
    ),
    [],
  );

  const collapseTheme = useMemo(
    () => ({
      components: {
        Collapse: {
          headerBg: theme === 'dark' ? '#2D2E30' : '#ffffff',
          contentBg: theme === 'dark' ? '#000000' : '#ffffff',
        },
      },
      token: {
        colorText: theme === 'dark' ? '#ffffff' : '#000000',
      },
    }),
    [theme],
  );

  const collapseStyle = useMemo(
    () => ({
      width: '25rem',
      border: `1px solid ${theme === 'dark' ? '#3c3d3e' : '#ECECEF'}`,
      padding: '0.5rem',
    }),
    [theme],
  );

  const handleToggleExpand = useCallback(() => {
    setIsExpanded(!isExpanded);
  }, [isExpanded]);

  if (!shouldRender) return null;

  return (
    <div id="file-management">
      <ConfigProvider theme={collapseTheme}>
        <Collapse
          size="small"
          activeKey={isExpanded ? ['1'] : []}
          expandIconPosition="end"
          bordered={false}
          style={collapseStyle}
          className={`${theme === 'dark' ? 'dark' : 'light'}`}
          onChange={handleToggleExpand}
          items={[
            {
              key: '1',
              label: t(label),
              children: (
                <Upload<GXUploadFile>
                  listType="text"
                  itemRender={renderItem}
                  fileList={allFiles}
                />
              ),
              styles: {
                header: {
                  fontWeight: '600',
                  padding: '0.75rem 0.5rem',
                  alignItems: 'center',
                },
              },
              extra: (
                <div className="d-flex gap-3 align-items-center">
                  <DownOutlined
                    style={{
                      transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                      transition: 'transform 0.3s ease',
                    }}
                  />
                  <AiOutlineClose
                    onClick={(e) => {
                      e.stopPropagation();
                      // Remove finished/errored files, keep only in-progress ones
                      clearCompletedFiles();
                      setIsVisible(false);
                    }}
                    style={{
                      cursor: 'pointer',
                      fontSize: '14px',
                      opacity: 0.7,
                      transition: 'opacity 0.2s ease',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.opacity = '1')}
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.opacity = '0.7')
                    }
                  />
                </div>
              ),
              showArrow: false,
            },
          ]}
        />
      </ConfigProvider>
    </div>
  );
};
