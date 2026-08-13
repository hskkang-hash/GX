// Common interfaces for ReadyToShipTab
export interface OrderRow {
  id: number;
  order_id: string;
  real_order_id?: string; // Add this field to store the actual order ID for API
  current_status__code: string;
  order_time: string;
  sender: string;
  recipient: string;
  creator: string;
  number_of_package: number;
  origin: string;
  destination: string;
  estimated_distance?: string;
  estimated_duration?: string;
  order_terminal_id?: number;
}

export interface Package {
  id: string;
  weight?: number;
  weightUnit?: string;
  order_id?: string;
}

export interface Drone {
  doneId: string;
  name: string;
  id: string;
  model: string;
  battery: string;
  maxLoad: string;
  maxLoadValue: number;
  maxLoadUnit: string;
  availablePayload: number; // Add available payload for weight calculations
  droneLocation: { lat: number; lng: number } | null;
  currentLoad: number;
  assignedPackages: string[];
  disabled: boolean;
  disableReason: {
    detailed_message?: string;
    code?: string;
    [key: string]: any;
  } | null;
}

export interface TableData {
  data: OrderRow[];
  totalItem: number;
  totalPage: number;
}

export interface SearchParams {
  pageSize: number;
  currentPage: number;
  objSearch: Record<string, unknown>;
}

export enum ProcessingStep {
  SELECT_ROUTE = 'SELECT_ROUTE',
  SELECT_DRONE = 'SELECT_DRONE',
}
