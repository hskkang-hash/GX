import { OpenInFull } from '@mui/icons-material';
import {
  Box,
  CircularProgress,
  IconButton,
  LinearProgress,
} from '@mui/material';
import { ConfigProvider, Dropdown, MenuProps } from 'antd';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BsChevronDown, BsChevronUp } from 'react-icons/bs';
import { RxDividerVertical } from 'react-icons/rx';
import { useNavigate } from 'react-router-dom';
import {
  CustomBtn,
  CustomizableTable,
  ToastTopHelper,
  useCalculateHeight,
  useTheme,
} from 'rj-core';

import FileTypeFile from '@/assets/images/FileTypeFile';
import FolderIcon from '@/assets/images/folder-icon.svg';
import Colors from '@/configs/Colors';
import { DownloadTemplateVideoAnalysis } from '@/features/DataAnalysis/components/DownloadTemplateVideoAnalysis';
import MediaGallery from '@/features/DataAnalysis/components/MediaGallery';
import { useDataAnalysis } from '@/features/DataAnalysis/hooks/useDataAnalysis';
import { CustomRoutes } from '@/services/API';
import { downloadElementAsPDF } from '@/utils/pdfUtils';
import { remToPx } from '@/utils/utils';

import { MediaDataState, VideoAnalysisItem } from '../types';
import { CustomVideoPlayer } from './CustomVideoPlayer';
import { FullscreenImageViewer } from './FullscreenImageViewer';

interface MediaPreviewPanelProps {
  selectedRow: MediaDataState | null;
  previewUrl: string | null;
  previewType: string | null;
  isLoadingPreview: boolean;
  detectionTypes: { value: string; label: string }[];
  onDetect: (detectionType: string) => void;
  videoAnalysisData: VideoAnalysisItem[];
  videoAnalysisId: number | null;
  isLoadingAnalysis: boolean;
  currentPrefix?: string; // Current folder path for back navigation
  isDetecting?: boolean; // Whether detection is in progress
  detectionProgress?: number; // Detection progress percentage (0-100)
}

export const MediaPreviewPanel = ({
  selectedRow,
  previewUrl,
  previewType,
  isLoadingPreview,
  detectionTypes,
  onDetect,
  videoAnalysisData,
  videoAnalysisId,
  isLoadingAnalysis,
  currentPrefix,
  isDetecting = false,
  detectionProgress = 0,
}: MediaPreviewPanelProps) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [isFullscreenOpen, setIsFullscreenOpen] = useState<boolean>(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const downloadTemplateRef = useRef<HTMLDivElement>(null);
  const { getDetailDataAnalysisAPI, detailDataAnalysis } = useDataAnalysis();
  const themeValue = useMemo(
    () => (theme === 'dark' ? 'dark' : 'light'),
    [theme],
  );

  // Fetch detail data when videoAnalysisId changes
  useEffect(() => {
    if (videoAnalysisId && videoAnalysisId > 0) {
      getDetailDataAnalysisAPI(videoAnalysisId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [videoAnalysisId]);

  const isVideoOrImage = useMemo(() => {
    return selectedRow?.type === 'video' || selectedRow?.type === 'image';
  }, [selectedRow]);

  // Refs for height calculation
  const videoHeaderRef = useRef<HTMLDivElement>(null);
  const videoPreviewRef = useRef<HTMLDivElement>(null);
  const aiSectionHeaderRef = useRef<HTMLDivElement>(null);

  // Calculate remaining height for AI analysis table
  // Subtracts: video header, video preview, ai section header, padding/borders
  const analysisTableHeight = useCalculateHeight({
    refElements: [videoHeaderRef, videoPreviewRef, aiSectionHeaderRef],
    additionalHeights: [48, remToPx(5)], // Padding and borders (1rem * 2 + borders)
  });

  const handleDropdownOpenChange = useCallback((open: boolean) => {
    setIsOpen(open);
  }, []);

  const dropdownTheme = useMemo(
    () => ({
      token: {
        controlItemBgActive: theme === 'dark' ? '#fff' : '#000',
        colorBgElevated: theme === 'dark' ? '#1F1F20' : '#fff',
        colorText: theme === 'dark' ? '#fff' : '#000',
        controlItemBgActiveHover:
          theme === 'dark' ? '#2d2e30' : 'rgba(0,0,0,0.04)',
        controlItemBgHover: theme === 'dark' ? '#2d2e30' : 'rgba(0,0,0,0.04)',
      },
    }),
    [theme],
  );

  const menuItems = useMemo(
    () =>
      detectionTypes.map((type) => ({
        label: t(type.label),
        key: type.value,
      })),
    [detectionTypes, t],
  );

  const settingsIcon = useMemo(
    () => (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <RxDividerVertical size={16} />
        {isOpen ? <BsChevronUp size={16} /> : <BsChevronDown size={16} />}
      </div>
    ),
    [isOpen],
  );

  const onClickDetect: MenuProps['onClick'] = ({ key }: { key: string }) => {
    if (selectedRow) {
      onDetect(key);
    }
  };

  const renderImageCell = useCallback(
    (row: {
      getValue: () => string;
      row: { original: { detected_image_path?: string } };
    }) => {
      const imagePath = row?.row?.original?.detected_image_path;
      if (
        !imagePath ||
        typeof imagePath !== 'string' ||
        imagePath.trim() === ''
      ) {
        return null;
      }
      return (
        <MediaGallery
          items={[
            {
              label: imagePath,
              value: imagePath,
              type: 'image',
            },
          ]}
          theme={themeValue}
        />
      );
    },
    [themeValue],
  );

  // Format seconds to video timestamp (e.g., 65.5 -> "1:05", 0.5 -> "0:00")
  const formatVideoTimestamp = useCallback(
    (seconds: number | null | undefined): string => {
      if (seconds === null || seconds === undefined) return '-';
      const totalSeconds = Math.floor(seconds);
      const minutes = Math.floor(totalSeconds / 60);
      const secs = totalSeconds % 60;
      return `${minutes}:${secs.toString().padStart(2, '0')}`;
    },
    [],
  );

  // Render timestamp cell - shows video time for videos, '-' for images
  const renderTimestampCell = useCallback(
    (row: {
      getValue: () => number | null | undefined;
      row: { original: { timestamp?: number | null } };
    }) => {
      const timestamp = row?.row?.original?.timestamp;
      // For images or missing timestamp, show '-'
      if (
        selectedRow?.type === 'image' ||
        timestamp === null ||
        timestamp === undefined
      ) {
        return '-';
      }
      return formatVideoTimestamp(timestamp);
    },
    [selectedRow?.type],
  );

  const COLUMNS_AIVideoAnalysis = useMemo(
    () => [
      {
        Header: t('Model'),
        accessor: 'object',
        enableSorting: false,
        enableColumnFilter: false,
      },
      {
        Header: t('Object Count'),
        accessor: 'object_count',
        enableSorting: false,
        enableColumnFilter: false,
      },
      {
        Header: t('Object'),
        accessor: 'detected_image_path',
        enableSorting: false,
        enableColumnFilter: false,
        cell: renderImageCell,
      },
      {
        Header: t('Detect Time'),
        accessor: 'timestamp',
        enableSorting: false,
        enableColumnFilter: false,
        cell: renderTimestampCell,
      },
    ],
    [renderImageCell, renderTimestampCell, formatVideoTimestamp, t],
  );

  const handleViewReport = useCallback(() => {
    if (videoAnalysisId && selectedRow) {
      const targetPath =
        CustomRoutes.mediaData.subRoutes.videoAnalysis.path.replace(
          ':id',
          videoAnalysisId.toString(),
        );
      const navigationState = {
        returnTo: CustomRoutes.mediaData.path,
        selectedRow: selectedRow,
        prefix: currentPrefix, // Include folder path for back navigation
      };

      // Navigate to MediaData Video Analysis page with state to restore selected row
      navigate(targetPath, {
        state: navigationState,
      });
    }
  }, [videoAnalysisId, selectedRow, navigate, currentPrefix]);

  // Helper function to validate and build video URL
  const buildVideoUrl = useCallback(
    (
      rawVideoPath: string | undefined | null,
    ): { videoUrl: string | null; videoFileName: string } => {
      if (!rawVideoPath || typeof rawVideoPath !== 'string') {
        return { videoUrl: null, videoFileName: '-' };
      }

      const videoUrl =
        rawVideoPath.startsWith('http://') ||
        rawVideoPath.startsWith('https://') ||
        rawVideoPath.startsWith('/')
          ? rawVideoPath
          : `https://${rawVideoPath}`;

      const isValidVideoUrl =
        videoUrl !== '-' &&
        typeof videoUrl === 'string' &&
        videoUrl.trim() !== '';

      const videoFileName = isValidVideoUrl
        ? videoUrl.split('/').pop() || 'Video'
        : '-';

      return { videoUrl: isValidVideoUrl ? videoUrl : null, videoFileName };
    },
    [],
  );

  const handleDownloadReport = useCallback(async (): Promise<void> => {
    if (!downloadTemplateRef.current) {
      return;
    }

    try {
      setIsDownloading(true);

      // Generate filename
      const { videoFileName } = buildVideoUrl(
        detailDataAnalysis?.video_path || selectedRow?.object_name,
      );
      const safeId =
        videoAnalysisId !== null &&
        !isNaN(videoAnalysisId) &&
        videoAnalysisId > 0
          ? videoAnalysisId
          : 'unknown';
      const filename = `DataAnalysis_${videoFileName === '-' ? 'report' : videoFileName}_${safeId}.pdf`;

      // Download as PDF with landscape orientation and full width
      await downloadElementAsPDF(downloadTemplateRef.current, filename, {
        margin: 10,
        format: 'a4',
        orientation: 'portrait',
        forceFullWidth: true,
      });

      ToastTopHelper.success(t('Report downloaded successfully'));
    } catch (error) {
      console.error('Error downloading PDF:', error);
      ToastTopHelper.error(t('Failed to download report'));
    } finally {
      setIsDownloading(false);
    }
  }, [detailDataAnalysis, selectedRow, videoAnalysisId, buildVideoUrl, t]);

  // Show placeholder for non-video/image files
  if (!isVideoOrImage || !selectedRow) {
    return (
      <>
        <Box
          sx={{
            width: '100%',
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '1rem',
            }}
          >
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <img
                src={FolderIcon}
                alt="folder-icon"
              />
            </Box>
            <p
              style={{
                margin: 0,
                textAlign: 'center',
                fontSize: '14px',
                color: Colors.Gray5,
              }}
            >
              {t('No preview available.')}
            </p>
          </Box>
        </Box>
        {/* Hidden component for PDF download */}
        <div style={{ position: 'absolute', left: '-9999px', top: '-9999px' }}>
          <DownloadTemplateVideoAnalysis
            ref={downloadTemplateRef}
            analysisType={selectedRow?.type === 'image' ? 'image' : 'video'}
            detailDataAnalysis={detailDataAnalysis || null}
          />
        </div>
      </>
    );
  }

  // Show full loading state only for initial load (no previewUrl yet)
  if (isLoadingPreview && !previewUrl) {
    return (
      <>
        <Box
          sx={{
            width: '100%',
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <CircularProgress />
          <p
            style={{
              marginTop: '1rem',
              color: theme === 'dark' ? '#fff' : '#333',
            }}
          >
            {t('Loading preview...')}
          </p>
        </Box>
        {/* Hidden component for PDF download */}
        <div style={{ position: 'absolute', left: '-9999px', top: '-9999px' }}>
          <DownloadTemplateVideoAnalysis
            ref={downloadTemplateRef}
            analysisType={selectedRow?.type === 'image' ? 'image' : 'video'}
            detailDataAnalysis={detailDataAnalysis || null}
          />
        </div>
      </>
    );
  }

  // Show video preview
  if (selectedRow.type === 'video' && previewUrl && previewType === 'video') {
    return (
      <>
        <Box
          sx={{
            width: '100%',
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {/* Header with title and detect button */}
          <Box
            ref={videoHeaderRef}
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              paddingBottom: '1rem',
              borderBottom: `1px solid ${theme === 'dark' ? '#2d2e30' : '#e0e0e0'}`,
            }}
          >
            <h3
              style={{ margin: 0, color: theme === 'dark' ? '#fff' : '#333' }}
            >
              {t('Video')}
            </h3>
            <ConfigProvider
              key="settings"
              theme={dropdownTheme}
            >
              <Dropdown
                trigger={['click']}
                placement="topRight"
                open={isOpen}
                onOpenChange={handleDropdownOpenChange}
                arrow={false}
                overlayClassName="custom-setting-multi-stream-monitor"
                menu={{
                  items: menuItems,
                  onClick: onClickDetect,
                }}
              >
                <CustomBtn
                  label={t('Detect')}
                  icon={settingsIcon}
                  isFlag={true}
                  type="button"
                  variant="outline"
                  color="primary"
                  size="sm"
                />
              </Dropdown>
            </ConfigProvider>
          </Box>

          {/* Video preview */}
          <Box
            ref={videoPreviewRef}
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: 0,
              margin: '1rem 0',
              overflow: 'hidden',
              position: 'relative',
            }}
          >
            <CustomVideoPlayer videoUrl={previewUrl} />
          </Box>

          {/* AI Video Data Analysis section */}
          <Box
            sx={{
              padding: '1rem',
              borderTop: `1px solid ${theme === 'dark' ? '#2d2e30' : '#e0e0e0'}`,
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
              flex: 1,
              minHeight: 0,
              overflow: 'hidden',
            }}
          >
            <Box
              ref={aiSectionHeaderRef}
              sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <h4
                style={{
                  margin: 0,
                  color: theme === 'dark' ? '#fff' : '#333',
                }}
              >
                {t('AI Video Data Analysis')}
              </h4>
              {videoAnalysisId && !isDetecting && (
                <Box sx={{ display: 'flex', gap: '0.5rem' }}>
                  <CustomBtn
                    label={t('View Report')}
                    onClick={handleViewReport}
                    type="button"
                    variant="outline"
                    color="primary"
                    size="sm"
                  />
                  <CustomBtn
                    label={t('Download Report')}
                    onClick={handleDownloadReport}
                    type="button"
                    variant="outline"
                    color="primary"
                    size="sm"
                    disabled={isDownloading}
                    loading={isDownloading}
                  />
                </Box>
              )}
            </Box>
            {isDetecting ? (
              <Box
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  alignItems: 'center',
                  padding: '2rem',
                  flex: 1,
                }}
              >
                <Box sx={{ width: '100%', maxWidth: 400 }}>
                  <LinearProgress
                    variant={
                      detectionProgress > 0 ? 'determinate' : 'indeterminate'
                    }
                    value={detectionProgress}
                    sx={{
                      height: 8,
                      borderRadius: 4,
                      backgroundColor: theme === 'dark' ? '#3d3d3d' : '#e0e0e0',
                      '& .MuiLinearProgress-bar': {
                        borderRadius: 4,
                        backgroundColor: '#1976d2',
                      },
                    }}
                  />
                </Box>
                <p
                  style={{
                    marginTop: '1rem',
                    color: theme === 'dark' ? '#999' : '#666',
                  }}
                >
                  {t('Detecting...')}
                </p>
              </Box>
            ) : isLoadingAnalysis || isLoadingPreview ? (
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  padding: '2rem',
                }}
              >
                <CircularProgress size={24} />
              </Box>
            ) : videoAnalysisData.length > 0 ? (
              <Box
                sx={{
                  flex: 1,
                  minHeight: 0,
                  overflow: 'auto',
                }}
              >
                <CustomizableTable
                  columns={COLUMNS_AIVideoAnalysis}
                  data={{
                    data: videoAnalysisData,
                    totalItem: videoAnalysisData.length,
                    totalPage: 1,
                  }}
                  stickyHeader
                  availableHeight={
                    analysisTableHeight > 100 ? analysisTableHeight : 200
                  }
                  hasPagination={false}
                  notUseGroupColumn
                  useSystemSetting
                  subTable
                  notShowSelectRow
                />
              </Box>
            ) : (
              <p
                style={{ margin: 0, color: theme === 'dark' ? '#999' : '#666' }}
              >
                {t('No detection results yet.')}
              </p>
            )}
          </Box>
        </Box>
        {/* Hidden component for PDF download */}
        <div style={{ position: 'absolute', left: '-9999px', top: '-9999px' }}>
          <DownloadTemplateVideoAnalysis
            ref={downloadTemplateRef}
            analysisType={selectedRow?.type === 'image' ? 'image' : 'video'}
            detailDataAnalysis={detailDataAnalysis || null}
          />
        </div>
      </>
    );
  }

  // Show image preview
  if (selectedRow.type === 'image' && previewUrl && previewType === 'image') {
    return (
      <>
        <Box
          sx={{
            width: '100%',
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: theme === 'dark' ? '#1F1F20' : '#fff',
            borderRadius: '8px',
            overflow: 'hidden',
          }}
        >
          {/* Header with title and detect button */}
          <Box
            ref={videoHeaderRef}
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              paddingBottom: '1rem',
              borderBottom: `1px solid ${theme === 'dark' ? '#2d2e30' : '#e0e0e0'}`,
            }}
          >
            <h3
              style={{ margin: 0, color: theme === 'dark' ? '#fff' : '#333' }}
            >
              {t('Image')}
            </h3>
            <ConfigProvider
              key="settings"
              theme={dropdownTheme}
            >
              <Dropdown
                trigger={['click']}
                placement="topRight"
                open={isOpen}
                onOpenChange={handleDropdownOpenChange}
                arrow={false}
                overlayClassName="custom-setting-multi-stream-monitor"
                menu={{
                  items: menuItems,
                  onClick: onClickDetect,
                }}
              >
                <CustomBtn
                  label={t('Detect')}
                  icon={settingsIcon}
                  isFlag={true}
                  type="button"
                  variant="outline"
                  color="primary"
                  size="sm"
                />
              </Dropdown>
            </ConfigProvider>
          </Box>

          {/* Image preview */}
          <Box
            ref={videoPreviewRef}
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: 0,
              overflow: 'auto',
              margin: '1rem 0',
              position: 'relative',
            }}
          >
            <img
              src={previewUrl}
              alt={selectedRow.object_name}
              style={{
                maxWidth: '100%',
                maxHeight: '100%',
                borderRadius: '8px',
                objectFit: 'contain',
                cursor: 'pointer',
              }}
              onClick={() => setIsFullscreenOpen(true)}
            />
            <IconButton
              onClick={() => setIsFullscreenOpen(true)}
              sx={{
                position: 'absolute',
                bottom: 8,
                right: 8,
                borderRadius: '8px',
                backgroundColor:
                  theme === 'dark' ? 'rgba(0, 0, 0, 0.5)' : '#FFFFFFCC',
                color: theme === 'dark' ? '#DDDFE2' : '#1F1F20',
                '&:hover': {
                  svg: {
                    transform: 'scale(1.1)',
                  },
                  backgroundColor:
                    theme === 'dark' ? 'rgba(0, 0, 0, 0.5)' : '#DDDFE2',
                  color: theme === 'dark' ? '#DDDFE2' : '#1F1F20',
                },
              }}
              size="small"
            >
              <OpenInFull fontSize="small" />
            </IconButton>
          </Box>

          {/* Fullscreen Image Modal */}
          <FullscreenImageViewer
            open={isFullscreenOpen}
            onClose={() => setIsFullscreenOpen(false)}
            imageUrl={previewUrl}
            imageName={selectedRow.object_name}
          />

          {/* AI Video Data Analysis section */}
          <Box
            sx={{
              padding: '1rem',
              borderTop: `1px solid ${theme === 'dark' ? '#2d2e30' : '#e0e0e0'}`,
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
              flex: 1,
              minHeight: 0,
              overflow: 'hidden',
            }}
          >
            <Box
              ref={aiSectionHeaderRef}
              sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <h4
                style={{
                  margin: 0,
                  color: theme === 'dark' ? '#fff' : '#333',
                }}
              >
                {t('AI Image Data Analysis')}
              </h4>
              {videoAnalysisId && !isDetecting && (
                <Box sx={{ display: 'flex', gap: '0.5rem' }}>
                  <CustomBtn
                    label={t('View Report')}
                    onClick={handleViewReport}
                    type="button"
                    variant="outline"
                    color="primary"
                    size="sm"
                  />
                  <CustomBtn
                    label={t('Download Report')}
                    onClick={handleDownloadReport}
                    type="button"
                    variant="outline"
                    color="primary"
                    size="sm"
                    disabled={isDownloading}
                    loading={isDownloading}
                  />
                </Box>
              )}
            </Box>
            {isDetecting ? (
              <Box
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  alignItems: 'center',
                  padding: '2rem',
                  flex: 1,
                }}
              >
                <Box sx={{ width: '100%', maxWidth: 400 }}>
                  <LinearProgress
                    variant={
                      detectionProgress > 0 ? 'determinate' : 'indeterminate'
                    }
                    value={detectionProgress}
                    sx={{
                      height: 8,
                      borderRadius: 4,
                      backgroundColor: theme === 'dark' ? '#3d3d3d' : '#e0e0e0',
                      '& .MuiLinearProgress-bar': {
                        borderRadius: 4,
                        backgroundColor: '#1976d2',
                      },
                    }}
                  />
                </Box>
                <p
                  style={{
                    marginTop: '1rem',
                    color: theme === 'dark' ? '#999' : '#666',
                  }}
                >
                  {t('Detecting...')}
                </p>
              </Box>
            ) : isLoadingAnalysis || isLoadingPreview ? (
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  padding: '2rem',
                }}
              >
                <CircularProgress size={24} />
              </Box>
            ) : videoAnalysisData.length > 0 ? (
              <Box
                sx={{
                  flex: 1,
                  minHeight: 0,
                  overflow: 'auto',
                }}
              >
                <CustomizableTable
                  columns={COLUMNS_AIVideoAnalysis}
                  data={{
                    data: videoAnalysisData,
                    totalItem: videoAnalysisData.length,
                    totalPage: 1,
                  }}
                  stickyHeader
                  availableHeight={
                    analysisTableHeight > 100 ? analysisTableHeight : 200
                  }
                  hasPagination={false}
                  notUseGroupColumn
                  useSystemSetting
                  subTable
                  notShowSelectRow
                />
              </Box>
            ) : (
              <p
                style={{ margin: 0, color: theme === 'dark' ? '#999' : '#666' }}
              >
                {t('No detection results yet.')}
              </p>
            )}
          </Box>
        </Box>
        {/* Hidden component for PDF download */}
        <div style={{ position: 'absolute', left: '-9999px', top: '-9999px' }}>
          <DownloadTemplateVideoAnalysis
            ref={downloadTemplateRef}
            analysisType={selectedRow?.type === 'image' ? 'image' : 'video'}
            detailDataAnalysis={detailDataAnalysis || null}
          />
        </div>
      </>
    );
  }

  // Fallback: show placeholder
  return (
    <>
      <Box
        sx={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '2rem',
          backgroundColor: theme === 'dark' ? '#1F1F20' : '#f5f5f5',
          borderRadius: '8px',
          color: theme === 'dark' ? '#fff' : '#333',
        }}
      >
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1rem',
          }}
        >
          <Box
            sx={{
              width: '80px',
              height: '80px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              '& svg': {
                width: '48px',
                height: '64px',
              },
            }}
          >
            <FileTypeFile color={theme === 'dark' ? '#999' : '#999'} />
          </Box>
          <p style={{ margin: 0, textAlign: 'center', fontSize: '14px' }}>
            {t('No preview available.')}
          </p>
        </Box>
      </Box>
      {/* Hidden component for PDF download */}
      <div style={{ position: 'absolute', left: '-9999px', top: '-9999px' }}>
        <DownloadTemplateVideoAnalysis
          ref={downloadTemplateRef}
          detailDataAnalysis={detailDataAnalysis || null}
        />
      </div>
    </>
  );
};
