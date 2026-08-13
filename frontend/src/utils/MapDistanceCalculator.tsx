import React, { useEffect, useState } from 'react';

interface Position {
  lat: number;
  lng: number;
}

interface MapDistanceCalculatorProps {
  positions: Position[];
  onDistanceCalculated: (distance: number) => void;
}

const calculateHaversineDistance = (
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
): number => {
  const R = 6371; // Radius of the Earth in kilometers
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c; // Distance in kilometers
};

// const MapDistanceCalculator: React.FC<MapDistanceCalculatorProps> = ({ positions }) => {
//     const [distance, setDistance] = useState<number>(0);

//     useEffect(() => {
//         if (!positions?.length) return;

//         let totalDistance = 0;
//         for (let i = 0; i < positions.length - 1; i++) {
//             const currentPoint = positions[i];
//             const nextPoint = positions[i + 1];
//             const segmentDistance = calculateHaversineDistance(
//                 currentPoint.lat,
//                 currentPoint.lng,
//                 nextPoint.lat,
//                 nextPoint.lng
//             );
//             totalDistance += segmentDistance;
//         }

//         setDistance(totalDistance);
//     }, [positions]);

//     return distance.toFixed(2) + " km";
// };

// export default MapDistanceCalculator;

const MapDistanceCalculator: React.FC<MapDistanceCalculatorProps> = ({
  positions,
  onDistanceCalculated,
}) => {
  useEffect(() => {
    if (!positions?.length) return;

    let totalDistance = 0;
    for (let i = 0; i < positions.length - 1; i++) {
      const current = positions[i];
      const next = positions[i + 1];
      const d = calculateHaversineDistance(
        current.lat,
        current.lng,
        next.lat,
        next.lng,
      );
      totalDistance += d;
    }

    onDistanceCalculated(totalDistance);
  }, [positions]);

  return null;
};
export default MapDistanceCalculator;
