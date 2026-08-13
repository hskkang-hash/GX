import dayjs from 'dayjs';

export interface DroneRoute {
  device: {
    id: number;
    name: string;
    color?: string;
  };
  route_path: {
    latitude: number;
    longitude: number;
    name?: string;
  }[];
}

export interface SelectOption {
  value: string | number | null;
  label: string | null;
  code: string | null;
}

export interface FormSurveillanceProfile {
  name: string;
  mission_id: SelectOption | null;
  repeat_type_id: SelectOption | null;
  repeat_until_type_id: SelectOption | null;
  repeat_occurrences: string | null;
  repeat_until_date: dayjs.Dayjs | null;
  type: string | null;
  operator: SelectOption | null;
  color_code: string | null;
  start_time: dayjs.Dayjs | null;
  note: string;
  code: string;
  altitude?: number | null;
  takeoff_altitude?: number | null;
  altitude_separation?: number | null;
}

export interface DroneAssignment {
  device_id: number | null;
  scheduled_start_time?: string | null;
  start_waypoint_id: number | null;
  end_waypoint_id: number | null;
  log_collection: boolean;
  video_recording: boolean;
  video_analysis: boolean;
  order: number;
  estimated_distance_km?: number;
  estimated_time_minutes?: number;
  note?: string;
  route_path?: Array<{
    order: number;
    latitude: number;
    longitude: number;
    altitude: number | null;
    distance_from_start?: number;
    type: string;
    mission_waypoint_id: number;
    name: string;
  }>;
  device?: any;
  color?: string;
  waiting_coordinates?: [number, number] | null;
}

export interface waypointDrone {
  description: string;
  distance_from_start: number;
  latitude: number;
  longitude: number;
  mission_waypoint_id: number;
  order: number;
  transect_index: number | null;
  type: string;
  waypoint_index: number;
}

export interface WaypointOption {
  value: number;
  label: string;
}

// INTERFACE FOR SURVEY MISSION STATE
export interface SurveyMissionState {
  id: number;
  code: string;
  name: string;
  region?: string | null;
  status__name: string;
  created_by_full_name: string;
  created_on: string;
  start_point: string;
  end_point: string;
  total_distance: number;
  estimated_time: number;
  note: string;
  group__name: string;
  group__id: number;
  status__code: string;
  is_active: boolean;
  return_to_home?: boolean;
  rejection_reason?: string;
}

export interface Waypoint {
  id?: number;
  order?: number;
  name?: string;
  operating_altitude?: number;
  terminal__latitude?: number;
  terminal__longitude?: number;
  command?: {
    value: number;
    label: string;
  };
  frame?: {
    value: number;
    label: string;
  };
  param_1?: number;
  param_2?: number;
  param_3?: number;
  param_4?: number;
  latitude: number;
  longitude: number;
  altitude?: number;
}

export interface ChartDataPoint {
  name: string;
  cruise_speed: number;
  operating_altitude: number;
  distance: number;
  order: number;
}

export interface ChartDataItem {
  waypointName: string;
  cruise_speed: number;
  operating_altitude: number;
  cumulativeDistance: number;
  order: number;
}

export interface WaypointDetailsProps {
  command?: string;
  frame?: string;
  param_1?: number;
  param_2?: number;
  param_3?: number;
  param_4?: number;
  latitude?: string;
  longitude?: string;
  altitude?: string;
}
