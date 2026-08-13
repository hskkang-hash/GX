import { yupResolver } from '@hookform/resolvers/yup';
import { Box } from '@mui/material';
import dayjs from 'dayjs';
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type FC,
  type ReactNode,
} from 'react';
import { FormProvider, useForm, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { BsTrash } from 'react-icons/bs';
import { GoPlus } from 'react-icons/go';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  ActionBtn,
  Container,
  CustomBreadcrumb,
  CustomBtn,
  CustomizableTable,
  CustomModal,
  FormBlock,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useTheme,
  useUserInfo,
} from 'rj-core';
import { v4 as uuidv4 } from 'uuid';

import Colors from '@/configs/Colors';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';
import { useSurveyMission } from '@/features/SurveyMission/hooks/useSurveyMission';
import { useDrawingModeStore } from '@/features/surveillanceProfile/stores/drawingModeStore';
import { calculateLineDistanceAndTime } from '@/features/surveillanceProfile/utils/calculateDistanceAndTime';
import { useFormNavigationBlocker } from '@/hooks/useFormNavigationBlocker';
import { CustomRoutes } from '@/services/API';
import { schemaSurveillanceProfile } from '@/services/schemaForm';

import { useSurveillanceProfile } from '../../../hooks/useSurveillanceProfile';
import { convertUnitValue } from '../../../utils/convertLineToWaypoints';
import { extractWaypointsDroneAssignments } from '../../../utils/convertMarkerData';
import type {
  ChartDataItem,
  ChartDataPoint,
  DroneAssignment as FormDroneAssignment,
  FormSurveillanceProfile,
  SelectOption,
  SurveyMissionState,
  Waypoint,
  waypointDrone,
} from './AddNewProfile.d';
import CoordinatePickerModal from './components/CoordinatePickerModal';
import FlightChart from './components/FlightChart';
import FormDataProfile from './components/FormDataProfile';
import GeneralInformation from './components/GeneralInformation';
import {
  DroneCell,
  StartTimeCell,
  SwitchCell,
  WaypointCell,
  WaitingCoordinatesCell,
} from './components/HelperCell';
import ProfileMap from './components/ProfileMap';

type RoutePathPoint = NonNullable<FormDroneAssignment['route_path']>[number];
type DefaultAssignment = {
  device_id?: number | null;
  scheduled_start_time?: string | null;
  start_waypoint?: { id: number | null } | null;
  end_waypoint?: { id: number | null } | null;
  log_collection?: boolean;
  video_recording?: boolean;
  video_analysis?: boolean;
  order?: number;
  device?: {
    id?: number | null;
    name?: string | null;
    color?: string | null;
  } | null;
  route_path?: RoutePathPoint[];
  waiting_coordinates?: [number, number] | null;
};

type DevicesDataState = {
  default_assignments?: DefaultAssignment[];
  maximum_drones?: number;
  start_end_points?: waypointDrone[];
  devices?: {
    id?: number | null;
    name?: string | null;
    color?: string | null;
  }[];
};

type UserInfo = {
  id?: number | null;
  first_name?: string | null;
};

type TableRowContext = {
  row?: {
    index?: number;
    original?: FormDroneAssignment;
  };
  index?: number;
  [key: string]: unknown;
};

type CustomizableColumn = {
  Header: string;
  accessor: string;
  filterVariant?: string;
  filterOptions?: unknown[];
  cell?: (row: TableRowContext) => ReactNode;
  customStyle?: CSSProperties;
  enableSorting?: boolean;
  enableColumnFilter?: boolean;
  notUseConfigTable?: boolean;
};

type CreateProfilePayload = {
  name: string;
  mission_id: number;
  start_time: string | null;
  operator_id: number;
  repeat_type_id: number;
  repeat_until_type_id?: number;
  repeat_until_date?: string | null;
  repeat_occurrences?: number | null;
  color_code: string;
  note: string;
  drones: Array<{
    device_id: number;
    order: number;
    scheduled_start_time: string | null;
    start_waypoint_id: number;
    end_waypoint_id: number;
    log_collection: boolean;
    video_recording: boolean;
    video_analysis: boolean;
    note: string;
  }>;
};

const AddNewProfile: FC = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [searchParams] = useSearchParams();
  const activeTabFromSearchParams = searchParams.get('tab') || null;
  const idFromSearchParams = searchParams.get('id') || null;
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);
  const [isFromRoute, setIsFromRoute] = useState<boolean>(false);
  const userInfo = useUserInfo();
  const {
    dateFormat,
    convertDateFormatToUTC,
    convertDateFormatToUTCfollowUserTimeZone,
    converRawDateToDateTimeFormat,
  } = useConvertDate();

  const [clickCheckErrorWaypoint, setClickCheckErrorWaypoint] = useState(false);

  const [devicesData, setDevicesData] = useState<DevicesDataState>({
    default_assignments: [],
    start_end_points: [],
  });

  const [isCoordinateModalOpen, setIsCoordinateModalOpen] = useState(false);
  const [selectedRowIndex, setSelectedRowIndex] = useState<number | null>(null);
  const MAX_DRONE_ASSIGNMENTS = devicesData?.maximum_drones || 0;
  const [droneAssignments, setDroneAssignments] = useState<
    FormDroneAssignment[]
  >([]);

  const [clickSave, setClickSave] = useState(false);

  const { getDetailSurveyMission } = useSurveyMission();
  const {
    fetchListAvalableDrones,
    createSurveillanceProfileAPI,
    fetchDetailSurveillanceProfile,
    detailSurveillanceProfile,
  } = useSurveillanceProfile();

  console.log('detailSurveillanceProfile', detailSurveillanceProfile);

  const [flagErrorWaypoint, setFlagErrorWaypoint] = useState<{
    [key: number]: boolean;
  }>({});
  const [flagErrorDrone, setFlagErrorDrone] = useState<{
    [key: number]: boolean;
  }>({});
  const [flagWarningDrone, setFlagWarningDrone] = useState<{
    [key: number]: boolean;
  }>({});
  const [flagErrorRequiredFields, setFlagErrorRequiredFields] = useState<{
    [key: number]: {
      device_id?: boolean;
      start_waypoint_id?: boolean;
      end_waypoint_id?: boolean;
    };
  }>({});

  const [surveyMission, setSurveyMission] = useState<SurveyMissionState | null>(
    null,
  );
  const [markerData, setMarkerData] = useState<
    Array<{
      lat: number;
      lng: number;
      name?: string;
      color?: string;
      operating_altitude?: number;
      routeId?: string | number;
    }>
  >([]);

  const [chartData, setChartData] = useState<ChartDataItem[]>([]);

  const setCurrentShape = useDrawingModeStore((state) => state.setCurrentShape);
  const currentShape = useDrawingModeStore((state) => state.currentShape);
  const [allWaypoints, setAllWaypoints] = useState<Waypoint[]>([]);
  const populatedProfileId = useRef<number | null>(null);

  const toNullableNumber = useCallback((value: unknown): number | null => {
    if (typeof value === 'number') {
      return Number.isNaN(value) ? null : value;
    }

    if (typeof value === 'string' && value.trim().length > 0) {
      const parsed = Number(value);
      return Number.isNaN(parsed) ? null : parsed;
    }

    return null;
  }, []);

  const isLineMode = useMemo(
    () => currentShape?.type === 'LINE',
    [currentShape],
  );

  const methods = useForm<FormSurveillanceProfile>({
    defaultValues: {
      mission_id: null,
      repeat_type_id: { value: 1, label: t('None'), code: 'none' },
      operator: {
        value: userInfo?.id ?? null,
        label: userInfo?.profile__name ?? null,
      },
      repeat_until_type_id: null,
      repeat_occurrences: null,
      repeat_until_date: null,
      start_time: null,
      color_code: '#1D9BE2',
      note: '',
      takeoff_altitude: null,
      altitude_separation: null,
    },
    resolver: yupResolver(schemaSurveillanceProfile(t)) as any,
    mode: 'onChange',
  });

  console.log('methods_dataaa3443', methods.getValues());

  const {
    handleSubmit,
    control,
    setError,
    watch,
    reset,
    setValue,
    formState: { isSubmitting, isDirty },
  } = methods;

  const missionSelect = useWatch<FormSurveillanceProfile, 'mission_id'>({
    control,
    name: 'mission_id',
  });

  const startTime = useWatch<FormSurveillanceProfile, 'start_time'>({
    control,
    name: 'start_time',
  });

  const missionId = useMemo<number | null>(() => {
    const value = missionSelect?.value;

    if (typeof value === 'number') {
      return value;
    }

    if (typeof value === 'string') {
      const parsed = Number(value);
      return Number.isNaN(parsed) ? null : parsed;
    }
    return null;
  }, [missionSelect]);

  const startTimePayload = useMemo<string | null>(() => {
    if (!startTime) {
      return null;
    }
    const startTimeValue = convertDateFormatToUTCfollowUserTimeZone(startTime);
    return startTimeValue;
  }, [startTime]);

  const defaultAssignments = useMemo<DefaultAssignment[]>(() => {
    return Array.isArray(devicesData.default_assignments)
      ? devicesData.default_assignments
      : [];
  }, [devicesData.default_assignments]);

  const defaultDevices = useMemo<DefaultAssignment[]>(() => {
    return Array.isArray(devicesData.devices) ? devicesData.devices : [];
  }, [devicesData.devices]);

  const startEndPoints = useMemo<waypointDrone[]>(() => {
    return Array.isArray(devicesData.start_end_points)
      ? devicesData.start_end_points
      : [];
  }, [devicesData.start_end_points]);

  const handleFormSubmit = useCallback(
    async (data: FormSurveillanceProfile): Promise<void> => {
      setClickSave(true);
      const missionIdValue = toNullableNumber(data.mission_id?.value) ?? 0;
      const operatorIdValue = toNullableNumber(data.operator?.value) ?? 0;
      const repeatTypeIdValue =
        toNullableNumber(data.repeat_type_id?.value) ?? 0;

      const drones = droneAssignments
        .filter(
          (assignment) =>
            assignment.device_id !== null &&
            assignment.start_waypoint_id !== null &&
            assignment.end_waypoint_id !== null,
        )
        .map((assignment, index) => {
          const drone: any = {
            device_id: assignment.device_id ?? 0,
            order: assignment.order ?? index + 1,
            scheduled_start_time: assignment.scheduled_start_time ?? null,
            start_waypoint_id: assignment.start_waypoint_id ?? 0,
            end_waypoint_id: assignment.end_waypoint_id ?? 0,
            log_collection: assignment.log_collection ?? true,
            video_recording: assignment.video_recording ?? true,
            video_analysis: assignment.video_analysis ?? true,
            note: assignment.note ?? '',
          };

          // Only include waiting_coordinates if it exists and is valid
          if (
            assignment.waiting_coordinates &&
            Array.isArray(assignment.waiting_coordinates) &&
            assignment.waiting_coordinates.length === 2
          ) {
            drone.waiting_coordinates = assignment.waiting_coordinates;
          }

          return drone;
        });

      const submitData: CreateProfilePayload = {
        name: data.name ?? '',
        mission_id: missionIdValue,
        start_time: data.start_time
          ? convertDateFormatToUTCfollowUserTimeZone(data.start_time)
          : null,
        operator_id: operatorIdValue,
        repeat_type_id: repeatTypeIdValue,
        color_code: data.color_code ?? '#1D9BE2',
        note: data.note ?? '',
        takeoff_altitude: data.takeoff_altitude ?? null,
        altitude_separation: data.altitude_separation ?? null,
        drones,
      };

      if (data.repeat_type_id?.code !== 'none') {
        submitData.repeat_until_type_id =
          toNullableNumber(data.repeat_until_type_id?.value) ?? 0;
      }

      if (
        data.repeat_type_id?.code !== 'never' &&
        data.repeat_until_type_id?.code === 'on_date'
      ) {
        submitData.repeat_until_date = data.repeat_until_date
          ? data.repeat_until_date
          : null;
      }

      if (
        data.repeat_type_id?.code !== 'never' &&
        data.repeat_until_type_id?.code === 'after_occurrences'
      ) {
        const occurrences = Number(data.repeat_occurrences ?? 0);
        submitData.repeat_occurrences = Number.isNaN(occurrences)
          ? 0
          : occurrences;
      }

      console.log('_________submitData_________', submitData);

      const { success, message } = await createSurveillanceProfileAPI(
        submitData as unknown as Parameters<
          typeof createSurveillanceProfileAPI
        >[0],
      );
      if (success) {
        ToastTopHelper.success(message);
        navigate(CustomRoutes.surveyProfile.path);
      } else {
        ToastTopHelper.error(message);
      }
    },
    [
      createSurveillanceProfileAPI,
      droneAssignments,
      navigate,
      toNullableNumber,
      dateFormat,
      convertDateFormatToUTC,
    ],
  );

  const missionOptions = useMemo<SelectOption[]>(() => {
    console.log('defaultDevices', defaultDevices);
    return defaultDevices.map((assignment) => ({
      value: assignment.id ?? null,
      label: assignment.name ?? null,
      color: assignment.color ?? null,
      terminal_latitude: assignment.terminal_latitude ?? null,
      terminal_longitude: assignment.terminal_longitude ?? null,
      code: null,
    }));
  }, [defaultDevices]);

  const waypointOptions = useMemo(() => {
    return startEndPoints.map((item) => ({
      value: item.description ?? '',
      label: item.description ?? '',
      code: item.mission_waypoint_id ?? '',
    }));
  }, [startEndPoints]);

  const handleFetchListAvalableDrones = useCallback(async (): Promise<void> => {
    const { success, data, message } = await fetchListAvalableDrones({
      mission_id: missionId,
      start_time: startTimePayload,
    });

    if (success) {
      if (data.default_assignments.length === 0) {
        ToastTopHelper.error(message || 'No drones available!');
        setDroneAssignments([]);
        setDevicesData({
          default_assignments: [],
          start_end_points: [],
          devices: [],
        });
        setMarkerData([]);
        setChartData([]);
        setAllWaypoints([]);
        setCurrentShape(null);
        setCurrentShape(null);
        return;
      }
      const typedData = data as DevicesDataState;
      setDevicesData(typedData);
      const assignments = Array.isArray(typedData.default_assignments)
        ? typedData.default_assignments
        : [];
      const markerDataLine = extractWaypointsDroneAssignments(assignments);
      setMarkerData(markerDataLine);
      const initialAssignments: FormDroneAssignment[] = assignments.map(
        (assignment, index) => ({
          device_id: assignment.device_id ?? null,
          scheduled_start_time: assignment.scheduled_start_time ?? null,
          start_waypoint_id: assignment.start_waypoint?.id ?? null,
          end_waypoint_id: assignment.end_waypoint?.id ?? null,
          log_collection: assignment.log_collection ?? false,
          video_recording: assignment.video_recording ?? false,
          video_analysis: assignment.video_analysis ?? false,
          order: assignment.order ?? index + 1,
          metadata: {},
          note: '',
          device: assignment.device ?? null,
          route_path: assignment.route_path ?? [],
          routeDistance: calculateLineDistanceAndTime(
            assignment.route_path ?? [],
          ).totalDistance,
          waiting_coordinates: assignment.waiting_coordinates ?? null,
        }),
      );
      setDroneAssignments(initialAssignments);
    } else {
      setDroneAssignments([]);
      setDevicesData({
        default_assignments: [],
        start_end_points: [],
        devices: [],
      });
      setMarkerData([]);
      setChartData([]);
      setAllWaypoints([]);
      setCurrentShape(null);
      setCurrentShape(null);
      ToastTopHelper.error(message || 'No drones available!');
    }
  }, [missionId, startTimePayload]);

  useEffect(() => {
    if (!missionId || !startTimePayload) {
      return;
    }

    handleFetchListAvalableDrones();
  }, [missionId, startTimePayload, handleFetchListAvalableDrones]);

  // Helper function to generate route_path from allWaypoints,extract waypoints from start to end
  const generateRoutePath = useCallback(
    (
      startWaypointId: number | null,
      endWaypointId: number | null,
    ): RoutePathPoint[] => {
      if (!startWaypointId || !endWaypointId || allWaypoints.length === 0) {
        return [];
      }

      const startIndex = allWaypoints.findIndex(
        (waypoint) => waypoint.id === startWaypointId,
      );
      const endIndex = allWaypoints.findIndex(
        (waypoint) => waypoint.id === endWaypointId,
      );

      if (startIndex === -1 || endIndex === -1 || startIndex > endIndex) {
        return [];
      }

      const routeWaypoints = allWaypoints.slice(startIndex, endIndex + 1);

      return routeWaypoints.map((waypoint, index): RoutePathPoint => {
        const altitude = waypoint.operating_altitude;

        return {
          order: waypoint.order ?? index + 1,
          latitude: Number(waypoint.latitude),
          longitude: Number(waypoint.longitude),
          altitude:
            typeof altitude === 'number'
              ? altitude
              : altitude
                ? Number(String(altitude).replace(/[^0-9.-]/g, ''))
                : null,
          distance_from_start: 0,
          type: 'waypoint',
          mission_waypoint_id: waypoint.id ?? 0,
          name: waypoint.name ?? `Waypoint ${waypoint.order ?? index + 1}`,
        };
      });
    },
    [allWaypoints],
  );

  // Recalculate route_paths when allWaypoints becomes available and assignments exist
  useEffect(() => {
    if (allWaypoints.length === 0) {
      return;
    }

    setDroneAssignments((previousAssignments) =>
      previousAssignments.map((assignment) => {
        if (
          assignment.start_waypoint_id &&
          assignment.end_waypoint_id &&
          (!assignment.route_path || assignment.route_path.length === 0)
        ) {
          const newRoutePath = generateRoutePath(
            assignment.start_waypoint_id,
            assignment.end_waypoint_id,
          );

          return {
            ...assignment,
            route_path: newRoutePath,
            routeDistance:
              calculateLineDistanceAndTime(newRoutePath).totalDistance,
          };
        }

        return assignment;
      }),
    );
  }, [allWaypoints, generateRoutePath]);

  // Update drone assignment by index
  const updateDroneAssignmentByIndex = useCallback(
    (index: number, field: keyof FormDroneAssignment, value: unknown): void => {
      setDroneAssignments((previousAssignments) => {
        if (index < 0 || index >= previousAssignments.length) {
          return previousAssignments;
        }

        const updatedAssignments = [...previousAssignments];
        const currentAssignment = updatedAssignments[index];

        if (field === 'device_id') {
          const deviceId = toNullableNumber(value);

          const deviceAssignment = defaultDevices.find(
            (assignment) => assignment.id === deviceId,
          );
          updatedAssignments[index] = {
            ...currentAssignment,
            device_id: deviceId,
            device: {
              color: deviceAssignment?.color ?? null,
              id: deviceAssignment?.id ?? null,
              name: deviceAssignment?.name ?? null,
              max_distance_km: deviceAssignment?.max_distance_km ?? 0,
              terminal_latitude: deviceAssignment?.terminal_latitude ?? null,
              terminal_longitude: deviceAssignment?.terminal_longitude ?? null,
            },
            waiting_coordinates: null,
          };

          setFlagErrorRequiredFields((previousErrors) => {
            const newErrors = { ...previousErrors };
            if (newErrors[index]) {
              delete newErrors[index].device_id;
              if (Object.keys(newErrors[index]).length === 0) {
                delete newErrors[index];
              }
            }
            return newErrors;
          });

          // Clear warning for old device (if exists) and new device
          const oldDeviceId = currentAssignment.device_id;
          if (oldDeviceId !== null && oldDeviceId !== undefined) {
            setFlagWarningDrone((previousErrors) => {
              const newErrors = { ...previousErrors };
              delete newErrors[oldDeviceId];
              return newErrors;
            });
          }
          if (deviceId !== null && deviceId !== undefined) {
            setFlagWarningDrone((previousErrors) => {
              const newErrors = { ...previousErrors };
              delete newErrors[deviceId];
              return newErrors;
            });
          }

          if (deviceId !== null) {
            setFlagErrorDrone((previousErrors) => {
              const newErrors = { ...previousErrors };
              delete newErrors[deviceId];
              return newErrors;
            });
          }
        } else if (
          field === 'start_waypoint_id' ||
          field === 'end_waypoint_id'
        ) {
          const waypointValue = toNullableNumber(value);

          updatedAssignments[index] = {
            ...currentAssignment,
            [field]: waypointValue,
          } as FormDroneAssignment;

          const nextStartId =
            field === 'start_waypoint_id'
              ? waypointValue
              : currentAssignment.start_waypoint_id;
          const nextEndId =
            field === 'end_waypoint_id'
              ? waypointValue
              : currentAssignment.end_waypoint_id;

          if (nextStartId && nextEndId) {
            const newRoutePath = generateRoutePath(nextStartId, nextEndId);
            updatedAssignments[index] = {
              ...updatedAssignments[index],
              route_path: newRoutePath,
              routeDistance:
                calculateLineDistanceAndTime(newRoutePath).totalDistance,
            };
          }

          const fieldKey =
            field === 'start_waypoint_id'
              ? 'start_waypoint_id'
              : 'end_waypoint_id';

          setFlagErrorRequiredFields((previousErrors) => {
            const newErrors = { ...previousErrors };
            if (newErrors[index]) {
              delete newErrors[index][fieldKey];
              if (Object.keys(newErrors[index]).length === 0) {
                delete newErrors[index];
              }
            }
            return newErrors;
          });

          const deviceId = updatedAssignments[index].device_id;
          if (deviceId !== null && deviceId !== undefined) {
            setFlagErrorWaypoint((previousErrors) => {
              const newErrors = { ...previousErrors };
              delete newErrors[deviceId];
              return newErrors;
            });
          }
        } else {
          updatedAssignments[index] = {
            ...currentAssignment,
            [field]: value,
          } as FormDroneAssignment;
        }

        return updatedAssignments;
      });
    },
    [defaultAssignments, generateRoutePath, toNullableNumber],
  );

  // Handle opening the coordinate picker modal
  const handleOpenCoordinateModal = useCallback((rowIndex: number): void => {
    setSelectedRowIndex(rowIndex);
    setIsCoordinateModalOpen(true);
  }, []);

  // Handle saving coordinates from the modal
  const handleSaveCoordinates = useCallback(
    (coordinates: [number, number]): void => {
      if (selectedRowIndex !== null) {
        updateDroneAssignmentByIndex(
          selectedRowIndex,
          'waiting_coordinates',
          coordinates,
        );
      }
    },
    [selectedRowIndex, updateDroneAssignmentByIndex],
  );

  const historyBehaviorColumns = useMemo<CustomizableColumn[]>(() => {
    const columns: CustomizableColumn[] = [];

    columns.push({
      Header: 'Drone',
      accessor: 'device.name',
      enableSorting: false,
      enableColumnFilter: false,
      cell: (row: TableRowContext) => {
        const contextRow = row.row ?? {};
        const rowIndex = contextRow.index ?? row.index ?? 0;
        const deviceId = contextRow.original?.device_id ?? undefined;

        const hasRequiredError =
          flagErrorRequiredFields[rowIndex]?.device_id || false;
        const hasDuplicateError =
          deviceId !== undefined ? flagErrorDrone[deviceId] || false : false;

        const hasWarningError = flagWarningDrone[deviceId ?? 0] || false;

        return (
          <DroneCell
            row={row}
            flagWarningDrone={hasWarningError}
            missionOptions={missionOptions}
            updateDroneAssignmentByIndex={updateDroneAssignmentByIndex}
            flagErrorDrone={hasRequiredError || hasDuplicateError}
          />
        );
      },
    });

    columns.push({
      Header: 'Start Time',
      accessor: 'scheduled_start_time',
      enableSorting: false,
      enableColumnFilter: false,
      customStyle: {
        width: '130px',
      },
      cell: (row: TableRowContext) => {
        console.log('row_dataaa3443', row);

        const contextRow = row.row ?? {};
        const rowIndex = contextRow.index ?? row.index ?? 0;
        const formStartTime = watch('start_time') ?? null;
        const hasRequiredError = contextRow?.original?.scheduled_start_time
          ? false
          : flagErrorRequiredFields[rowIndex]?.scheduled_start_time || false;

        return (
          <StartTimeCell
            row={row}
            updateDroneAssignmentByIndex={updateDroneAssignmentByIndex}
            realStartTime={contextRow?.original?.scheduled_start_time}
            startTime={formStartTime}
            flagErrorWaypoint={hasRequiredError || false}
          />
        );
      },
    });

    columns.push({
      Header: 'Start Point',
      accessor: 'start_waypoint_id',
      enableSorting: false,
      enableColumnFilter: false,
      customStyle: {
        width: '150px',
      },
      cell: (row: TableRowContext) => {
        const contextRow = row.row ?? {};
        const rowIndex = contextRow.index ?? row.index ?? 0;
        const deviceId = contextRow.original?.device_id ?? undefined;
        const hasRequiredError =
          flagErrorRequiredFields[rowIndex]?.start_waypoint_id || false;
        const hasWaypointError =
          deviceId !== undefined ? flagErrorWaypoint[deviceId] || false : false;
        return (
          <WaypointCell
            row={row}
            waypointOptions={waypointOptions}
            updateDroneAssignmentByIndex={updateDroneAssignmentByIndex}
            flagErrorWaypoint={hasRequiredError || hasWaypointError}
            isDisabled={isFromRoute}
            type="start"
          />
        );
      },
    });

    columns.push({
      Header: 'End Point',
      accessor: 'end_waypoint_id',
      enableSorting: false,
      enableColumnFilter: false,
      customStyle: {
        width: '200px',
      },
      cell: (row: TableRowContext) => {
        const contextRow = row.row ?? {};
        const rowIndex = contextRow.index ?? row.index ?? 0;
        const deviceId = contextRow.original?.device_id ?? undefined;
        const hasRequiredError =
          flagErrorRequiredFields[rowIndex]?.end_waypoint_id || false;
        const hasWaypointError =
          deviceId !== undefined ? flagErrorWaypoint[deviceId] || false : false;
        return (
          <WaypointCell
            row={row}
            waypointOptions={waypointOptions}
            updateDroneAssignmentByIndex={updateDroneAssignmentByIndex}
            flagErrorWaypoint={hasRequiredError || hasWaypointError}
            isDisabled={isFromRoute}
            type="end"
          />
        );
      },
    });

    columns.push({
      Header: 'Waiting Coordinates',
      accessor: 'waiting_coordinates',
      enableSorting: false,
      enableColumnFilter: false,
      customStyle: { width: '200px' },
      cell: (row: TableRowContext) => (
        <WaitingCoordinatesCell
          row={row}
          onOpenModal={handleOpenCoordinateModal}
          isDisabled={isFromRoute}
        />
      ),
    });

    if (defaultAssignments[0]?.log_collection) {
      columns.push({
        Header: 'Log',
        accessor: 'log_collection',
        enableSorting: false,
        enableColumnFilter: false,
        customStyle: { width: '80px' },
        cell: (row: TableRowContext) => (
          <SwitchCell
            row={row}
            field="log_collection"
            updateDroneAssignmentByIndex={updateDroneAssignmentByIndex}
          />
        ),
      });
    }

    if (defaultAssignments[0]?.video_recording) {
      columns.push({
        Header: 'Record',
        accessor: 'video_recording',
        enableSorting: false,
        enableColumnFilter: false,
        customStyle: {
          width: '80px',
        },
        cell: (row: TableRowContext) => (
          <SwitchCell
            row={row}
            field="video_recording"
            updateDroneAssignmentByIndex={updateDroneAssignmentByIndex}
          />
        ),
      });
    }

    if (defaultAssignments[0]?.video_analysis) {
      columns.push({
        Header: 'Analysis',
        accessor: 'video_analysis',
        enableSorting: false,
        enableColumnFilter: false,
        customStyle: {
          width: '80px',
        },
        cell: (row: TableRowContext) => (
          <SwitchCell
            row={row}
            field="video_analysis"
            updateDroneAssignmentByIndex={updateDroneAssignmentByIndex}
          />
        ),
      });
    }

    if (!isFromRoute) {
      columns.push({
        Header: t(' '),
        accessor: 'action',
        cell: (row: TableRowContext) => {
          const contextRow = row.row ?? {};
          const rowIndex = contextRow.index ?? row.index ?? 0;

          const assignment =
            rowIndex !== undefined ? droneAssignments[rowIndex] : null;
          if (rowIndex === 0) {
            return null;
          }
          if (!assignment) {
            return null;
          }
          return (
            <div
              className="special-label"
              onClick={(event) => {
                event.stopPropagation();
                setDroneAssignments((previous) => {
                  const filtered = previous.filter(
                    (item, index) => index !== rowIndex,
                  );
                  return filtered.map((item, itemIndex) => ({
                    ...item,
                    order: itemIndex + 1,
                  }));
                });
              }}
              style={{ cursor: 'pointer' }}
            >
              <BsTrash size={16} />
            </div>
          );
        },
        customStyle: { width: '20px', textAlign: 'center' as const },
        enableSorting: false,
        enableColumnFilter: false,
        notUseConfigTable: true,
      });
    }

    return columns;
  }, [
    defaultAssignments,
    droneAssignments,
    flagErrorDrone,
    flagErrorRequiredFields,
    flagErrorWaypoint,
    isFromRoute,
    missionOptions,
    startTime,
    t,
    updateDroneAssignmentByIndex,
    waypointOptions,
    handleOpenCoordinateModal,
  ]);

  // Drone route for map display
  const droneRoutes = useMemo(() => {
    if (!droneAssignments || droneAssignments.length === 0) {
      return [];
    }
    return droneAssignments
      .filter(
        (assignment) =>
          assignment.device_id &&
          assignment.route_path &&
          assignment.route_path.length > 0,
      )
      .map((assignment) => ({
        route_path:
          assignment.route_path?.map((item) => ({
            lat: item.latitude,
            lng: item.longitude,
            name: item.name,
            altitude: item.altitude ?? 0,
            command: item?.command_name ?? 'WAYPOINT',
            frame: item?.frame_name ?? 'FRAME',
            param_1: item?.params?.[0] ?? 0,
            param_2: item?.params?.[1] ?? 0,
            param_3: item?.params?.[2] ?? 0,
            param_4: item?.params?.[3] ?? 0,
          })) || [],
        device: assignment.device || null,
      }));
  }, [droneAssignments]);

  const handleAddDroneAssignment = useCallback((): void => {
    if (droneAssignments.length >= MAX_DRONE_ASSIGNMENTS) {
      return;
    }
    const templateAssignment = defaultAssignments[0];
    setDroneAssignments((previous) => {
      const newOrder = previous.length + 1;

      return [
        ...previous,
        {
          device_id: null,
          scheduled_start_time: null,
          start_waypoint_id: null,
          end_waypoint_id: null,
          log_collection: templateAssignment?.log_collection ?? false,
          video_recording: templateAssignment?.video_recording ?? false,
          video_analysis: templateAssignment?.video_analysis ?? false,
          order: newOrder,
          estimated_distance_km: 0,
          estimated_time_minutes: 0,
          metadata: {},
          note: '',
          route_path: [],
          waiting_coordinates: null,
        },
      ];
    });
  }, [defaultAssignments, droneAssignments.length, MAX_DRONE_ASSIGNMENTS]);

  const getDataMission = useCallback(async (): Promise<void> => {
    if (!missionId) {
      return;
    }

    const { data } = await getDetailSurveyMission({
      id: missionId,
    });

    if (!data) {
      return;
    }
    setIsFromRoute(
      (data?.from_route || data?.drone_segments?.length > 0) ?? false,
    );

    setValue(
      'takeoff_altitude',
      convertUnitValue(data?.takeoff_altitude ?? '100 m')?.value,
    );
    setValue(
      'altitude_separation',
      convertUnitValue(data?.altitude_separation ?? '10 m')?.value,
    );

    setSurveyMission(data);
    setAllWaypoints(data?.all_waypoints);

    const points = data.line_mission
      ? data.all_waypoints.map((waypoint: Waypoint) => ({
          lat: Number(waypoint.latitude),
          lng: Number(waypoint.longitude),
        }))
      : data.polygon?.map((point: [number, number]) => ({
          lat: point[0],
          lng: point[1],
        })) || [];

    const newShape = {
      id: uuidv4(),
      type: (data?.line_mission
        ? 'LINE'
        : data?.polygon?.length === 16
          ? 'CIRCULAR'
          : data?.polygon?.length === 4
            ? 'POLYGON'
            : 'TRACE') as 'LINE' | 'CIRCULAR' | 'POLYGON' | 'TRACE',
      points,
      pointsLength: data?.line_mission ? points.length : null,
      return: data?.return_to_home || false,
    };

    setCurrentShape(newShape);

    const processedChartData = data.chart_data
      .sort((a: ChartDataPoint, b: ChartDataPoint) => a.order - b.order)
      .map(
        (
          item: ChartDataPoint,
          index: number,
          array: ChartDataPoint[],
        ): ChartDataItem => {
          const cumulativeDistance = array
            .slice(0, index + 1)
            .reduce((sum, waypoint) => sum + (waypoint.distance || 0), 0);

          return {
            waypointName: item.name,
            cruise_speed: item.cruise_speed || 0,
            operating_altitude: item.operating_altitude || 0,
            cumulativeDistance: Math.round(cumulativeDistance * 100) / 100,
            order: item.order,
          };
        },
      );

    setChartData(processedChartData);
  }, [getDetailSurveyMission, missionId, setCurrentShape]);

  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!missionId || defaultAssignments.length === 0) {
      return undefined;
    }

    timeoutRef.current = setTimeout(() => {
      void (async () => {
        await getDataMission();
      })();
    }, 1500);

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [missionId, defaultAssignments]);

  // Reset populated profile ID when idFromSearchParams changes
  useEffect(() => {
    if (idFromSearchParams) {
      const profileId = Number(idFromSearchParams);
      // Reset if it's a different profile
      if (populatedProfileId.current !== profileId) {
        populatedProfileId.current = null;
      }
    } else {
      populatedProfileId.current = null;
    }
  }, [idFromSearchParams]);

  // Fetch detail profile when idFromSearchParams exists
  useEffect(() => {
    if (idFromSearchParams) {
      const profileId = Number(idFromSearchParams);
      if (populatedProfileId.current !== profileId) {
        void fetchDetailSurveillanceProfile(profileId);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idFromSearchParams]);

  console.log('detail_dataaa3443', detailSurveillanceProfile);

  useEffect(() => {
    if (!detailSurveillanceProfile || !idFromSearchParams) {
      return;
    }
    const profileId = Number(idFromSearchParams);
    const detail = detailSurveillanceProfile;
    if (populatedProfileId.current === profileId) {
      return;
    }

    populatedProfileId.current = profileId;

    methods.reset({
      name: detail.name ?? '',
      mission_id: detail.mission_id
        ? {
            value: detail.mission_id,
            label: detail.mission ?? null,
          }
        : null,
      start_time: detail.start_time
        ? converRawDateToDateTimeFormat(detail.start_time)
        : null,
      operator: {
        value: detail.operator__id || null,
        label: detail.operator || null,
      },
      repeat_type_id: detail.repeat_type__code
        ? {
            value: detail.repeat_type_id || null,
            label: detail.repeat_type__name || null,
            code: detail.repeat_type__code,
          }
        : { value: 1, label: t('None'), code: 'none' },
      repeat_until_type_id: {
        value:
          detail.repeat_type__code == 'none'
            ? null
            : detail.repeat_until_type_id || null,
        label:
          detail.repeat_type__code == 'none'
            ? null
            : detail.repeat_until_type__name || null,
        code:
          detail.repeat_type__code == 'none'
            ? null
            : detail.repeat_until_type__code || null,
      },
      repeat_occurrences: detail.repeat_occurrences || null,
      repeat_until_date: detail.repeat_until_date ?? null,
      color_code: detail.color_code || '#1D9BE2',
      note: detail.note || '',
    });

    if (detail.drone_assignments && Array.isArray(detail.drone_assignments)) {
      const assignments: FormDroneAssignment[] = detail.drone_assignments.map(
        (assignment: {
          device__id?: number;
          start_waypoint_id?: number;
          end_waypoint_id?: number;
          start_time?: string;
          log_collection?: boolean;
          video_recording?: boolean;
          video_analysis?: boolean;
          route_path?: Array<{
            latitude: number;
            longitude: number;
            name?: string;
          }>;
          start_time?: string;
          device?: {
            id?: number;
            name?: string;
            color?: string;
          };
          waiting_coordinates?: [number, number] | null;
        }) => ({
          device_id: assignment.device__id ?? null,
          scheduled_start_time: assignment.start_time ?? null,
          start_waypoint_id: assignment.start_waypoint_id ?? null,
          end_waypoint_id: assignment.end_waypoint_id ?? null,
          log_collection: assignment.log_collection ?? false,
          video_recording: assignment.video_recording ?? false,
          video_analysis: assignment.video_analysis ?? false,
          order: 0,
          metadata: {},
          note: '',
          device: assignment.device ?? null,
          route_path:
            assignment.route_path?.map((point, index) => ({
              order: index + 1,
              latitude: point.latitude,
              longitude: point.longitude,
              altitude: null,
              distance_from_start: 0,
              type: 'waypoint',
              mission_waypoint_id: 0,
              name: point.name ?? `Waypoint ${index + 1}`,
            })) ?? [],
          waiting_coordinates: assignment.waiting_coordinates ?? null,
        }),
      );

      assignments.forEach((assignment, index) => {
        assignment.order = index + 1;
      });

      setDroneAssignments(assignments);
    }
  }, [
    detailSurveillanceProfile,
    idFromSearchParams,
    t,
    userInfo,
    dateFormat,
    methods,
    converRawDateToDateTimeFormat,
  ]);

  const onCancel = (): void => {
    navigate(
      CustomRoutes.surveyProfile.path + '?tab=' + activeTabFromSearchParams,
    );
  };

  const { showModal, setShowModal, handleModalSave, handleModalCancel } =
    useFormNavigationBlocker({
      isDirty: clickSave == false && isDirty,
      onSave: async () => {
        const formData = watch();
        await handleFormSubmit(formData);
        reset(formData, {
          keepDirty: false,
          keepValues: true,
        });
      },
      onCancel,
      handleSubmit,
    });

  const invalidStartTime = startTime
    ? dayjs(startTime).isBefore(dayjs())
    : false;

  const handleCheckErrorWaypoint = useCallback((): void => {
    setClickCheckErrorWaypoint(true);
    const droneErrors: Record<number, boolean> = {};
    const flagWarningDrone: Record<number, boolean> = {};
    const waypointErrors: Record<number, boolean> = {};
    const requiredFieldsErrors: Record<
      number,
      {
        device_id?: boolean;
        start_waypoint_id?: boolean;
        end_waypoint_id?: boolean;
      }
    > = {};
    let hasError = false;
    let errorMessage = '';

    const seen = new Set<number>();
    const duplicates = new Set<number>();

    droneAssignments.forEach((assignment, index) => {
      const hasAnyData =
        assignment.device_id !== null ||
        assignment.scheduled_start_time !== null ||
        assignment.start_waypoint_id !== null ||
        assignment.end_waypoint_id !== null;

      if (!hasAnyData) {
        return;
      }

      const rowErrors: {
        device_id?: boolean;
        start_waypoint_id?: boolean;
        end_waypoint_id?: boolean;
        scheduled_start_time?: boolean;
      } = {};

      if (
        assignment.device?.max_distance_km &&
        assignment.routeDistance > assignment.device?.max_distance_km
      ) {
        flagWarningDrone[assignment.device?.id ?? 0] = true;
        hasError = true;
        if (!errorMessage) {
          errorMessage = t(
            'The distance exceeds the flight range. Please select another drone.',
          );
        }
      }

      if (assignment.device_id === null) {
        rowErrors.device_id = true;
        hasError = true;
        if (!errorMessage) {
          errorMessage = t('Please fill in the missing information.');
        }
      }

      if (assignment.scheduled_start_time === null) {
        rowErrors.scheduled_start_time = true;
        hasError = true;
        if (!errorMessage) {
          errorMessage = t('Please fill in the scheduled start time.');
        }
      }

      if (assignment.start_waypoint_id === null) {
        rowErrors.start_waypoint_id = true;
        hasError = true;
        if (!errorMessage) {
          errorMessage = t('Please fill in the missing information.');
        }
      }

      if (assignment.end_waypoint_id === null) {
        rowErrors.end_waypoint_id = true;
        hasError = true;
        if (!errorMessage) {
          errorMessage = t('Please fill in the missing information.');
        }
      }

      const deviceId = assignment.device_id;
      const startWaypointId = assignment.start_waypoint_id;
      const endWaypointId = assignment.end_waypoint_id;
      const scheduledStartTime = assignment.scheduled_start_time;

      if (
        deviceId !== null &&
        startWaypointId !== null &&
        endWaypointId !== null &&
        scheduledStartTime !== null
      ) {
        if (seen.has(deviceId)) {
          duplicates.add(deviceId);
        } else {
          seen.add(deviceId);
        }

        if (startWaypointId === endWaypointId) {
          waypointErrors[deviceId] = true;
          hasError = true;
          if (!errorMessage) {
            errorMessage = t('Start and end waypoint cannot be the same.');
          }
        } else if (allWaypoints.length > 0) {
          const startWaypoint = allWaypoints.find(
            (waypoint) => waypoint.id === startWaypointId,
          );
          const endWaypoint = allWaypoints.find(
            (waypoint) => waypoint.id === endWaypointId,
          );

          if (
            startWaypoint?.order !== undefined &&
            endWaypoint?.order !== undefined
          ) {
            if (endWaypoint.order <= startWaypoint.order) {
              waypointErrors[deviceId] = true;
              hasError = true;
              if (!errorMessage) {
                errorMessage = t(
                  'End waypoint order must be greater than start waypoint order.',
                );
              }
            }

            if (index > 0) {
              const previousAssignment = droneAssignments[index - 1];
              if (
                previousAssignment.end_waypoint_id !== null &&
                previousAssignment.device_id !== null
              ) {
                const previousEndWaypoint = allWaypoints.find(
                  (waypoint) =>
                    waypoint.id === previousAssignment.end_waypoint_id,
                );

                if (
                  previousEndWaypoint?.order !== undefined &&
                  startWaypoint.order <= previousEndWaypoint.order
                ) {
                  waypointErrors[deviceId] = true;
                  hasError = true;
                  if (!errorMessage) {
                    errorMessage = t(
                      'Start waypoint of current drone must be after end waypoint of previous drone.',
                    );
                  }
                }
              }
            }
          }
        }
      }
      if (Object.keys(rowErrors).length > 0) {
        requiredFieldsErrors[index] = rowErrors;
      }
    });

    if (duplicates.size > 0) {
      hasError = true;
      duplicates.forEach((id) => {
        droneErrors[id] = true;
      });
      if (!errorMessage) {
        errorMessage = t('A drone cannot be selected more than once.');
      }
    }

    if (hasError) {
      setFlagErrorDrone(droneErrors);
      setFlagErrorWaypoint(waypointErrors);
      setFlagErrorRequiredFields(requiredFieldsErrors);
      setFlagWarningDrone(flagWarningDrone);
      ToastTopHelper.error(errorMessage);
      return;
    }

    if (invalidStartTime) {
      setError('start_time', {
        message: t('Start time must be in the future.'),
      });
      return;
    }

    setFlagErrorDrone({});
    setFlagErrorWaypoint({});
    setFlagErrorRequiredFields({});
    setFlagWarningDrone({});
    setClickCheckErrorWaypoint(false);
    handleSubmit(handleFormSubmit)();
  }, [
    allWaypoints,
    droneAssignments,
    handleFormSubmit,
    handleSubmit,
    t,
    invalidStartTime,
  ]);

  return (
    <Container
      id="list-device"
      isOpenCanvas={openOffcanvas}
    >
      <FormProvider {...methods}>
        <form
          onSubmit={handleSubmit(handleFormSubmit)}
          className="form-route"
        >
          <CustomBreadcrumb
            items={[
              {
                url:
                  CustomRoutes.surveyProfile.path +
                  '?tab=' +
                  activeTabFromSearchParams,
              },
              { text: t('Add New Profile') },
            ]}
            buttons={[
              <CustomBtn
                label={t('Cancel')}
                variant="outline"
                color="secondary"
                size="md"
                style={{ width: '6rem' }}
                type="button"
                onClick={onCancel}
              />,
              <CustomBtn
                size="md"
                style={{ width: '6rem' }}
                label={t('Submit')}
                type="button"
                disabled={droneAssignments.length === 0 || isSubmitting}
                onClick={handleCheckErrorWaypoint}
                loading={isSubmitting}
              />,
            ]}
          />
          <Main>
            <div className="form-container">
              {detailSurveillanceProfile?.cancel_reason && (
                <FormBlock
                  style={{
                    backgroundColor: theme === 'dark' ? '#513D2B' : '#FBEBDD',
                    color: theme === 'dark' ? '#ECECEF' : Colors.Gray7,
                    padding: '8px 12px',
                  }}
                >
                  <b>{t('Reason')}:</b>{' '}
                  {detailSurveillanceProfile?.cancel_reason}
                </FormBlock>
              )}
              <FormDataProfile />
              {defaultAssignments.length > 0 && (
                <>
                  {/* <div style={{ height: '37rem', backgroundColor: 'white' }}> */}
                  <ProfileMap
                    markerData={markerData}
                    isLineMode={isLineMode}
                    droneRoutes={droneRoutes}
                    height="40rem"
                  />
                  {/* </div> */}
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '1.46fr 1fr',
                      gap: '1.25rem',
                    }}
                  >
                    <FormBlock>
                      <div className="detail-route__section-title">
                        {t('Drones List')}
                      </div>
                      <div className="list-device__table-container">
                        <CustomizableTable
                          subTable
                          notUseGroupColumn
                          notShowSelectRow
                          useSystemSetting
                          columns={historyBehaviorColumns}
                          data={{
                            data: droneAssignments || [],
                            totalItem: droneAssignments?.length || 0,
                            totalPage: 1,
                          }}
                          hasPagination={false}
                          refreshTable={refreshTable}
                          setRefreshTable={setRefreshTable}
                          currentPage={currentPage}
                          setCurrentPage={setCurrentPage}
                          pageSize={pageSize}
                          setPageSize={setPageSize}
                          offcanvas={openOffcanvas}
                          setOpenOffcanvas={(boolean: boolean) => {
                            setOpenOffcanvas(boolean);
                          }}
                          stickyHeader
                        />
                      </div>
                      {droneAssignments?.length < MAX_DRONE_ASSIGNMENTS &&
                        !isFromRoute && (
                          <CustomBtn
                            label={t('Add Drone')}
                            variant="outline"
                            color="primary"
                            type="button"
                            style={{ marginTop: '1rem', border: 'none' }}
                            icon={<GoPlus size={18} />}
                            onClick={() => {
                              handleAddDroneAssignment();
                            }}
                          />
                        )}
                    </FormBlock>
                    <Box
                      sx={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '1.25rem',
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '1rem',
                          height: '68rem',
                        }}
                      >
                        <FormBlock>
                          <GeneralInformation
                            surveyMission={surveyMission as SurveyMissionState}
                            chartData={chartData}
                            label={t('Information')}
                          />
                        </FormBlock>
                        <FormBlock>
                          <FlightChart
                            chartData={chartData}
                            label={t('Flight speed and altitude chart')}
                          />
                        </FormBlock>
                      </div>
                    </Box>
                  </div>
                </>
              )}
            </div>
          </Main>
        </form>
        {/* HANDLE MODAL SAVE AND CANCEL */}
        <CustomModal
          title={t('Save changes')}
          show={showModal}
          onHide={() => setShowModal(false)}
        >
          <div style={{ width: '25rem' }}>
            {t(
              'Your unsaved changes will be lost. Do you want to save changes before leaving?',
            )}
          </div>
          <ActionBtn
            leftButtons={[
              <CustomBtn
                key="modal-save-btn"
                type="submit"
                color="primary"
                size="lg"
                actionType={ROLE_PERMISSION.UPDATE}
                onClick={handleModalSave}
                label={t('Save')}
                disabled={isSubmitting}
                loading={isSubmitting}
              />,
            ]}
            rightButtons={[
              <CustomBtn
                key="modal-cancel-btn"
                type="button"
                variant="outline"
                color="secondary"
                size="lg"
                onClick={handleModalCancel}
                label={t('Cancel')}
              />,
            ]}
          />
        </CustomModal>

        {/* COORDINATE PICKER MODAL */}
        <CoordinatePickerModal
          isOpen={isCoordinateModalOpen}
          onClose={() => setIsCoordinateModalOpen(false)}
          onSave={handleSaveCoordinates}
          selectedDrone={
            selectedRowIndex !== null
              ? droneAssignments[selectedRowIndex]
              : null
          }
          initialCoordinates={
            selectedRowIndex !== null
              ? droneAssignments[selectedRowIndex]?.waiting_coordinates
              : null
          }
          markerData={markerData}
          isLineMode={isLineMode}
          droneRoutes={droneRoutes}
        />
      </FormProvider>
    </Container>
  );
};

export default AddNewProfile;
