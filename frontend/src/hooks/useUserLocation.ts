import { useState, useEffect, useCallback } from 'react';

import {
  getUserLocation,
  getWeatherData,
  GeolocationResult,
} from '@/utils/geolocation';

interface WeatherData {
  current_weather: {
    temperature: number;
    windspeed: number;
    weathercode: number;
    time: string;
  };
}

interface UseUserLocationReturn {
  location: GeolocationResult | null;
  weather: WeatherData | null;
  loading: boolean;
  error: string | null;
  getLocation: () => Promise<void>;
  getWeather: (lat: number, lon: number) => Promise<void>;
}

export const useUserLocation = (): UseUserLocationReturn => {
  const [location, setLocation] = useState<GeolocationResult | null>(null);
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getLocation = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const userLocation = await getUserLocation();
      setLocation(userLocation);

      // Automatically get weather data when location is obtained
      const weatherData = await getWeatherData(
        userLocation.latitude,
        userLocation.longitude,
      );
      setWeather(weatherData);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      console.error('Error getting user location:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const getWeather = useCallback(async (lat: number, lon: number) => {
    setLoading(true);
    setError(null);

    try {
      const weatherData = await getWeatherData(lat, lon);
      setWeather(weatherData);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      console.error('Error getting weather data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    location,
    weather,
    loading,
    error,
    getLocation,
    getWeather,
  };
};
