import { yupResolver } from '@hookform/resolvers/yup';
import { useCallback, useEffect, useRef, useState } from 'react';
import { FormProvider, Resolver, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import {
  CustomBreadcrumb,
  CustomBtn,
  FormBlock,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useTheme,
} from 'rj-core';
import { v4 as uuidv4 } from 'uuid';

import { CheckRoleAccount } from '@/utils/CheckRoleAccount';

import Colors from '../../../configs/Colors';
import { useFormDirtyContext } from '../../../contexts/FormDirtyContext';
import { useFormDirty } from '../../../hooks/useFormDirty';
import { CustomRoutes } from '../../../services/API';
import { surveyMissionSchema } from '../../../services/schemaForm';
import { FormSurveyMission } from '../components/FormSurveyMission';
import { DrawingShape } from '../components/drawing/types';
import { Marker } from '../components/drawingGoogle';
import { useSurveyMission } from '../hooks/useSurveyMission';
import { useDrawingModeStore } from '../stores/drawingModeStore';
import {
  SurveyMissionFormValues,
  SurveyMissionState,
  Waypoint,
} from '../types/surveyMission.types';
import { convertUnitValue } from '../utils/convertLineToWaypoints';
import {
  ConvertCommandInput,
  ConvertFrameInput,
} from '../utils/convertMissionData';

export const ConvertFrameOutput = (
  frame: Record<string, string | number | null | undefined> | undefined,
  defaultFrame: {
    label: string;
    value: string;
  } | null,
) => {
  if (!frame || (Object.keys(frame) && Object.keys(frame).length === 0)) {
    return defaultFrame;
  }

  try {
    const frameId = Object.keys(frame)[0];
    const frameObj = frame[frameId];

    return frameId && frameObj
      ? {
          label: frameObj,
          value: Number(frameId),
        }
      : defaultFrame;
  } catch (error) {
    return defaultFrame;
  }
};

export const ConvertCommandOutput = (
  command: Record<string, string | number | null | undefined> | undefined,
  defaultCMD: {
    label: string;
    value: string;
  } | null,
) => {
  if (!command) {
    return {
      cruise_speed: 7,
      command_terminal: defaultCMD,
      frame_1: 0,
      frame_2: 0,
      frame_3: 0,
      frame_4: 0,
      altitude: 0,
    };
  }

  try {
    const commandId = Object.keys(command)[0];
    const commandObj = command[commandId];

    if (!commandObj || typeof commandObj !== 'object') {
      throw new Error('Invalid command object structure');
    }

    const commandName = Object.keys(commandObj)[0];

    const values = (commandObj as Record<string, unknown>)[
      commandName
    ] as unknown[];

    return {
      command_terminal:
        commandName && commandId
          ? {
              label: commandName,
              value: Number(commandId),
            }
          : defaultCMD,
      param_1: (values?.[0] as number) ?? 0,
      param_2: (values?.[1] as number) ?? 0,
      param_3: (values?.[2] as number) ?? 0,
      param_4: (values?.[3] as number) ?? 0,
      altitude: (values?.[6] as number) ?? 0,
      cruise_speed: 7,
    };
  } catch (error) {
    return {
      cruise_speed: 7,
      command_terminal: defaultCMD,
      frame_1: 0,
      frame_2: 0,
      frame_3: 0,
      frame_4: 0,
      altitude: 0,
    };
  }
};

export const EditSurveyMissionPage = () => {
  const { t } = useTranslation();
  const { id } = useParams();
  const navigate = useNavigate();
  const [theme] = useTheme();
  const [markerData, setMarkerData] = useState<Marker[]>([]);
  const headerPageRef = useRef<HTMLElement>(
    null,
  ) as React.RefObject<HTMLElement>;
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const drawingMode = useDrawingModeStore((state) => state.drawingMode);
  const currentShape = useDrawingModeStore((state) => state.currentShape);
  const currentMode =
    drawingMode === 'NONE' ? (currentShape?.type ?? 'POLYGON') : drawingMode;

  const isNotReviewing = useDrawingModeStore((state) => state.isNotReviewing);

  const setIsNotReviewing = useDrawingModeStore(
    (state) => state.setIsNotReviewing,
  );
  const setCurrentShape = useDrawingModeStore((state) => state.setCurrentShape);
  const setIsEditable = useDrawingModeStore((state) => state.setIsEditable);

  const [surveyMission, setSurveyMission] = useState<SurveyMissionState | null>(
    null,
  );
  const [clickSave, setClickSave] = useState(false);

  const { getDetailSurveyMission, updateSurveyMission } = useSurveyMission();

  const setWaypointsList = useDrawingModeStore(
    (state) => state.setWaypointsList,
  );
  const setQgcMissionData = useDrawingModeStore(
    (state) => state.setQgcMissionData,
  );

  const { setDirty } = useFormDirtyContext();

  const methods = useForm<SurveyMissionFormValues>({
    defaultValues: {
      group: null,
      name: null,
      region: null,
      return: true,
      maximum_number_of_drones: null,
      purpose: null,
      log_collection: false,
      video_recording: false,
      video_analysis: false,
      total_distance: null,
      estimated_time: null,
      note: null,
      waypoints: [],
      from_route: false,
      settings: {
        hover_and_capture: false,
        altitude: 50,
        takeoff_altitude: 100,
        altitude_separation: 10,
        overlap: 70,
        trigger_distance: 30,
        spacing: 150,
        angle: 140,
        turnaround_distance: 100,
      },
    },
    resolver: yupResolver(
      surveyMissionSchema(isRoleSuperuser, currentMode),
    ) as unknown as Resolver<SurveyMissionFormValues>,
  });

  const {
    handleSubmit,
    formState: { isValid, isSubmitting, isDirty },
    trigger,
  } = methods;

  const clearAll = useDrawingModeStore((state) => state.clearAll);

  // Only clear store when component unmounts, not when mounting
  useEffect(() => {
    return () => {
      clearAll(); // Clear when component unmounts
    };
  }, [clearAll]);

  const handleCancel = () => {
    navigate(
      CustomRoutes.surveyMission.subRoutes.detailSurveyMission.path.replace(
        ':id',
        id || '',
      ),
    );
  };

  const getDetailData = useCallback(async () => {
    const { data } = await getDetailSurveyMission({ id: Number(id) });
    if (data) {
      setSurveyMission(data);
      const waypoints = data.all_waypoints.map((waypoint: Waypoint) => {
        const command_line = ConvertCommandOutput(waypoint.command_line, null);
        const frame = ConvertFrameOutput(waypoint.frame, null);
        return {
          cruise_speed: waypoint?.cruise_speed?.split(' ')?.[0] ?? 7,
          command: command_line.command_terminal,
          frame: frame,
          param_1: command_line.param_1,
          param_2: command_line.param_2,
          param_3: command_line.param_3,
          param_4: command_line.param_4,
          latitude: waypoint.latitude,
          longitude: waypoint.longitude,
          altitude: command_line.altitude,
        };
      });

      const markerDataPolygon = data.qgc_mission_data?.mission?.items
        .find(
          (item: {
            type: string;
            TransectStyleComplexItem?: {
              VisualTransectPoints?: [number, number][];
            };
          }) => item.type === 'ComplexItem',
        )
        ?.TransectStyleComplexItem?.VisualTransectPoints?.map(
          (waypoint: [number, number]) => ({
            lat: waypoint[0],
            lng: waypoint[1],
          }),
        );

      setMarkerData(markerDataPolygon || []);

      setWaypointsList(waypoints);
      setIsEditable(false);
      if (data.qgc_mission_data) {
        setQgcMissionData(data.qgc_mission_data);
      }

      const points =
        data?.polygon
          ?.map((point: [number, number]) => ({
            lat: Number(point[0]),
            lng: Number(point[1]),
          }))
          .filter(
            (point: { lat: number; lng: number }) =>
              !isNaN(point.lat) &&
              !isNaN(point.lng) &&
              !(point.lat === 0 && point.lng === 0),
          ) || [];

      const newShape: DrawingShape = {
        id: uuidv4(),
        type: (data.polygon?.length === 16
          ? 'CIRCULAR'
          : data.polygon?.length === 4
            ? 'POLYGON'
            : 'TRACE') as 'CIRCULAR' | 'POLYGON' | 'TRACE',
        points,
        return: data.return_to_home || false,
      };

      if (data?.from_route || data?.drone_segments?.length > 0) {
        setIsNotReviewing(true);
      } else {
        setIsNotReviewing(false);
      }

      // Set currentShape - it will be used to render the line if points exist
      setCurrentShape(newShape);
      methods.reset({
        group: data?.group__id
          ? {
              value: data?.group__id,
              label: data?.group__name,
            }
          : null,
        name: data?.name,
        region: data?.region || null,
        return: data?.return_to_home,
        maximum_number_of_drones: data?.maximum_drones,
        purpose: data?.purpose__id
          ? {
              value: data?.purpose__id,
              label: data?.purpose__name,
            }
          : null,
        log_collection: data?.log_collection,
        video_recording: data?.video_recording,
        video_analysis: data?.video_analysis,
        total_distance: convertUnitValue(data?.total_distance)?.value,
        estimated_time: convertUnitValue(data?.estimated_time)?.value,
        note: data?.note,
        waypoints: waypoints,
        from_route: data?.from_route || false,
        settings: {
          hover_and_capture: data?.hover_and_capture || false,
          altitude: convertUnitValue(data?.altitude)?.value || 50,
          takeoff_altitude:
            convertUnitValue(data?.takeoff_altitude)?.value || 100,
          altitude_separation:
            convertUnitValue(data?.altitude_separation)?.value || 10,
          overlap: convertUnitValue(data?.frontal_overlap)?.value || 70,
          trigger_distance:
            convertUnitValue(data?.trigger_distance)?.value || 30,
          spacing: convertUnitValue(data?.spacing)?.value || 150,
          angle: convertUnitValue(data?.survey_angle)?.value || 140,
          turnaround_distance:
            convertUnitValue(data?.turnaround_distance)?.value || 100,
        },
      });
    }
  }, [
    id,
    methods,
    getDetailSurveyMission,
    setQgcMissionData,
    setIsEditable,
    setCurrentShape,
    setIsNotReviewing,
    setWaypointsList,
  ]);

  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (id) {
      timeoutRef.current = setTimeout(() => {
        getDetailData();
      }, 1000);
    }
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const onSubmit = useCallback(
    async (data: SurveyMissionFormValues) => {
      // Mark as saving to prevent dirty form popup during submission
      setClickSave(true);

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const payload: any = {
        ...(isRoleSuperuser ? { group_id: data.group?.value } : {}),
        polygon:
          currentShape?.points?.map((point) => [point.lat, point.lng]) || [],
        terminals: data.waypoints?.map((waypoint, index) => ({
          terminal_id: null,
          stop: false,
          order: index,
          latitude: String(waypoint.latitude),
          longitude: String(waypoint.longitude),
          name: `Waypoint ${index + 1}`,
          for_robot: false,
          altitude: waypoint.altitude,
          command_line: ConvertCommandInput(waypoint),
          frame: ConvertFrameInput(waypoint),
          cruise_speed: String(waypoint.cruise_speed),
        })),
        name: data.name,
        region: data.region,
        maximum_drones: data.maximum_number_of_drones,
        purpose_id: data.purpose?.value,
        log_collection: data.log_collection,
        video_recording: data.video_recording,
        video_analysis: data.video_analysis,
        note: data.note,
        hover_and_capture: data.settings?.hover_and_capture,
        altitude: data.settings?.altitude,
        takeoff_altitude: data.settings?.takeoff_altitude,
        altitude_separation: data.settings?.altitude_separation,
        survey_angle: data.settings?.angle,
        frontal_overlap: data.settings?.overlap,
        side_overlap: data.settings?.overlap,
        entry_location: 1,
        cruise_speed: 10,
        hover_speed: 5,
        spacing: data.settings?.spacing,
        trigger_distance: data.settings?.trigger_distance,
        turnaround_distance: data.settings?.turnaround_distance,
        total_distance: data.total_distance,
        estimated_time: data.estimated_time,
        from_route: data.from_route,
        is_change: isNotReviewing ? false : true,
      };
      const { message, success } = await updateSurveyMission({
        id: Number(id),
        data: payload,
      });
      if (success) {
        setDirty(false);
        ToastTopHelper.success(message);
        navigate(CustomRoutes.surveyMission.path);
      } else {
        setClickSave(false);
        ToastTopHelper.error(message);
      }
    },
    [
      currentShape,
      isRoleSuperuser,
      updateSurveyMission,
      navigate,
      id,
      setDirty,
      isNotReviewing,
    ],
  );

  // Đăng ký form với navigation blocker
  useFormDirty({
    isDirty: isDirty && !clickSave,
    triggerValidation: trigger,
    handleSubmit: methods.handleSubmit,
    onSubmit: onSubmit,
    isValid,
  });

  const isDebouncedReviewPending = useDrawingModeStore(
    (state) => state.isDebouncedReviewPending,
  );

  return (
    <>
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)}>
          <CustomBreadcrumb
            headerPageRef={headerPageRef}
            items={[
              {
                url: CustomRoutes.surveyMission.subRoutes.detailSurveyMission.path.replace(
                  ':id',
                  id || '',
                ),
              },
              { text: t('Edit Mission') },
            ]}
            buttons={[
              <CustomBtn
                label={t('Cancel')}
                variant="outline"
                color="secondary"
                size="md"
                style={{ width: '6rem' }}
                type="button"
                onClick={handleCancel}
              />,
              [
                <CustomBtn
                  size="md"
                  style={{ width: '6rem' }}
                  label={t('SurveyMission.Resubmit')}
                  type="submit"
                  actionType={ROLE_PERMISSION.UPDATE}
                  loading={isSubmitting}
                  disabled={
                    !isValid || isSubmitting || isDebouncedReviewPending
                  }
                />,
              ],
            ]}
          />
          <Main>
            {surveyMission?.status__code === 'rejected' && (
              <FormBlock
                style={{
                  backgroundColor: theme === 'dark' ? '#513D2B' : '#FBEBDD',
                  color: theme === 'dark' ? '#ECECEF' : Colors.Gray7,
                  fontWeight: 'normal',
                  padding: '8px 12px',
                  gridColumn: 'span 2',
                }}
                className="mb-3 mt-2"
              >
                {surveyMission?.rejection_reason || '-'}
              </FormBlock>
            )}
            <FormSurveyMission
              markerData={markerData}
              setMarkerData={setMarkerData}
            />
          </Main>
        </form>
      </FormProvider>
    </>
  );
};
