import { useCallback, useEffect, useMemo, useRef } from 'react';
import { Control, useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { CustomInputHookForm, FormBlock } from 'rj-core';

import CustomCheckBox from '../../../components/Form/CustomCheckBox';
import { CustomSwitchBtn } from '../../../components/Form/CustomSwitchBtn';
import PaginationSelect from '../../../components/selects/PaginationSelect';
import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import useCommonAPI from '../../useCommonAPI/useAPI';
import { useDebouncedSurveyReview } from '../hooks/useDebouncedSurveyReview';
import { useDrawingModeStore } from '../stores/drawingModeStore';
import { SurveyMissionFormValues } from '../types/surveyMission.types';
import MapForRouteUnified from './MapForRouteUnified';
import { SettingsSurvey } from './SettingsSurvey';
import { WaypointList } from './WaypointList';
import { calculatePolygonBounds } from './drawing/utils';
import { Marker } from './drawingGoogle';

interface KakaoAddressResult {
  road_address?: {
    region_1depth_name?: string;
    region_2depth_name?: string;
  };
  address?: {
    region_1depth_name?: string;
    region_2depth_name?: string;
  };
}

export const FormSurveyMission = ({
  markerData = [],
  setMarkerData,
}: {
  markerData?: Marker[];
  setMarkerData?: (markerData: Marker[]) => void;
}) => {
  const { t } = useTranslation();
  const { control, watch, setValue, trigger } = useFormContext();
  const { getOptionsByModel } = useCommonAPI();
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const drawingMode = useDrawingModeStore((state) => state.drawingMode);
  const currentShape = useDrawingModeStore((state) => state.currentShape);
  const waypointsList = useDrawingModeStore((state) => state.waypointsList);
  const isNotReviewing = useDrawingModeStore((state) => state.isNotReviewing);
  const setIsEditable = useDrawingModeStore((state) => state.setIsEditable);
  const setCurrentShape = useDrawingModeStore((state) => state.setCurrentShape);

  // Only show settings for Polygon, Circular, and Trace modes
  const shouldShowSettings = useMemo(
    () =>
      isNotReviewing
        ? false
        : ['POLYGON', 'CIRCULAR', 'TRACE', 'NONE'].includes(
            drawingMode === 'NONE'
              ? (currentShape?.type ?? 'POLYGON')
              : drawingMode,
          ),
    [drawingMode, currentShape, isNotReviewing],
  );

  const polygon = useMemo(
    () => currentShape?.points?.map((point) => [point.lat, point.lng]),
    [currentShape],
  );
  const hover_and_capture = watch('settings.hover_and_capture');
  const altitude = watch('settings.altitude');
  const takeoff_altitude = watch('settings.takeoff_altitude');
  const altitude_separation = watch('settings.altitude_separation');
  const survey_angle = watch('settings.angle');
  const trigger_distance = watch('settings.trigger_distance');
  const spacing = watch('settings.spacing');
  const turnaround_distance = watch('settings.turnaround_distance');
  const returnValue = watch('return');
  const overlap = watch('settings.overlap');
  const regionUpdateTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const formatRegionLabel = useCallback(
    (district?: string, province?: string): string | null => {
      const trimmedDistrict = district?.trim() || '';
      const trimmedProvince = province?.trim() || '';
      if (trimmedDistrict && trimmedProvince) {
        return `${trimmedDistrict}, ${trimmedProvince}`;
      }
      if (trimmedProvince) {
        return trimmedProvince;
      }
      if (trimmedDistrict) {
        return trimmedDistrict;
      }
      return null;
    },
    [],
  );

  const reverseGeocodeRegion = useCallback(
    async (lat: number, lng: number): Promise<string | null> => {
      if (
        typeof window !== 'undefined' &&
        window.kakao?.maps?.services?.Geocoder
      ) {
        return new Promise((resolve) => {
          const geocoder = new window.kakao.maps.services.Geocoder();
          geocoder.coord2Address(
            lng,
            lat,
            (result: KakaoAddressResult[], status: string) => {
              if (
                status === window.kakao.maps.services.Status.OK &&
                result.length > 0
              ) {
                const addr = result[0].road_address || result[0].address;
                const regionLabel = formatRegionLabel(
                  addr?.region_2depth_name,
                  addr?.region_1depth_name,
                );
                resolve(regionLabel);
                return;
              }
              resolve(null);
            },
          );
        });
      }

      if (typeof window !== 'undefined' && window.google?.maps?.Geocoder) {
        return new Promise((resolve) => {
          const geocoder = new window.google.maps.Geocoder();
          geocoder.geocode({ location: { lat, lng } }, (results, status) => {
            if (status === 'OK' && results && results.length > 0) {
              const components = results[0].address_components || [];
              const province = components.find((component) =>
                component.types?.includes('administrative_area_level_1'),
              )?.long_name;
              const district =
                components.find((component) =>
                  component.types?.includes('administrative_area_level_2'),
                )?.long_name ||
                components.find((component) =>
                  component.types?.includes('sublocality_level_1'),
                )?.long_name ||
                components.find((component) =>
                  component.types?.includes('locality'),
                )?.long_name;
              resolve(formatRegionLabel(district, province));
              return;
            }
            resolve(null);
          });
        });
      }

      return null;
    },
    [formatRegionLabel],
  );
  // Prepare survey data for debounced API call
  const surveyData = useMemo(
    () => ({
      polygon: polygon || [],
      hover_and_capture: hover_and_capture || false,
      altitude: altitude || 0,
      takeoff_altitude: takeoff_altitude || 0,
      altitude_separation: altitude_separation || 0,
      survey_angle: survey_angle || 0,
      trigger_distance: trigger_distance || 0,
      spacing: spacing || 0,
      turnaround_distance: turnaround_distance || 0,
      return_to_home: returnValue,
      overlap: overlap || 0,
    }),
    [
      polygon,
      hover_and_capture,
      altitude,
      takeoff_altitude,
      altitude_separation,
      survey_angle,
      trigger_distance,
      spacing,
      turnaround_distance,
      returnValue,
      overlap,
    ],
  );

  // Check if initial data has been loaded from server (for edit page)
  // If waypointsList has data and polygon exists, it means data was loaded from server
  // We need to check this synchronously to set skipInitialCall correctly
  const shouldSkipInitialCall =
    waypointsList.length > 0 &&
    polygon &&
    polygon.length > 0 &&
    shouldShowSettings;

  // Use debounced hook to automatically call API when data changes
  // Skip initial call when data is first loaded from edit page
  const { isPending } = useDebouncedSurveyReview({
    data: surveyData,
    delay: 1000, // 1 second delay
    enabled: isNotReviewing
      ? false
      : shouldShowSettings && polygon && polygon.length > 0, // Only enable when in drawing mode and polygon exists
    skipInitialCall: shouldSkipInitialCall, // Skip initial call if data was loaded from edit page
  });

  const setIsDebouncedReviewPending = useDrawingModeStore(
    (state) => state.setIsDebouncedReviewPending,
  );

  // Sync pending state to store
  useEffect(() => {
    setIsDebouncedReviewPending(isPending);
  }, [isPending, setIsDebouncedReviewPending]);

  // Use ref to track previous returnValue to avoid infinite loops
  const prevReturnValueRef = useRef(returnValue);

  // Update currentShape with return property when returnValue changes
  useEffect(() => {
    if (currentShape && prevReturnValueRef.current !== returnValue) {
      setCurrentShape({
        ...currentShape,
        return: returnValue || false,
      });
      prevReturnValueRef.current = returnValue;
    }
  }, [returnValue, currentShape, setCurrentShape]);

  // Update currentShape with return property when currentShape is created/updated
  const updateCurrentShapeWithReturn = useCallback(() => {
    if (currentShape && currentShape.return !== returnValue) {
      setCurrentShape({
        ...currentShape,
        return: returnValue || false,
      });
    }
  }, [currentShape, returnValue, setCurrentShape]);

  useEffect(() => {
    updateCurrentShapeWithReturn();
  }, [currentShape?.id, updateCurrentShapeWithReturn]);

  const waypointsPreview = useDrawingModeStore(
    (state) => state.waypointsPreview,
  );

  // Handle waypoints for POLYGON, CIRCULAR, TRACE modes - use API-generated waypoints
  useEffect(() => {
    if (waypointsList.length > 0) {
      // For polygon modes, use API-generated waypoints
      setValue('waypoints', waypointsList);
      setIsEditable(false);

      // Trigger validation after setting waypoints
      trigger('waypoints');
    } else {
      // Clear form waypoints when waypointsList is empty
      setValue('waypoints', []);
      setValue('total_distance', null);
      setValue('estimated_time', null);

      // Trigger validation after clearing waypoints
      trigger('waypoints');
    }
  }, [waypointsList, setValue, setIsEditable, trigger]);

  // Calculate marker data based on current state
  const calculatedMarkerData = useMemo(() => {
    // For polygon modes, use waypointsPreview from API
    // If waypointsPreview is empty but we have waypointsList, use it as fallback
    // If both are empty but we have currentShape points, use them to keep the shape visible
    if (waypointsPreview.length > 0) {
      return waypointsPreview
        .map((point: [number, number]) => ({
          lat: Number(point[0]),
          lng: Number(point[1]),
        }))
        .filter(
          (point: { lat: number; lng: number }) =>
            !isNaN(point.lat) &&
            !isNaN(point.lng) &&
            !(point.lat === 0 && point.lng === 0) &&
            point.lat >= -90 &&
            point.lat <= 90 &&
            point.lng >= -180 &&
            point.lng <= 180,
        ) as Marker[];
    } else if (waypointsList.length > 0) {
      // Fallback to waypointsList when waypointsPreview is not yet available
      return waypointsList
        .map((waypoint) => ({
          lat: Number(waypoint.latitude),
          lng: Number(waypoint.longitude),
        }))
        .filter(
          (point: { lat: number; lng: number }) =>
            !isNaN(point.lat) &&
            !isNaN(point.lng) &&
            !(point.lat === 0 && point.lng === 0) &&
            point.lat >= -90 &&
            point.lat <= 90 &&
            point.lng >= -180 &&
            point.lng <= 180,
        ) as Marker[];
    } else if (currentShape?.points && currentShape.points.length > 0) {
      // Final fallback to currentShape points to keep the shape visible
      return currentShape.points
        .map((point) => ({
          lat: Number(point.lat),
          lng: Number(point.lng),
        }))
        .filter(
          (point: { lat: number; lng: number }) =>
            !isNaN(point.lat) &&
            !isNaN(point.lng) &&
            !(point.lat === 0 && point.lng === 0) &&
            point.lat >= -90 &&
            point.lat <= 90 &&
            point.lng >= -180 &&
            point.lng <= 180,
        ) as Marker[];
    }
    return [];
  }, [waypointsPreview, waypointsList, currentShape]);

  // Track previous values to detect changes
  const prevDrawingModeRef = useRef(drawingMode);
  const prevWaypointsPreviewRef = useRef(waypointsPreview);
  const prevCalculatedMarkerDataRef = useRef<Marker[]>([]);

  // Sync calculated marker data to markerData state via setMarkerData
  // Update when:
  // 1. markerData is empty (no data yet)
  // 2. drawingMode changes (mode switched)
  // 3. waypointsPreview changes (useDebouncedSurveyReview updated)
  useEffect(() => {
    const drawingModeChanged = prevDrawingModeRef.current !== drawingMode;
    const waypointsPreviewChanged =
      JSON.stringify(prevWaypointsPreviewRef.current) !==
      JSON.stringify(waypointsPreview);
    const hasNoMarkerData = markerData.length === 0;

    // Always update refs to track current state
    prevDrawingModeRef.current = drawingMode;
    prevWaypointsPreviewRef.current = waypointsPreview;
    prevCalculatedMarkerDataRef.current = calculatedMarkerData;

    // Update markerData if it's empty, mode changed, or waypointsPreview changed
    if (
      (hasNoMarkerData || drawingModeChanged || waypointsPreviewChanged) &&
      setMarkerData
    ) {
      setMarkerData(calculatedMarkerData);
    }
  }, [
    calculatedMarkerData,
    setMarkerData,
    drawingMode,
    waypointsPreview,
    markerData.length,
  ]);

  useEffect(() => {
    if (!currentShape?.points || currentShape.points.length === 0) {
      return;
    }

    if (regionUpdateTimeoutRef.current) {
      clearTimeout(regionUpdateTimeoutRef.current);
    }

    regionUpdateTimeoutRef.current = setTimeout(async () => {
      try {
        const { center } = calculatePolygonBounds(currentShape.points);
        const regionLabel = await reverseGeocodeRegion(center.lat, center.lng);
        if (regionLabel) {
          setValue('region', regionLabel, {
            shouldDirty: true,
            shouldTouch: true,
          });
        }
      } catch (error) {
        console.error('Unable to update region from polygon', error);
      }
    }, 600);

    return () => {
      if (regionUpdateTimeoutRef.current) {
        clearTimeout(regionUpdateTimeoutRef.current);
      }
    };
  }, [currentShape, reverseGeocodeRegion, setValue]);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
      }}
    >
      <FormBlock>
        <div className={`form-grid gap-3`}>
          {isRoleSuperuser ? (
            <>
              <PaginationSelect
                label={t('SurveyMission.Group')}
                name="group"
                control={control}
                loadOptions={getOptionsByModel({
                  name_modal: 'usergroup',
                  search_field: 'name',
                  key: 'name',
                  value: 'id',
                })}
                disabled={isNotReviewing}
                placeholder={t('SurveyMission.Select')}
                required
              />
              <div className="form-grid-9-1 gap-3">
                <CustomInputHookForm
                  control={control}
                  required
                  name="name"
                  label={t('SurveyMission.Name')}
                  placeholder={t('SurveyMission.Name')}
                  // disabled={isNotReviewing}
                />
                {/* <div className="align-content-center mt-4">
                  <CustomSwitchBtn
                    name="return"
                    control={control}
                    label={t('SurveyMission.Return')}
                    isHorizontal
                    disabled={isNotReviewing}
                  />
                </div> */}
              </div>
            </>
          ) : (
            <div className="grid-span-full">
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '30fr 1fr',
                  gap: '2rem',
                }}
              >
                <CustomInputHookForm
                  control={control}
                  required
                  name="name"
                  label={t('SurveyMission.Name')}
                  placeholder={t('SurveyMission.Name')}
                  // disabled={isNotReviewing}
                />
                {/* <div
                  className="align-content-center mt-4"
                  style={{
                    width: '8.5rem',
                    whiteSpace: 'nowrap',
                  }}
                >
                  <CustomSwitchBtn
                    name="return"
                    control={control}
                    label={t('SurveyMission.Return')}
                    isHorizontal
                    disabled={isNotReviewing}
                  />
                </div> */}
              </div>
            </div>
          )}
          <div className="form-grid">
            <CustomInputHookForm
              control={control}
              name="maximum_number_of_drones"
              label={t('SurveyMission.Maximum Number of Drones')}
              placeholder={t('SurveyMission.Maximum Number of Drones')}
              required
              disabled={isNotReviewing}
            />
            <PaginationSelect
              required
              label={t('SurveyMission.Purpose')}
              name="purpose"
              control={control}
              loadOptions={getOptionsByModel({
                name_modal: 'MissionPurpose',
                search_field: 'name',
              })}
              placeholder={t('SurveyMission.Select')}
              // disabled={isNotReviewing}
            />
          </div>
          <div>
            <CustomCheckBox
              name="log_collection"
              control={control}
              label={t('SurveyMission.Log Collection')}
              subLabel={t('SurveyMission.Allow')}
              // disabled={isNotReviewing}
            />
            <CustomCheckBox
              name="video_recording"
              control={control}
              label={t('SurveyMission.Video Recording')}
              subLabel={t('SurveyMission.Allow')}
              // disabled={isNotReviewing}
            />
            <CustomCheckBox
              name="video_analysis"
              control={control}
              label={t('SurveyMission.Video Analysis')}
              subLabel={t('SurveyMission.Allow')}
              // disabled={isNotReviewing}
            />
          </div>
          <div className="form-grid">
            <CustomInputHookForm
              control={control}
              name="total_distance"
              label={t('SurveyMission.Total Distance')}
              placeholder={t('SurveyMission.Total Distance')}
              disabled
            />
            <CustomInputHookForm
              control={control}
              name="estimated_time"
              label={t('SurveyMission.Estimated Time')}
              placeholder={t('SurveyMission.Estimated Time')}
              disabled
            />
          </div>
          <div className="form-grid">
            <CustomInputHookForm
              control={control}
              name="region"
              label={t('Region')}
              placeholder={t('Region')}
              disabled
              // disabled={isNotReviewing}
            />
            <CustomInputHookForm
              control={control}
              name="note"
              label="Note"
              placeholder={t('Note')}
              // disabled={isNotReviewing}
            />
          </div>
        </div>
      </FormBlock>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '6fr 15fr',
          gap: '1rem',
        }}
      >
        <FormBlock
          style={{
            height: '49rem',
          }}
        >
          <p
            style={{
              marginBottom: '16px',
              fontSize: '1.2rem',
              fontWeight: 600,
            }}
          >
            {t('SurveyMission.Waypoints List')}
          </p>
          <div style={{ overflow: 'auto', height: '44rem' }}>
            <WaypointList
              waypoints={waypointsList}
              control={control as unknown as Control<SurveyMissionFormValues>}
            />
          </div>
        </FormBlock>
        <MapForRouteUnified
          style={{
            height: '49rem',
          }}
          notUseActionButtons={isNotReviewing}
          markerData={markerData.length > 0 ? markerData : []}
          overlayContent={shouldShowSettings ? <SettingsSurvey /> : null}
        />
      </div>
    </div>
  );
};
