export interface DroneAssignment {
  id: number;
  drone: string;
  start_time: string;
  start_point: string;
  end_point: string;
  log: boolean;
  record: boolean;
  analysis: boolean;
  video_path: string;
  color?: string;
  route_path?: {
    latitude: number;
    longitude: number;
    name?: string;
  }[];
}

export interface SurveillanceProfileState {
  altitude?: number;
  takeoff_altitude?: number;
  altitude_separation?: number;
  region?: string | null;
  id?: number;
  profile_id?: number;
  profile_name?: string;
  mission__id?: number;
  mission__line_mission?: boolean;
  purpose?: string;
  created_date: string;
  start_date: string;
  end_date: string;
  total_distance: number;
  total_time: number;
  log: string;
  record: string;
  analysis: string;
  operator: string;
  chart_data: {
    waypointName: string;
    cruise_speed: number;
    operating_altitude: number;
    cumulativeDistance: number;
    order: number;
  }[];
  route_path?: {
    latitude: number;
    longitude: number;
    name?: string;
  }[];
  drone_assignments?: DroneAssignment[];
  return?: boolean | null;
  maximum_number_of_drones?: number | null;
  total_estimated_time?: number | null;
  operator__id?: number | null;
  repeat_occurrences?: number | null;
  repeat_until_date?: string | null;
  operator__first_name?: string | null;
  operator__last_name?: string | null;
  note?: string | null;
  color_code?: string | null;
  repeat_type_id?: number | null;
  repeat_until_type_id?: number | null;
  repeat_until_type__code?: string | null;
  repeat_until_type__name?: string | null;
  name?: string | null;
  mission?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  repeat?: string | null;
  repeat_type__code?: string | null;
  repeat_type__name?: string | null;
}

export interface SurveillanceProfileResponse {
  cancel_reject_reason?: string | null;
  id?: number | null;
  name?: string | null;
  mission__region?: string | null;
  region?: string | null;
  purpose__name?: string | null;
  created_on?: string | null;
  start_time?: string | null;
  estimated_end_time?: string | null;
  actual_start_time?: string | null;
  actual_end_time?: string | null;
  total_distance?: number | null;
  estimated_time?: number | null;
  cancel_reason?: string | null;
  total_flight_time?: number | null;
  mission__log_collection?: boolean | null;
  mission__video_recording?: boolean | null;
  mission__video_analysis?: boolean | null;
  operator_full_name?: string | null;
  mission?: string | null;
  mission_id?: number | null;
  repeat?: string | null;
  repeat_type__code?: string | null;
  return?: string | null;
  maximum_number_of_drones?: string | null;
  total_estimated_time?: string | null;
  operator?: string | null;
  operator__id?: number | null;
  repeat_occurrences?: number | null;
  repeat_until_date?: string | null;
  operator__first_name?: string | null;
  operator__last_name?: string | null;
  note?: string | null;
  color_code?: string | null;
  repeat_type_id?: number | null;
  repeat_until_type_id?: number | null;
  repeat_until_type__code?: string | null;
  repeat_until_type__name?: string | null;
  chart_data?: {
    waypointName: string;
    cruise_speed: number;
    operating_altitude: number;
    cumulativeDistance: number;
    order: number;
  }[];
  status__code?: string | null;
  rejection_reason?: string | null;
  group__name?: string | null;
  devices?: unknown;
  drone_assignments?: {
    id?: number;
    device__id?: number;
    device__serial_number?: string;
    scheduled_start_time?: string;
    start_waypoint__name?: string;
    end_waypoint__name?: string;
    start_waypoint_id?: number;
    end_waypoint_id?: number;
    log_collection?: boolean;
    video_recording?: boolean;
    video_analysis?: boolean;
    device__color?: string;
    log_path?: string;
    video_path?: string;
    analysis_path?: string;
    route_path?: Array<{
      latitude: number;
      longitude: number;
      name?: string;
      command_name?: string;
      frame_name?: string;
      param_1?: number;
      param_2?: number;
      param_3?: number;
      param_4?: number;
      altitude?: number;
      params?: {
        [key: string]: number;
      };
    }>;
    device?: {
      id?: number;
      name?: string;
      color?: string;
    };
  }[];
  has_video_analysis?: boolean | null;
}
