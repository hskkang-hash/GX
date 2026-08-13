import { Dayjs } from 'dayjs';
import { SurveillanceProfileState } from '../../../../types';

export interface TimelineEvent {
    id: string | number;
    startTime: string; // Format: "HH:mm"
    endTime: string; // Format: "HH:mm"
    profileName: string;
    color: string;
    darkColor: string;
    itemId?: string; // For drone view: "D-1761807222897"
    lane?: number; // Lane index for overlapping events (0-based)
    status_code: string;
}

// Interface for API response
export interface ProfileEvent {
    profile_id: number;
    profile_name: string;
    start_time: string; // Format: "07/11/2025 00:00"
    end_time: string; // Format: "07/11/2025 00:02"
    color_code: string;
    status_code: string
}

export interface DroneEvent {
    drone_id: number;
    drone_serial: string;
    profiles: ProfileEvent[];
}

export interface EventsTimelineData {
    by_profile: ProfileEvent[];
    by_drone: DroneEvent[];
}

export interface TimelineViewProps {
    viewType: 'profile' | 'drone';
    onViewTypeChange: (type: 'profile' | 'drone') => void;
    selectedItems: Array<{ label: string; value: string | number }>;
    onSelectedItemsChange: (items: Array<{ label: string; value: string | number }>) => void;
    availableItems: Array<{ label: string; value: string | number }>;
    selectedDate: Dayjs | string;
    onDateChange: (date: Dayjs | null) => void;
    events: TimelineEvent[];
    onEventClick?: (event: { detailSurveillanceProfile: SurveillanceProfileState | null, markerData: MarkerData[] }) => void;
    currentPage: number;
    totalItems: number;
    pageSize: number;
    onPageChange: (page: number) => void;
}