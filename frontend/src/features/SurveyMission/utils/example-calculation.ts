/**
 * Example calculation to demonstrate distance and time calculation
 * This file is for demonstration purposes only
 */
import { calculateLineDistanceAndTime } from './calculateDistanceAndTime';

// Example: Calculate distance and time for a line survey mission
const exampleWaypoints = [
  { latitude: 10.8231, longitude: 106.6297 }, // Starting point in HCMC
  { latitude: 10.8331, longitude: 106.6397 }, // 1.4km northeast
  { latitude: 10.8431, longitude: 106.6497 }, // Another 1.4km northeast
  { latitude: 10.8531, longitude: 106.6597 }, // Another 1.4km northeast
];

const result = calculateLineDistanceAndTime(exampleWaypoints, 20);

console.log('=== Survey Mission Calculation Example ===');
console.log(`Total Distance: ${result.totalDistance.toFixed(2)} km`);
console.log(`Estimated Time: ${result.estimatedTime} minutes`);
console.log(`Cruise Speed: 20 m/s`);
console.log('');

// Manual calculation verification:
// Total distance ≈ 4.2 km (3 segments × 1.4 km each)
// Time = (4200 meters) / (20 m/s) / 60 = 3.5 minutes ≈ 3 minutes (floored)
console.log('Manual verification:');
console.log(`Expected distance: ~4.2 km`);
console.log(`Expected time: 3 minutes (4200m ÷ 20m/s ÷ 60)`);
console.log(`Actual distance: ${result.totalDistance.toFixed(2)} km`);
console.log(`Actual time: ${result.estimatedTime} minutes`);

export { exampleWaypoints, result };
