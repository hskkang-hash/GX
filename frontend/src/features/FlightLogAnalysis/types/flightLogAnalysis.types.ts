interface FlightLogAnalysisState {
  id: number;
  route_code: string;
  route_name: string;
  start_time: string;
  end_time: string;
  total_distance: string;
  start_point__name: string;
  end_point__name: string;
  drone_anomaly_prediction__name: string;
  drone_anomaly_prediction__code: string;
  group__name: string;
  name: string;
  mission: string;
  mission_id: string;
  repeat: string;
  operator: string;
  purpose: string;
  return: string;
  maximum_number_of_drones: string;
  service_name: string;
  drone_name: string;
  profile_drone__profile: string;
  mission_name: string;
}

type FlightLogAnalysisPage = {
  pageSize: number | null;
  currentPage: number;
  selectedRows: FlightLogAnalysisState[] | [];
  selectedRow: FlightLogAnalysisState | null;
  refreshTable: boolean | false;
  openOffcanvas: boolean | false;
  modalDetail: boolean | false;
  data: {
    data: FlightLogAnalysisState[] | [];
    totalItem: number;
    totalPage: number;
  };
};

type FlightLogAnalysisPageAction =
  | {
      type: 'SET_PAGE_SIZE';
      payload: number;
    }
  | {
      type: 'SET_CURRENT_PAGE';
      payload: number;
    }
  | {
      type: 'SET_SELECTED_ROWS';
      payload: FlightLogAnalysisState[];
    }
  | {
      type: 'SET_SELECTED_ROW';
      payload: FlightLogAnalysisState | null;
    }
  | {
      type: 'TOGGLE_REFRESH';
      payload?: boolean;
    }
  | {
      type: 'OPEN_OFFCANVAS';
      payload?: boolean;
    }
  | {
      type: 'OPEN_MODAL_DETAIL';
      payload?: boolean;
    }
  | {
      type: 'SET_DATA';
      payload: {
        data: FlightLogAnalysisState[];
        totalItem: number;
        totalPage: number;
      };
    };

export type {
  FlightLogAnalysisState,
  FlightLogAnalysisPage,
  FlightLogAnalysisPageAction,
};
