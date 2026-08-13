import dayjs from 'dayjs';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { FormProvider, useForm, useWatch } from 'react-hook-form';
import { Container, HeaderWithBtn, Main, useTheme, useUserInfo } from 'rj-core';

import Colors from '@/configs/Colors';

import Panel from '../components/Panel';
import useDashboard from '../hooks/useDashboard';
import { useConvertDate } from '../utils/formatDateTime';
import AbnormalSignsOverview from './components/AbnormalSignsOverview';
import DailyProfileOverview from './components/DailyProfileOverview';
import DroneStatusChart from './components/DroneStatusChart';
import NotificationsList from './components/NotificationsList';
import RegionDronesList from './components/RegionDronesList';
import SurveillanceMapDashboard from './components/SurveillanceMapDashboard';
import WeatherInfoSurveillance from './components/WeatherInfoSurveillance';
import WeatherInfoSkeletonSurveillance from './components/WeatherInforSurveillanceSkeleton';
import { useAbnormalSignsWebSocket } from './hooks/useAbnormalSignsWebSocket';
import useSurveillanceDashboard, {
  AbnormalSignMessage,
  AbnormalSignsOverview as AbnormalSignsOverviewType,
  DailyProfileOverview as DailyProfileOverviewType,
  DroneStatusOverview,
  RegionDrone,
} from './hooks/useSurveillanceDashboard';
import { ProfilePolygonData } from './mapsComponents/PolygonOverlay';
import { updateRelativeTime } from './utils/mockRealtimeNotifications';

const SurveillanceDashboard: React.FC = () => {
  const [theme] = useTheme();
  const headerPageRef = useRef(null);
  const {
    getDroneStatusOverview,
    getDailyProfileOverview,
    getAbnormalSignsOverview,
    getAbnormalSignsMessages,
    getTodayProfilesPolygon,
    getLocationWeather,
    getTodayRegionDrones,
  } = useSurveillanceDashboard();
  const userInfo = useUserInfo();
  console.log('userInfo', userInfo);
  const { dateFormat, convertDateToUTCStartOfDay, convertDateToUTCEndOfDay } =
    useConvertDate();
  const thisWeekStartDate = useRef(
    dayjs().startOf('week').format(dateFormat),
  ).current;
  const thisWeekEndDate = useRef(
    dayjs().endOf('week').format(dateFormat),
  ).current;

  const [droneStatus, setDroneStatus] = useState<DroneStatusOverview | null>(
    null,
  );
  const [dailyProfile, setDailyProfile] =
    useState<DailyProfileOverviewType | null>(null);
  const [abnormalSigns, setAbnormalSigns] =
    useState<AbnormalSignsOverviewType | null>(null);
  const [notifications, setNotifications] = useState<AbnormalSignMessage[]>([]);
  const [profilesPolygon, setProfilesPolygon] = useState<ProfilePolygonData[]>(
    [],
  );
  const [locationSetting, setLocationSetting] = useState(null);

  const [isLoadingAll, setIsLoadingAll] = useState(true);
  const [isLoadingDroneStatus, setIsLoadingDroneStatus] = useState(true);
  const [isLoadingDailyProfile, setIsLoadingDailyProfile] = useState(true);
  const [isLoadingAbnormalSigns, setIsLoadingAbnormalSigns] = useState(true);
  const [isLoadingNotifications, setIsLoadingNotifications] = useState(true);
  const [isLoadingWeather, setIsLoadingWeather] = useState(true);
  const [isLoadingRegionDrones, setIsLoadingRegionDrones] = useState(true);
  const [regionDrones, setRegionDrones] = useState<RegionDrone[]>([]);
  // Pagination state for region drones
  const [regionDronesPage, setRegionDronesPage] = useState(1);
  const [regionDronesTotalPages, setRegionDronesTotalPages] = useState(0);
  const [isLoadingRegionDronesPage, setIsLoadingRegionDronesPage] =
    useState(false);
  const regionDronesPageSize = 4;

  const [selectedDate, setSelectedDate] = useState<string>(
    dayjs().format('YYYY-MM-DD'),
  );

  // Selected detection state for syncing between notifications list and map markers
  const [selectedDetectionId, setSelectedDetectionId] = useState<
    string | number | null
  >(null);

  // Pagination state for notifications
  const [notificationsPage, setNotificationsPage] = useState(1);
  const [notificationsTotalPages, setNotificationsTotalPages] = useState(0);
  const [isLoadingMoreNotifications, setIsLoadingMoreNotifications] =
    useState(false);
  const notificationsPageSize = 5;

  // WebSocket state for realtime notifications
  // Status can be: "completed" (use polling) or "realtime" (use WebSocket)
  const [notificationStatus, setNotificationStatus] =
    useState<string>('completed');

  const [searchLocationCenter, setSearchLocationCenter] = useState<{
    lat: number;
    lng: number;
  } | null>(null);

  const methods = useForm({
    defaultValues: {
      start_date: thisWeekStartDate,
      end_date: thisWeekEndDate,
    },
  });
  const { control } = methods;

  const startTime = useWatch({
    control,
    name: 'start_date',
  });

  const endTime = useWatch({
    control,
    name: 'end_date',
  });

  const todayStart = dayjs().startOf('day').format(dateFormat);
  const todayEnd = dayjs().endOf('day').format(dateFormat);
  const formattedTodayStartTime = convertDateToUTCStartOfDay(todayStart);
  const formattedTodayEndTime = convertDateToUTCEndOfDay(todayEnd);

  // Initialize WebSocket for realtime abnormal signs notifications
  // Connects only when status === "realtime"
  const { isConnected: isWebSocketConnected } = useAbnormalSignsWebSocket({
    groupCode:
      (userInfo as { group_code?: string } | undefined)?.group_code || 'anyang',
    enabled: notificationStatus === 'realtime',
    onMessage: (message) => {
      // Prepend new realtime message to notifications list
      console.log('[DASHBOARD] Received realtime notification:', message);
      setNotifications((prev) => [message, ...prev]);
    },
  });

  // Update relative timestamps every second for all notifications
  // This ensures "Just now" → "5s ago" → "2m ago" updates in realtime
  useEffect(() => {
    const interval = setInterval(() => {
      setNotifications((prev) => {
        const updated = updateRelativeTime(prev);
        // Only update if at least one relative_time actually changed
        // This prevents unnecessary re-renders when times are still the same
        const hasChanged = prev.some(
          (msg, idx) => msg.relative_time !== updated[idx]?.relative_time,
        );
        return hasChanged ? updated : prev;
      });
    }, 1000); // Update every second

    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    setIsLoadingAll(true);
    setIsLoadingDroneStatus(true);
    setIsLoadingDailyProfile(true);
    setIsLoadingAbnormalSigns(true);
    setIsLoadingNotifications(true);
    setIsLoadingWeather(true);
    setIsLoadingRegionDrones(true);

    const formattedStartTime = convertDateToUTCStartOfDay(startTime);
    const formattedEndTime = convertDateToUTCEndOfDay(endTime);

    try {
      // Fetch all data in parallel and update UI as each completes
      const promises = [
        // Drone Status
        getDroneStatusOverview()
          .then((res) => {
            if (res.success && res.data) {
              setDroneStatus(res.data);
            }
          })
          .finally(() => setIsLoadingDroneStatus(false)),

        // Daily Profile
        getDailyProfileOverview(selectedDate)
          .then((res) => {
            if (res.success && res.data) {
              setDailyProfile(res.data);
            }
          })
          .finally(() => setIsLoadingDailyProfile(false)),

        // Abnormal Signs
        getAbnormalSignsOverview(formattedStartTime, formattedEndTime)
          .then((res) => {
            if (res.success && res.data) {
              setAbnormalSigns(res.data);
            }
          })
          .finally(() => setIsLoadingAbnormalSigns(false)),

        // Notifications
        getAbnormalSignsMessages(
          formattedTodayStartTime,
          formattedTodayEndTime,
          100,
          1,
          notificationsPageSize,
        )
          .then((res) => {
            if (res.success && res.data) {
              setNotifications(res.data.messages || []);
              setNotificationsPage(res.data.page || 1);
              setNotificationsTotalPages(res.data.total_pages || 0);
              console.log('notificationsRes.data', res.data);
              const status = res.data.status || 'completed';
              setNotificationStatus(status);
              console.log('[DASHBOARD] Notification status:', status);
            }
          })
          .finally(() => setIsLoadingNotifications(false)),

        // Profiles Polygon (no loading state - handled by map)
        getTodayProfilesPolygon().then((res) => {
          if (res.success && res.data && res.data.length > 0) {
            const transformedProfiles = res.data.map(
              (profile: {
                is_line_mission?: boolean;
                polygon: [number, number][] | { lat: number; lng: number }[];
              }) => ({
                is_line_mission: profile.is_line_mission || false,
                polygon: profile.polygon,
              }),
            );
            setProfilesPolygon(transformedProfiles);
          } else {
            setProfilesPolygon([]);
          }
        }),

        // Location Weather
        getLocationWeather()
          .then((res) => {
            if (res.success && res.data) {
              setLocationSetting(res.data);
            }
          })
          .finally(() => setIsLoadingWeather(false)),

        // Region Drones (fetch first page)
        getTodayRegionDrones(1, regionDronesPageSize)
          .then((res) => {
            if (res.success && res.data) {
              setRegionDrones(res.data.regions);
              setRegionDronesPage(res.data.page);
              setRegionDronesTotalPages(res.data.totalPages);
            }
          })
          .finally(() => setIsLoadingRegionDrones(false)),
      ];

      // Wait for all to complete
      await Promise.all(promises);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setIsLoadingAll(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  // Load more notifications (for realtime infinite scroll)
  const loadMoreNotifications = useCallback(async () => {
    if (
      isLoadingMoreNotifications ||
      notificationsPage >= notificationsTotalPages
    ) {
      return;
    }

    setIsLoadingMoreNotifications(true);
    const nextPage = notificationsPage + 1;

    try {
      const response = await getAbnormalSignsMessages(
        formattedTodayStartTime,
        formattedTodayEndTime,
        100,
        nextPage,
        notificationsPageSize,
      );

      if (response.success && response.data) {
        setNotifications((prev) => [
          ...prev,
          ...(response.data.messages || []),
        ]);
        setNotificationsPage(response.data.page || nextPage);
        setNotificationsTotalPages(response.data.total_pages || 0);
      }
    } catch (error) {
      console.error('Error loading more notifications:', error);
    } finally {
      setIsLoadingMoreNotifications(false);
    }
  }, [
    isLoadingMoreNotifications,
    notificationsPage,
    notificationsTotalPages,
    formattedTodayStartTime,
    formattedTodayEndTime,
    notificationsPageSize,
    getAbnormalSignsMessages,
  ]);

  // Handle page change for backend pagination (completed status)
  const handleNotificationPageChange = useCallback(
    async (page: number) => {
      if (isLoadingMoreNotifications || page < 1) {
        return;
      }

      setIsLoadingMoreNotifications(true);

      try {
        const response = await getAbnormalSignsMessages(
          formattedTodayStartTime,
          formattedTodayEndTime,
          100,
          page,
          notificationsPageSize,
        );

        if (response.success && response.data) {
          // Replace messages (not append) for backend pagination
          setNotifications(response.data.messages || []);
          setNotificationsPage(response.data.page || page);
          setNotificationsTotalPages(response.data.total_pages || 0);
        }
      } catch (error) {
        console.error('Error changing notification page:', error);
      } finally {
        setIsLoadingMoreNotifications(false);
      }
    },
    [
      isLoadingMoreNotifications,
      formattedTodayStartTime,
      formattedTodayEndTime,
      notificationsPageSize,
      getAbnormalSignsMessages,
    ],
  );

  // Handle page change for region drones pagination
  const handleRegionDronesPageChange = useCallback(
    async (page: number) => {
      if (isLoadingRegionDronesPage || page < 1 || page > regionDronesTotalPages) {
        return;
      }

      setIsLoadingRegionDronesPage(true);

      try {
        const response = await getTodayRegionDrones(page, regionDronesPageSize);

        if (response.success && response.data) {
          setRegionDrones(response.data.regions);
          setRegionDronesPage(response.data.page);
          setRegionDronesTotalPages(response.data.totalPages);
        }
      } catch (error) {
        console.error('Error changing region drones page:', error);
      } finally {
        setIsLoadingRegionDronesPage(false);
      }
    },
    [
      isLoadingRegionDronesPage,
      regionDronesTotalPages,
      regionDronesPageSize,
      getTodayRegionDrones,
    ],
  );

  const handleDateChange = useCallback(
    async (date: string) => {
      setSelectedDate(date);
      setIsLoadingDailyProfile(true);
      try {
        const { success, data } = await getDailyProfileOverview(date);
        if (success && data) {
          setDailyProfile(data);
        }
      } finally {
        setIsLoadingDailyProfile(false);
      }
    },
    [getDailyProfileOverview],
  );

  useEffect(() => {
    if (startTime !== thisWeekStartDate || endTime !== thisWeekEndDate) {
      setIsLoadingAbnormalSigns(true);
      const fetchDetectingAbnormalSigns = async () => {
        const formattedStartTime = convertDateToUTCStartOfDay(startTime);
        const formattedEndTime = convertDateToUTCEndOfDay(endTime);
        const { success, data } = await getAbnormalSignsOverview(
          formattedStartTime,
          formattedEndTime,
        );
        if (success && data) {
          setAbnormalSigns(data);
        } else {
          setAbnormalSigns(null);
        }
        setIsLoadingAbnormalSigns(false);
      };
      fetchDetectingAbnormalSigns();
    }
  }, [startTime, endTime]);

  const { saveWeatherData } = useDashboard();

  const saveWeatherSetting = useCallback(
    async (data: {
      latitude?: number;
      longitude?: number;
      address?: string;
    }) => {
      try {
        const { success, message } = await saveWeatherData({
          latitude: data?.latitude,
          longitude: data?.longitude,
          address: data?.address,
          is_surveillance_dashboard: true,
        });
        if (success) {
          console.log('Save weather setting success', message);
        } else {
          console.log('Save weather setting error', message);
        }
      } catch (error) {
        console.log('Error save weather setting', error);
      }
    },
    [saveWeatherData],
  );

  return (
    <Container>
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[]}
      />
      <Main>
        <FormProvider {...methods}>
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              height: 'calc(100vh - 5rem)',
              overflow: 'hidden',
              paddingTop: '0.755rem',
            }}
          >
            {/* HEADER SECTION */}
            <div
              style={{
                color: theme === 'dark' ? Colors.Gray3 : '#333',
                display: 'flex',
                flexDirection: 'column',
                paddingBottom: '1rem',
                flexShrink: 0,
              }}
            >
              <Panel
                fullHeight
                shouldHaveAspectRatio={false}
                contentStyles={{
                  paddingTop: '0.75rem',
                  paddingBottom: '0.75rem',
                }}
              >
                {isLoadingWeather ? (
                  <WeatherInfoSkeletonSurveillance />
                ) : (
                  <WeatherInfoSurveillance
                    data={locationSetting}
                    handleRefresh={fetchDashboardData}
                    isRefreshing={isLoadingWeather}
                    setSearchLocation={(locationValue) => {
                      setSearchLocationCenter(
                        locationValue?.lat && locationValue?.lng
                          ? {
                              lat: Number(locationValue?.lat),
                              lng: Number(locationValue?.lng),
                            }
                          : null,
                      );
                      if (
                        locationValue?.lat &&
                        locationValue?.lng &&
                        locationValue?.type !== 'weather_setting' &&
                        locationValue?.type !== 'location'
                      ) {
                        saveWeatherSetting({
                          latitude: locationValue?.lat,
                          longitude: locationValue?.lng,
                          address:
                            locationValue?.structured_formatting
                              ?.secondary_text || '',
                        });
                      }
                    }}
                  />
                )}
              </Panel>
            </div>

            <div
              style={{
                color: theme === 'dark' ? Colors.Gray3 : '#333',
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gridTemplateRows: 'auto 1fr auto',
                gap: '1.2rem',
                flex: 1,
                minHeight: 0,
                overflow: 'hidden',
              }}
            >
              {/* Row 1: Drone Status Chart (2 cols) + Daily Profile (1 col) + Abnormal Signs (1 col) */}
              {/* Drone Status Chart */}
              <Panel
                shouldHaveAspectRatio={false}
                panelStyles={{
                  width: '100%',
                  borderRadius: '0.75rem',
                  gridColumn: '1 / span 2',
                  minWidth: 0,
                  height: '25rem',
                }}
                contentStyles={{
                  padding: '1.25rem',
                  gap: '1rem',
                }}
              >
                <DroneStatusChart
                  data={droneStatus}
                  isLoading={isLoadingDroneStatus}
                />
              </Panel>

              {/* Daily Profile Overview */}
              <Panel
                shouldHaveAspectRatio={false}
                panelStyles={{
                  height: '25rem',
                  borderRadius: '0.75rem',
                }}
              >
                <DailyProfileOverview
                  data={dailyProfile}
                  isLoading={isLoadingDailyProfile}
                  onDateChange={handleDateChange}
                />
              </Panel>

              {/* Abnormal Signs Overview */}
              <Panel
                shouldHaveAspectRatio={false}
                panelStyles={{
                  height: '25rem',
                  borderRadius: '0.75rem',
                }}
              >
                <AbnormalSignsOverview
                  data={abnormalSigns}
                  isLoading={isLoadingAbnormalSigns}
                  formatDate={dateFormat}
                  control={control}
                />
              </Panel>

              {/* Row 2: Map (3 cols) + Notifications (1 col) */}
              <Panel
                shouldHaveAspectRatio={false}
                panelStyles={{
                  borderRadius: '0.75rem',
                  gridColumn: '1 / span 3',
                  minHeight: 0,
                  height: '100%',
                }}
                contentStyles={{
                  padding: 0,
                  height: '100%',
                }}
              >
                <SurveillanceMapDashboard
                  centerTerminal={searchLocationCenter}
                  profiles={profilesPolygon}
                  isLoading={isLoadingAll}
                  style={{
                    height: '100%',
                    width: '100%',
                  }}
                  detectionNotifications={notifications}
                  selectedDetectionId={selectedDetectionId}
                  onSelectionChange={(detection) => {
                    setSelectedDetectionId(detection?.id || null);
                  }}
                />
              </Panel>

              {/* Notifications Panel */}
              <Panel
                shouldHaveAspectRatio={false}
                panelStyles={{
                  width: '100%',
                  borderRadius: '0.75rem',
                  minHeight: 0,
                  height: '100%',
                }}
                contentStyles={{
                  padding: '1.25rem',
                  height: '100%',
                  overflow: 'hidden',
                }}
              >
                <NotificationsList
                  messages={notifications}
                  isLoading={isLoadingNotifications}
                  onLoadMore={loadMoreNotifications}
                  hasMore={notificationsPage < notificationsTotalPages}
                  isLoadingMore={isLoadingMoreNotifications}
                  isWebSocketConnected={isWebSocketConnected}
                  notificationStatus={
                    notificationStatus as 'realtime' | 'completed'
                  }
                  currentApiPage={notificationsPage}
                  totalApiPages={notificationsTotalPages}
                  onPageChange={handleNotificationPageChange}
                  onNotificationClick={(message) => {
                    // Only set selection if message has detected_image_path (has a marker)
                    if (message.detected_image_path && message.id) {
                      setSelectedDetectionId(message.id);
                    }
                  }}
                />
              </Panel>

              {/* Row 3: Region Drones List (Full width) */}
              {/* <Panel
                shouldHaveAspectRatio={false}
                panelStyles={{
                  width: '100%',
                  borderRadius: '0.75rem',
                  gridColumn: '1 / span 4',
                }}
                contentStyles={{
                  padding: '1.25rem',
                  height: '100%',
                }}
              > */}
              {(regionDrones.length > 0 || regionDronesTotalPages > 0) && (
                <div
                  style={{
                    width: '100%',
                    borderRadius: '0.75rem',
                    gridColumn: '1 / span 4',
                  }}
                >
                  <RegionDronesList
                    data={regionDrones}
                    isLoading={isLoadingRegionDrones}
                    currentPage={regionDronesPage}
                    totalPages={regionDronesTotalPages}
                    onPageChange={handleRegionDronesPageChange}
                    isLoadingPage={isLoadingRegionDronesPage}
                  />
                </div>
              )}
              {/* </Panel> */}
            </div>
          </div>
        </FormProvider>
      </Main>
    </Container>
  );
};

export default SurveillanceDashboard;
