import { yupResolver } from '@hookform/resolvers/yup';
import { useCallback, useEffect, useRef, useState } from 'react';
import { FormProvider, useForm, Resolver } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  CustomBreadcrumb,
  CustomBtn,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
} from 'rj-core';

import { useFormDirty } from '@/hooks/useFormDirty';
import { CheckRoleAccount } from '@/utils/CheckRoleAccount';

import { useFormDirtyContext } from '../../../contexts/FormDirtyContext';
import { CustomRoutes } from '../../../services/API';
import { surveyMissionSchema } from '../../../services/schemaForm';
import { FormSurveyMission } from '../components/FormSurveyMission';
import { Marker } from '../components/drawingGoogle';
import { useSurveyMission } from '../hooks/useSurveyMission';
import { useDrawingModeStore } from '../stores/drawingModeStore';
import { SurveyMissionFormValues } from '../types/surveyMission.types';
import {
  ConvertCommandInput,
  ConvertFrameInput,
} from '../utils/convertMissionData';

export const AddSurveyMissionPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const headerPageRef = useRef<HTMLElement>(
    null,
  ) as React.RefObject<HTMLElement>;
  const [markerData, setMarkerData] = useState<Marker[]>([]);
  const [clickSave, setClickSave] = useState(false);
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const drawingMode = useDrawingModeStore((state) => state.drawingMode);
  const currentShape = useDrawingModeStore((state) => state.currentShape);
  const isDebouncedReviewPending = useDrawingModeStore(
    (state) => state.isDebouncedReviewPending,
  );

  // Determine the current mode for validation
  const currentMode =
    drawingMode === 'NONE' ? (currentShape?.type ?? 'POLYGON') : drawingMode;

  const { addSurveyMission } = useSurveyMission();
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
      settings: {
        hover_and_capture: true,
        altitude: 150,
        takeoff_altitude: 100,
        altitude_separation: 10,
        overlap: 65,
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
    trigger,
    formState: { isValid, isSubmitting, isDirty },
  } = methods;

  const clearAll = useDrawingModeStore((state) => state.clearAll);

  // Clear store when component mounts and unmounts
  useEffect(() => {
    clearAll(); // Reset store when component mounts
    return () => {
      clearAll(); // Also clear when component unmounts
    };
  }, [clearAll]);

  const handleCancel = () => {
    navigate(CustomRoutes.surveyMission.path);
  };

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
          altitude: waypoint.altitude,
          name: `Waypoint ${index + 1}`,
          for_robot: false,
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
        total_distance: data.total_distance,
        estimated_time: data.estimated_time,
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
        from_route: false,
      };
      const { message, success } = await addSurveyMission({ data: payload });
      if (success) {
        setDirty(false);
        ToastTopHelper.success(message);
        navigate(CustomRoutes.surveyMission.path);
      } else {
        setClickSave(false);
        ToastTopHelper.error(message);
      }
    },
    [currentShape, isRoleSuperuser, addSurveyMission, navigate, setDirty],
  );

  useFormDirty({
    isDirty: isDirty && !clickSave,
    triggerValidation: trigger,
    handleSubmit: methods.handleSubmit,
    onSubmit: onSubmit,
    isValid,
  });

  return (
    <>
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)}>
          <CustomBreadcrumb
            headerPageRef={headerPageRef}
            items={[
              {
                url: CustomRoutes.surveyMission.path,
              },
              { text: t('Add New Mission') },
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
              <CustomBtn
                size="md"
                style={{ width: '6rem' }}
                label={t('Save')}
                type="submit"
                actionType={ROLE_PERMISSION.UPDATE}
                loading={isSubmitting}
                disabled={!isValid || isSubmitting || isDebouncedReviewPending}
              />,
            ]}
          />
          <Main>
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
