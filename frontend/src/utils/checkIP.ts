/**
 * Check the real IP address from frontend
 * This helps verify if VPN is working
 */
export const checkRealIP = async (): Promise<any> => {
  try {
    // Check if we have cached IP data (cache for 5 minutes)
    const cachedIP = localStorage.getItem('cached_ip_data');
    const cachedTime = localStorage.getItem('cached_ip_time');

    if (cachedIP && cachedTime) {
      const now = Date.now();
      const cacheAge = now - parseInt(cachedTime);

      // If cache is less than 5 minutes old, use it
      if (cacheAge < 5 * 60 * 1000) {
        console.log('Using cached IP data');
        return JSON.parse(cachedIP);
      }
    }

    // Check IP using multiple services
    const ipServices = [
      'https://api.ipify.org?format=json',
      'https://ipapi.co/json/',
      'https://httpbin.org/ip',
      'https://api.myip.com',
    ];

    for (const service of ipServices) {
      try {
        const response = await fetch(service, {
          method: 'GET',
          headers: {
            Accept: 'application/json',
          },
          // Add timeout
          signal: AbortSignal.timeout(5000),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        console.log(`IP Check (${service}):`, data);

        // Cache the successful result
        localStorage.setItem('cached_ip_data', JSON.stringify(data));
        localStorage.setItem('cached_ip_time', Date.now().toString());

        // Return the first successful result
        return data;
      } catch (error) {
        console.log(`Failed to check IP with ${service}:`, error);
        continue;
      }
    }

    return null;
  } catch (error) {
    console.error('Error checking IP:', error);
    return null;
  }
};

/**
 * Check if VPN is working by comparing IP with location
 */
export const checkVPNStatus = async () => {
  try {
    console.log('=== VPN Status Check ===');

    // Check IP
    const ipData = await checkRealIP();
    console.log('IP Data:', ipData);

    // Check browser geolocation
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          console.log('Browser Geolocation:', {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
          });

          // Compare IP location with GPS location
          if (ipData && ipData.country) {
            console.log('IP Country:', ipData.country);
            console.log(
              'GPS Coordinates:',
              `${position.coords.latitude}, ${position.coords.longitude}`,
            );

            // You can add reverse geocoding here to get country from GPS
            console.log('=== VPN Analysis ===');
            console.log(
              'If IP country differs from your actual location, VPN is working',
            );
          }
        },
        (error) => {
          console.log('Geolocation error:', error.message);
        },
      );
    }
  } catch (error) {
    console.error('Error checking VPN status:', error);
  }
};

/**
 * Test function to check if IP detection is working
 * Call this in browser console to test
 */
export const testIPDetection = async () => {
  console.log('🧪 Testing IP Detection...');

  try {
    const ipData = await checkRealIP();

    if (ipData) {
      console.log('✅ IP Detection Working:', {
        ip: ipData.ip || ipData.query || 'Unknown',
        country: ipData.country || ipData.country_name || 'Unknown',
        city: ipData.city || ipData.regionName || 'Unknown',
        isp: ipData.isp || ipData.org || 'Unknown',
      });

      // Test VPN status
      await checkVPNStatus();
    } else {
      console.log(
        '❌ IP Detection Failed: Could not get IP data from any service',
      );
    }
  } catch (error) {
    console.error('❌ IP Detection Error:', error);
  }
};

/**
 * Get IP data with detailed information
 */
export const getDetailedIPInfo = async () => {
  try {
    const ipData = await checkRealIP();

    if (!ipData) {
      return {
        success: false,
        error: 'Could not get IP data',
      };
    }

    return {
      success: true,
      data: {
        ip: ipData.ip || ipData.query || 'Unknown',
        country: ipData.country || ipData.country_name || 'Unknown',
        city: ipData.city || ipData.regionName || 'Unknown',
        region: ipData.region || ipData.regionName || 'Unknown',
        isp: ipData.isp || ipData.org || 'Unknown',
        timezone: ipData.timezone || 'Unknown',
        latitude: ipData.lat || ipData.latitude || null,
        longitude: ipData.lon || ipData.longitude || null,
      },
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
};
