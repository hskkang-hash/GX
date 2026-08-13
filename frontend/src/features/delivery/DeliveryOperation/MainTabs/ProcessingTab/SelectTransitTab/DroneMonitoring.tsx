import {
  Box,
  Checkbox,
  FormControlLabel,
  IconButton,
  Paper,
  Popover,
  Skeleton,
  Typography,
} from '@mui/material';
import React, { useLayoutEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { IoSettingsOutline } from 'react-icons/io5';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useTheme } from 'rj-core';

import DeliveryLocationIcon from '@/assets/images/delivery_location.svg';
import DroneIcon from '@/assets/images/drone-icon-red.svg';
import { Tabs } from '@/components/Form/Tabs';
import CustomSelectControlled from '@/components/selects/CustomSelectControlled';
import Colors, { cardBg, infoBg, textLabel } from '@/configs/Colors';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import API, { endpoint } from '@/services/API';
import { remToPx } from '@/utils/utils';

import { Map } from '../../../../../../components/maps';
import { useOperationOrder } from '../../../hooks/useOperationOrder';
import StreamingDroneMonitor from './StreamingDroneMonitor';

// Extended colors for chart lines (supports unlimited items)
const CHART_COLORS = [
  '#FF6B6B', // Red
  '#FFB84D', // Orange
  '#4DD091', // Green
  '#4DABF7', // Blue
  '#9775FA', // Purple
  '#FF6B9D', // Pink
  '#FFA94D', // Light Orange
  '#51CF66', // Light Green
  '#339AF0', // Sky Blue
  '#CC5DE8', // Violet
  '#FFD43B', // Yellow
  '#FF8787', // Light Red
  '#69DB7C', // Mint
  '#74C0FC', // Light Blue
  '#DA77F2', // Lavender
  '#FFC078', // Peach
  '#94D82D', // Lime
  '#4FCBEB', // Cyan
  '#F783AC', // Rose
  '#FFE066', // Gold
];

// Function to get color for an item (cycles through colors if more items than colors)
const getColorForIndex = (index: number): string => {
  return CHART_COLORS[index % CHART_COLORS.length];
};

// Monitoring items configuration
interface MonitoringItem {
  id: string;
  label: string;
  type: string;
  checked: boolean;
  color: string;
  dataKey?: string;
}

const createMonitoringItems = (): MonitoringItem[] => {
  const items: MonitoringItem[] = [
    {
      id: 'x-axis',
      label: 'X-Axis',
      type: 'axis',
      checked: true,
      color: '#FF6B6B',
      dataKey: 'x',
    },
    {
      id: 'y-axis',
      label: 'Y-Axis',
      type: 'axis',
      checked: true,
      color: '#FFB84D',
      dataKey: 'y',
    },
    {
      id: 'z-axis',
      label: 'Z-Axis',
      type: 'axis',
      checked: true,
      color: '#4DD091',
      dataKey: 'z',
    },
    {
      id: 'vibe-x',
      label: 'Vibe X',
      type: 'vibration',
      checked: false,
      color: '#ff6b9d',
      dataKey: 'vibe_x',
    },
    {
      id: 'vibe-y',
      label: 'Vibe Y',
      type: 'vibration',
      checked: false,
      color: '#ff8fb3',
      dataKey: 'vibe_y',
    },
    {
      id: 'vibe-z',
      label: 'Vibe Z',
      type: 'vibration',
      checked: false,
      color: '#ffb3c9',
      dataKey: 'vibe_z',
    },
    {
      id: 'gps',
      label: 'GPS',
      type: 'gps',
      checked: false,
      color: '#4dabf7',
      dataKey: 'gps',
    },
  ];

  // Add RC input channels (ch1in - ch18in)
  for (let i = 1; i <= 18; i++) {
    items.push({
      id: `ch${i}in`,
      label: `ch${i}in`,
      type: 'rc_channel',
      checked: false,
      color: `hsl(${(i * 20) % 360}, 70%, 60%)`,
      dataKey: `ch${i}in`,
    });
  }

  // Add Servo output channels (ch1out - ch16out)
  for (let i = 1; i <= 16; i++) {
    items.push({
      id: `ch${i}out`,
      label: `ch${i}out`,
      type: 'servo_output',
      checked: false,
      color: `hsl(${(i * 15 + 180) % 360}, 70%, 60%)`,
      dataKey: `ch${i}out`,
    });
  }

  return items;
};

const infoCards = [
  {
    label: 'Current battery',
    value: 'battery_percent',
    unit: '%',
    color: '#2D8CFF',
    highlight: true,
  },
  {
    label: 'Distance traveled',
    value: 'distance_traveled',
    unit: 'km',
    color: '#2D8CFF',
  },
  {
    label: 'Wind Speed',
    value: 'wind_speed',
    unit: 'km/h',
    color: '#2D8CFF',
  },
  {
    label: 'Drone Temp.',
    value: 'temperature',
    unit: '℃',
    color: '#2D8CFF',
  },
];

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    name: string;
    color: string;
  }>;
}

const CustomTooltip = ({ active, payload }: CustomTooltipProps) => {
  if (active && payload && payload.length) {
    return (
      <Paper sx={{ p: 1, fontSize: 13, boxShadow: 2 }}>
        <div>
          {payload.map((entry, index) => (
            <div
              key={index}
              style={{ color: entry.color }}
            >
              {entry.name}: <b>{entry.value}</b>
            </div>
          ))}
        </div>
      </Paper>
    );
  }
  return null;
};

// Custom Legend Component with hover stats
interface CustomLegendProps {
  payload?: Array<{
    value: string;
    color: string;
    dataKey: string;
  }>;
  chartData: any[];
  theme: string;
  textLabelColor: string;
}

const CustomChartLegend = ({
  payload,
  chartData,
  theme,
  textLabelColor,
}: CustomLegendProps) => {
  const { t } = useTranslation();
  const [hoveredItem, setHoveredItem] = React.useState<string | null>(null);

  const getStats = (dataKey: string) => {
    const values = chartData
      .map((d) => d[dataKey])
      .filter((v) => typeof v === 'number' && !isNaN(v));

    if (values.length === 0) return { max: 0, min: 0, mean: 0 };

    const max = Math.max(...values);
    const min = Math.min(...values);
    const mean = values.reduce((a, b) => a + b, 0) / values.length;

    return { max, min, mean: Math.round(mean * 100) / 100 };
  };

  if (!payload) return null;

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 3,
        pb: 1,
        flexWrap: 'wrap',
      }}
    >
      {payload.map((entry, index) => {
        const stats = getStats(entry.dataKey);
        const isHovered = hoveredItem === entry.dataKey;

        return (
          <Box
            key={`legend-${index}`}
            onMouseEnter={() => setHoveredItem(entry.dataKey)}
            onMouseLeave={() => setHoveredItem(null)}
            sx={{
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              zIndex: isHovered ? 10000 : 1,
              '&:hover': {
                transform: 'translateY(-2px)',
              },
            }}
          >
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                bgcolor: entry.color,
              }}
            />
            <Typography
              fontSize="0.875rem"
              color={textLabelColor}
              fontWeight={isHovered ? 600 : 400}
            >
              {entry.value}
            </Typography>

            {/* Hover tooltip with stats */}
            {isHovered && (
              <Paper
                sx={{
                  position: 'absolute',
                  top: '100%',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  mt: 0.5,
                  p: 1,
                  zIndex: 10001,
                  minWidth: 90,
                  boxShadow: 4,
                  bgcolor: theme === 'dark' ? '#1F1F20' : '#444646',
                }}
              >
                <Typography
                  fontSize="0.875rem"
                  color={'white'}
                  mb={0.5}
                  fontWeight={600}
                >
                  {entry.value}
                </Typography>
                <Box
                  display="flex"
                  flexDirection="column"
                  gap={0.5}
                >
                  <Box
                    display="flex"
                    justifyContent="space-between"
                    gap={2}
                  >
                    <Typography
                      fontSize="0.875rem"
                      color={'white'}
                    >
                      {t('Max')}:
                    </Typography>
                    <Typography
                      fontSize="0.875rem"
                      color={entry.color}
                      fontWeight={600}
                    >
                      {stats.max}
                    </Typography>
                  </Box>
                  <Box
                    display="flex"
                    justifyContent="space-between"
                    gap={2}
                  >
                    <Typography
                      fontSize="0.875rem"
                      color={'white'}
                    >
                      {t('Min')}:
                    </Typography>
                    <Typography
                      fontSize="0.875rem"
                      color={entry.color}
                      fontWeight={600}
                    >
                      {stats.min}
                    </Typography>
                  </Box>
                  <Box
                    display="flex"
                    justifyContent="space-between"
                    gap={2}
                  >
                    <Typography
                      fontSize="0.875rem"
                      color={'white'}
                    >
                      {t('Mean')}:
                    </Typography>
                    <Typography
                      fontSize="0.875rem"
                      color={entry.color}
                      fontWeight={600}
                    >
                      {stats.mean}
                    </Typography>
                  </Box>
                </Box>
              </Paper>
            )}
          </Box>
        );
      })}
    </Box>
  );
};

interface DroneData {
  history?: {
    acceleration?: {
      x?: number[];
      y?: number[];
      z?: number[];
    };
    acceleration_raw?: {
      x?: number[];
      y?: number[];
      z?: number[];
    };
    vibration?: {
      x?: number[];
      y?: number[];
      z?: number[];
    };
    vibration_raw?: {
      x?: number[];
      y?: number[];
      z?: number[];
    };
    timestamps?: number[];
    timestamps_vibration?: number[];
    temperature?: number[];
    [key: string]:
      | number[]
      | { x?: number[]; y?: number[]; z?: number[] }
      | undefined;
  };
  telemetry?: {
    axes?: {
      x?: number;
      y?: number;
      z?: number;
    };
    axes_raw?: {
      x?: number;
      y?: number;
      z?: number;
    };
    vibration?: {
      x?: number;
      y?: number;
      z?: number;
    };
    vibration_raw?: {
      x?: number;
      y?: number;
      z?: number;
    };
    rc_channels?: {
      channels?: {
        [key: string]: number; // chan1, chan2, etc.
      };
    };
    servo_output?: {
      servos?: {
        [key: string]: number; // servo1, servo2, etc.
      };
    };
    gps_satellites?: number;
    battery_percent?: number;
    distance_traveled?: number;
    wind_speed?: number;
    temperature?: number;
    [key: string]:
      | number
      | { x?: number; y?: number; z?: number }
      | { channels?: { [key: string]: number } }
      | { servos?: { [key: string]: number } }
      | undefined;
  };
  position?: {
    latitude: number;
    longitude: number;
  };
  status?: {
    is_moving: boolean;
    arrived_at_base: boolean;
    system_status: string;
  };
  color?: string;
}

const DroneMonitoring = ({ selectedOrder }) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const { fetchDroneStatus } = useOperationOrder();

  // Separate data states for chart and axis values
  const [chartDroneData, setChartDroneData] = useState<DroneData | null>(null);
  const [axisDroneData, setAxisDroneData] = useState<DroneData | null>(null);

  const [routeMap, setRouteMap] = useState<
    { lat: number; lng: number; name: string }[]
  >([]);
  const [selectedDrone, setSelectedDrone] = useState(null);
  const [mapBounds, setMapBounds] = useState<
    | {
        sw: { lat: number; lng: number };
        ne: { lat: number; lng: number };
      }
    | undefined
  >(undefined);
  const statusRef = useRef<HTMLDivElement>(null);
  const droneMonitoringRef = useRef<HTMLDivElement>(null);
  const axisValuesSectionRef = useRef<HTMLDivElement>(null);
  const [mapHeight, setMapHeight] = useState<number>(350);
  const [mapCenter, setMapCenter] = useState<{ lat: number; lng: number }>({
    lat: 37.5665,
    lng: 126.978,
  });
  const [hasFitBounds, setHasFitBounds] = useState(false);
  const { getLatLongFromAddressGoogle } = useCommonAPI();
  const [userHasInteractedWithMap, setUserHasInteractedWithMap] =
    useState(false);
  const hasInitializedBoundsRef = useRef(false);

  // Separate monitoring items for chart and axis values
  const [chartMonitoringItems, setChartMonitoringItems] = useState<
    MonitoringItem[]
  >(() => {
    const items = createMonitoringItems();
    // Default: select first 3 items (x, y, z) for chart
    return items.map((item, index) => ({
      ...item,
      checked: index < 3,
    }));
  });

  const [axisMonitoringItems, setAxisMonitoringItems] = useState<
    MonitoringItem[]
  >(() => {
    const items = createMonitoringItems();
    // Default: select 9 items for axis values (3 rows x 3 columns)
    // X-Axis, Y-Axis, Z-Axis, Vibe X, Vibe Y, Vibe Z, GPS, ch1in, ch2in
    const defaultItems = [
      'x-axis',
      'y-axis',
      'z-axis',
      'vibe-x',
      'vibe-y',
      'vibe-z',
      'gps',
      'ch1in',
      'ch2in',
    ];
    return items.map((item) => ({
      ...item,
      checked: defaultItems.includes(item.id),
    }));
  });

  // Separate popover states for chart and axis values
  const [chartAnchorEl, setChartAnchorEl] = useState<HTMLElement | null>(null);
  const [axisAnchorEl, setAxisAnchorEl] = useState<HTMLElement | null>(null);
  const [popoverWidth, setPopoverWidth] = useState<number>(300);
  const chartSettingsButtonRef = useRef<HTMLButtonElement | null>(null);

  useLayoutEffect(() => {
    if (statusRef.current) {
      setMapHeight(statusRef.current.offsetHeight);
    }
    if (droneMonitoringRef.current) {
      setPopoverWidth(droneMonitoringRef.current.offsetWidth - remToPx(2));
    }
  });

  // Add ResizeObserver to track height changes in real-time for status section
  React.useEffect(() => {
    if (!statusRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const height = entry.contentRect.height;
        setMapHeight(height);
      }
    });

    resizeObserver.observe(statusRef.current);

    return () => {
      resizeObserver.disconnect();
    };
  }, []);

  // Add ResizeObserver to track width changes for droneMonitoringRef
  React.useEffect(() => {
    if (!droneMonitoringRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const width = entry.contentRect.width;
        setPopoverWidth(width - remToPx(2));
      }
    });

    resizeObserver.observe(droneMonitoringRef.current);

    return () => {
      resizeObserver.disconnect();
    };
  }, []);

  // Memoize selected monitoring items for chart
  const selectedChartMonitoringItems = React.useMemo(
    () => chartMonitoringItems.filter((item) => item.checked),
    [chartMonitoringItems],
  );

  // Memoize selected monitoring items for axis values
  const selectedAxisMonitoringItems = React.useMemo(
    () => axisMonitoringItems.filter((item) => item.checked),
    [axisMonitoringItems],
  );

  // Use refs to store latest selected items without triggering re-render
  const selectedChartMonitoringItemsRef = useRef(selectedChartMonitoringItems);
  const selectedAxisMonitoringItemsRef = useRef(selectedAxisMonitoringItems);

  React.useEffect(() => {
    selectedChartMonitoringItemsRef.current = selectedChartMonitoringItems;
  }, [selectedChartMonitoringItems]);

  React.useEffect(() => {
    selectedAxisMonitoringItemsRef.current = selectedAxisMonitoringItems;
  }, [selectedAxisMonitoringItems]);

  React.useEffect(() => {
    if (selectedOrder) {
      setSelectedDrone(selectedOrder?.delivery_device?.[0]);
    }
  }, [selectedOrder]);

  // ========== CHART DATA FETCHING ==========
  // Main interval effect for chart - only depends on selectedDrone
  React.useEffect(() => {
    const fetchChartDroneStatusData = async () => {
      const selectedItemsList = selectedChartMonitoringItemsRef.current.map(
        (item) => item.id,
      );

      // Don't call API if no items selected
      if (selectedItemsList.length === 0) {
        return;
      }

      const { success, data } = await fetchDroneStatus({
        drone_uuid: selectedDrone?.uuid,
        monitoring_items: selectedItemsList,
        time_window_minutes: 15,
      });
      if (success) {
        setChartDroneData(data);
      }
    };

    if (selectedDrone && selectedChartMonitoringItemsRef.current.length > 0) {
      // Initial fetch
      fetchChartDroneStatusData();

      // Set up interval to fetch every 6 seconds
      const intervalId = setInterval(fetchChartDroneStatusData, 6000);

      // Cleanup interval on component unmount or when selectedDrone changes
      return () => {
        clearInterval(intervalId);
      };
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDrone]);

  // Fetch chart data immediately when chart monitoring items change
  React.useEffect(() => {
    const fetchChartDroneStatusData = async () => {
      const selectedItemsList = selectedChartMonitoringItems.map(
        (item) => item.id,
      );

      if (selectedItemsList.length === 0 || !selectedDrone) {
        return;
      }

      const { success, data } = await fetchDroneStatus({
        drone_uuid: selectedDrone?.uuid,
        monitoring_items: selectedItemsList,
        time_window_minutes: 15,
      });
      if (success) {
        setChartDroneData(data);
      }
    };

    // Only fetch if we have selected items and drone
    if (selectedChartMonitoringItems.length > 0 && selectedDrone) {
      fetchChartDroneStatusData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedChartMonitoringItems, selectedDrone]);

  // ========== AXIS VALUES DATA FETCHING ==========
  // Main interval effect for axis values - only depends on selectedDrone
  React.useEffect(() => {
    const fetchAxisDroneStatusData = async () => {
      const selectedItemsList = selectedAxisMonitoringItemsRef.current.map(
        (item) => item.id,
      );

      // Don't call API if no items selected
      if (selectedItemsList.length === 0) {
        return;
      }

      const { success, data } = await fetchDroneStatus({
        drone_uuid: selectedDrone?.uuid,
        monitoring_items: selectedItemsList,
        time_window_minutes: 15,
      });
      if (success) {
        setAxisDroneData(data);
      }
    };

    if (selectedDrone && selectedAxisMonitoringItemsRef.current.length > 0) {
      // Initial fetch
      fetchAxisDroneStatusData();

      // Set up interval to fetch every 6 seconds
      const intervalId = setInterval(fetchAxisDroneStatusData, 6000);

      // Cleanup interval on component unmount or when selectedDrone changes
      return () => {
        clearInterval(intervalId);
      };
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDrone]);

  // Fetch axis values data immediately when axis monitoring items change
  React.useEffect(() => {
    const fetchAxisDroneStatusData = async () => {
      const selectedItemsList = selectedAxisMonitoringItems.map(
        (item) => item.id,
      );

      if (selectedItemsList.length === 0 || !selectedDrone) {
        return;
      }

      const { success, data } = await fetchDroneStatus({
        drone_uuid: selectedDrone?.uuid,
        monitoring_items: selectedItemsList,
        time_window_minutes: 15,
      });
      if (success) {
        setAxisDroneData(data);
      }
    };

    // Only fetch if we have selected items and drone
    if (selectedAxisMonitoringItems.length > 0 && selectedDrone) {
      fetchAxisDroneStatusData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAxisMonitoringItems, selectedDrone]);

  // Helper function to calculate distance between two lat/lng points using Haversine formula
  const calculateDistance = (
    lat1: number,
    lng1: number,
    lat2: number,
    lng2: number,
  ): number => {
    const R = 6371; // Radius of the Earth in km
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLng = ((lng2 - lng1) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((lat1 * Math.PI) / 180) *
        Math.cos((lat2 * Math.PI) / 180) *
        Math.sin(dLng / 2) *
        Math.sin(dLng / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c; // Distance in km
  };

  React.useEffect(() => {
    const fetchRouteDetail = async () => {
      setRouteMap([]);
      const { success: routeDetailSuccess, data: routeDetailData } =
        await API.get(endpoint.routes + `/${selectedOrder?.route_id}`);

      if (routeDetailSuccess && routeDetailData) {
        console.log('routeDetailData', routeDetailData);

        let closestTerminalIndex: number | null = null;

        // If no delivery terminal, find the closest terminal to destination
        if (!selectedOrder?.order_terminal_id) {
          const result = await getLatLongFromAddressGoogle(
            selectedOrder?.destination || '',
          );

          if (
            result.data?.lat &&
            result.data?.lng &&
            routeDetailData?.route_terminals
          ) {
            const destinationLat = result.data.lat;
            const destinationLng = result.data.lng;
            let minDistance = Infinity;
            routeDetailData.route_terminals.forEach(
              (
                terminal: { latitude: number; longitude: number },
                index: number,
              ) => {
                const distance = calculateDistance(
                  destinationLat,
                  destinationLng,
                  terminal.latitude,
                  terminal.longitude,
                );
                if (distance < minDistance) {
                  minDistance = distance;
                  closestTerminalIndex = index;
                }
              },
            );
          }
        }

        const routesMapData =
          routeDetailData?.route_terminals?.map(
            (
              item: {
                latitude: number;
                longitude: number;
                name: string;
                for_robot: boolean;
                terminal_id: number;
              },
              index: number,
            ) => {
              if (item.terminal_id === selectedOrder?.order_terminal_id) {
                return {
                  lat: item.latitude,
                  lng: item.longitude,
                  name: item.name,
                  icon: DeliveryLocationIcon,
                };
              } else if (
                !selectedOrder?.order_terminal_id &&
                closestTerminalIndex !== null &&
                index === closestTerminalIndex
              ) {
                return {
                  lat: item.latitude,
                  lng: item.longitude,
                  name: item.name,
                  icon: DeliveryLocationIcon,
                };
              } else {
                return {
                  lat: item.latitude,
                  lng: item.longitude,
                  name: item.name,
                };
              }
            },
          ) || [];

        setRouteMap(routesMapData);
      }
    };

    if (selectedOrder?.route_id) {
      fetchRouteDetail();
    }
  }, [selectedOrder]);

  // Transform data for chart based on selected chart monitoring items
  const chartData = React.useMemo(() => {
    if (!chartDroneData?.history) {
      return [];
    }

    // Determine which timestamps to use (axes use timestamps, vibration uses timestamps_vibration)
    const hasVibrationItems = selectedChartMonitoringItems.some(
      (item) => item.type === 'vibration',
    );
    const hasAxisItems = selectedChartMonitoringItems.some(
      (item) => item.type === 'axis',
    );

    // Use vibration timestamps if only vibration items are selected, otherwise use regular timestamps
    const timestamps =
      hasVibrationItems &&
      !hasAxisItems &&
      chartDroneData.history.timestamps_vibration
        ? chartDroneData.history.timestamps_vibration
        : chartDroneData.history.timestamps;

    if (!timestamps || !timestamps.length) {
      return [];
    }

    return timestamps.map((timestamp, index) => {
      const dataPoint: any = { timestamp };

      // Add data for each selected chart monitoring item
      selectedChartMonitoringItems.forEach((item) => {
        const dataKey = item.dataKey!;
        let value = 0;

        // Try different data sources based on item type
        if (
          item.type === 'axis' &&
          (dataKey === 'x' || dataKey === 'y' || dataKey === 'z')
        ) {
          // For axes, get from acceleration
          value = chartDroneData.history?.acceleration?.[dataKey]?.[index] ?? 0;
        } else if (item.type === 'vibration') {
          // For vibration items (vibe-x, vibe-y, vibe-z)
          // Get from vibration (NOT acceleration_raw)
          const axis = item.id.split('-')[1] as 'x' | 'y' | 'z'; // Extract 'x', 'y', 'z' from 'vibe-x'
          value = chartDroneData.history?.vibration?.[axis]?.[index] ?? 0;
        } else if (chartDroneData.history?.[dataKey]) {
          // Direct match with history field
          const historyData = chartDroneData.history[dataKey];
          if (Array.isArray(historyData)) {
            value = historyData[index] ?? 0;
          }
        } else if (item.type === 'rc_channel') {
          // RC channels don't have history - use current telemetry value
          const channelNum = item.id.replace('ch', '').replace('in', '');
          const channelKey = `chan${channelNum}`;
          value =
            chartDroneData.telemetry?.rc_channels?.channels?.[channelKey] ?? 0;
        } else if (item.type === 'servo_output') {
          // Servo outputs don't have history - use current telemetry value
          const servoNum = item.id.replace('ch', '').replace('out', '');
          const servoKey = `servo${servoNum}`;
          value =
            chartDroneData.telemetry?.servo_output?.servos?.[servoKey] ?? 0;
        } else if (item.type === 'gps') {
          // GPS doesn't have history - use current telemetry value
          value = chartDroneData.telemetry?.gps_satellites ?? 0;
        }

        dataPoint[dataKey] = value;
      });

      return dataPoint;
    });
  }, [chartDroneData?.history, selectedChartMonitoringItems]);

  // Calculate map bounds and center based on route terminals + initial drone position (ONLY ONCE)
  // Only auto-fit bounds when:
  // 1. Haven't initialized bounds yet AND
  // 2. User hasn't manually interacted with the map AND
  // 3. We have route data
  React.useEffect(() => {
    if (
      !hasInitializedBoundsRef.current &&
      !userHasInteractedWithMap &&
      routeMap.length > 0
    ) {
      const points: { lat: number; lng: number }[] = [...routeMap];

      // Include drone position if available for initial bounds calculation (use axisDroneData for map)
      if (
        axisDroneData?.position?.latitude &&
        axisDroneData?.position?.longitude
      ) {
        points.push({
          lat: axisDroneData.position.latitude,
          lng: axisDroneData.position.longitude,
        });
      }

      if (points.length > 0) {
        const lats = points.map((p) => p.lat);
        const lngs = points.map((p) => p.lng);

        const bounds = {
          sw: {
            lat: Math.min(...lats),
            lng: Math.min(...lngs),
          },
          ne: {
            lat: Math.max(...lats),
            lng: Math.max(...lngs),
          },
        };
        setMapBounds(bounds);

        const center = {
          lat: (bounds.sw.lat + bounds.ne.lat) / 2,
          lng: (bounds.sw.lng + bounds.ne.lng) / 2,
        };
        setMapCenter(center);

        setHasFitBounds(true);
        hasInitializedBoundsRef.current = true; // Mark as initialized
      }
    }
  }, [routeMap, userHasInteractedWithMap, axisDroneData?.position]);

  // Reset map interaction states when selected order changes
  React.useEffect(() => {
    setHasFitBounds(false);
    setUserHasInteractedWithMap(false);
    hasInitializedBoundsRef.current = false; // Reset initialization flag
  }, [selectedOrder]);

  // Handle map user interactions (pan, zoom, etc.)
  const handleMapInteraction = React.useCallback(() => {
    if (!userHasInteractedWithMap) {
      setUserHasInteractedWithMap(true);
    }
  }, [userHasInteractedWithMap]);

  // ========== CHART MONITORING MENU HANDLERS ==========
  const handleOpenChartMonitoringMenu = (
    event?: React.MouseEvent<HTMLElement>,
  ) => {
    // Always anchor to the button ref for consistent positioning
    if (chartSettingsButtonRef.current) {
      setChartAnchorEl(chartSettingsButtonRef.current);
    }
  };

  const handleCloseChartMonitoringMenu = () => {
    setChartAnchorEl(null);
  };

  const isChartMonitoringMenuOpen = Boolean(chartAnchorEl);

  const handleChartMonitoringItemChange = (itemId: string) => {
    setChartMonitoringItems((prevItems) =>
      prevItems.map((i) =>
        i.id === itemId ? { ...i, checked: !i.checked } : i,
      ),
    );
  };

  // ========== AXIS VALUES MONITORING MENU HANDLERS ==========
  const handleOpenAxisMonitoringMenu = (
    event: React.MouseEvent<HTMLElement>,
  ) => {
    setAxisAnchorEl(event.currentTarget);
  };

  const handleCloseAxisMonitoringMenu = () => {
    setAxisAnchorEl(null);
  };

  const isAxisMonitoringMenuOpen = Boolean(axisAnchorEl);

  const handleAxisMonitoringItemChange = (itemId: string) => {
    setAxisMonitoringItems((prevItems) =>
      prevItems.map((i) =>
        i.id === itemId ? { ...i, checked: !i.checked } : i,
      ),
    );
  };

  // Check if any stream uses RTSP
  const hasRtspStreams = React.useMemo(() => {
    if (!selectedOrder) return false;

    const videoUrls = selectedOrder.is_use_webrtc
      ? selectedOrder.webrtc_data || []
      : selectedOrder.streamming_data || [];

    return videoUrls.some((url) => url.startsWith('rtsp://'));
  }, [selectedOrder]);

  return (
    <Box
      display="flex"
      gap={2}
      width="100%"
    >
      {/* Map */}
      <Box
        flex={1}
        sx={{ position: 'relative', width: '50%', maxWidth: '50%' }}
      >
        <Map
          center={userHasInteractedWithMap ? undefined : mapCenter}
          operatingMarkers={routeMap}
          droneMarkers={
            axisDroneData?.position
              ? [
                  {
                    lat: axisDroneData.position.latitude,
                    lng: axisDroneData.position.longitude,
                    name: 'Drone',
                    icon: axisDroneData.color
                      ? `data:image/svg+xml;utf8,<svg width="32" height="32" viewBox="0 0 22 22" xmlns="http://www.w3.org/2000/svg"><path d="m6 3a3 3 0 0 0 -3 3 3 3 0 0 0 3 3 3 3 0 0 0 1.0859375-.2070312c.5392711.8209481.9140625 1.6424172.9140625 2.2070312 0 .563623-.3724493 1.384498-.9101562 2.205078a3 3 0 0 0 -1.0898438-.205078 3 3 0 0 0 -3 3 3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0 -.2050781-1.080078c.8233483-.542436 1.6446221-.919922 2.2050781-.919922.55949 0 1.37815.375313 2.201172.916016a3 3 0 0 0 -.201172 1.083984 3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0 -3-3 3 3 0 0 0 -1.085938.207031c-.539273-.820943-.914062-1.642417-.914062-2.207031 0-.563623.372445-1.3844956.910156-2.2050781a3 3 0 0 0 .002.00195 3 3 0 0 0 1.087844.2031281 3 3 0 0 0 3-3 3 3 0 0 0 -3-3 3 3 0 0 0 -3 3 3 3 0 0 0 .205078 1.0800781c-.823351.5424443-1.644622.9199219-2.205078.9199219-.55949 0-1.3781473-.3753084-2.2011719-.9160156a3 3 0 0 0 .2011719-1.0839844 3 3 0 0 0 -3-3zm0 1a2 2 0 0 1 2 2 2 2 0 0 1 -.0527344.453125c-.4577913-.368834-.8926099-.7589139-1.2402344-1.1601562a1 1 0 0 0 -.6933593-.2929688 1 1 0 0 0 -.7207031.2929688 1 1 0 0 0 0 1.4140624 1 1 0 0 0 .058594.054688c.3824613.333788.7551689.7476371 1.1074216 1.1835933a2 2 0 0 1 -.4589844.0546875 2 2 0 0 1 -2-2 2 2 0 0 1 2-2zm10 0a2 2 0 0 1 2 2 2 2 0 0 1 -2 2 2 2 0 0 1 -.457031-.054687c.37051-.4592027.761959-.8951713 1.164062-1.2382813a1 1 0 0 0 0-1.4140624 1 1 0 0 0 -1.414062 0 1 1 0 0 0 -.05274.054687c-.337606.3818392-.750702.7543351-1.185541 1.1054687a2 2 0 0 1 -.054688-.453125 2 2 0 0 1 2-2zm-10 10a2 2 0 0 1 .4570312.05469c-.3705108.459203-.7619484.895165-1.1640624 1.238281a1 1 0 0 0 0 1.414062 1 1 0 0 0 1.4140624 0 1 1 0 0 0 .052734-.05469c.3376223-.381857.7507063-.754333.1855473-1.105468a2 2 0 0 1 .0546875.453125 2 2 0 0 1 -2 2 2 2 0 0 1 -2-2 2 2 0 0 1 2-2zm10 0a2 2 0 0 1 2 2 2 2 0 0 1 -2 2 2 2 0 0 1 -2-2 2 2 0 0 1 .05273-.453125c.457792.368835.892604.758903 1.240235 1.160156a1 1 0 0 0 1.414062 0 1 1 0 0 0 0-1.414062c-.01717-.01465-.0336-.03387-.05078-.04883a1 1 0 0 0 -.0078-.0059c-.382475-.333732-.755177-.747602-1.107431-1.183551a2 2 0 0 1 .458984-.054688z" style="fill:%23${axisDroneData.color?.replace('#', '') || '000000'};fill-opacity:1;stroke:none"/></svg>`
                      : DroneIcon,
                  },
                ]
              : []
          }
          polylines={routeMap.length > 0 ? [routeMap] : []}
          bounds={userHasInteractedWithMap ? undefined : mapBounds}
          style={{ height: mapHeight + 60 }}
          onMapInteraction={handleMapInteraction}
        />
      </Box>

      {/* Drone Status Monitoring section */}
      {selectedOrder ? (
        <Box
          ref={droneMonitoringRef}
          flex={1}
          sx={{
            bgcolor: cardBg[theme],
            borderRadius: 3,
            boxShadow: '0 2px 12px 0 rgba(44, 62, 80, 0.07)',
            p: '1rem',
            minHeight: 420,
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
            width: '50%',
            maxWidth: '50%',
          }}
        >
          <Tabs
            items={[
              {
                label: t('Streaming Monitor'),
                contentStyle: {
                  marginTop: '0.5rem',
                },
                content: (
                  <StreamingDroneMonitor
                    selectedOrder={selectedOrder}
                    width={'100%'}
                    height={mapHeight}
                  />
                ),
              },
              {
                label: t('Drone Status'),
                contentStyle: {
                  marginTop: '0.5rem',
                  // backgroundColor: Colors.White,
                },
                content: (
                  <Box ref={statusRef}>
                    {/* Header */}
                    <Box
                      display="flex"
                      alignItems="center"
                      justifyContent="space-between"
                      mb={1}
                    >
                      <Typography
                        variant="h6"
                        fontWeight={600}
                        color={textLabel[theme]}
                      >
                        {t('Drone Status Monitoring')}
                      </Typography>
                      <Box
                        display="flex"
                        alignItems="center"
                        gap={1}
                      >
                        <CustomSelectControlled
                          size="lg"
                          options={selectedOrder?.delivery_device}
                          value={selectedOrder?.delivery_device?.find(
                            (opt) => opt.value === selectedDrone?.value,
                          )}
                          setValue={(opt) => {
                            setSelectedDrone(opt);
                          }}
                          menuPlacement="auto"
                          menuPortalTarget={document.body}
                          disabled={false}
                        />
                      </Box>
                    </Box>

                    <Box
                      p="0.75rem"
                      bgcolor={infoBg[theme]}
                      borderRadius="0.75rem"
                    >
                      {/* Chart */}
                      <Box
                        onClick={handleOpenChartMonitoringMenu}
                        sx={{
                          width: '100%',
                          height: 150,
                          mb: 1,
                          position: 'relative',
                          bgcolor: theme === 'dark' ? '#1F1F20' : '#ffffff',
                          borderRadius: '0.5rem',
                          px: 1,
                          cursor: 'pointer',
                          transition: 'all 0.2s ease',
                          '&:hover': {
                            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
                            transform: 'translateY(-1px)',
                          },
                        }}
                      >
                        {/* Pencil icon for chart monitoring settings */}
                        <IconButton
                          ref={chartSettingsButtonRef}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenChartMonitoringMenu(e);
                          }}
                          size="small"
                          sx={{
                            position: 'absolute',
                            top: '0.5rem',
                            right: '0.5rem',
                            zIndex: 10,
                            color: isChartMonitoringMenuOpen
                              ? 'var(--ga-primary)'
                              : textLabel[theme],
                            padding: '0.375rem',
                            transition: 'all 0.2s ease',
                            '&:hover': {
                              color: 'var(--ga-primary)',
                              backgroundColor: cardBg[theme],
                              borderColor: 'var(--ga-primary)',
                            },
                          }}
                        >
                          <IoSettingsOutline fontSize="1.375rem" />
                        </IconButton>

                        <ResponsiveContainer
                          width="100%"
                          height="100%"
                        >
                          <LineChart
                            data={chartData}
                            margin={{ top: 10, right: 20, left: 0, bottom: 0 }}
                            key={selectedChartMonitoringItems
                              .map((i) => i.id)
                              .join(',')}
                          >
                            <CartesianGrid
                              strokeDasharray="3 3"
                              vertical={false}
                              stroke="#E9EDF5"
                            />
                            <XAxis
                              dataKey="timestamp"
                              tick={{ fontSize: 13, fill: '#A0A4A8' }}
                              axisLine={false}
                              tickLine={false}
                              tickFormatter={(value) =>
                                new Date(value * 1000).toLocaleTimeString()
                              }
                            />
                            <YAxis
                              domain={[0, 100]}
                              tick={{ fontSize: 13, fill: '#A0A4A8' }}
                              axisLine={false}
                              tickLine={false}
                            />
                            <Tooltip
                              content={<CustomTooltip />}
                              cursor={{
                                stroke: '#B5D1FF',
                                strokeWidth: 1,
                                strokeDasharray: '3 3',
                              }}
                            />
                            <Legend
                              verticalAlign="top"
                              height={30}
                              content={(props) => (
                                <CustomChartLegend
                                  {...props}
                                  chartData={chartData}
                                  theme={theme}
                                  textLabelColor={textLabel[theme]}
                                />
                              )}
                            />
                            {selectedChartMonitoringItems.map((item, index) => {
                              const color = getColorForIndex(index);
                              return (
                                <Line
                                  key={item.id}
                                  type="monotone"
                                  dataKey={item.dataKey}
                                  name={item.label}
                                  stroke={color}
                                  strokeWidth={2}
                                  dot={false}
                                  activeDot={{
                                    r: 4,
                                    fill: color,
                                    stroke: '#fff',
                                    strokeWidth: 2,
                                  }}
                                  isAnimationActive={false}
                                />
                              );
                            })}
                          </LineChart>
                        </ResponsiveContainer>
                      </Box>

                      {/* Axis values */}
                      <Box
                        ref={axisValuesSectionRef}
                        sx={{
                          maxHeight: 'calc(2 * (4.5rem + 2rem) - 2rem)', // 2 rows: (card height + gap) * 2 - last gap
                          overflowY: 'auto',
                          padding: '2px',
                          margin: '-2px',
                          '&::-webkit-scrollbar': {
                            width: '6px',
                          },
                          '&::-webkit-scrollbar-track': {
                            background:
                              theme === 'dark' ? '#212529' : '#f8f9fa',
                            borderRadius: '4px',
                          },
                          '&::-webkit-scrollbar-thumb': {
                            background:
                              theme === 'dark' ? '#444646' : '#c1c1c1',
                            borderRadius: '4px',
                            '&:hover': {
                              background: theme === 'dark' ? '#555' : '#a8a8a8',
                            },
                          },
                        }}
                      >
                        <Box
                          display="flex"
                          gap={'1rem'}
                          flexWrap="wrap"
                        >
                          {selectedAxisMonitoringItems.map((item, index) => {
                            const color = getColorForIndex(index);

                            // Get value based on item type (use axisDroneData)
                            let value: number | undefined;
                            if (
                              item.type === 'axis' &&
                              (item.dataKey === 'x' ||
                                item.dataKey === 'y' ||
                                item.dataKey === 'z')
                            ) {
                              // Axes values from telemetry.axes
                              value =
                                axisDroneData?.telemetry?.axes?.[item.dataKey];
                            } else if (item.type === 'vibration') {
                              // Vibration values from telemetry.vibration
                              const axis = item.id.split('-')[1] as
                                | 'x'
                                | 'y'
                                | 'z';
                              value =
                                axisDroneData?.telemetry?.vibration?.[axis];
                            } else if (item.type === 'rc_channel') {
                              // RC channels
                              const channelNum = item.id
                                .replace('ch', '')
                                .replace('in', '');
                              const channelKey = `chan${channelNum}`;
                              value =
                                axisDroneData?.telemetry?.rc_channels
                                  ?.channels?.[channelKey];
                            } else if (item.type === 'servo_output') {
                              // Servo outputs
                              const servoNum = item.id
                                .replace('ch', '')
                                .replace('out', '');
                              const servoKey = `servo${servoNum}`;
                              value =
                                axisDroneData?.telemetry?.servo_output
                                  ?.servos?.[servoKey];
                            } else if (item.type === 'gps') {
                              // GPS satellites
                              value = axisDroneData?.telemetry?.gps_satellites;
                            } else {
                              // Other values
                              const telemetryValue =
                                axisDroneData?.telemetry?.[item.dataKey!];
                              value =
                                typeof telemetryValue === 'number'
                                  ? telemetryValue
                                  : undefined;
                            }

                            const displayValue =
                              typeof value === 'number' ? value : 0;

                            return (
                              <Box
                                key={item.id}
                                onClick={() => {
                                  if (axisValuesSectionRef.current) {
                                    setAxisAnchorEl(
                                      axisValuesSectionRef.current,
                                    );
                                  }
                                }}
                                sx={{
                                  bgcolor: cardBg[theme],
                                  borderRadius: '0.5rem',
                                  p: '0.75rem',
                                  display: 'flex',
                                  width: 'calc(33.333% - 0.875rem)',
                                  justifyContent: 'space-between',
                                  alignItems: 'center',
                                  cursor: 'pointer',
                                  transition: 'all 0.2s ease',
                                  '&:hover': {
                                    boxShadow: '0 0 4px var(--ga-primary)',
                                    // border: `0.5px solid ${theme === 'dark' ? 'var(--ga-primary-dark)' : 'var(--ga-primary)'}`,
                                    transform: 'translateY(-1px)',
                                  },
                                }}
                              >
                                <Box flex={1}>
                                  <Typography
                                    fontSize="1rem"
                                    fontWeight={400}
                                    color={textLabel[theme]}
                                    mb={0.5}
                                  >
                                    {item.label}
                                  </Typography>
                                  <Box
                                    sx={{
                                      height: '0.5rem',
                                      bgcolor:
                                        theme === 'dark'
                                          ? '#444646'
                                          : '#E9EDF5',
                                      borderRadius: 4,
                                      mt: 0.5,
                                      mr: 1,
                                      position: 'relative',
                                      overflow: 'hidden',
                                    }}
                                  >
                                    <Box
                                      sx={{
                                        position: 'absolute',
                                        left: 0,
                                        top: 0,
                                        height: '100%',
                                        width: `${Math.min(displayValue, 100)}%`,
                                        bgcolor: color,
                                        borderRadius: 4,
                                      }}
                                    />
                                  </Box>
                                </Box>
                                <Typography
                                  fontWeight={700}
                                  fontSize="1.75rem"
                                  color={color}
                                >
                                  {displayValue}
                                </Typography>
                              </Box>
                            );
                          })}
                        </Box>
                      </Box>

                      {/* Info cards */}
                      <Box
                        display="flex"
                        gap={2}
                        mt={1}
                      >
                        {infoCards.map((card) => (
                          <Box
                            key={card.label}
                            flex={1}
                            sx={{
                              bgcolor: cardBg[theme],
                              borderRadius: '0.5rem',
                              p: '0.75rem',
                              display: 'flex',
                              flexDirection: 'column',
                              alignItems: 'flex-start',
                              minWidth: 0,
                            }}
                          >
                            <Typography
                              fontSize="1.25rem"
                              color={textLabel[theme]}
                              fontWeight={600}
                              mb={0.5}
                            >
                              {t(card.label)}
                            </Typography>
                            <Typography
                              fontSize="2.25rem"
                              fontWeight={700}
                              color={
                                theme === 'dark'
                                  ? 'var(--ga-primary-dark)'
                                  : 'var(--ga-primary)'
                              }
                              lineHeight={1.1}
                              mt="0.5rem"
                            >
                              {axisDroneData?.telemetry?.[card.value]}{' '}
                              <span
                                style={{
                                  fontSize: '1.25rem',
                                  fontWeight: 400,
                                  color:
                                    theme === 'dark'
                                      ? Colors.Gray3
                                      : Colors.Gray7,
                                }}
                              >
                                {card.unit}
                              </span>
                            </Typography>
                          </Box>
                        ))}
                      </Box>
                    </Box>
                  </Box>
                ),
              },
            ]}
          />
        </Box>
      ) : (
        <Box
          flex={1}
          borderRadius={2}
          boxShadow={1}
          sx={{
            width: '50%',
            maxWidth: '50%',
          }}
        >
          <Skeleton
            variant="text"
            width="100%"
            height={mapHeight}
            // animation="wave"
          />
        </Box>
      )}

      {/* Chart Monitoring Items Selection Popover */}
      <Popover
        open={isChartMonitoringMenuOpen}
        anchorEl={chartAnchorEl}
        onClose={handleCloseChartMonitoringMenu}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
        sx={{
          '& .MuiPopover-paper': {
            boxShadow: '0px 4px 12px 0px rgba(0, 0, 0, 0.1)',
            borderRadius: '12px',
          },
        }}
      >
        <Box
          sx={{
            width: popoverWidth,
            bgcolor: theme === 'dark' ? '#2c2c2c' : '#ffffff',
            p: 1.5,
          }}
        >
          <Typography
            variant="h6"
            component="h2"
            fontWeight={600}
            color={textLabel[theme]}
            mb={2}
          >
            {t('Select chart monitoring items')}
          </Typography>

          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: 1,
              maxHeight: mapHeight - remToPx(2) - remToPx(3) - remToPx(4),
              overflow: 'auto',
              '&::-webkit-scrollbar': {
                width: '6px',
              },
              '&::-webkit-scrollbar-track': {
                background: theme === 'dark' ? '#212529' : '#f8f9fa',
                borderRadius: '4px',
              },
              '&::-webkit-scrollbar-thumb': {
                background: theme === 'dark' ? '#444646' : '#c1c1c1',
                borderRadius: '4px',
                '&:hover': {
                  background: theme === 'dark' ? '#555' : '#a8a8a8',
                },
              },
              '&::-webkit-scrollbar-button': {
                display: 'none',
              },
            }}
          >
            {chartMonitoringItems.map((item) => {
              // Find the index of this item in selected items to determine color
              const selectedIndex = selectedChartMonitoringItems.findIndex(
                (selectedItem) => selectedItem.id === item.id,
              );
              const checkboxColor =
                selectedIndex >= 0
                  ? getColorForIndex(selectedIndex)
                  : textLabel[theme];

              return (
                <FormControlLabel
                  key={item.id}
                  control={
                    <Checkbox
                      checked={item.checked}
                      onChange={() => handleChartMonitoringItemChange(item.id)}
                      sx={{
                        color: textLabel[theme],
                        '&.Mui-checked': {
                          color: checkboxColor,
                        },
                      }}
                    />
                  }
                  label={
                    <Typography
                      fontSize="1rem"
                      color={textLabel[theme]}
                    >
                      {item.label}
                    </Typography>
                  }
                  sx={{
                    margin: 0,
                  }}
                />
              );
            })}
          </Box>
        </Box>
      </Popover>

      {/* Axis Values Monitoring Items Selection Popover */}
      <Popover
        open={isAxisMonitoringMenuOpen}
        anchorEl={axisAnchorEl}
        onClose={handleCloseAxisMonitoringMenu}
        anchorOrigin={{
          vertical: 'top',
          horizontal: 'center',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'center',
        }}
        sx={{
          '& .MuiPopover-paper': {
            boxShadow: '0px 4px 12px 0px rgba(0, 0, 0, 0.1)',
            borderRadius: '12px',
          },
        }}
      >
        <Box
          sx={{
            width: popoverWidth,
            bgcolor: theme === 'dark' ? '#2c2c2c' : '#ffffff',
            p: 1.5,
          }}
        >
          <Typography
            variant="h6"
            component="h2"
            fontWeight={600}
            color={textLabel[theme]}
            mb={2}
          >
            {t('Select monitoring items')}
          </Typography>

          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, 1fr)',
              gap: 1,
              maxHeight: mapHeight - remToPx(2) - remToPx(3) - remToPx(4),
              overflow: 'auto',
              '&::-webkit-scrollbar': {
                width: '6px',
              },
              '&::-webkit-scrollbar-track': {
                background: theme === 'dark' ? '#212529' : '#f8f9fa',
                borderRadius: '4px',
              },
              '&::-webkit-scrollbar-thumb': {
                background: theme === 'dark' ? '#444646' : '#c1c1c1',
                borderRadius: '4px',
                '&:hover': {
                  background: theme === 'dark' ? '#555' : '#a8a8a8',
                },
              },
              '&::-webkit-scrollbar-button': {
                display: 'none',
              },
            }}
          >
            {axisMonitoringItems.map((item) => {
              // Find the index of this item in selected items to determine color
              const selectedIndex = selectedAxisMonitoringItems.findIndex(
                (selectedItem) => selectedItem.id === item.id,
              );
              const checkboxColor =
                selectedIndex >= 0
                  ? getColorForIndex(selectedIndex)
                  : textLabel[theme];

              return (
                <FormControlLabel
                  key={item.id}
                  control={
                    <Checkbox
                      checked={item.checked}
                      onChange={() => handleAxisMonitoringItemChange(item.id)}
                      sx={{
                        color: textLabel[theme],
                        '&.Mui-checked': {
                          color: checkboxColor,
                        },
                      }}
                    />
                  }
                  label={
                    <Typography
                      fontSize="1rem"
                      color={textLabel[theme]}
                    >
                      {item.label}
                    </Typography>
                  }
                  sx={{
                    margin: 0,
                  }}
                />
              );
            })}
          </Box>
        </Box>
      </Popover>
    </Box>
  );
};

export default DroneMonitoring;
