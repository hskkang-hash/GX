import { Height } from '@mui/icons-material';
import { Box, Popover, CircularProgress } from '@mui/material';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';
import { useEffect, useState, useRef, useCallback } from 'react';
import API, { endpoint } from '@/services/API';

import './operationalStatus.scss';

const droneStatus = [
  {
    color: '#69DC8A',
    name: 'Available',
  },
  {
    color: '#F64E60',
    name: 'Critical',
  },
];

interface SensorData {
  name: string;
  status: string;
  situation: string;
}

interface HealthData {
  uniqueId: string;
  sensors: SensorData[];
  timestamp: string;
}

const getDefaultHealthData = (): HealthData => {
  return {
    uniqueId: '',
    sensors: [
      {
        name: 'Aircraft Attitude',
        status: 'ON',
        situation: 'Error',
      },
      {
        name: 'Gyro Sensor',
        status: 'ON',
        situation: 'Error',
      },
      {
        name: 'GPS',
        status: 'ON',
        situation: 'Error',
      },
      {
        name: 'Accelerometer',
        status: 'ON',
        situation: 'Error',
      },
      {
        name: 'Magnetometer',
        status: 'ON',
        situation: 'Error',
      },
      {
        name: 'Vibration Sensor',
        status: 'ON',
        situation: 'Error',
      },
    ],
    timestamp: new Date().toISOString(),
  };
};

const getSensorColor = (situation: string): string => {
  // Only "Normal" is green, everything else is red
  if (situation === 'Normal') {
    return '#69DC8A';
  }
  return '#F64E60';
};

const PopoverDevice = ({
  open,
  anchorEl,
  handleClose,
  deviceId,
}: {
  open: boolean;
  anchorEl: HTMLElement | null;
  handleClose: () => void;
  theme: string;
  deviceId?: number;
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [healthData, setHealthData] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const hasFetchedRef = useRef(false);

  const fetchHealthData = useCallback(() => {
    if (!deviceId) return;
    
    setLoading(true);
    API.get(endpoint.checkDroneHealth(deviceId))
      .then((response: any) => {
        if (response.success && response.data) {
          setHealthData(response.data);
        } else {
          // Use default data on error
          setHealthData(getDefaultHealthData());
        }
      })
      .catch((err: any) => {
        console.error('Error fetching drone health:', err);
        // Use default data on error and wait for next call
        setHealthData(getDefaultHealthData());
      })
      .finally(() => {
        setLoading(false);
      });
  }, [deviceId]);

  useEffect(() => {
    // Clear any existing interval first
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (open && deviceId) {
      // Only fetch immediately on first open, not on every render
      if (!hasFetchedRef.current) {
        // Set default data immediately
        setHealthData(getDefaultHealthData());
        // Fetch immediately when popover opens
        fetchHealthData();
        hasFetchedRef.current = true;
      }
      
      // Set up interval to fetch every 5 seconds
      intervalRef.current = setInterval(() => {
        fetchHealthData();
      }, 5000);
    } else {
      // Reset state when popover closes
      if (!open) {
        setHealthData(null);
        hasFetchedRef.current = false;
      }
    }

    // Cleanup interval on unmount or when dependencies change
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [open, deviceId, fetchHealthData]);

  // Only render popover if open and deviceId exists
  if (!open || !deviceId) {
    return null;
  }

  return (
    <Popover
      anchorOrigin={{
        vertical: 'bottom',
        horizontal: 'center',
      }}
      transformOrigin={{
        vertical: 'top',
        horizontal: 'center',
      }}
      // id={id}
      open={open}
      anchorEl={anchorEl}
      onClose={handleClose}
      sx={{
        '& .MuiPopover-paper': {
          boxShadow:
            theme === 'light'
              ? '1px 1px 4px rgba(0, 0, 0, 0.02)'
              : '1px 1px 4px rgba(255, 255, 255, 0.02)',
          borderRadius: '0.75rem',
          color: theme === 'light' ? '#1F1F20' : '#ECECEF',
          backgroundColor: theme === 'light' ? 'white' : '#1F1F20',
        },
      }}
    >
      <div>
        <Box
          flexDirection="column"
          display="flex"
          gap="0.5rem"
          padding="0.75rem"
        >
          <Box
            flexDirection="row"
            display="flex"
            gap="1.5rem"
          >
            {droneStatus.map((item) => (
              <Box
                key={item.name}
                flexDirection="row"
                alignItems="center"
                display="flex"
                gap="0.5rem"
              >
                <Box
                  sx={{
                    width: 10,
                    height: 10,
                    backgroundColor: item.color,
                    flexShrink: 0,
                    borderRadius: '50%',
                  }}
                ></Box>
                <span>{t(item.name)}</span>
              </Box>
            ))}
          </Box>
          {loading && !healthData ? (
            <Box
              display="flex"
              justifyContent="center"
              alignItems="center"
              padding="2rem"
            >
              <CircularProgress size={24} />
            </Box>
          ) : healthData && healthData.sensors ? (
            <table className="device-status-table">
              <thead>
                <tr>
                  {healthData.sensors.map((sensor) => (
                    <th key={sensor.name}>{t(sensor.name)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  {healthData.sensors.map((sensor) => {
                    const color = getSensorColor(sensor.situation);
                    return (
                      <td key={sensor.name}>
                        <Box
                          sx={{
                            display: 'flex',
                            justifyContent: 'flex-start',
                            alignItems: 'flex-start',
                          }}
                        >
                          <Box
                            sx={{
                              width: 10,
                              height: 10,
                              backgroundColor: color,
                              flexShrink: 0,
                              borderRadius: '50%',
                            }}
                          ></Box>
                        </Box>
                      </td>
                    );
                  })}
                </tr>
              </tbody>
            </table>
          ) : null}
        </Box>
      </div>
    </Popover>
  );
};

export default PopoverDevice;
