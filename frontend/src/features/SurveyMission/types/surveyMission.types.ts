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
  capture_altitude: number;
  takeoff_altitude: number;
  altitude_separation: number;
}

export interface SurveyMissionPageState {
  pageSize: number | null;
  currentPage: number;
  selectedRows: SurveyMissionState[] | [];
  refreshTable: boolean | false;
  openOffcanvas: boolean | false;
  showApproveMissionModal: boolean | false;
  showRejectMissionModal: boolean | false;
  showImportMissionModal: boolean | false;
  data: {
    data: SurveyMissionState[] | null;
    totalItem: number | 0;
    totalPage: number | 0;
  };
  missionId: number | null;
  hasPermissionActionSurveyMission: boolean | false;
}

export interface RejectMissionFormValues {
  reason: string;
}

export interface Waypoint {
  cruise_speed?: string;
  operating_altitude?: string;
  terminal__latitude: string;
  terminal__longitude: string;
  command_line: any;
  command: {
    value: number;
    label: string;
  };
  frame: {
    value: number;
    label: string;
  };
  param_1: number;
  param_2: number;
  param_3: number;
  param_4: number;
  param_5: number;
  param_6: number;
  latitude: string;
  longitude: string;
  altitude: number;
}

export interface SurveyMissionFormValues {
  group: {
    value: number;
    label: string;
  } | null;
  name: string | null;
  region: string | null;
  return: boolean;
  maximum_number_of_drones: number | null;
  purpose: {
    value: number;
    label: string;
  } | null;
  log_collection: boolean;
  video_recording: boolean;
  video_analysis: boolean;
  total_distance: number | null;
  estimated_time: number | null;
  note: string | null;
  waypoints: Waypoint[] | [];
  from_route?: boolean;
  settings: {
    hover_and_capture: boolean;
    altitude: number;
    takeoff_altitude: number;
    altitude_separation: number;
    overlap: number;
    trigger_distance: number;
    spacing: number;
    angle: number;
    turnaround_distance: number;
  };
}

export interface ImportMissionFormValues {
  name: string | null;
  purpose_id: number | undefined;
  route_ids: number[];
  log_collection: boolean;
  video_recording: boolean;
  video_analysis: boolean;
  note: string | null;
  total_distance: number | null;
  estimated_time: number | null;
  altitude: number | null;
  takeoff_altitude: number | null;
  altitude_separation: number | null;
  cruise_speed: number | null;
  hover_speed: number | null;
}
