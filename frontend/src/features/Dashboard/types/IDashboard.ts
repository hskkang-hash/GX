export interface PanelDataItem {
  color: {
    dark: string;
    light: string;
  };
  label: string;
  value: number;
}

export interface PanelData {
  data: PanelDataItem[];
  percentage?: number;
}

export interface PanelConfig {
  type?: string;
  field?: string;
  icon?: string;
  columns?: string[];
}

export interface Panel {
  id: number;
  panel_title: string;
  panel_type: string;
  panel_config: PanelConfig;
  panel_data: PanelData;
}

export interface DashboardData {
  id: number;
  name: string;
  code: string;
  layout_config: object;
  created_on: string;
  data_updated_at: string;
  panels: Panel[];
  weather_setting?: {
    latitude: number;
    longitude: number;
    address: string;
  };
  routes: any[];
}
