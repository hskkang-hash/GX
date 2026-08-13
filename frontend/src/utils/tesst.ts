export interface GeocodingResult {
  display_name: string;
  lat: string;
  lon: string;
}

export const geocodeAddress = async (
  address: string,
): Promise<GeocodingResult | null> => {
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(address)}`,
      {
        headers: {
          'User-Agent': 'GuardianX/1.0',
        },
      },
    );

    const data = await response.json();
    if (data && data.length > 0) {
      return {
        display_name: data[0].display_name,
        lat: data[0].lat,
        lon: data[0].lon,
      };
    }
    return null;
  } catch (error) {
    console.error('Geocoding error:', error);
    return null;
  }
};

export const reverseGeocode = async (
  lat: number,
  lon: number,
): Promise<GeocodingResult | null> => {
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`,
      {
        headers: {
          'User-Agent': 'GuardianX/1.0',
        },
      },
    );

    const data = await response.json();
    if (data) {
      return {
        display_name: data.display_name,
        lat: data.lat,
        lon: data.lon,
      };
    }
    return null;
  } catch (error) {
    console.error('Reverse geocoding error:', error);
    return null;
  }
};
