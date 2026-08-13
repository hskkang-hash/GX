import API, { endpoint } from '@/services/API';
import {
  getDashboardLocation,
  testIPGeolocation,
} from '@/utils/requestLocationPermission';

export default function useDashboard() {
  const getDashboardData = async () => {
    let locationParams = '';
    try {
      const location = await getDashboardLocation();

      if (
        location.source === 'browser_geolocation' &&
        location.latitude &&
        location.longitude
      ) {
        locationParams = `?user_latitude=${location.latitude}&user_longitude=${location.longitude}&location_source=${location.source}&location_accuracy=${location.accuracy}`;
        if (location.country) {
          locationParams += `&user_country=${location.country}`;
        }
        if (location.city) {
          locationParams += `&user_city=${location.city}`;
        }
      } else if (
        location.source === 'ip_geolocation' &&
        location.latitude &&
        location.longitude
      ) {
        locationParams = `?user_latitude=${location.latitude}&user_longitude=${location.longitude}&location_source=${location.source}&location_accuracy=${location.accuracy}`;
        if (location.country) {
          locationParams += `&user_country=${location.country}`;
        }
        if (location.city) {
          locationParams += `&user_city=${location.city}`;
        }
        if (location.ip) {
          locationParams += `&user_ip=${location.ip}`;
        }
      } else {
        locationParams = `?location_source=none`;
      }
    } catch {
      locationParams = `?location_source=none`;
    }

    const fullUrl = endpoint.getDashboardData + locationParams;

    const response = await API.get(fullUrl);
    if (response.success) {
      return {
        success: true,
        data: response.data,
        message: response?.message,
      };
    } else {
      return {
        success: false,
        data: null,
        message: response?.message,
      };
    }
  };

  const refreshDashboardData = async () => {
    let locationParams = '';
    try {
      const location = await getDashboardLocation();

      if (
        location.source === 'browser_geolocation' &&
        location.latitude &&
        location.longitude
      ) {
        locationParams = `?user_latitude=${location.latitude}&user_longitude=${location.longitude}&location_source=${location.source}&location_accuracy=${location.accuracy}`;
        if (location.country) {
          locationParams += `&user_country=${location.country}`;
        }
        if (location.city) {
          locationParams += `&user_city=${location.city}`;
        }
      } else if (
        location.source === 'ip_geolocation' &&
        location.latitude &&
        location.longitude
      ) {
        locationParams = `?user_latitude=${location.latitude}&user_longitude=${location.longitude}&location_source=${location.source}&location_accuracy=${location.accuracy}`;
        if (location.country) {
          locationParams += `&user_country=${location.country}`;
        }
        if (location.city) {
          locationParams += `&user_city=${location.city}`;
        }
        if (location.ip) {
          locationParams += `&user_ip=${location.ip}`;
        }
      } else {
        locationParams = `?location_source=none`;
      }
    } catch {
      locationParams = `?location_source=none`;
    }

    const fullUrl = endpoint.refreshDashboardData + locationParams;

    const response = await API.post(fullUrl);
    if (response.success) {
      return {
        success: true,
        data: response.data,
        message: response?.message,
      };
    } else {
      return {
        success: false,
        data: null,
        message: response?.message,
      };
    }
  };

  const testLocation = async () => {
    const result = await testIPGeolocation();
    return result;
  };

  const getDashboardDataAngYang = async ({
    start_date,
    end_date,
  }: {
    start_date?: string | null;
    end_date?: string | null;
  } = {}) => {
    try {
      let params = '';
      if (start_date && end_date) {
        params = `?start_date=${start_date}&end_date=${end_date}`;
      }
      const fullUrl = endpoint.getDashboardDataAngYang;
      const response = await API.get(fullUrl, {
        params: {
          start_date: start_date,
          end_date: end_date,
        },
      });
      return {
        success: response.success,
        data: response.success ? response.data : null,
        message: response?.message,
      };
    } catch (error) {
      return {
        success: false,
        data: null,
        message: (error as Error).message || 'Error fetching dashboard data',
      };
    }
  };

  const saveWeatherData = async (data: any) => {
    try {
      const response = await API.post(endpoint.saveWeatherData, data);
      console.log('response_saveWeatherData', response);
      return {
        success: response.success,
        message: response?.message,
      };
    } catch (error) {
      return {
        success: false,
        data: null,
        message: (error as Error).message || 'Error saving weather data',
      };
    }
  };

  const getWeatherData = async () => {
    try {
      const response = await API.get(endpoint.saveWeatherData);
      console.log('response_saveWeatherData', response);
      return {
        success: response.success,
        message: response?.message,
      };
    } catch (error) {
      return {
        success: false,
        data: null,
        message: (error as Error).message || 'Error saving weather data',
      };
    }
  };

  const getDeviceLocation = async () => {
    try {
      const response = await API.get(endpoint.deviceLocation);
      return {
        success: response.success,
        message: response?.message,
        data: response?.data,
      };
    } catch (error) {
      return {
        success: false,
        data: null,
        message: (error as Error).message || 'Error getting device location',
      };
    }
  };

  return {
    getDashboardData,
    refreshDashboardData,
    testLocation,
    getDashboardDataAngYang,
    saveWeatherData,
    getWeatherData,
    getDeviceLocation,
  };
}
