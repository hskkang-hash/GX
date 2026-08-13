import { ConfigProvider, Dropdown, MenuProps } from 'antd';
import {
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
} from 'react';
import { useTranslation } from 'react-i18next';
import {
  BsArrowRight,
  BsChevronDown,
  BsChevronUp,
  BsEye,
} from 'react-icons/bs';
import { RxDividerVertical } from 'react-icons/rx';
import { useLocation } from 'react-router-dom';
import {
  Container,
  CustomBtn,
  CustomizableTable,
  HeaderWithBtn,
  Main,
  ToastTopHelper,
  useCalculateHeight,
  useTheme,
} from 'rj-core';

import { CustomRoutes } from '../../../services/API';
import { remToPx } from '../../../utils/utils';
import { MediaDataBreadcrumb } from '../components/MediaDataBreadcrumb';
import { MediaPreviewPanel } from '../components/MediaPreviewPanel';
import { ViewFile } from '../components/ViewFile';
import { MEDIA_DATA_COLUMNS } from '../data';
import { useMediaData } from '../hooks/useMediaData';
import { useMediaUploadDetectionWebSocket } from '../hooks/useMediaUploadDetectionWebSocket';
import {
  initialMediaDataState,
  MediaDataPageReducer,
} from '../store/MediaData.reducer';
import {
  useMediaDataDetectionStore,
  useMediaDataNavigationStore,
} from '../store/MediaData.store';
import { MediaDataState } from '../types';

export const MediaDataPage = () => {
  const [theme] = useTheme();
  const { t } = useTranslation();
  const location = useLocation();
  const headerPageRef = useRef<HTMLDivElement>(null);

  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [enableDetectionWs, setEnableDetectionWs] = useState<boolean>(false);
  // Track failed preview attempts to prevent infinite retry loop
  const [previewError, setPreviewError] = useState<string | null>(null);

  // Zustand store for detection tracking (no persistence, survives navigation)
  const {
    detectingFiles,
    addDetectingFiles,
    removeDetectingFile,
    hasDetectingFiles,
  } = useMediaDataDetectionStore();
  const updateBreadcrumbFromPathRef =
    useRef<
      (
        path: string,
        shouldPushHistory?: boolean,
        shouldUpdateSearch?: boolean,
      ) => void
    >(undefined);

  const [state, dispatch] = useReducer(
    MediaDataPageReducer,
    initialMediaDataState,
  );

  const {
    selectedRows,
    refreshTable,
    openOffcanvas,
    isOpenViewFile,
    breadcrumbItems,
    selectedRowForPreview,
    isLoadingPreview,
  } = state;

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [
      remToPx(10),
      breadcrumbItems.length > 0 ? remToPx(3) : 0,
    ],
  });
  const {
    getMediaDataAPI,
    setPageSize,
    setCurrentPage,
    data,
    pageSize,
    currentPage,
    objSearch,
    setObjSearch,
    previewFileAPI,
    viewFile,
    downloadFileAPI,
    detectFileTypeAPI,
    getDetectionTypeAPI,
    detectionTypes,
    videoAnalysisData,
    videoAnalysisId,
    isLoadingAnalysis,
  } = useMediaData();

  // WebSocket for upload detection progress
  const handleDetectionComplete = useCallback(
    (analysisId?: number, videoPath?: string) => {
      console.log(
        '[DETECTION] Detection completed, analysisId:',
        analysisId,
        'videoPath:',
        videoPath,
      );

      // Extract path from video_path URL and remove from detecting files
      let pathFromUrl: string | null = null;
      if (videoPath) {
        try {
          const url = new URL(videoPath);
          pathFromUrl = url.pathname; // e.g., "/guardianx-dev/anyang/.../file.mp4"

          // Remove from detecting files (Zustand store)
          removeDetectingFile(pathFromUrl);

          // Disable WebSocket if no more files are being detected
          if (!hasDetectingFiles()) {
            setEnableDetectionWs(false);
          }
        } catch (error) {
          console.error('[DETECTION] Error parsing video path:', error);
        }
      }

      // Match video_path with selectedRowForPreview.full_object_name
      // video_path: "https://files.gaion.dev/guardianx-dev/anyang/.../file.mp4"
      // full_object_name: "/guardianx-dev/anyang/.../file.mp4"
      if (selectedRowForPreview && pathFromUrl) {
        // Check if paths match
        if (pathFromUrl === selectedRowForPreview.full_object_name) {
          previewFileAPI(selectedRowForPreview.full_object_name);
          ToastTopHelper.success(t('Detection completed successfully'));
        } else {
          ToastTopHelper.success(t('Detection completed'));
        }
      } else if (selectedRowForPreview) {
        // No videoPath provided, refresh anyway
        previewFileAPI(selectedRowForPreview.full_object_name);
        ToastTopHelper.success(t('Detection completed successfully'));
      } else {
        ToastTopHelper.success(t('Detection completed'));
      }
    },
    [
      selectedRowForPreview,
      previewFileAPI,
      t,
      removeDetectingFile,
      hasDetectingFiles,
    ],
  );

  const handleDetectionError = useCallback(
    (error: string) => {
      console.error('[DETECTION] Detection error:', error);
      setEnableDetectionWs(false);
      ToastTopHelper.error(error || t('Detection failed'));
    },
    [t],
  );

  const {
    isConnected: isDetectionWsConnected,
    isProcessing: isDetectionProcessing,
    progress: detectionProgress,
  } = useMediaUploadDetectionWebSocket({
    enabled: enableDetectionWs,
    onComplete: handleDetectionComplete,
    onError: handleDetectionError,
  });

  // Zustand store for persist on reload
  const {
    selectedRowForPreview: persistedSelectedRow,
    currentPrefix: persistedPrefix,
    setSelectedRowForPreview: persistSelectedRow,
    setCurrentPrefix: persistCurrentPrefix,
    clearNavigationState,
  } = useMediaDataNavigationStore();

  // Track current row path to detect actual row changes
  const currentRowPathRef = useRef<string | null>(null);

  const setSelectedRowForPreview = useCallback(
    (row: MediaDataState | null) => {
      const newPath = row?.full_object_name || null;
      const isNewRow = newPath !== currentRowPathRef.current;

      console.log('[setSelectedRowForPreview]', {
        newPath,
        currentPath: currentRowPathRef.current,
        isNewRow,
      });

      dispatch({ type: 'SET_SELECTED_ROW_FOR_PREVIEW', payload: row });
      persistSelectedRow(row); // Persist to Zustand store

      // Only clear error when selecting a DIFFERENT row, not the same one
      if (isNewRow) {
        console.log('[setSelectedRowForPreview] Clearing previewError for new row');
        currentRowPathRef.current = newPath;
        setPreviewError(null);
      }
    },
    [persistSelectedRow],
  );

  const setLoadingPreview = useCallback((loading: boolean) => {
    dispatch({ type: 'SET_LOADING_PREVIEW', payload: loading });
  }, []);

  // Flag to skip clearing preview during restoration (back navigation / page reload)
  const isRestoringRef = useRef(false);

  // Restore from navigation state (back from video analysis) or persisted state (page reload)
  useEffect(() => {
    const navState = location.state as {
      selectedRow?: MediaDataState;
      returnTo?: string;
      prefix?: string;
    } | null;

    // Priority 1: Restore from navigation state (back from video analysis page)
    if (
      navState?.selectedRow &&
      location.pathname === CustomRoutes.mediaData.path
    ) {
      // Set flag to skip clearing preview in data fetch effect
      isRestoringRef.current = true;

      // Restore folder path if provided (use exact prefix with trailing slash)
      if (navState.prefix && restoreFromPrefixRef.current) {
        restoreFromPrefixRef.current(navState.prefix);
      }

      // Restore selected row and load preview
      setSelectedRowForPreview(navState.selectedRow);
      if (
        navState.selectedRow.type === 'video' ||
        navState.selectedRow.type === 'image'
      ) {
        setLoadingPreview(true);
        previewFileAPI(navState.selectedRow.full_object_name)
          .catch((error) => {
            console.error('Failed to load preview:', error);
            setPreviewError(
              error?.response?.data?.message || 'Failed to load preview',
            );
          })
          .finally(() => {
            setLoadingPreview(false);
          });
      }

      // Clear navigation state to prevent re-triggering
      window.history.replaceState({}, document.title);
      return;
    }

    // Priority 2: Restore from Zustand persisted state (page reload)
    if (
      persistedSelectedRow &&
      !selectedRowForPreview &&
      location.pathname === CustomRoutes.mediaData.path
    ) {
      // Set flag to skip clearing preview in data fetch effect
      isRestoringRef.current = true;

      // Restore folder path first (use exact prefix with trailing slash)
      if (persistedPrefix && restoreFromPrefixRef.current) {
        restoreFromPrefixRef.current(persistedPrefix);
      }

      // Restore selected row (use callback to properly handle state)
      setSelectedRowForPreview(persistedSelectedRow);

      // Load preview if video/image
      if (
        persistedSelectedRow.type === 'video' ||
        persistedSelectedRow.type === 'image'
      ) {
        setLoadingPreview(true);
        previewFileAPI(persistedSelectedRow.full_object_name)
          .catch((error) => {
            console.error('Failed to load preview:', error);
            setPreviewError(
              error?.response?.data?.message || 'Failed to load preview',
            );
          })
          .finally(() => {
            setLoadingPreview(false);
          });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state, location.pathname]);

  // Ensure preview is loaded when selectedRowForPreview exists but viewFile is null
  // This handles edge cases where row is restored but preview wasn't fetched
  // Skip if there's a preview error to prevent infinite retry loop
  useEffect(() => {
    console.log('[Preview useEffect] Check:', {
      selectedRowForPreview: selectedRowForPreview?.full_object_name,
      viewFile: !!viewFile,
      isLoadingPreview,
      previewError,
      type: selectedRowForPreview?.type,
    });

    if (
      selectedRowForPreview &&
      !viewFile &&
      !isLoadingPreview &&
      !previewError && // Don't retry if previous attempt failed
      (selectedRowForPreview.type === 'video' ||
        selectedRowForPreview.type === 'image')
    ) {
      console.log('[Preview useEffect] Calling previewFileAPI');
      setLoadingPreview(true);
      previewFileAPI(selectedRowForPreview.full_object_name)
        .catch((error) => {
          console.error('[Preview useEffect] Caught error:', error);
          const errorMsg =
            error?.response?.data?.message || 'Failed to load preview';
          console.log('[Preview useEffect] Setting previewError:', errorMsg);
          setPreviewError(errorMsg);
        })
        .finally(() => {
          console.log('[Preview useEffect] Finally - setting loading false');
          setLoadingPreview(false);
        });
    }
  }, [
    selectedRowForPreview,
    viewFile,
    isLoadingPreview,
    previewFileAPI,
    previewError,
  ]);

  // Track previous values to detect actual changes and prevent infinite loops
  const prevObjSearchRef = useRef<string | undefined>(undefined);
  const prevCurrentPageRef = useRef(currentPage);
  const prevPageSizeRef = useRef(pageSize);
  const getMediaDataAPIRef = useRef(getMediaDataAPI);

  // Keep ref updated
  useEffect(() => {
    getMediaDataAPIRef.current = getMediaDataAPI;
  }, [getMediaDataAPI]);

  useEffect(() => {
    if (!pageSize) return;

    // Serialize objSearch for comparison
    const objSearchStr = JSON.stringify(objSearch);
    const objSearchChanged = prevObjSearchRef.current !== objSearchStr;
    const pageChanged = prevCurrentPageRef.current !== currentPage;
    const pageSizeChanged = prevPageSizeRef.current !== pageSize;

    // Only fetch if something actually changed
    if (objSearchChanged || pageChanged || pageSizeChanged) {
      // Clear preview when navigating to different folder/search
      // BUT skip clearing if we're restoring from back navigation or page reload
      if ((objSearchChanged || pageChanged) && !isRestoringRef.current) {
        setSelectedRowForPreview(null);
        dispatch({ type: 'SET_VIEW_FILE', payload: null });
        setLoadingPreview(false);
      }
      // Reset restoration flag after data fetch is triggered
      isRestoringRef.current = false;

      // Update refs before calling API
      prevObjSearchRef.current = objSearchStr;
      prevCurrentPageRef.current = currentPage;
      prevPageSizeRef.current = pageSize;

      // Fetch data using ref to avoid dependency issues
      getMediaDataAPIRef.current();
    }
  }, [
    pageSize,
    objSearch,
    currentPage,
    setSelectedRowForPreview,
    setLoadingPreview,
  ]);

  useEffect(() => {
    getDetectionTypeAPI();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-reconnect WebSocket if there are files being detected (after navigation)
  useEffect(() => {
    if (hasDetectingFiles() && !enableDetectionWs) {
      console.log('[DETECTION] Reconnecting WebSocket - files still detecting');
      setEnableDetectionWs(true);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const setBreadcrumbItems = useCallback(
    (
      items: {
        url?: string;
        text?: string;
        func?: () => void;
        fullObjectName?: string;
      }[],
    ) => {
      dispatch({ type: 'SET_BREADCRUMB_ITEMS', payload: items });
    },
    [],
  );

  const setRefreshTable = useCallback((refresh: boolean) => {
    dispatch({ type: 'TOGGLE_REFRESH', payload: refresh });
  }, []);

  const pushHistoryState = useCallback((prefix: string) => {
    window.history.pushState(
      {
        prefix,
      },
      '',
      window.location.pathname,
    );
  }, []);

  // Restore navigation state from exact prefix (used for back navigation and page reload)
  // This preserves the exact prefix format including trailing slash
  const restoreFromPrefix = useCallback(
    (prefix: string) => {
      if (!prefix) {
        setObjSearch({});
        setBreadcrumbItems([]);
        setRefreshTable(true);
        return;
      }

      // Build breadcrumb from prefix path segments (exclude empty trailing segment)
      const pathSegments = prefix.split('/').filter(Boolean);

      const breadcrumbItemsFromPath = pathSegments.map((item, index) => {
        // Build cumulative path up to current segment (with trailing slash for folder)
        const cumulativePath = pathSegments.slice(0, index + 1).join('/') + '/';

        return {
          text: item,
          func: () => {
            // When clicking breadcrumb, restore to that level
            restoreFromPrefix(cumulativePath);
            pushHistoryState(cumulativePath);
          },
        };
      });

      const finalBreadcrumbItems = [
        {
          func: () => {
            setObjSearch({});
            setBreadcrumbItems([]);
            pushHistoryState('');
          },
        },
        ...breadcrumbItemsFromPath,
      ];

      setBreadcrumbItems(finalBreadcrumbItems);

      // Set objSearch to EXACT prefix (preserving trailing slash)
      setObjSearch({
        searchParams: [
          {
            id: 'prefix',
            value: prefix,
          },
        ],
      });

      setRefreshTable(true);
    },
    [setObjSearch, setBreadcrumbItems, setRefreshTable, pushHistoryState],
  );

  // Store restoreFromPrefix in ref for use in restoration effect
  const restoreFromPrefixRef = useRef(restoreFromPrefix);
  useEffect(() => {
    restoreFromPrefixRef.current = restoreFromPrefix;
  }, [restoreFromPrefix]);

  const updateBreadcrumbFromPath = useCallback(
    (path: string, shouldPushHistory = true, shouldUpdateSearch = true) => {
      const pathSegments = path.split('/').filter(Boolean);
      const breadcrumbItems = pathSegments.map((item, index) => {
        // Build cumulative path up to current segment
        const cumulativePath = pathSegments.slice(0, index + 1).join('/');

        return {
          text: item,
          func: () => {
            // Update breadcrumb to show only up to clicked item
            updateBreadcrumbFromPath(cumulativePath);
          },
        };
      });

      const newBreadcrumbItems = [
        {
          func: () => {
            setObjSearch({});
            setBreadcrumbItems([]);
            pushHistoryState('');
          },
        },
        ...breadcrumbItems,
      ];

      setBreadcrumbItems(newBreadcrumbItems);

      // Calculate prefix value for search and history
      const prefixValue =
        pathSegments.length > 0
          ? pathSegments.length === 1
            ? `${pathSegments[0]}/`
            : pathSegments.join('/')
          : '';

      // Update search params if needed
      if (shouldUpdateSearch) {
        setRefreshTable(true);
        if (prefixValue === '') {
          setObjSearch({});
        } else {
          setObjSearch({
            searchParams: [
              {
                id: 'prefix',
                value: prefixValue,
              },
            ],
          });
        }
      }

      // Push to history if needed
      if (shouldPushHistory) {
        pushHistoryState(prefixValue);
      }
    },
    [setObjSearch, setBreadcrumbItems, setRefreshTable, pushHistoryState],
  );

  // Store updateBreadcrumbFromPath in ref
  useEffect(() => {
    updateBreadcrumbFromPathRef.current = updateBreadcrumbFromPath;
  }, [updateBreadcrumbFromPath]);

  // Handle browser back/forward button
  useEffect(() => {
    const handlePopState = (event: PopStateEvent) => {
      if (event.state) {
        const { prefix } = event.state;

        if (prefix !== undefined) {
          // Restore from prefix using consistent function
          if (restoreFromPrefixRef.current) {
            restoreFromPrefixRef.current(prefix);
          }
        }
      } else {
        // If no state, go back to root
        setObjSearch({});
        setBreadcrumbItems([]);
        setRefreshTable(true);
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => {
      window.removeEventListener('popstate', handlePopState);
    };
  }, [setBreadcrumbItems, setObjSearch, setRefreshTable]);

  const createBreadcrumbItemsFromPath = useCallback(
    (path: string) => {
      const pathSegments = path.split('/').filter(Boolean);
      return pathSegments.map((item, index) => {
        // Build cumulative path up to current segment
        const cumulativePath = pathSegments.slice(0, index + 1).join('/');

        return {
          text: item,
          func: () => {
            // Update breadcrumb to show only up to clicked item
            updateBreadcrumbFromPath(cumulativePath);
          },
        };
      });
    },
    [updateBreadcrumbFromPath],
  );

  const handleSelectFolder = useCallback(
    (folder: MediaDataState | null) => {
      if (!folder?.full_object_name) return;

      const pathSegments = folder.full_object_name.split('/').slice(0, -1);
      const path = pathSegments.join('/');

      const newBreadcrumbItems = createBreadcrumbItemsFromPath(path);

      const finalBreadcrumbItems = [
        {
          func: () => {
            setObjSearch({});
            setBreadcrumbItems([]);
            pushHistoryState('');
          },
        },
        ...newBreadcrumbItems,
      ];

      setBreadcrumbItems(finalBreadcrumbItems);

      setObjSearch({
        searchParams: [
          {
            id: 'prefix',
            value: folder.full_object_name,
          },
        ],
      });

      // Push to history
      pushHistoryState(folder.full_object_name);
    },
    [
      setObjSearch,
      setBreadcrumbItems,
      createBreadcrumbItemsFromPath,
      pushHistoryState,
    ],
  );

  const setOpenOffcanvasCb = useCallback((open: boolean) => {
    dispatch({ type: 'OPEN_OFFCANVAS', payload: open });
  }, []);

  const setOpenViewFileCb = useCallback(
    (open: boolean, row: MediaDataState | null) => {
      dispatch({ type: 'OPEN_VIEW_FILE', payload: open });
      if (open) {
        previewFileAPI(row?.full_object_name || '');
      }
    },
    [previewFileAPI],
  );

  const handleSelectedRows = useCallback((rows: MediaDataState[]) => {
    dispatch({ type: 'SET_SELECTED_ROWS', payload: rows });
  }, []);

  const handleDownload = useCallback(async () => {
    const isFolderOrBucket = selectedRows.some(
      (row) => row.type === 'folder' || row.type === 'bucket',
    );

    await downloadFileAPI(
      selectedRows.map((row) => row.full_object_name),
      isFolderOrBucket ? 'folder' : 'file',
    );
  }, [downloadFileAPI, selectedRows]);

  const viewAction = useCallback(
    (
      type: 'video' | 'image' | 'folder' | 'bucket' | 'document',
      row: MediaDataState,
    ) => {
      switch (type) {
        case 'video':
        case 'image':
        case 'document':
          return (
            <BsEye
              size={16}
              onClick={() => {
                setOpenViewFileCb(true, row);
              }}
            />
          );
        case 'bucket':
        case 'folder':
          return (
            <BsArrowRight
              size={16}
              onClick={() => {
                handleSelectFolder(row);
                setRefreshTable(true);
              }}
              style={{ cursor: 'pointer' }}
            />
          );
        default:
          return null;
      }
    },
    [setOpenViewFileCb, handleSelectFolder, setRefreshTable],
  );

  const onClickButtonSetting: MenuProps['onClick'] = useCallback(
    async ({ key }: { key: string }) => {
      const mediaItems = selectedRows.map((row) => ({
        object_path: row.full_object_name,
        media_type: row.type,
      }));
      await detectFileTypeAPI({
        media_items: mediaItems,
        detection_type: key,
      });
      // Add files to detecting set (Zustand store)
      addDetectingFiles(selectedRows.map((row) => row.full_object_name));
      // Enable WebSocket to listen for detection progress
      setEnableDetectionWs(true);
    },
    [detectFileTypeAPI, selectedRows, addDetectingFiles],
  );

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

  // Calculate current prefix from objSearch for back navigation
  const currentPrefix = useMemo(() => {
    const prefixParam = objSearch?.searchParams?.find(
      (param) => param.id === 'prefix',
    );
    return prefixParam?.value as string | undefined;
  }, [objSearch]);

  // Persist currentPrefix when it changes
  useEffect(() => {
    persistCurrentPrefix(currentPrefix);
  }, [currentPrefix, persistCurrentPrefix]);

  const isDisabledDownload = useMemo(() => {
    return (
      selectedRows.length === 0 ||
      selectedRows.some((row) => row.type === 'bucket')
    );
  }, [selectedRows]);

  const isDisabledSettings = useMemo(() => {
    return (
      selectedRows.length === 0 ||
      selectedRows.some((row) => row.type === 'bucket' || row.type === 'folder')
    );
  }, [selectedRows]);

  const buttons = useMemo(
    () => [
      <CustomBtn
        key="download"
        label={t('Download')}
        onClick={handleDownload}
        type="button"
        variant="outline"
        color="primary"
        size="sm"
        disabled={isDisabledDownload}
      />,
      <ConfigProvider
        key="settings"
        theme={dropdownTheme}
      >
        <Dropdown
          open={isOpen}
          onOpenChange={handleDropdownOpenChange}
          trigger={['click']}
          placement="topLeft"
          arrow={false}
          disabled={isDisabledSettings}
          overlayClassName="custom-setting-multi-stream-monitor"
          menu={{
            items: menuItems,
            onClick: onClickButtonSetting,
          }}
        >
          <CustomBtn
            label={t('Settings')}
            icon={settingsIcon}
            isFlag={true}
            type="button"
            variant="outline"
            color="primary"
            size="sm"
          />
        </Dropdown>
      </ConfigProvider>,
    ],
    [
      t,
      handleDownload,
      isDisabledDownload,
      isDisabledSettings,
      dropdownTheme,
      menuItems,
      onClickButtonSetting,
      settingsIcon,
      isOpen,
      handleDropdownOpenChange,
    ],
  );

  const handleClickRow = useCallback(
    async (row: MediaDataState | { original: MediaDataState }) => {
      // Handle both formats: MediaDataState or { original: MediaDataState }
      const rowData = 'original' in row ? row.original : row;

      if (rowData.type === 'folder' || rowData.type === 'bucket') {
        handleSelectFolder(rowData);
        setRefreshTable(true);
        setSelectedRowForPreview(null);
      } else if (rowData.type === 'video' || rowData.type === 'image') {
        // Auto-fetch preview for video/image
        setSelectedRowForPreview(rowData);
        setLoadingPreview(true);
        try {
          await previewFileAPI(rowData.full_object_name);
        } catch (error) {
          console.error('Failed to load preview:', error);
          setPreviewError(
            (error as any)?.response?.data?.message || 'Failed to load preview',
          );
        } finally {
          setLoadingPreview(false);
        }
      } else {
        // For other file types, just set selected row (will show placeholder)
        setSelectedRowForPreview(rowData);
      }
    },
    [
      handleSelectFolder,
      setRefreshTable,
      setSelectedRowForPreview,
      previewFileAPI,
      setLoadingPreview,
    ],
  );

  const handleDetectInPreview = useCallback(
    async (detectionType: string) => {
      if (!selectedRowForPreview) return;

      const mediaItems = [
        {
          object_path: selectedRowForPreview.full_object_name,
          media_type: selectedRowForPreview.type,
        },
      ];
      await detectFileTypeAPI({
        media_items: mediaItems,
        detection_type: detectionType,
      });
      // Add file to detecting set (Zustand store)
      addDetectingFiles([selectedRowForPreview.full_object_name]);
      // Enable WebSocket to listen for detection progress
      setEnableDetectionWs(true);
    },
    [selectedRowForPreview, detectFileTypeAPI, addDetectingFiles],
  );

  // Find matching row in current data for highlighting (by full_object_name)
  // This ensures we use the actual row reference from table data
  const highlightRows = useMemo(() => {
    if (!selectedRowForPreview || !data.data) return [];
    const matchingRow = data.data.find(
      (row) => row.full_object_name === selectedRowForPreview.full_object_name,
    );
    return matchingRow ? [matchingRow] : [];
  }, [selectedRowForPreview, data.data]);

  // Check if currently selected row is being detected
  const isSelectedRowDetecting = useMemo(() => {
    if (!selectedRowForPreview) return false;
    return detectingFiles.has(selectedRowForPreview.full_object_name);
  }, [selectedRowForPreview, detectingFiles]);

  return (
    <Container>
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[]}
      />
      <Main>
        <div
          style={{
            display: 'flex',
            gap: '1rem',
            height: '100%',
          }}
        >
          {/* Left: Table */}
          <div
            style={{
              flex: '0 0 65%',
              minWidth: 0,
              height: 'calc(100vh - 5rem)',
              padding: '1rem',
              backgroundColor: theme === 'dark' ? '#1F1F20' : 'white',
              borderRadius: '8px',
              color: theme === 'dark' ? '#fff' : '#333',
            }}
          >
            {breadcrumbItems.length > 0 ? (
              <MediaDataBreadcrumb
                ref={headerPageRef}
                items={breadcrumbItems}
              />
            ) : null}
            <CustomizableTable
              subTable
              stickyHeader
              useSystemSetting
              availableHeight={spaceTableHeight}
              columns={MEDIA_DATA_COLUMNS}
              data={data}
              objSearch={objSearch}
              setObjSearch={setObjSearch}
              refreshTable={refreshTable}
              setRefreshTable={setRefreshTable}
              currentPage={currentPage}
              setCurrentPage={setCurrentPage}
              pageSize={pageSize}
              setPageSize={setPageSize}
              offcanvas={openOffcanvas}
              setOpenOffcanvas={setOpenOffcanvasCb}
              onSelectedRows={handleSelectedRows}
              onClickRow={handleClickRow}
              buttons={buttons}
              hightlidhtRow={highlightRows[0] || null}
            />
          </div>

          {/* Right: Preview Panel */}
          <div
            style={{
              flex: '0 0 35%',
              minWidth: 0,
              padding: '1rem',
              backgroundColor: theme === 'dark' ? '#1F1F20' : 'white',
              borderRadius: '8px',
              color: theme === 'dark' ? '#fff' : '#333',
            }}
          >
            <MediaPreviewPanel
              selectedRow={selectedRowForPreview}
              previewUrl={viewFile?.url || null}
              previewType={viewFile?.type || null}
              isLoadingPreview={isLoadingPreview}
              detectionTypes={detectionTypes}
              onDetect={handleDetectInPreview}
              videoAnalysisData={videoAnalysisData}
              videoAnalysisId={videoAnalysisId}
              isLoadingAnalysis={isLoadingAnalysis}
              currentPrefix={currentPrefix}
              isDetecting={isSelectedRowDetecting}
              detectionProgress={detectionProgress}
            />
          </div>
        </div>
        <ViewFile
          link={viewFile?.url || ''}
          type={
            viewFile?.type as
              | 'video'
              | 'image'
              | 'pdf'
              | 'docx'
              | 'ppt'
              | 'pptx'
          }
          isOpen={isOpenViewFile}
          onClose={() => setOpenViewFileCb(false, null)}
        />
      </Main>
    </Container>
  );
};
