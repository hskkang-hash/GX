import { Box } from '@mui/material';
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Control, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { LoadOptions } from 'react-select-async-paginate';
import { CustomInputHookForm, useTheme } from 'rj-core';

import GearIcon from '@/assets/images/GearIcon';
import Truncate from '@/components/truncate/Truncate';
import Colors from '@/configs/Colors';

import PaginationSelect from '../../../components/selects/PaginationSelect';
import { useRoute } from '../../routes/useAPI/useRoute';
import { useDrawingModeStore } from '../stores/drawingModeStore';
import {
  SurveyMissionFormValues,
  Waypoint,
} from '../types/surveyMission.types';
import './WaypointList.scss';

interface SelectOption {
  value: string | number;
  label: string;
  isDefault?: boolean;
  [key: string]: unknown;
}

interface WaypointListProps {
  waypoints: Waypoint[];
  control: Control<SurveyMissionFormValues>;
}

type UniqueIdentifier = string | number;

interface WaypointItemProps {
  waypoint: Waypoint;
  index: number;
  isExpanded: boolean;
  control: Control<SurveyMissionFormValues>;
  theme: string;
  isEditable: boolean;
  isNotReviewing: boolean;
  loadOptionsCMD: LoadOptions<
    SelectOption,
    any, // eslint-disable-line @typescript-eslint/no-explicit-any
    { page?: number; page_size?: number }
  >;
  loadOptionsFrame: LoadOptions<
    SelectOption,
    any, // eslint-disable-line @typescript-eslint/no-explicit-any
    { page?: number; page_size?: number }
  >;
  onToggleExpand: () => void;
  t: (key: string) => string;
}

const WaypointItem: React.FC<WaypointItemProps> = React.memo(
  ({
    index,
    isExpanded,
    control,
    theme,
    isEditable,
    isNotReviewing,
    loadOptionsCMD,
    loadOptionsFrame,
    onToggleExpand,
    t,
  }) => {
    const headerStyle = useMemo(
      () => ({
        borderBottom: isExpanded
          ? `1px solid ${theme === 'dark' ? '#444646' : '#E0E0E0'}`
          : 'none',
      }),
      [isExpanded, theme],
    );

    const iconStyle = useMemo(
      () => ({
        transform: isExpanded ? 'rotate(90deg)' : '',
      }),
      [isExpanded],
    );

    const iconColor = useMemo(
      () =>
        isExpanded
          ? Colors.Primary
          : theme === 'dark'
            ? 'var(--ga-dark-theme-font-color)'
            : 'var( --ga-light-theme-font-color)',
      [isExpanded, theme],
    );

    const waypointLabel = useMemo(() => `Waypoint ${index + 1}`, [index]);

    const cruiseSpeedLabel = useMemo(() => t('Cruise Speed (m/s)'), [t]);

    const commandLabel = useMemo(() => t('Command'), [t]);
    const frameLabel = useMemo(() => t('Frame'), [t]);
    const selectLabel = useMemo(() => t('Select'), [t]);
    const param1Label = useMemo(() => t('Param 1'), [t]);
    const param2Label = useMemo(() => t('Param 2'), [t]);
    const param3Label = useMemo(() => t('Param 3'), [t]);
    const param4Label = useMemo(() => t('Param 4'), [t]);
    const latitudeLabel = useMemo(() => t('Param5/Latitude/X'), [t]);
    const longitudeLabel = useMemo(() => t('Param6/Longitude/Y'), [t]);
    const altitudeLabel = useMemo(() => t('Param7/Altitude/Z'), [t]);

    return (
      <div className="dropdown-terminal">
        <div
          className="dropdown-terminal__header"
          style={headerStyle}
        >
          <Box sx={{ flex: 1 }}>
            <Truncate
              content={waypointLabel}
              maxLengthContent={35}
              tooltipContent={waypointLabel}
            />
          </Box>
          <span
            onClick={onToggleExpand}
            className="dropdown-terminal__icon"
            style={iconStyle}
          >
            <GearIcon color={iconColor} />
          </span>
        </div>
        {isExpanded && (
          <div className="dropdown-terminal__content">
            <CustomInputHookForm
              control={control}
              label={cruiseSpeedLabel}
              name={`waypoints.${index}.cruise_speed`}
              type="number"
              placeholder={cruiseSpeedLabel}
              required
              disabled={isNotReviewing}
            />
            <PaginationSelect
              label={commandLabel}
              required
              name={`waypoints.${index}.command`}
              control={control}
              loadOptions={loadOptionsCMD}
              placeholder={selectLabel}
              disabled={!isEditable || isNotReviewing}
            />
            <PaginationSelect
              label={frameLabel}
              required
              name={`waypoints.${index}.frame`}
              control={control}
              loadOptions={loadOptionsFrame}
              placeholder={selectLabel}
              disabled={!isEditable || isNotReviewing}
            />
            <CustomInputHookForm
              control={control}
              label={param1Label}
              name={`waypoints.${index}.param_1`}
              type="number"
              placeholder={param1Label}
              required
              disabled={!isEditable || isNotReviewing}
            />
            <CustomInputHookForm
              control={control}
              label={param2Label}
              name={`waypoints.${index}.param_2`}
              type="number"
              placeholder={param2Label}
              required
              disabled={!isEditable || isNotReviewing}
            />
            <CustomInputHookForm
              control={control}
              label={param3Label}
              name={`waypoints.${index}.param_3`}
              type="number"
              placeholder={param3Label}
              required
              disabled={!isEditable || isNotReviewing}
            />
            <CustomInputHookForm
              control={control}
              label={param4Label}
              name={`waypoints.${index}.param_4`}
              type="number"
              placeholder={param4Label}
              required
              disabled={!isEditable || isNotReviewing}
            />
            <CustomInputHookForm
              control={control}
              name={`waypoints.${index}.latitude`}
              label={latitudeLabel}
              type="decimal"
              placeholder={latitudeLabel}
              disabled={!isEditable || isNotReviewing}
            />
            <CustomInputHookForm
              control={control}
              name={`waypoints.${index}.longitude`}
              label={longitudeLabel}
              type="decimal"
              placeholder={longitudeLabel}
              disabled={!isEditable}
            />
            <CustomInputHookForm
              control={control}
              name={`waypoints.${index}.altitude`}
              label={altitudeLabel}
              type="decimal"
              placeholder={altitudeLabel}
              disabled={isNotReviewing}
            />
          </div>
        )}
      </div>
    );
  },
  (prevProps, nextProps) => {
    return (
      prevProps.index === nextProps.index &&
      prevProps.isExpanded === nextProps.isExpanded &&
      prevProps.isEditable === nextProps.isEditable &&
      prevProps.theme === nextProps.theme &&
      prevProps.waypoint === nextProps.waypoint
    );
  },
);

WaypointItem.displayName = 'WaypointItem';

export const WaypointList: React.FC<WaypointListProps> = React.memo(
  ({ waypoints, control }) => {
    const { t } = useTranslation();
    const [theme] = useTheme();
    const [expandedItemIds, setExpandedItemIds] = useState<UniqueIdentifier[]>(
      [],
    );
    const isNotReviewing = useDrawingModeStore((state) => state.isNotReviewing);
    const { getOptionsCMD, getOptionsFrame } = useRoute();
    const isEditable = useDrawingModeStore((state) => state.isEditable);
    const setWaypointsList = useDrawingModeStore(
      (state) => state.setWaypointsList,
    );

    // Create wrapper functions for PaginationSelect
    const loadOptionsCMD = useCallback<
      LoadOptions<
        SelectOption,
        any, // eslint-disable-line @typescript-eslint/no-explicit-any
        { page?: number; page_size?: number }
      >
    >(
      (search, loadedOptions, additional) => {
        return getOptionsCMD()(search, loadedOptions, {
          page: additional?.page || 1,
        }) as ReturnType<
          LoadOptions<
            SelectOption,
            any, // eslint-disable-line @typescript-eslint/no-explicit-any
            { page?: number; page_size?: number }
          >
        >;
      },
      [getOptionsCMD],
    );

    const loadOptionsFrame = useCallback<
      LoadOptions<
        SelectOption,
        any, // eslint-disable-line @typescript-eslint/no-explicit-any
        { page?: number; page_size?: number }
      >
    >(
      (search, loadedOptions, additional) => {
        return getOptionsFrame()(search, loadedOptions, {
          page: additional?.page || 1,
        }) as ReturnType<
          LoadOptions<
            SelectOption,
            any, // eslint-disable-line @typescript-eslint/no-explicit-any
            { page?: number; page_size?: number }
          >
        >;
      },
      [getOptionsFrame],
    );

    const toggleExpandItem = useCallback((id: UniqueIdentifier) => {
      setExpandedItemIds((prev) => {
        if (prev.includes(id)) {
          return prev.filter((item) => item !== id);
        } else {
          return [...prev, id];
        }
      });
    }, []);

    // Watch form waypoints to sync with store when latitude/longitude changes
    const formWaypoints = useWatch({
      control,
      name: 'waypoints',
      defaultValue: [],
    });

    // Use ref to track last synced waypoints to prevent infinite loops
    const lastSyncedWaypointsRef = useRef<string>('');
    // Use ref to track previous formWaypoints to detect actual changes
    const prevFormWaypointsRef = useRef<string>('');

    // Helper function to serialize waypoints for comparison (only relevant fields)
    const serializeWaypointsForComparison = useCallback((wps: Waypoint[]) => {
      return JSON.stringify(
        wps.map((wp) => ({
          latitude: Number(wp.latitude),
          longitude: Number(wp.longitude),
          cruise_speed: Number(wp.cruise_speed),
          operating_altitude: Number(wp.operating_altitude),
          altitude: wp.altitude,
        })),
      );
    }, []);

    // Sync form waypoints with store when coordinates change
    // Only react to formWaypoints changes, NOT waypoints changes
    useEffect(() => {
      if (
        !Array.isArray(formWaypoints) ||
        formWaypoints.length === 0 ||
        formWaypoints.length !== waypoints.length
      ) {
        return;
      }

      // Serialize form waypoints to check if they actually changed
      const serializedFormWaypoints = serializeWaypointsForComparison(
        formWaypoints as Waypoint[],
      );

      // Skip if formWaypoints haven't actually changed
      if (prevFormWaypointsRef.current === serializedFormWaypoints) {
        return;
      }

      // Update the ref to track this as the new previous value
      prevFormWaypointsRef.current = serializedFormWaypoints;

      // Serialize store waypoints for comparison
      const serializedStoreWaypoints =
        serializeWaypointsForComparison(waypoints);

      // Only sync if form waypoints are different from store waypoints
      // AND different from what we last synced (to prevent loops)
      if (
        serializedFormWaypoints !== serializedStoreWaypoints &&
        lastSyncedWaypointsRef.current !== serializedFormWaypoints
      ) {
        lastSyncedWaypointsRef.current = serializedFormWaypoints;
        setWaypointsList(formWaypoints as Waypoint[]);
      }
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [formWaypoints, serializeWaypointsForComparison, setWaypointsList]);

    // Memoize expanded state lookup
    const expandedSet = useMemo(
      () => new Set(expandedItemIds),
      [expandedItemIds],
    );

    const emptyMessage = useMemo(
      () =>
        t(
          'SurveyMission.Create a surveillance route on the map (right side) to display the waypoint list.',
        ),
      [t],
    );

    if (waypoints.length === 0) {
      return <span>{emptyMessage}</span>;
    }

    return (
      <div className="waypoint-list">
        {waypoints.map((waypoint, index) => {
          const waypointId = index + 1;
          const isExpanded = expandedSet.has(waypointId);

          return (
            <WaypointItem
              key={index}
              waypoint={waypoint}
              index={index}
              isExpanded={isExpanded}
              control={control}
              theme={theme}
              isEditable={isEditable}
              isNotReviewing={isNotReviewing}
              loadOptionsCMD={loadOptionsCMD}
              loadOptionsFrame={loadOptionsFrame}
              onToggleExpand={() => toggleExpandItem(waypointId)}
              t={t}
            />
          );
        })}
      </div>
    );
  },
  (prevProps, nextProps) => {
    // Custom comparison function to check if waypoints have changed
    if (prevProps.waypoints.length !== nextProps.waypoints.length) {
      return false;
    }

    return prevProps.waypoints.every((waypoint, index) => {
      const nextWaypoint = nextProps.waypoints[index];
      if (!nextWaypoint) return false;

      return (
        waypoint.cruise_speed === nextWaypoint.cruise_speed &&
        waypoint.operating_altitude === nextWaypoint.operating_altitude &&
        waypoint.command === nextWaypoint.command &&
        waypoint.frame === nextWaypoint.frame &&
        waypoint.param_1 === nextWaypoint.param_1 &&
        waypoint.param_2 === nextWaypoint.param_2 &&
        waypoint.param_3 === nextWaypoint.param_3 &&
        waypoint.param_4 === nextWaypoint.param_4 &&
        waypoint.latitude === nextWaypoint.latitude &&
        waypoint.longitude === nextWaypoint.longitude &&
        waypoint.altitude === nextWaypoint.altitude
      );
    });
  },
);

WaypointList.displayName = 'WaypointList';
