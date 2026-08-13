/**
 * Request location permission and get coordinates for dashboard
 * @returns Promise with location info including permission status
 */
export const requestLocationForDashboard = (): Promise<{
  latitude?: number;
  longitude?: number;
  permissionStatus: 'granted' | 'denied' | 'prompt' | 'not_supported';
}> => {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve({ permissionStatus: 'not_supported' });
      return;
    }

    if ('permissions' in navigator) {
      navigator.permissions
        .query({ name: 'geolocation' as PermissionName })
        .then((result) => {
          if (result.state === 'granted') {
            getLocation();
          } else if (result.state === 'prompt') {
            showPermissionRequest();
          } else if (result.state === 'denied') {
            resolve({ permissionStatus: 'denied' });
          }
        })
        .catch(() => {
          showPermissionRequest();
        });
    } else {
      showPermissionRequest();
    }

    function getLocation() {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const coords = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          };
          resolve({ ...coords, permissionStatus: 'granted' });
        },
        () => {
          resolve({ permissionStatus: 'granted' });
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 300000,
        },
      );
    }

    function showPermissionRequest() {
      const confirmed = confirm(
        'This app would like to access your location to provide accurate weather information. Allow?',
      );

      if (confirmed) {
        getLocation();
      } else {
        resolve({ permissionStatus: 'denied' });
      }
    }
  });
};

/**
 * Get IP location data
 */
export const getIPLocation = async (): Promise<{
  ip: string;
  country: string;
  city: string;
  latitude: number;
  longitude: number;
} | null> => {
  try {
    try {
      const response = await fetch('https://ipinfo.io/json', {
        method: 'GET',
        headers: {
          Accept: 'application/json',
        },
        signal: AbortSignal.timeout(5000),
      });

      if (response.ok) {
        const data = await response.json();

        let latitude = 0,
          longitude = 0;
        if (data.loc) {
          const [lat, lng] = data.loc.split(',').map(Number);
          latitude = lat;
          longitude = lng;
        }

        const formattedData = {
          ip: data.ip || 'Unknown',
          country: data.country || 'Unknown',
          city: data.city || 'Unknown',
          latitude: latitude,
          longitude: longitude,
        };

        if (latitude === 0 && longitude === 0) {
          throw new Error('Invalid coordinates');
        }

        return formattedData;
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch {
      try {
        const fallbackResponse = await fetch('https://ipapi.co/json/', {
          method: 'GET',
          headers: {
            Accept: 'application/json',
          },
          signal: AbortSignal.timeout(5000),
        });

        if (fallbackResponse.ok) {
          const fallbackData = await fallbackResponse.json();

          const fallbackResult = {
            ip: fallbackData.ip || 'Unknown',
            country: fallbackData.country || 'Unknown',
            city: fallbackData.city || 'Unknown',
            latitude: fallbackData.latitude || 0,
            longitude: fallbackData.longitude || 0,
          };

          if (fallbackResult.latitude === 0 && fallbackResult.longitude === 0) {
            throw new Error('Invalid coordinates');
          }

          return fallbackResult;
        } else {
          throw new Error(`HTTP ${fallbackResponse.status}`);
        }
      } catch {
        return null;
      }
    }
  } catch {
    return null;
  }
};

/**
 * Test IP geolocation function for debugging
 */
export const testIPGeolocation = async () => {
  if ('permissions' in navigator) {
    try {
      await navigator.permissions.query({
        name: 'geolocation' as PermissionName,
      });
    } catch {
      // Handle error silently
    }
  }

  const ipResult = await getIPLocation();
  const dashboardResult = await getDashboardLocation();

  return {
    ipResult,
    dashboardResult,
  };
};

/**
 * Get location coordinates for weather dashboard
 * Priority: Browser Geolocation for accuracy
 * Fallback: IP geolocation if GPS not available
 * @returns Promise with coordinates and source info
 */
export const getDashboardLocation = async (): Promise<{
  latitude?: number;
  longitude?: number;
  source: 'browser_geolocation' | 'ip_geolocation' | 'none';
  accuracy?: number;
  country?: string;
  city?: string;
  ip?: string;
}> => {
  try {
    const locationResult = await requestLocationForDashboard();

    // Case 1: Permission granted and GPS worked
    if (
      locationResult.permissionStatus === 'granted' &&
      locationResult.latitude &&
      locationResult.longitude
    ) {
      return {
        latitude: locationResult.latitude,
        longitude: locationResult.longitude,
        source: 'browser_geolocation',
        accuracy: 50,
      };
    }

    // Case 2: Permission granted but GPS failed - use IP geolocation
    if (locationResult.permissionStatus === 'granted') {
      const ipLocation = await getIPLocation();

      if (ipLocation && ipLocation.latitude && ipLocation.longitude) {
        if (ipLocation.latitude !== 0 && ipLocation.longitude !== 0) {
          return {
            latitude: ipLocation.latitude,
            longitude: ipLocation.longitude,
            source: 'ip_geolocation',
            accuracy: 50000,
            country: ipLocation.country,
            city: ipLocation.city,
            ip: ipLocation.ip,
          };
        }
      }
    }

    // Case 3: Permission denied (tắt quyền) - try IP geolocation
    if (locationResult.permissionStatus === 'denied') {
      const ipLocation = await getIPLocation();

      if (ipLocation && ipLocation.latitude && ipLocation.longitude) {
        if (ipLocation.latitude !== 0 && ipLocation.longitude !== 0) {
          return {
            latitude: ipLocation.latitude,
            longitude: ipLocation.longitude,
            source: 'ip_geolocation',
            accuracy: 50000,
            country: ipLocation.country,
            city: ipLocation.city,
            ip: ipLocation.ip,
          };
        }
      }
    }

    // Case 4: Permission prompt or not supported - try IP geolocation
    const ipLocation = await getIPLocation();

    if (ipLocation && ipLocation.latitude && ipLocation.longitude) {
      if (ipLocation.latitude !== 0 && ipLocation.longitude !== 0) {
        return {
          latitude: ipLocation.latitude,
          longitude: ipLocation.longitude,
          source: 'ip_geolocation',
          accuracy: 50000,
          country: ipLocation.country,
          city: ipLocation.city,
          ip: ipLocation.ip,
        };
      }
    }

    // No location data available
    return {
      source: 'none',
      accuracy: 50000,
    };
  } catch {
    return {
      source: 'none',
      accuracy: 50000,
    };
  }
};
