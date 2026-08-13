/**
 * Calculate distance between two points using Haversine formula
 * @param lat1 - Latitude of first point
 * @param lng1 - Longitude of first point
 * @param lat2 - Latitude of second point
 * @param lng2 - Longitude of second point
 * @returns Distance in kilometers
 */
export const calculateDistance = (
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number,
): number => {
  const R = 6371; // Earth's radius in kilometers
  const dLat = (lat2 - lat1) * (Math.PI / 180);
  const dLng = (lng2 - lng1) * (Math.PI / 180);

  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * (Math.PI / 180)) *
      Math.cos(lat2 * (Math.PI / 180)) *
      Math.sin(dLng / 2) *
      Math.sin(dLng / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
};

/**
 * Calculate total distance for a line of waypoints
 * @param waypoints - Array of waypoints with latitude and longitude
 * @returns Total distance in kilometers
 */
export const calculateTotalDistance = (
  waypoints: { latitude: number; longitude: number }[],
): number => {
  if (waypoints.length < 2) {
    return 0;
  }

  let totalDistance = 0;
  for (let i = 0; i < waypoints.length - 1; i++) {
    const current = waypoints[i];
    const next = waypoints[i + 1];

    totalDistance += calculateDistance(
      current.latitude,
      current.longitude,
      next.latitude,
      next.longitude,
    );
  }

  return Number(totalDistance.toFixed(2));
};

/**
 * Calculate estimated time based on total distance and cruise speed
 * @param totalDistanceKm - Total distance in kilometers
 * @param cruiseSpeed - Cruise speed in m/s (default: 20)
 * @returns Estimated time in minutes
 */
export const calculateEstimatedTime = (
  totalDistanceKm: number,
  cruiseSpeed: number = 20,
): number => {
  if (totalDistanceKm <= 0 || cruiseSpeed <= 0) {
    return 0;
  }

  // Convert distance from km to meters
  const totalDistanceM = totalDistanceKm * 1000;

  // Calculate time in minutes: (distance in meters) / (speed in m/s) / 60
  return Number((totalDistanceM / cruiseSpeed / 60).toFixed(2));
};

/**
 * Calculate both distance and estimated time for line mode
 * @param waypoints - Array of waypoints with latitude and longitude
 * @param cruiseSpeed - Cruise speed in m/s (default: 20)
 * @returns Object containing total distance (in km) and estimated time (in minutes)
 */
export const calculateLineDistanceAndTime = (
  waypoints: { latitude: number; longitude: number }[],
  cruiseSpeed: number = 20,
): { totalDistance: number; estimatedTime: number } => {
  const totalDistance = calculateTotalDistance(waypoints); // Returns km
  const estimatedTime = calculateEstimatedTime(totalDistance, cruiseSpeed); // Returns minutes

  return {
    totalDistance, // in kilometers
    estimatedTime, // in minutes
  };
};
