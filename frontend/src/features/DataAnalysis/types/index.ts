interface DataAnalysisState {
  id: number;
  video_path: string;
  drone_name: string;
  operator_name: string;
  register_number: string;
  manufacturer: string;
  flight_distance: string;
  flight_time: string;
  flight_altitude: string;
  capture_altitude: string;
  start_point_x: number;
  start_point_y: number;
  end_point_x: number;
  end_point_y: number;
  start_time: string;
  end_time: string;
  remark: string;
  profile_name: string;
  profile_device__created_on: string;
  purpose: string;
  analysis: Array<{
    detections: Array<{
      label: string;
    }>;
    detection_count: number;
    datetime: string;
    detected_image_path: string;
    timestamp: number | null;
  }>;
  mission_location: string;
  stream_monitor__is_external?: boolean;
  stream_monitor__ip_source?: string;
  stream_monitor__id?: number;
  stream_monitor__external_drone_name?: string;
  stream_monitor__external_operation_name?: string;
  stream_monitor__external_registration_number?: string;
  stream_monitor__external_manufacturer?: string;
  stream_monitor__external_flight_distance?: number | string;
  stream_monitor__external_flight_time?: number | string;
  stream_monitor__external_flight_altitude?: number | string;
  stream_monitor__external_start_point_x?: string | number;
  stream_monitor__external_start_point_y?: string | number;
  stream_monitor__external_end_point_x?: string | number;
  stream_monitor__external_end_point_y?: string | number;
  stream_monitor__external_start_time?: string;
  stream_monitor__external_end_time?: string;
  stream_monitor__external_remark?: string;
}

export type { DataAnalysisState };
