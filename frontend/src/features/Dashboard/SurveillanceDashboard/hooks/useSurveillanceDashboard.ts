import API, { endpoint } from '@/services/API';

export interface DroneStatusOverview {
  active: number;
  on_mission: number;
  warning: number;
  inactive: number;
}

export interface DailyProfileOverview {
  total: number;
  completed: number;
  processing: number;
  date: string;
}

export interface AbnormalSignsOverview {
  fire_smoke: number;
  animals: number;
  human: number;
  vehicle: number;
  anomaly: number;
}

export interface AbnormalSignMessage {
  id: string;
  timestamp: string;
  category: string;
  message: string;
  icon_type: string; // Icon type for display (e.g., 'warning', 'info', 'critical')
  relative_time?: string; // Human-readable relative time (e.g., '2 minutes ago', 'Just now')
  location?: {
    lat: number;
    lng: number;
  };
  // Detection image and location data
  detected_image_path?: string; // URL to the detected image
  drone_location?: {
    drone_id: string;
    location: {
      latitude: number;
      longitude: number;
      altitude: number;
    };
    timestamp: number;
    age_seconds: number;
  };
  detection_count?: number; // Number of detections in this frame
}

export interface ProfilePolygon {
  id: number;
  name: string;
  code: string;
  color_code: string;
  mission_id: number;
  is_line_mission: boolean;
  polygon: Array<{ lat: number; lng: number }>;
  status: string;
}

export interface WeatherSetting {
  latitude: number;
  longitude: number;
  address: string;
}

export default function useSurveillanceDashboard() {
  const getDroneStatusOverview = async () => {
    try {
      const response = await API.get(endpoint.surveillanceDashboardDroneStatus);
      if (response.success) {
        return {
          success: true,
          data: response.data as DroneStatusOverview,
          message: response?.message,
        };
      } else {
        return {
          success: false,
          data: null,
          message: response?.message,
        };
      }
    } catch (error) {
      return {
        success: false,
        data: null,
        message:
          (error as Error).message || 'Error fetching drone status overview',
      };
    }
  };

  const getDailyProfileOverview = async (date?: string) => {
    try {
      const params = date ? { date } : {};
      const response = await API.get(
        endpoint.surveillanceDashboardDailyProfile,
        {
          params,
        },
      );
      if (response.success) {
        return {
          success: true,
          data: response.data as DailyProfileOverview,
          message: response?.message,
        };
      } else {
        return {
          success: false,
          data: null,
          message: response?.message,
        };
      }
    } catch (error) {
      return {
        success: false,
        data: null,
        message:
          (error as Error).message || 'Error fetching daily profile overview',
      };
    }
  };

  const getAbnormalSignsOverview = async (
    startDate: string,
    endDate: string,
  ) => {
    try {
      const response = await API.get(
        endpoint.surveillanceDashboardAbnormalSigns,
        startDate && endDate
          ? {
            params: {
              start_date: startDate,
              end_date: endDate,
            },
          }
          : {},
      );
      if (response.success) {
        return {
          success: true,
          data: response.data as AbnormalSignsOverview,
          message: response?.message,
        };
      } else {
        return {
          success: false,
          data: null,
          message: response?.message,
        };
      }
    } catch (error) {
      return {
        success: false,
        data: null,
        message:
          (error as Error).message || 'Error fetching abnormal signs overview',
      };
    }
  };

  const getAbnormalSignsMessages = async (
    startDate: string,
    endDate: string,
    limit: number = 100,
    page: number = 1,
    pageSize: number = 5,
  ) => {
    try {
      const response = await API.get(
        endpoint.surveillanceDashboardAbnormalSignsMessages,
        {
          params: {
            start_date: startDate,
            end_date: endDate,
            limit,
            page,
            page_size: pageSize,
          },
        },
      );
      if (response.success) {
        console.log('response_data', response);
        return {
          success: true,
          data: {
            messages: response.data?.messages
              ? response.data?.messages.map((message: AbnormalSignMessage) => ({
                ...message,
                detected_image_path: message?.image_url || null,
                drone_location: {
                  location: {
                    latitude: message?.image_lat || 0,
                    longitude: message?.image_lng || 0,
                  },
                },
              }))
              : [],

            total: response.data?.total || 0,
            page: response.data?.page || page,
            page_size: response.data?.page_size || pageSize,
            total_pages: response.data?.total_pages || 0,
            status: response.data?.status || 'unknown',
          },
          message: response?.message,
        };
      } else {
        return {
          success: false,
          data: null,
          message: response?.message,
        };
      }
    } catch (error) {
      return {
        success: false,
        data: null,
        message:
          (error as Error).message || 'Error fetching abnormal signs messages',
      };
    }
  };

  const getTodayProfilesPolygon = async () => {
    try {
      const response = await API.get(
        endpoint.surveillanceDashboardTodayProfilesPolygon,
      );
      if (response.success) {
        return {
          success: true,
          data: (response.data?.profiles || []) as ProfilePolygon[],
          message: response?.message,
        };
      } else {
        return {
          success: false,
          data: [],
          message: response?.message,
        };
      }
    } catch (error) {
      return {
        success: false,
        data: [],
        message: (error as Error).message || 'Error fetching profiles polygon',
      };
    }
  };

  const getLocationWeather = async () => {
    try {
      const response = await API.get(
        endpoint.surveillanceDashboardLocationWeather,
      );
      console.log('responsegetLocationWeathersdsdsd', response);
      if (response.success) {
        return {
          success: true,
          data: response.data,
          message: response?.message,
        };
      } else {
        return {
          success: false,
          data: [],
          message: response?.message,
        };
      }
    } catch (error) {
      return {
        success: false,
        data: [],
        message: (error as Error).message || 'Error fetching profiles polygon',
      };
    }
  };

  const getTodayRegionDrones = async (page: number = 1, pageSize: number = 4) => {
    try {
      const response = await API.get(
        endpoint.surveillanceDashboardTodayRegionDrones,
        {
          params: {
            page,
            page_size: pageSize,
          },
        },
      );
      console.log('responsegetTodayRegionDrones', response);
      if (response.success) {
        return {
          success: true,
          data: {
            regions: (response.data?.regions || []) as RegionDrone[],
            total: response.data?.total || 0,
            page: response.data?.page || page,
            pageSize: response.data?.page_size || pageSize,
            totalPages: response.data?.total_pages || 0,
          },
          message: response?.message,
        };
      } else {
        return {
          success: false,
          data: null,
          message: response?.message,
        };
      }
    } catch (error) {
      return {
        success: false,
        data: null,
        message:
          (error as Error).message || 'Error fetching today region drones',
      };
    }
  };

  return {
    getDroneStatusOverview,
    getDailyProfileOverview,
    getAbnormalSignsOverview,
    getAbnormalSignsMessages,
    getTodayProfilesPolygon,
    getLocationWeather,
    getTodayRegionDrones,
  };
}

export interface DroneInfo {
  device_id: number;
  device_name: string;
  serial_number: string;
  unit_id: string;
  color: string;
  status_code: string;
  status_name: string;
}

export interface RegionDrone {
  region: string;
  drones: DroneInfo[];
}

export interface RegionDronesResponse {
  regions: RegionDrone[];
}
