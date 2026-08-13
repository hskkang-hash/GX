type DroneAssignmentRoutePoint = {
  latitude: number | string;
  longitude: number | string;
  altitude?: number | string | null;
  name?: string;
  params?: Record<string, readonly string[]>;
};

type DroneAssignmentWithRoute = {
  id?: number | string;
  device_id?: number | string;
  device__color?: string;
  device?: {
    id: number | string;
    color?: string;
  };
  route_path?: DroneAssignmentRoutePoint[];
};

type ConvertedCommand = {
  command: string;
  param1: string | undefined;
  param2: string | undefined;
  param3: string | undefined;
  param4: string | undefined;
};

export const convertCommand = (
  input?: Record<string, readonly string[]>,
): ConvertedCommand | null => {
  if (!input) {
    return null;
  }

  const entries = Object.entries(input);

  if (entries.length === 0) {
    return null;
  }

  const [command, params] = entries[0];

  return {
    command,
    param1: params[0],
    param2: params[1],
    param3: params[2],
    param4: params[3],
  };
};

export const extractWaypoints = (
  data: unknown,
): Array<{
  lat: number;
  lng: number;
  operating_altitude: number;
  name?: string;
  color?: string;
  routeId?: string | number;
}> => {
  if (!Array.isArray(data)) return [];

  return (data as DroneAssignmentWithRoute[]).flatMap((item) => {
    if (!Array.isArray(item.route_path)) return [];
    const routeId = item.id ?? undefined;

    return item.route_path.map((point) => {
      const command = convertCommand(point.params);

      return {
        lat: Number(point.latitude),
        lng: Number(point.longitude),
        operating_altitude: Number(point.altitude ?? 0),
        name: point.name,
        color: item.device__color,
        routeId: routeId,
        frame: point.frame_name,
        command: command?.command,
        param1: command?.param1,
        param2: command?.param2,
        param3: command?.param3,
        param4: command?.param4,
      };
    });
  });
};

export const extractWaypointsDroneAssignments = (
  data: unknown,
): Array<{
  lat: number;
  lng: number;
  operating_altitude: number;
  name?: string;
  color?: string;
  routeId?: string | number;
}> => {
  if (!Array.isArray(data)) return [];

  return (data as DroneAssignmentWithRoute[]).flatMap((item) => {
    if (!Array.isArray(item.route_path)) return [];
    const routeId = item.device_id ?? undefined;

    return item.route_path.map((point) => {
      const command = convertCommand(point.params);

      return {
        lat: Number(point.latitude),
        lng: Number(point.longitude),
        operating_altitude: Number(point.altitude ?? 0),
        name: point.name,
        color: item.device?.color,
        routeId,
        frame: point?.frame_name,
        command: point?.command_name,
        param1: command?.param1,
        param2: command?.param2,
        param3: command?.param3,
        param4: command?.param4,
      };
    });
  });
};
