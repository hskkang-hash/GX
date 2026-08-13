import { ConfigProvider, Dropdown, MenuProps } from 'antd';
import React, {
  RefObject,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useTranslation } from 'react-i18next';
import { BsGrid, BsGrid3X3Gap, BsLayoutSplit, BsSquare } from 'react-icons/bs';
import { IoSettingsOutline } from 'react-icons/io5';
import { TfiLayoutGrid4 } from 'react-icons/tfi';
import { Container, HeaderWithBtn, useTheme, useUserInfo } from 'rj-core';

import API, { endpoint } from '@/services/API';

import AIStreamView from './components/AIStreamView';
import { AddExternalStreamModal } from './components/AddExternalStreamModal';
import DroneCameraView from './components/DroneCameraView';
import { AIModal } from './components/DroneCameraView/components/AIModal';
import { getThemeStyles } from './styles';

// Layout configurations
export type LayoutType = '1x1' | '1x2' | '2x2' | '3x3' | '4x4' | 'custom';

interface LayoutConfig {
  type: LayoutType;
  columns: number;
  rows: number;
  maxStreams: number;
  icon: React.ReactNode;
  label: string;
}

interface AIModel {
  id: number;
  stream_monitor_id: number;
  ai_model_id: number;
  ai_model__name: string;
  ai_model__code: string;
  is_active: boolean;
  in_use: boolean;
  ai_stream_url?: string;
}

interface StreamMonitor {
  id: number;
  name: string;
  code: string;
  is_external: boolean;
  is_use_webrtc: boolean;
  rtsp_url: string;
  stream_path: string;
  stream_url: string;
  is_active: boolean;
  is_visualize: boolean;
  drone__id: number;
  drone__name: string;
  drone__serial_number: string;
  ip_source: string;
  ai_models: AIModel[];
  order: number;
  drone_color: string;
  external_drone_name?: string;
}

// Camera configurations with HLS and RTSP detection
export interface CameraConfig {
  id: string;
  name: string;
  isExternal?: boolean;
  is_use_webrtc: boolean;
  stream_url: string;
  rtsp_url: string;
  stream_path: string;
  isHls?: boolean;
  isRtsp?: boolean;
  isActive?: boolean;
  isVisualize?: boolean;
  code?: string;
  ai_models?: AIModel[];
  id_stream?: number;
  drone_id?: number;
  ip_source?: string;
  hasActiveAI?: boolean;
  aiStreamUrl?: string;
  drone_color?: string;
}

const MultiStreamMonitor = () => {
  const { t } = useTranslation();
  const LAYOUT_CONFIGS: Record<LayoutType, LayoutConfig> = {
    '1x1': {
      type: '1x1',
      columns: 1,
      rows: 1,
      maxStreams: 1,
      icon: <BsSquare size={24} />,
      label: t('Single View'),
    },
    '1x2': {
      type: '1x2',
      columns: 2,
      rows: 2,
      maxStreams: 2,
      icon: <BsLayoutSplit size={24} />,
      label: t('1x2 Layout'),
    },
    '2x2': {
      type: '2x2',
      columns: 2,
      rows: 2,
      maxStreams: 4,
      icon: <BsGrid size={24} />,
      label: t('2x2 Grid'),
    },
    '3x3': {
      type: '3x3',
      columns: 3,
      rows: 3,
      maxStreams: 9,
      icon: <BsGrid3X3Gap size={24} />,
      label: t('3x3 Grid'),
    },
    '4x4': {
      type: '4x4',
      columns: 4,
      rows: 4,
      maxStreams: 16,
      icon: <TfiLayoutGrid4 size={24} />,
      label: t('4x4 Grid'),
    },
    custom: {
      type: 'custom',
      columns: 2,
      rows: 2,
      maxStreams: 4,
      icon: <BsGrid size={24} />,
      label: t('Custom Layout'),
    },
  };
  const [theme] = useTheme();
  const [selectedLayout, setSelectedLayout] = useState<LayoutType>('2x2');
  const [hoveredLayout, setHoveredLayout] = useState<LayoutType | null>(null);
  const [enabledStreams, setEnabledStreams] = useState<Set<string>>(
    new Set([]),
  );
  const [showAIModal, setShowAIModal] = useState(false);
  const [showExternalStreamModal, setShowExternalStreamModal] = useState(false);
  const [cameraConfigs, setCameraConfigs] = useState<CameraConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const userInfo = useUserInfo();

  // New state for flexible layout features
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [isMultiSelectMode, setIsMultiSelectMode] = useState(false);
  const [selectedVideos, setSelectedVideos] = useState<Set<string>>(new Set());
  const [customLayout, setCustomLayout] = useState<LayoutConfig | null>(null);
  const [modalPosition, setModalPosition] = useState({ top: 0, left: 0 });
  const [isFeedMode, setIsFeedMode] = useState(false);
  const [feedVideos, setFeedVideos] = useState<Set<string>>(new Set());
  const headerRef = useRef<HTMLDivElement>(null);

  // Ref for settings button
  const settingsButtonRef = useRef<HTMLButtonElement>(null);

  const currentLayout = customLayout || LAYOUT_CONFIGS[selectedLayout];

  // Calculate maxStreams and adjust layout for AI streams
  const { maxStreams, adjustedLayout } = useMemo(() => {
    const baseMaxStreams = currentLayout.maxStreams;

    const aiStreamCount = cameraConfigs
      // .filter((s) => s.isActive && s.isVisualize && s.stream_url)
      .slice(0, baseMaxStreams)
      .filter(
        (cam) =>
          enabledStreams.has(cam.id) && cam.hasActiveAI && cam.aiStreamUrl,
      ).length;

    const totalItems =
      aiStreamCount > 0 && selectedLayout !== 'custom'
        ? baseMaxStreams + aiStreamCount
        : baseMaxStreams;

    // If we have AI streams and current layout is 1x1, adjust to horizontal layout
    if (selectedLayout === '1x1') {
      const horizontalLayout: LayoutConfig = {
        type: 'custom',
        columns: totalItems,
        rows: 1,
        maxStreams: totalItems,
        icon: <BsGrid size={24} />,
        label: `Custom (${totalItems} videos)`,
      };

      return {
        maxStreams: totalItems,
        adjustedLayout: horizontalLayout,
      };
    }

    return {
      maxStreams: totalItems,
      adjustedLayout: currentLayout,
    };
  }, [currentLayout, cameraConfigs, enabledStreams, selectedLayout]);

  const styles = getThemeStyles(theme, headerRef as RefObject<HTMLDivElement>);

  // Calculate modal position based on settings button
  const calculateModalPosition = useCallback(() => {
    if (settingsButtonRef.current) {
      const buttonRect = settingsButtonRef.current.getBoundingClientRect();
      setModalPosition({
        top: buttonRect.top - 10, // 10px gap above button (will be adjusted with modal height)
        left: buttonRect.left,
      });
    }
  }, []);

  // Update modal position when settings modal is shown
  useEffect(() => {
    if (showSettingsModal) {
      calculateModalPosition();
    }
  }, [showSettingsModal, calculateModalPosition]);

  const fetchStreamMonitors = useCallback(
    async (options?: { skipLayoutReset?: boolean }) => {
      try {
        setLoading(true);
        setError(null);

        const response = await API.get(endpoint.streamingList);
        console.log('[fetchStreamMonitors] API response:', response);

        if (response.success && response.data) {
          const streams: CameraConfig[] = response.data.map(
            (stream: StreamMonitor) => {
              // Check if stream has active AI models
              const activeAIModels =
                stream.ai_models?.filter(
                  (model) => model.is_active && model.in_use,
                ) || [];

              const hasActiveAI = activeAIModels.length > 0;
              const aiStreamUrl = hasActiveAI
                ? activeAIModels[activeAIModels.length - 1]?.ai_stream_url
                : undefined;

              return {
                id: stream.id,
                code: stream.code,
                name: stream.name,
                isExternal: stream.is_external || false,
                drone_color: stream.drone_color,
                is_use_webrtc: stream.is_use_webrtc,
                rtsp_url: stream.rtsp_url,
                stream_path: stream.stream_path,
                stream_url: stream.stream_url,
                isHls:
                  !stream.is_use_webrtc && stream.stream_url.includes('.m3u8'),
                isRtsp: !!stream.is_use_webrtc,
                isActive: stream.is_active,
                isVisualize: stream.is_visualize,
                ip_source: stream.ip_source,
                ai_models: stream.ai_models,
                id_stream: stream.id,
                drone_id: stream.drone__id,
                hasActiveAI,
                aiStreamUrl,
                order: stream.order,
                is_visualize: stream.is_visualize,
                drone__name: stream?.drone__name
                  ? stream.drone__name
                  : stream?.external_drone_name
                    ? stream.external_drone_name
                    : stream?.name || '',
              };
            },
          );

          setCameraConfigs(streams);

          // Auto-enable active streams
          const activeStreams = streams
            .filter((s) => s.isActive && s.isVisualize && s.stream_url)
            .map((s) => s.id);

          console.log('[fetchStreamMonitors] All streams:', streams.length);
          console.log(
            '[fetchStreamMonitors] Active streams (isActive && isVisualize && stream_url):',
            activeStreams,
          );
          console.log(
            '[fetchStreamMonitors] Streams detail:',
            streams.map((s) => ({
              id: s.id,
              name: s.name,
              isActive: s.isActive,
              isVisualize: s.isVisualize,
              stream_url: s.stream_url,
              isExternal: s.isExternal,
            })),
          );

          setEnabledStreams(new Set(activeStreams));

          // active streams with ai
          const activeStreamsWithAI = streams
            .filter((s) => s.isActive && s.isVisualize && s.stream_url)
            .filter((s) => s.hasActiveAI)
            .map((s) => s.id);

          // Auto-set layout based on total grid items (including AI streams)
          const activeCount = activeStreamsWithAI.length + activeStreams.length;

          const totalGridItems = activeCount; // Each AI stream adds one more grid item

          console.log(
            '[fetchStreamMonitors] activeStreamsWithAI:',
            activeStreamsWithAI.length,
          );
          console.log(
            '[fetchStreamMonitors] activeCount (total grid items):',
            activeCount,
          );
          console.log(
            '[fetchStreamMonitors] skipLayoutReset:',
            options?.skipLayoutReset,
          );

          // Skip layout reset if requested (e.g., when adding external stream)
          // Only recalculate layout on initial mount, not on refresh
          if (options?.skipLayoutReset) {
            console.log('[fetchStreamMonitors] Skipping layout reset');
          } else if (activeCount > 0) {
            let layoutType: LayoutType = '1x1';
            let customLayoutConfig: LayoutConfig | null = null;

            if (activeCount === 1) {
              layoutType = '1x1';
            } else if (activeCount === 2) {
              layoutType = '1x2';
            } else if (activeCount === 4) {
              layoutType = '2x2';
            } else if (activeCount === 9) {
              layoutType = '3x3';
            } else if (activeCount === 16) {
              layoutType = '4x4';
            } else {
              // Calculate custom layout for other counts
              let columns = 2;
              let rows = 2;

              if (totalGridItems <= 2) {
                columns = 2;
                rows = 1;
              } else if (totalGridItems <= 4) {
                columns = 2;
                rows = 2;
              } else if (totalGridItems <= 6) {
                columns = 3;
                rows = 2;
              } else if (totalGridItems <= 9) {
                columns = 3;
                rows = 3;
              } else if (totalGridItems <= 12) {
                columns = 4;
                rows = 3;
              } else {
                columns = 4;
                rows = 4;
              }

              customLayoutConfig = {
                type: 'custom',
                columns,
                rows,
                maxStreams: activeCount,
                icon: <BsGrid size={24} />,
                label: `Custom (${totalGridItems} videos)`,
              };
              layoutType = 'custom';
            }

            console.log(
              '[fetchStreamMonitors] Setting layout:',
              layoutType,
              customLayoutConfig,
            );
            setSelectedLayout(layoutType);
            setCustomLayout(customLayoutConfig);
          }
        }
      } catch (err) {
        console.error('Failed to fetch stream monitors:', err);
        setError('Failed to load stream monitors. Please try again.');
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  // Fetch streams on mount
  useEffect(() => {
    fetchStreamMonitors();
  }, [fetchStreamMonitors]);

  // Handle keyboard events for multi-select
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.altKey && showSettingsModal) {
        setIsMultiSelectMode(true);
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (!e.altKey) {
        setIsMultiSelectMode(false);
        // Don't clear selected videos when modal is open
        if (!showSettingsModal) {
          setSelectedVideos(new Set());
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [showSettingsModal]);

  // Handle video selection
  const handleVideoSelect = useCallback(
    (videoId: string) => {
      if (!isMultiSelectMode) return;

      setSelectedVideos((prev) => {
        const newSet = new Set(prev);
        if (newSet.has(videoId)) {
          newSet.delete(videoId);
        } else {
          newSet.add(videoId);
        }
        return newSet;
      });
    },
    [isMultiSelectMode],
  );

  // Generate custom layout based on selected videos (Feed button)
  const generateCustomLayout = useCallback(() => {
    const selectedCount = selectedVideos.size;
    if (selectedCount === 0) return;

    // Set feed mode and feed videos
    setIsFeedMode(true);
    setFeedVideos(new Set(selectedVideos));

    // Clear selected videos and close modal
    setSelectedVideos(new Set());
    setIsMultiSelectMode(false);
    setShowSettingsModal(false);
  }, [selectedVideos]);

  // Get active cameras and AI streams based on enabled streams
  const activeCameras = useMemo(() => {
    const cameras = cameraConfigs
      .filter((cam) => enabledStreams.has(cam.id))
      .slice(0, maxStreams);

    return cameras;
  }, [maxStreams, cameraConfigs, enabledStreams]);

  // Get active cameras with AI streams info
  const activeCamerasWithAI = useMemo(() => {
    return activeCameras.map((cam) => ({
      ...cam,
      hasAIStream: cam.hasActiveAI && cam.aiStreamUrl,
    }));
  }, [activeCameras]);

  // Create grid items: main streams + AI streams as separate items
  const allGridItems = useMemo(() => {
    const gridItems: (CameraConfig & { isAIStream: boolean })[] = [];

    // Add main streams
    activeCamerasWithAI.forEach((cam) => {
      gridItems.push({
        ...cam,
        isAIStream: false,
      });

      // If this stream has AI, add AI stream as separate item
      if (cam.hasAIStream) {
        gridItems.push({
          ...cam,
          id: `${cam.id}-ai`, // Keep the same ID structure for consistency
          name: `${cam.name} (AI)`,
          isAIStream: true,
        });
      }
    });

    return gridItems.slice(0, maxStreams);
  }, [activeCamerasWithAI, maxStreams]);

  // Filter grid items based on feed mode
  const filteredGridItems = useMemo(() => {
    // If not in feed mode, show all grid items
    if (!isFeedMode || feedVideos.size === 0) {
      return allGridItems;
    }

    // Filter to only show feed videos
    return allGridItems.filter((item) => {
      // For AI streams, check if the main stream is in feed
      if (item.isAIStream) {
        const mainStreamId = item.id.replace('-ai', '');
        return feedVideos.has(mainStreamId) || feedVideos.has(item.id);
      }

      // For main streams, check if in feed
      return feedVideos.has(item.id);
    });
  }, [allGridItems, isFeedMode, feedVideos]);

  // Calculate layout for filtered items
  const filteredLayout = useMemo(() => {
    const filteredCount = filteredGridItems.length;

    if (filteredCount === 0) {
      return adjustedLayout;
    }

    // If we have filtered items, create a custom layout for them
    let columns = 2;
    let rows = 2;

    if (filteredCount === 1) {
      columns = 1;
      rows = 1;
    } else if (filteredCount === 2) {
      // Special case: 2 videos should use 2x2 grid but only show videos in top 2 slots
      columns = 2;
      rows = 2;
    } else if (filteredCount <= 4) {
      columns = 2;
      rows = 2;
    } else if (filteredCount <= 6) {
      columns = 3;
      rows = 2;
    } else if (filteredCount <= 9) {
      columns = 3;
      rows = 3;
    } else if (filteredCount <= 12) {
      columns = 4;
      rows = 3;
    } else {
      columns = 4;
      rows = 4;
    }

    return {
      type: 'custom' as LayoutType,
      columns,
      rows,
      maxStreams: filteredCount === 2 ? 4 : filteredCount, // For 2 videos, reserve 4 slots but only show 2
      icon: <BsGrid size={24} />,
      label: `Custom (${filteredCount} videos)`,
    };
  }, [filteredGridItems, adjustedLayout]);

  const handleLayoutChange = useCallback(
    (layout: LayoutType) => {
      setSelectedLayout(layout);

      // Exit feed mode when changing layout
      if (isFeedMode) {
        setIsFeedMode(false);
        setFeedVideos(new Set());
      }

      // Reset custom layout when selecting predefined layouts
      if (layout !== 'custom') {
        setCustomLayout(null);

        // Restore all active streams when switching back to predefined layouts
        const activeStreams = cameraConfigs
          .filter((s) => s.isActive && s.isVisualize)
          .map((s) => s.id);

        setEnabledStreams(new Set(activeStreams));
      }
    },
    [cameraConfigs, isFeedMode],
  );

  const handleIconHover = useCallback((layout: LayoutType | null) => {
    setHoveredLayout(layout);
  }, []);

  const getGridStyle = useMemo(() => {
    // Use filtered layout if in feed mode, otherwise use adjusted layout
    const layoutToUse = isFeedMode ? filteredLayout : adjustedLayout;
    const { columns, rows } = layoutToUse;
    return {
      gridTemplateColumns: `repeat(${columns}, 1fr)`,
      gridTemplateRows: `repeat(${rows}, 1fr)`,
      height: '100%',
      minHeight: '100%',
    };
  }, [adjustedLayout, filteredLayout, isFeedMode]);

  const onClickButtonSetting: MenuProps['onClick'] = ({ key }) => {
    if (key === 'multi-stream-setting') {
      setShowAIModal((prev) => !prev);
    } else if (key === 'add-external-stream') {
      setShowExternalStreamModal(true);
    } else {
      setShowSettingsModal((prev) => !prev);
    }
  };

  return (
    <Container>
      <HeaderWithBtn
        buttons={[]}
        ref={headerRef}
      />
      <div style={styles.container}>
        {/* Sidebar */}
        <div style={styles.sidebar}>
          <div style={styles.sidebarIconWrap}>
            {Object.values(LAYOUT_CONFIGS)
              .filter((config) => config.type !== 'custom')
              .map((config) => (
                <button
                  key={config.type}
                  style={{
                    ...styles.sidebarIcon,
                    ...(selectedLayout === config.type
                      ? styles.sidebarIconActive
                      : {}),
                    ...(hoveredLayout === config.type
                      ? styles.sidebarIconHover
                      : {}),
                  }}
                  onClick={() => handleLayoutChange(config.type)}
                  onMouseEnter={() => handleIconHover(config.type)}
                  onMouseLeave={() => handleIconHover(null)}
                  title={config.label}
                >
                  {config.icon}
                </button>
              ))}
          </div>

          {/* Settings Button - Bottom Left */}
          <ConfigProvider
            theme={{
              token: {
                controlItemBgActive: theme === 'dark' ? '#fff' : '#000',
                colorBgElevated: theme === 'dark' ? '#1F1F20' : '#fff',
                colorText: theme === 'dark' ? '#fff' : '#000',
                controlItemBgActiveHover:
                  theme === 'dark' ? '#2d2e30' : 'rgba(0,0,0,0.04)',
                // controlItemBgHover:
                //   theme === 'dark' ? '#2d2e30' : 'rgba(0,0,0,0.04)',
              },
            }}
          >
            <Dropdown
              trigger={['click']}
              placement="topLeft"
              arrow={false}
              overlayClassName="custom-setting-multi-stream-monitor"
              menu={{
                items: [
                  {
                    label: t('Add External Stream'),
                    key: 'add-external-stream',
                  },
                  {
                    label: t('Multi-Stream Setting'),
                    key: 'multi-stream-setting',
                  },
                  {
                    label: t('Feed'),
                    key: 'feed',
                  },
                ],
                onClick: onClickButtonSetting,
              }}
            >
              <button
                ref={settingsButtonRef}
                style={{
                  ...styles.settingsButton,
                  ...(showSettingsModal ? styles.settingsButtonActive : {}),
                }}
                onMouseEnter={(e) => {
                  if (!showSettingsModal) {
                    // e.currentTarget.style.backgroundColor =
                    //   theme === 'dark' ? '#404040' : '#e9ecef';
                    e.currentTarget.style.color = 'var(--ga-primary)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!showSettingsModal) {
                    // e.currentTarget.style.backgroundColor =
                    //   theme === 'dark' ? '#1F1F20' : '#fff';
                    e.currentTarget.style.color =
                      theme === 'dark' ? '#888' : '#666';
                  }
                }}
                onClick={() => setShowSettingsModal(false)}
                title={t('Settings')}
              >
                <IoSettingsOutline size={24} />
              </button>
            </Dropdown>
          </ConfigProvider>
        </div>

        {/* Main Content */}
        <div style={styles.mainContent}>
          {/* Loading State */}
          {loading && (
            <div style={styles.loadingContainer}>
              <span>{t('Loading streams...')}</span>
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div style={styles.errorContainer}>
              <span>{t(error)}</span>
              <button
                style={styles.retryButton}
                onClick={fetchStreamMonitors}
              >
                {t('Retry')}
              </button>
            </div>
          )}

          {/* Grid Container */}
          {!loading && (
            <div
              style={{
                ...styles.gridContainer,
                ...getGridStyle,
              }}
            >
              {/* All Grid Items (Main streams + AI streams as separate items) */}
              {filteredGridItems.map((item, index) => {
                const hasVideo = item?.is_use_webrtc
                  ? item?.stream_path
                  : item?.stream_url;

                // For 2 videos in feed mode, only show first 2 videos (top row)
                const shouldShowVideo =
                  !isFeedMode || filteredGridItems.length !== 2 || index < 2;

                if (!hasVideo) {
                  return (
                    <div
                      key={`${item.id}`}
                      style={{
                        ...styles.emptyGridItem,
                        ...(selectedVideos.has(item.id) && {
                          border: '2px solid #007bff',
                          boxShadow: '0 0 8px rgba(0, 123, 255, 0.5)',
                        }),
                        ...(!shouldShowVideo && { display: 'none' }),
                      }}
                      onClick={() => handleVideoSelect(item.id)}
                    >
                      <div style={styles.emptySlotLabel}>
                        <span style={styles.emptySlotDot}></span>
                        {t('No Video Available')}
                      </div>
                    </div>
                  );
                }

                if (item.isAIStream) {
                  // Render AI stream as separate grid item
                  return (
                    <div
                      key={`ai-${item.id}`}
                      style={{
                        ...styles.gridItem,
                        ...(selectedVideos.has(item.id) && {
                          border: '2px solid #007bff',
                          boxShadow: '0 0 8px rgba(0, 123, 255, 0.5)',
                        }),
                        ...(!shouldShowVideo && { display: 'none' }),
                      }}
                      onClick={() => handleVideoSelect(item.id)}
                    >
                      <AIStreamView
                        streamUrl={item.aiStreamUrl!}
                        width="100%"
                        height="100%"
                        label={`${item.name}`}
                        droneCode={item.code}
                        droneColor={item?.drone__color}
                        gridColumn={filteredLayout.columns}
                        aiModelCode={
                          item.ai_models?.[0]?.ai_model__code || null
                        }
                      />
                    </div>
                  );
                }

                // Regular stream without AI
                return (
                  <div
                    key={`stream-${item.id}`}
                    style={{
                      ...styles.gridItem,
                      ...(selectedVideos.has(item.id) && {
                        border: '2px solid #007bff',
                        boxShadow: '0 0 8px rgba(0, 123, 255, 0.5)',
                      }),
                      ...(!shouldShowVideo && { display: 'none' }),
                    }}
                    onClick={() => handleVideoSelect(item.id)}
                  >
                    <DroneCameraView
                      index={index}
                      camera={item}
                      videoUrl={
                        item?.is_use_webrtc ? item.stream_path : item.stream_url
                      }
                      droneName={item.name}
                      droneCode={item.code}
                      isHls={!!item.isHls}
                      isRtsp={!!item.isRtsp}
                      droneColor={item.drone_color}
                      gridColumn={filteredLayout.columns}
                      streamId={item.id}
                      socketUrl={`${import.meta.env.VITE_STREAMING_WS}/ws/drawing/session/1/`}
                      sessionId="1"
                      userId={
                        (
                          userInfo as { id?: number | string }
                        )?.id?.toString() || '1'
                      }
                      width="100%"
                      height="100%"
                      onSaveSuccess={fetchStreamMonitors}
                      isExternal={item.isExternal}
                    />
                  </div>
                );
              })}

              {/* Empty Grid Items */}
              {Array.from(
                {
                  length:
                    (isFeedMode ? filteredLayout.maxStreams : maxStreams) -
                    filteredGridItems.length,
                },
                (_, index) => {
                  // For 2 videos in feed mode, show empty slots for bottom row
                  const isBottomRow =
                    isFeedMode && filteredGridItems.length === 2 && index >= 2;
                  const shouldShowEmpty =
                    !isFeedMode ||
                    filteredGridItems.length !== 2 ||
                    isBottomRow;

                  return (
                    <div
                      key={`empty-${index}`}
                      style={{
                        ...styles.emptyGridItem,
                        ...(!shouldShowEmpty && { display: 'none' }),
                      }}
                    >
                      <div style={styles.emptySlotLabel}>
                        <span style={styles.emptySlotDot}></span>
                        {t('No Video Available')}
                      </div>
                    </div>
                  );
                },
              )}
            </div>
          )}
        </div>

        {/* Settings Modal */}
        {showSettingsModal && (
          <div
            style={{
              position: 'fixed',
              bottom: '5rem',
              left: '1.5rem',
              backgroundColor: theme === 'dark' ? '#2a2a2a' : '#ffffff',
              borderRadius: '12px',
              padding: '1rem',
              maxWidth: '350px',
              width: 'auto',
              border: `1px solid ${theme === 'dark' ? '#404040' : '#e9ecef'}`,
              boxShadow:
                theme === 'dark'
                  ? '0 8px 32px rgba(0,0,0,0.5)'
                  : '0 8px 32px rgba(0,0,0,0.15)',
              zIndex: 999999,
            }}
          >
            <div style={{ marginBottom: '1rem' }}>
              <div
                style={{
                  color: theme === 'dark' ? '#ccc' : '#666',
                  fontSize: '13px',
                  lineHeight: '1.4',
                }}
              >
                <p style={{ marginBottom: '0.5rem' }}>
                  <span
                    dangerouslySetInnerHTML={{
                      __html: t(
                        'After selecting videos (multi-selection) with <strong>Alt + Click</strong>, click the <strong>Feed</strong> button to display only the selected videos on the screen (split view output).',
                      ),
                    }}
                  />
                </p>
                {selectedVideos.size > 0 && (
                  <div
                    style={{
                      backgroundColor:
                        theme === 'dark' ? '#007bff22' : '#e3f2fd',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      border: `1px solid ${theme === 'dark' ? '#007bff44' : '#007bff'}`,
                      marginTop: '0.5rem',
                    }}
                  >
                    <strong style={{ color: '#007bff' }}>
                      {t('{{count}} video(s) selected', {
                        count: selectedVideos.size,
                      })}
                    </strong>
                  </div>
                )}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                style={{
                  flex: 1,
                  padding: '8px 12px',
                  backgroundColor: '#007bff',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: selectedVideos.size > 0 ? 'pointer' : 'not-allowed',
                  fontSize: '12px',
                  fontWeight: 'bold',
                  opacity: selectedVideos.size > 0 ? 1 : 0.5,
                }}
                onClick={generateCustomLayout}
                disabled={selectedVideos.size === 0}
              >
                {t('Feed')}
              </button>
            </div>
          </div>
        )}

        {/* AI Modal */}
        {showAIModal && (
          <AIModal
            cameraConfigs={cameraConfigs}
            isOpen={showAIModal}
            onClose={() => setShowAIModal(false)}
            onSaveSuccess={fetchStreamMonitors}
          />
        )}

        {/* Add External Stream Modal */}
        {showExternalStreamModal && (
          <AddExternalStreamModal
            isOpen={showExternalStreamModal}
            onClose={() => setShowExternalStreamModal(false)}
            onSaveSuccess={() => fetchStreamMonitors({ skipLayoutReset: true })}
          />
        )}
      </div>
    </Container>
  );
};

export default MultiStreamMonitor;
