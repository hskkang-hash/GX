import API from './API';

export interface NotamSearchParams {
  sch_series?: string;
  search_type?: string;
  sch_snow_series?: string;
  sch_select?: string;
  sch_inorout?: string;
  sch_from_date?: string;
  sch_from_time?: string;
  sch_to_date?: string;
  sch_to_time?: string;
  sch_notam_no?: string;
  sch_elevation_min?: string;
  sch_elevation_max?: string;
  sch_airport?: string;
  sch_full_text?: string;
  iborderby?: string;
  ibpage?: number;
}

export interface NotamData {
  LOCATION: string;
  QCODE_MEAN: string;
  SERIES: string;
  ISSUE_TIME: string;
  QCODE: string;
  EFFECTIVEEND: string;
  FIR: string;
  NOTAM_NO: string;
  ECODE: string;
  AIS_TYPE: string;
  FULL_TEXT: string;
  SEQ: string;
  EFFECTIVESTART: string;
}

export interface NotamResponse {
  DATA: NotamData[];
  Total: number;
}

export interface NotamDetailItem {
  ITEM: string;
  MEAN: string;
}

export interface NotamDetailResponse {
  DATA: NotamDetailItem[];
}

/**
 * Search NOTAM data via backend proxy
 */
export const searchValidNotam = async (
  params: NotamSearchParams
): Promise<NotamResponse> => {
  try {
    // Send JSON to backend proxy, which will forward to AIM API
    const response = await API.post<NotamResponse>(
      '/api/proxy/notam',
      params
    );

    console.log('Raw API response:', response);
    console.log('Response type:', typeof response);
    console.log('Response.DATA:', response.DATA);
    console.log('Response.Total:', response.Total);

    // API client already unwraps the response, so return response directly
    return response;
  } catch (error) {
    console.error('Error fetching NOTAM data:', error);
    throw error;
  }
};

/**
 * Get detailed NOTAM information in Korean
 */
export const getNotamDetailKr = async (
  seq: string
): Promise<NotamDetailResponse> => {
  try {
    // Call backend proxy which forwards to AIM API
    const response = await API.post<NotamDetailResponse>(
      '/api/proxy/notam-detail',
      { seq }
    );

    return response;
  } catch (error) {
    console.error('Error fetching NOTAM detail:', error);
    throw error;
  }
};

/**
 * Get default search parameters
 */
export const getDefaultSearchParams = (): NotamSearchParams => {
  const now = new Date();
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);

  const formatDate = (date: Date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const formatTime = (date: Date) => {
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${hours}${minutes}`;
  };

  return {
    search_type: 'V',
    sch_inorout: 'D',
    sch_from_date: formatDate(now),
    sch_from_time: formatTime(now),
    sch_to_date: formatDate(tomorrow),
    sch_to_time: formatTime(tomorrow),
    sch_series: '',
    sch_snow_series: '',
    sch_select: '',
    sch_notam_no: '',
    sch_elevation_min: '',
    sch_elevation_max: '',
    sch_airport: '',
    sch_full_text: '',
    iborderby: '',
    ibpage: 1,
  };
};
