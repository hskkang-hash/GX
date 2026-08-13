import { haversineDistance } from '../../../utils/utils';

interface Terminal {
  cruise_speed: number;
  operating_altitude: number;
  stop: boolean;
  latitude: number;
  longitude: number;
  time_stops: string;
  terminal_id: string;
}

interface EstimatedTime {
  value: number;
  unit: string;
}

// conver "40 km/h" to 40, "10 mins" to 10, "40 m" to 40 return { value: number, unit: string }
const convertUnit = (value: string) => {
  const [num, unit] = value.split(' ');
  return { value: Number(num), unit };
};

export const convertEstimated = (
  listTerminal: Terminal[],
  isReturn = false,
): {
  totalDistance: number;
  totalEstimated: EstimatedTime;
  estimatedArrivalTime: EstimatedTime;
  averageSpeed: number;
  totalTimeStop: number;
} => {
  // calculate average speed
  const averageSpeed =
    listTerminal.length > 0
      ? listTerminal.reduce(
          (acc, terminal) =>
            acc + (terminal.cruise_speed ? Number(terminal.cruise_speed) : 0),
          0,
        ) / listTerminal.length
      : 0;

  // calculate total time stop
  let totalTimeStop =
    listTerminal.length > 0
      ? Number(
          (
            listTerminal.reduce((acc, terminal) => {
              return (
                acc +
                (terminal.stop && terminal.time_stops
                  ? typeof terminal.time_stops === 'string'
                    ? convertUnit(terminal.time_stops)?.value
                    : terminal.time_stops
                  : 0)
              );
            }, 0) / 60
          ).toFixed(2),
        )
      : 0;

  // calculate distance take off and landing
  const distanceTakeOffAndLanding =
    listTerminal.length > 0
      ? listTerminal.reduce((acc, terminal, index) => {
          if (index === 0) {
            return (
              acc +
              (terminal.stop && terminal.operating_altitude
                ? Number(terminal.operating_altitude)
                : 0)
            );
          }
          if (index === listTerminal.length - 1) {
            return (
              acc +
              (terminal.stop && terminal.operating_altitude
                ? Number(terminal.operating_altitude)
                : 0)
            );
          }
          return (
            acc +
            (terminal.stop && terminal.operating_altitude
              ? Number(terminal.operating_altitude) * 2
              : 0)
          );
        }, 0) / 1000 // convert m to km
      : 0;

  // calculate total distance
  let totalDistance =
    listTerminal.length > 1
      ? listTerminal.reduce((acc, terminal, index) => {
          if (index < listTerminal.length - 1) {
            const segment = haversineDistance(
              terminal,
              listTerminal[index + 1],
            );
            return acc + segment;
          }
          return acc;
        }, 0) + distanceTakeOffAndLanding
      : 0;

  // calculate flight time
  const flightTimeMinutes = isReturn
    ? averageSpeed > 0
      ? (totalDistance / (averageSpeed * 3.6)) * 60 * 2
      : 0
    : averageSpeed > 0
      ? (totalDistance / (averageSpeed * 3.6)) * 60
      : 0;

  // calculate total estimated time
  const totalEstimatedMinutes = isReturn
    ? flightTimeMinutes + totalTimeStop * 2
    : flightTimeMinutes + totalTimeStop;

  const totalEstimated: EstimatedTime = {
    value:
      totalEstimatedMinutes > 0 ? Number(totalEstimatedMinutes.toFixed(2)) : 0,
    unit: 'mins',
  };

  const estimatedArrivalTime: EstimatedTime = {
    value: flightTimeMinutes > 0 ? Number(flightTimeMinutes.toFixed(2)) : 0,
    unit: 'mins',
  };

  if (isReturn) {
    totalTimeStop = totalTimeStop * 2;
    totalDistance = totalDistance * 2;
  }

  return {
    totalDistance,
    totalEstimated,
    estimatedArrivalTime,
    averageSpeed,
    totalTimeStop,
  };
};

export const convertUnitTimeStopsToSeconds = (
  value: number,
  unit: string,
): number => {
  // Normalize unit to lowercase for consistent comparison
  const normalizedUnit = unit.toLowerCase();

  // Convert to seconds based on unit
  switch (normalizedUnit) {
    // Seconds - already in seconds
    case 's':
    case 'seconds':
    case 'second':
    case 'sec':
    case 'secs':
      return Number(value);

    // Minutes - convert to seconds
    case 'min':
    case 'minutes':
    case 'minute':
    case 'mins':
      return Number(value) * 60;

    // Hours - convert to seconds
    case 'h':
    case 'hours':
    case 'hour':
    case 'hrs':
    case 'hr':
      return Number(value) * 3600;

    // Default case - assume seconds if unit not recognized
    default:
      return Number(value);
  }
};
