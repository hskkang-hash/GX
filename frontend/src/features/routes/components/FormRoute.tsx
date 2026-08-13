// @ts-nocheck
import { yupResolver } from '@hookform/resolvers/yup';
import { Box, Typography } from '@mui/material';
import { ConfigProvider, Switch } from 'antd';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { FormProvider, useForm, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { IoTrashOutline } from 'react-icons/io5';
import {
  ActionBtn,
  CustomBreadcrumb,
  CustomBtn,
  CustomInputHookForm,
  CustomModal,
  CustomizableTable,
  FormBlock,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useConfigSystem,
  useTheme,
} from 'rj-core';

import GearIcon from '@/assets/images/GearIcon';
import Truncate from '@/components/truncate/Truncate';
import Colors from '@/configs/Colors';
import useAPI from '@/features/terminals/useAPI/useAPI';
import { useFormNavigationBlocker } from '@/hooks/useFormNavigationBlocker';
import { schemaRoute } from '@/services/schemaForm';
import { isEmptyObject } from '@/utils/fetchFromObject';
import { convertValueToUnit } from '@/utils/utils';

import { CustomSwitchBtn } from '../../../components/Form/CustomSwitchBtn';
import { SelectOption } from '../../../components/selects/CustomSelect';
import PaginationSelect from '../../../components/selects/PaginationSelect';
import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import useCommonAPI from '../../useCommonAPI/useAPI';
import { Command } from '../useAPI/useAPI';
import { useRoute } from '../useAPI/useRoute';
import {
  convertEstimated,
  convertUnitTimeStopsToSeconds,
} from '../utils/convertEstimated';
import './FormRoute.scss';
import MapForRouteUnified from './MapForRouteUnified';
import { SortableList } from './SortableList';

// Define types for form data
export interface FormDataRoute {
  name: string;
  group: SelectOption | null;
  service: SelectOption | null;
  description?: string;
  code: string;
  note?: string;
  total_distance?: string;
  estimated_time?: string;
  total_stops?: number | null;
  terminals?: Terminal[];
  name_search?: string;
  address_search?: string;
  two_way?: boolean;
}

export interface Terminal {
  route_terminal_id?: number;
  terminal_id: number;
  name: string;
  stop: boolean;
  order: number;
  longitude: number;
  latitude: number;
  time_stops?: string;
  for_robot?: boolean;
  is_temp?: boolean;
  is_new?: boolean;
  cruise_speed?: number;
  operating_altitude?: number;
  command?: Command;
  frame?: { label: string; value: number | string } | null;
  is_edit?: boolean;
}

interface FormRouteProps {
  initialData?: FormDataRoute;
  onSubmit: (data: FormDataRoute) => Promise<void>;
  onCancel: () => void;
  breadcrumbItems: { url?: string; text?: string }[];
  isEdit?: boolean;
}

type UniqueIdentifier = string | number;

const FormRoute = ({
  initialData,
  onSubmit,
  onCancel,
  breadcrumbItems,
  isEdit = false,
}: FormRouteProps) => {
  const { t } = useTranslation();
  const [configSystem] = useConfigSystem();

  const defaultCruiseSpeed =
    configSystem?.['Waypoint Settings']?.waypoit_speed || 7;

  const [objSearch, setObjSearch] = useState({});
  const [pageSize, setPageSize] = useState<number>(5);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [theme] = useTheme();
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);
  const { getListDockingStation } = useAPI();
  const [isShowTable, setIsShowTable] = useState<boolean>(false);
  const { getOptionsByModel } = useCommonAPI();
  const { getOptionsCMD, getOptionsFrame } = useRoute();

  const [data, setData] = useState<{
    data: any[];
    totalItem: number;
    totalPage: number;
  }>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });

  // const resolver = useMemo(() => yupResolver(schemaRoute(t)) as any, [t]);

  const methods = useForm<FormDataRoute>({
    defaultValues: initialData
      ? initialData
      : {
          code: 'R-' + new Date().getTime().toString(),
          group: null,
          service: null,
          name: '',
          description: '',
          note: '',
          total_distance: '',
          estimated_time: '',
          total_stops: null,
          name_search: '',
          address_search: '',
          // two_way: false,
          terminals: [],
        },
    resolver: yupResolver(schemaRoute(t, isRoleSuperuser)) as any,
    mode: 'all',
  });

  const {
    handleSubmit,
    control,
    setValue,
    reset,
    watch,
    formState: { isDirty, errors, isValid, isSubmitting },
    clearErrors,
    trigger,
  } = methods;

  // Re-trigger validation when language changes to update error messages
  useEffect(() => {
    // Only trigger if there are existing errors to translate
    const hasErrors = Object.keys(errors).length > 0;
    if (hasErrors) {
      trigger();
    }
  }, [t, trigger]);

  const terminals = watch('terminals');

  // const isReturn = watch('two_way');

  const [defaultCMD, setDefaultCMD] = useState<Command | null>(null);
  const [defaultTakeoffCMD, setDefaultTakeoffCMD] = useState<Command | null>(
    null,
  );

  console.log('defaultCMD', defaultCMD);
  const [defaultFrame, setDefaultFrame] = useState<null>(null);

  const { getDefaultCMD, getDefaultFrame, getDefaultTakeoffCMD } = useRoute();

  const [clickSave, setClickSave] = useState(false);

  const { showModal, setShowModal, handleModalSave, handleModalCancel } =
    useFormNavigationBlocker({
      isDirty: clickSave == false && isDirty,
      onSave: async () => {
        const formData = watch();
        await onSubmit(formData);
        reset(formData, {
          keepDirty: false,
          keepValues: true,
        });
      },
      onCancel,
      handleSubmit,
    });

  const handleFormSubmit = async (data: FormData) => {
    setClickSave(true);
    try {
      await onSubmit(data);
      reset(data, {
        keepDirty: false,
        keepValues: true,
      });
      // navigate(CustomRoutes.terminals.path);
    } catch (error) {
      console.error('Error saving form:', error);
    }
  };

  useEffect(() => {
    (async () => {
      // Load NAV_WAYPOINT command (for normal waypoints)
      const { options: cmdOptions } = await getDefaultCMD('NAV_WAYPOINT');
      setDefaultCMD(cmdOptions.length > 0 ? cmdOptions[0] : null);

      // Load NAV_TAKEOFF command (for first terminal)
      const { options: takeoffOptions } = await getDefaultTakeoffCMD();
      console.log('takeoffOptions', takeoffOptions);
      setDefaultTakeoffCMD(
        takeoffOptions.length > 0 ? takeoffOptions[0] : null,
      );

      // Load frame options
      const { options: frameOptions } = await getDefaultFrame('GLOBAL');
      console.log('frameOptions', frameOptions);
      setDefaultFrame(frameOptions.length > 0 ? frameOptions[0] : null);
    })();
  }, []);

  useEffect(() => {
    if (initialData) {
      reset(initialData);
      // Reset initialization flag when switching to edit mode
      isInitializedRef.current = false;
    } else {
      // Reset initialization flag when switching to create mode
      isInitializedRef.current = false;
    }
  }, [initialData, reset]);

  const handleToggleTerminal = useCallback(
    (terminal: Terminal) => {
      const isAdded = watch('terminals')?.some(
        (item) => item.terminal_id === terminal.terminal_id,
      );
      if (isAdded) {
        // Remove the terminal
        const updatedTerminals = watch('terminals')?.filter(
          (item) => item.terminal_id !== terminal.terminal_id,
        );

        // Reorder remaining terminals to keep sequence
        const reorderedTerminals = updatedTerminals?.map((terminal, index) => ({
          ...terminal,
          order: index + 1,
        }));

        setValue('terminals', reorderedTerminals, { shouldDirty: true });
      } else {
        const cruiseSpeed =
          watch('terminals')?.[watch('terminals')?.length - 1]?.cruise_speed ||
          defaultCruiseSpeed;

        // Add the terminal with the next order number
        setValue(
          'terminals',
          [
            ...(watch('terminals') || []),
            {
              ...terminal,
              order: (watch('terminals')?.length || 0) + 1,
              cruise_speed: cruiseSpeed,
              operating_altitude: '20',
              latitude: terminal.latitude || 0,
              longitude: terminal.longitude || 0,
            },
          ],
          { shouldDirty: true },
        );
      }
    },
    [watch, setValue],
  );

  // Handle change for_robot terminal
  const onChangeForRobot = useCallback(
    (checked: boolean, id: string | number) => {
      const updatedTerminals = watch('terminals')?.map((item) =>
        item.terminal_id === id ? { ...item, for_robot: checked } : item,
      );
      setValue('terminals', updatedTerminals, { shouldDirty: true });
    },
    [watch, setValue],
  );

  // Track previous cruise speeds to detect changes
  const prevCruiseSpeedsRef = useRef<number[]>([]);
  const isInitializedRef = useRef<boolean>(false);

  // Watch for cruise_speed changes and update subsequent terminals
  const watchedCruiseSpeeds = useWatch({
    control,
    name: 'terminals',
    defaultValue: terminals || [],
  });

  useEffect(() => {
    if (!watchedCruiseSpeeds || watchedCruiseSpeeds.length === 0) return;

    const currentCruiseSpeeds = watchedCruiseSpeeds.map(
      (terminal) => terminal.cruise_speed || 0,
    );
    const prevCruiseSpeeds = prevCruiseSpeedsRef.current;

    // Initialize previous speeds on first load (for edit mode)
    if (!isInitializedRef.current) {
      prevCruiseSpeedsRef.current = [...currentCruiseSpeeds];
      isInitializedRef.current = true;
      return; // Don't trigger logic on initial load
    }

    // Check if any cruise_speed has changed
    let changedIndex = -1;
    for (let i = 0; i < currentCruiseSpeeds.length; i++) {
      if (
        currentCruiseSpeeds[i] !== prevCruiseSpeeds[i] &&
        currentCruiseSpeeds[i] > 0
      ) {
        changedIndex = i;
        break;
      }
    }

    // Update previous speeds
    prevCruiseSpeedsRef.current = [...currentCruiseSpeeds];

    // If a change was detected, update all terminals after the changed one
    if (changedIndex >= 0) {
      const changedSpeed = currentCruiseSpeeds[changedIndex];
      const changedOrder = watchedCruiseSpeeds[changedIndex].order;

      const updatedTerminals = watchedCruiseSpeeds.map((terminal) => {
        if (terminal.order >= changedOrder) {
          return { ...terminal, cruise_speed: changedSpeed };
        }
        return terminal;
      });

      setValue('terminals', updatedTerminals, { shouldDirty: true });
    }
  }, [watchedCruiseSpeeds, setValue]);

  const TerminalColumns = useMemo(
    () => [
      {
        Header: 'Terminal Name',
        accessor: 'name',
        enableSorting: false,
        enableColumnFilter: false,
        customStyle: {
          verticalAlign: 'top',
          width: '6.5rem',
        },
        cell: (row: any) => {
          return row.getValue() ? (
            <Truncate
              content={row.getValue()}
              tooltipContent={row.getValue()}
            />
          ) : (
            '-'
          );
        },
      },
      {
        Header: 'Terminal Type',
        accessor: 'type_name',
        enableSorting: false,
        enableColumnFilter: false,
        customStyle: {
          width: '120px',
        },
        cell: (row: any) => {
          return row.getValue() ? (
            <Truncate
              content={row.getValue()}
              tooltipContent={row.getValue()}
            />
          ) : (
            '-'
          );
        },
      },
      {
        Header: 'Address',
        accessor: 'address',
        enableSorting: false,
        enableColumnFilter: false,
        cell: (row: any) => {
          return row.getValue() ? (
            <Truncate
              content={row.getValue()}
              tooltipContent={row.getValue()}
            />
          ) : (
            '-'
          );
        },
      },
      {
        Header: 'Note',
        accessor: 'note',
        enableSorting: false,
        enableColumnFilter: false,
        customStyle: {
          width: '6.5rem',
        },
        cell: (row: any) => {
          return row.getValue() ? (
            <Truncate
              content={row.getValue()}
              tooltipContent={row.getValue()}
            />
          ) : (
            '-'
          );
        },
      },
      {
        Header: '',
        accessor: 'action',

        enableSorting: false,
        enableColumnFilter: false,
        notUseConfigTable: true,
        customStyle: { width: '6rem' },
        cell: (row: any) => {
          const cruiseSpeed =
            row?.row?.original.cruise_speed || defaultCruiseSpeed;

          let timeStopsCurrent = 0;

          if (row?.row?.original.time_stops) {
            const { value, unit } = convertValueToUnit(
              row?.row?.original.time_stops,
            );
            timeStopsCurrent = convertUnitTimeStopsToSeconds(value, unit);
          }

          // Check if this will be the first terminal
          const currentTerminalsLength = watch('terminals')?.length || 0;
          const isFirstTerminal = currentTerminalsLength === 0;

          // Use TAKEOFF command for first terminal, WAYPOINT for others
          const commandToUse = isFirstTerminal ? defaultTakeoffCMD : defaultCMD;

          const terminal = {
            terminal_id: row?.row?.original.id,
            name: row?.row?.original.name,
            stop: false,
            order: currentTerminalsLength + 1,
            longitude: row?.row?.original.longitude || 0,
            latitude: row?.row?.original.latitude || 0,
            altitude: row?.row?.original.altitude || 0,
            time_stops: timeStopsCurrent,
            for_robot: false,
            is_temp: false,
            cruise_speed: cruiseSpeed,
            operating_altitude: 10,
            command: {
              command_terminal: commandToUse,
              frame_1: 0,
              frame_2: 0,
              frame_3: 0,
              frame_4: 0,
              altitude: 0,
            },
            frame: defaultFrame,
            // takeoff_support: false,
          };
          const isAdded = watch('terminals')?.some(
            (item) => item.terminal_id === terminal.terminal_id,
          );
          return (
            <div>
              <CustomBtn
                type="button"
                label={isAdded ? t('Remove') : t('Add')}
                variant="outline"
                color={isAdded ? 'secondary' : 'primary'}
                size="sm"
                style={{ width: '6rem' }}
                onClick={() => handleToggleTerminal(terminal)}
              />
            </div>
          );
        },
      },
    ],
    [watch, setValue, defaultCMD, defaultTakeoffCMD, defaultFrame, t], // eslint-disable-line react-hooks/exhaustive-deps
  );

  // Watch form values
  const nameSearch = watch('name_search');
  const addressSearch = watch('address_search');

  const handleRemoveTerminal = useCallback(
    (terminal_id: string | number) => {
      // First remove the terminal
      const updatedTerminals = watch('terminals')?.filter(
        (item) => item.terminal_id !== terminal_id,
      );

      // Then update the order values to be sequential
      const reorderedTerminals = updatedTerminals?.map((terminal, index) => ({
        ...terminal,
        order: index + 1,
      }));

      setValue('terminals', reorderedTerminals, { shouldDirty: true });
    },
    [watch, setValue],
  );

  const handleGetListTerminals = useCallback(
    async ({
      pageSize,
      currentPage,
      objSearch,
    }: {
      pageSize: number;
      currentPage: number;
      objSearch: any;
    }) => {
      const { data, totalItem, totalPage } = await getListDockingStation({
        pageSize: pageSize,
        currentPage: currentPage,
        objSearch: objSearch,
        active: true,
      });

      setData({
        data: data,
        totalItem: totalItem,
        totalPage: totalPage,
      });
    },
    [getListDockingStation],
  );

  const handleSearchTerminal = useCallback(() => {
    setObjSearch((prev) => ({
      ...prev,
      searchParams: [
        {
          id: 'name',
          value: nameSearch === '' ? null : nameSearch,
        },
        {
          id: 'address',
          value: addressSearch === '' ? null : addressSearch,
        },
        {
          id: 'search_route',
          value: true,
        },
        ...(prev.searchParams || []).filter(
          (item) => !['name', 'address'].includes(item.id),
        ),
      ],
    }));
    setIsShowTable(true);
  }, [nameSearch, addressSearch]);

  useEffect(() => {
    if (pageSize && currentPage && !isEmptyObject(objSearch)) {
      handleGetListTerminals({
        pageSize: pageSize,
        currentPage: currentPage,
        objSearch: objSearch,
      });
    }
  }, [pageSize, currentPage, objSearch]);

  // Watch all time_stops fields to trigger recalculation when they change
  const watchedTerminals = useWatch({
    control,
    name: 'terminals',
    defaultValue: terminals || [],
  });

  // Memoize updated terminals calculation
  const updatedTerminals = useMemo(() => {
    const currentTerminals = watchedTerminals || terminals;
    if (!currentTerminals || currentTerminals.length === 0) return [];

    return currentTerminals.map((terminal, index) => ({
      ...terminal,
      stop:
        index === 0 || index === currentTerminals.length - 1
          ? true
          : terminal.time_stops !== undefined &&
              parseInt(terminal.time_stops, 10) > 0
            ? true
            : false,
    }));
  }, [watchedTerminals, terminals]);

  // Memoize actual stops calculation
  const actualStops = useMemo(() => {
    return updatedTerminals.filter(
      (terminal) => terminal.time_stops && Number(terminal.time_stops) > 0,
    ).length;
  }, [updatedTerminals]);

  // Memoize distance and time calculations
  const { totalDistance, totalEstimated } = useMemo(() => {
    if (updatedTerminals.length <= 1) {
      return { totalDistance: 0, totalEstimated: { value: 0, unit: 's' } };
    }
    return convertEstimated(updatedTerminals, false);
  }, [updatedTerminals]);
  // }, [updatedTerminals, isReturn]);

  // Check if terminals need to be updated (avoid infinite loop)
  const shouldUpdateTerminals = useMemo(() => {
    if (!terminals || terminals.length === 0) return false;

    return !(
      terminals.length === updatedTerminals.length &&
      terminals.every(
        (term, index) => term.stop === updatedTerminals[index]?.stop,
      )
    );
  }, [terminals, updatedTerminals]);

  // Update terminals if needed
  useEffect(() => {
    if (shouldUpdateTerminals) {
      setValue('terminals', updatedTerminals, { shouldDirty: false });
    }
  }, [shouldUpdateTerminals, updatedTerminals, setValue]);

  // Update form values
  useEffect(() => {
    if (!terminals || terminals.length === 0) {
      setValue('total_stops', null);
      setValue('total_distance', '');
      setValue('estimated_time', '');
      return;
    }

    setValue('total_stops', actualStops);

    if (updatedTerminals.length > 1) {
      setValue('total_distance', `${totalDistance.toFixed(2)} km`, {
        shouldDirty: false,
      });
      setValue(
        'estimated_time',
        `${totalEstimated.value.toFixed(2)} ${totalEstimated.unit}`,
        {
          shouldDirty: false,
        },
      );
    } else {
      setValue('total_distance', '');
      setValue('estimated_time', '');
    }
  }, [
    terminals,
    actualStops,
    totalDistance,
    totalEstimated,
    updatedTerminals.length,
    watchedTerminals,
    setValue,
  ]);

  const createUniqueWaypointName = useCallback((terminals: Terminal[]) => {
    let index = 1;
    let name;
    const existingNames = new Set(terminals.map((point) => point.name));

    do {
      name = `Waypoint ${index}`;
      index++;
    } while (existingNames.has(name));

    return name;
  }, []);

  // Function to map command value to display name
  const mapCommandToName = useCallback(
    (commandValue: string | number): string => {
      const commandId =
        typeof commandValue === 'string'
          ? parseInt(commandValue, 10)
          : commandValue;

      if (commandId === 22) {
        // MAV_CMD_NAV_TAKEOFF
        return 'Takeoff';
      } else if (commandId === 20) {
        // MAV_CMD_NAV_RETURN_TO_LAUNCH
        return 'Return To Launch';
      } else if (commandId === 21) {
        // MAV_CMD_NAV_LAND
        return 'Land';
      } else if (commandId === 181) {
        // MAV_CMD_DO_SET_RELAY
        return 'Set relay';
      } else if (commandId === 182) {
        // MAV_CMD_DO_REPEAT_RELAY
        return 'Cycle relay';
      } else if (commandId === 183) {
        // MAV_CMD_DO_SET_SERVO
        return 'Set Servo';
      } else if (commandId === 2000) {
        // MAV_CMD_DO_DIGICAM_CONTROL
        return 'Camera Trigger';
      } else if (commandId === 208) {
        // MAV_CMD_DO_PARACHUTE
        return 'Trigger parachute';
      } else if (commandId === 211) {
        // MAV_CMD_DO_GRIPPER
        return 'Gripper Mechanism';
      } else {
        return 'Waypoint';
      }
    },
    [],
  );

  // Function to update terminal name based on command
  // Only updates name for temporary terminals (is_temp: true)
  const updateTerminalName = useCallback(
    (terminalIndex: number, commandValue: string | number) => {
      const terminalsCurrent = watch('terminals') || [];

      // Only update name for temporary terminals
      if (
        terminalsCurrent[terminalIndex] &&
        terminalsCurrent[terminalIndex].is_temp === true
      ) {
        const newName = mapCommandToName(commandValue);
        const updatedTerminals = [...terminalsCurrent];
        updatedTerminals[terminalIndex] = {
          ...updatedTerminals[terminalIndex],
          name: newName,
        };
        setValue('terminals', updatedTerminals, { shouldDirty: true });
      }
    },
    [watch, setValue, mapCommandToName],
  );

  const handleAddLocation = useCallback(
    (position: any) => {
      const terminalsCurrent = watch('terminals') || [];

      const cruiseSpeed =
        terminalsCurrent[terminalsCurrent.length - 1]?.cruise_speed ||
        defaultCruiseSpeed;

      const newWaypoint = {
        latitude: position.lat,
        longitude: position.lng,
        terminal_id: parseInt(Math.random().toString(36).substring(2, 15), 36),
        order: (terminalsCurrent?.length || 0) + 1,
        is_temp: true,
        stop: false,
        is_new: true,
        name: createUniqueWaypointName(terminalsCurrent),
        cruise_speed: cruiseSpeed,
        operating_altitude: 20,
        time_stops: 0,
        command: {
          command_terminal: defaultCMD,
          frame_1: 0,
          frame_2: 0,
          frame_3: 0,
          frame_4: 0,
          altitude: 0,
        },
        frame: defaultFrame,
        for_robot: false,
      };

      console.log('newWaypoint', newWaypoint);

      setValue('terminals', [...terminalsCurrent, newWaypoint], {
        shouldDirty: true,
      });
    },
    [
      watch,
      setValue,
      createUniqueWaypointName,
      defaultCMD,
      defaultFrame,
      defaultCruiseSpeed,
    ],
  );

  const [expandedItemIds, setExpandedItemIds] = useState<UniqueIdentifier[]>(
    [],
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

  const handleMarkerClick = useCallback(
    (marker: { lat: number; lng: number; name?: string }) => {
      const terminalsCurrent = watch('terminals') || [];
      // Find terminal by matching coordinates (with small tolerance for floating point comparison)
      const terminal = terminalsCurrent.find((term) => {
        const latDiff = Math.abs(term.latitude - marker.lat);
        const lngDiff = Math.abs(term.longitude - marker.lng);
        // Use a small tolerance (0.000001 degrees ≈ 0.1 meters)
        return latDiff < 0.000001 && lngDiff < 0.000001;
      });

      if (terminal) {
        // Expand the terminal
        toggleExpandItem(terminal.order);

        // Scroll to the terminal element after a short delay to ensure it's rendered
        setTimeout(() => {
          const terminalElement = document.querySelector(
            `[data-terminal-order="${terminal.order}"]`,
          );
          if (terminalElement) {
            terminalElement.scrollIntoView({
              behavior: 'smooth',
              block: 'center',
            });
          }
        }, 100);
      }
    },
    [watch, toggleExpandItem],
  );

  useEffect(() => {
    const handleValidation = async () => {
      if (terminals != null && terminals.length > 0) {
        await trigger(['terminals']);
      } else {
        await clearErrors(['terminals']);
      }
    };
    const timeoutId = setTimeout(handleValidation, 200);
    return () => clearTimeout(timeoutId);
  }, [terminals, clearErrors, trigger]);

  const lastTerminal = useMemo(
    () => (terminals && terminals?.length > 0 ? terminals?.length - 1 : null),
    [terminals],
  );

  console.log('defaultCMD', defaultCMD);

  return (
    <FormProvider {...methods}>
      <form
        onSubmit={handleSubmit(handleFormSubmit)}
        className="form-route"
      >
        <CustomBreadcrumb
          items={breadcrumbItems}
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
              label={t('Save')}
              type={!isValid ? 'button' : 'submit'}
              loading={isSubmitting}
              disabled={isSubmitting}
              onClick={async () => {
                if ((watch('terminals')?.length || 0) < 2) {
                  ToastTopHelper.warning(
                    t(
                      'You haven’t created a valid route yet. Please select at least two terminals to form a complete route before saving.',
                    ),
                  );
                } else {
                  if (!isValid) {
                    // If validation fails, find terminals with errors and expand them

                    if (errors.terminals && Array.isArray(errors.terminals)) {
                      const terminalsWithErrors: UniqueIdentifier[] = [];
                      errors.terminals.forEach((terminalErrors, index) => {
                        if (
                          terminalErrors &&
                          Object.keys(terminalErrors).length > 0
                        ) {
                          terminalsWithErrors.push(index + 1);
                        }
                      });

                      // Expand terminals that have validation errors
                      if (terminalsWithErrors.length > 0) {
                        setExpandedItemIds(terminalsWithErrors);
                      }
                    }

                    trigger();

                    console.log('errors', isValid, errors);
                    return;
                  }
                  // handleSubmit(onSubmit)();
                }
              }}
            />,
          ]}
        />
        <Main>
          <div className="form-container">
            <FormBlock>
              <div className="">
                <div className="form-grid">
                  {isRoleSuperuser ? (
                    <div className="form-grid">
                      <div className="grid-column-4">
                        <CustomInputHookForm
                          name="code"
                          label={t('route.id')}
                          disabled
                        />
                      </div>
                      <div className="grid-column-4">
                        <PaginationSelect
                          required
                          label={t('Group')}
                          name="group"
                          control={control}
                          loadOptions={getOptionsByModel({
                            name_modal: 'usergroup',
                            search_field: 'name',
                            key: 'name',
                            value: 'id',
                          })}
                          placeholder={t('Select')}
                        />
                      </div>
                    </div>
                  ) : (
                    <CustomInputHookForm
                      name="code"
                      label={t('route.id')}
                      disabled
                    />
                  )}

                  <div className="d-flex gap-3">
                    <div className="flex-grow-1">
                      <CustomInputHookForm
                        required
                        name="name"
                        label={t('Name')}
                      />
                    </div>
                    {/* <div className="align-content-center mt-4">
                    <CustomSwitchBtn
                      name="two_way"
                      control={control}
                      label={t('Return?')}
                      isHorizontal
                    />
                  </div> */}
                  </div>
                </div>

                <div
                  style={{
                    display: 'grid',
                    gap: '12px',
                    gridTemplateColumns: '1fr 1fr 2fr',
                    marginTop: '1rem',
                  }}
                >
                  <PaginationSelect
                    required
                    label={t('Service')}
                    name="service"
                    control={control}
                    loadOptions={getOptionsByModel({
                      name_modal: 'routeService',
                      search_field: 'name',
                      key: 'name',
                      value: 'id',
                    })}
                    placeholder={t('Select')}
                  />
                  <CustomInputHookForm
                    name="total_stops"
                    label="Total Stops"
                    disabled
                  />
                  <CustomInputHookForm
                    name="total_distance"
                    label="Total Distance"
                    disabled
                  />
                </div>
                <div
                  style={{
                    display: 'grid',
                    gap: '12px',
                    gridTemplateColumns: '1fr 1fr',
                    marginTop: '1rem',
                  }}
                >
                  <CustomInputHookForm
                    name="estimated_time"
                    label="Estimated Time"
                    disabled
                  />
                  <CustomInputHookForm
                    name="note"
                    label="Note"
                  />
                </div>
              </div>
            </FormBlock>
            <Box
              sx={{
                display: 'grid',
                gap: '12px',
                gridTemplateColumns:
                  data?.data?.length > 0 ||
                  (watch('terminals')?.length || 0) > 0
                    ? '3fr 2fr'
                    : '1fr',
              }}
            >
              <FormBlock>
                <Typography
                  variant="body1"
                  style={{ marginBottom: '0.875rem' }}
                  sx={{
                    color: Colors.Gray5,
                  }}
                >
                  {t(
                    'Please search by name or select the city, district, or ward below to find terminals and add them to your route.',
                  )}
                </Typography>
                <div className="d-flex gap-3 ">
                  <div className="d-flex gap-3 w-100">
                    <div style={{ width: '100%' }}>
                      <CustomInputHookForm
                        name="name_search"
                        placeholder={t('Search by Name')}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            handleSearchTerminal();
                          }
                        }}
                      />
                    </div>
                    <div style={{ width: '100%' }}>
                      <CustomInputHookForm
                        name="address_search"
                        placeholder={t('Search by Address')}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            handleSearchTerminal();
                          }
                        }}
                      />
                    </div>
                    <CustomBtn
                      label={t('Search')}
                      variant="outline"
                      color="primary"
                      type="button"
                      onClick={() => handleSearchTerminal()}
                      style={{ width: '12rem', height: '2.975rem' }}
                    />
                  </div>
                </div>
                {isShowTable &&
                  (data?.data?.length > 0 ||
                  (watch('terminals')?.length || 0) > 0 ? (
                    <div>
                      <div
                        style={{
                          marginTop: '1.244rem',
                          marginBottom: '0.933rem',
                          fontSize: '1rem',
                          fontWeight: 600,
                        }}
                      >
                        {t('Available Terminals')}
                      </div>
                      <CustomizableTable
                        notShowSelectRow
                        useSystemSetting
                        columns={TerminalColumns}
                        data={data}
                        objSearch={objSearch}
                        setObjSearch={setObjSearch}
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
                      />
                    </div>
                  ) : (
                    <div>
                      <div
                        style={{
                          marginTop: '1.244rem',
                          marginBottom: '0.933rem',
                          fontSize: '1rem',
                          fontWeight: 600,
                        }}
                      >
                        {t('Available Terminals')}
                      </div>
                      <span style={{ color: Colors.Gray5, fontSize: '1rem' }}>
                        {t('No results found.')}
                      </span>
                    </div>
                  ))}
              </FormBlock>
              {(data?.data?.length > 0 ||
                (watch('terminals')?.length || 0) > 0) && (
                <FormBlock>
                  <Typography
                    sx={{
                      fontFamily: 'Inter',
                      fontWeight: 600,
                      fontSize: '1rem',
                    }}
                  >
                    {t('Selected Terminals (Drag to reorder)')}
                  </Typography>

                  <div style={{ marginTop: '12px', marginBottom: '16px' }}>
                    {(watch('terminals')?.length || 0) > 0 ? (
                      <SortableList
                        items={watch('terminals') || []}
                        onChange={(items) => {
                          const updatedItems = items?.map((item, index) => {
                            // Determine which command to use based on position
                            const isFirstTerminal = index === 0;
                            // Check if current command was manually set (not default)
                            const commandData = item.command as any;
                            const currentCommandId =
                              commandData?.command_terminal?.value;
                            const isManuallySetCommand =
                              currentCommandId &&
                              currentCommandId !== defaultCMD?.value &&
                              currentCommandId !== defaultTakeoffCMD?.value;

                            // For first terminal: always use defaultTakeoffCMD
                            // For other terminals: keep manually set command if exists, otherwise use defaultCMD
                            let commandToUse;
                            if (isFirstTerminal) {
                              commandToUse = defaultTakeoffCMD;
                            } else {
                              // If command was manually set, keep it
                              if (
                                isManuallySetCommand &&
                                commandData?.command_terminal
                              ) {
                                commandToUse = commandData.command_terminal;
                              } else {
                                commandToUse = defaultCMD;
                              }
                            }

                            // Check if command is changing
                            const isCommandChanging =
                              commandToUse &&
                              currentCommandId !== commandToUse?.value;

                            return {
                              ...item,
                              order: index + 1,
                              for_robot:
                                index === items.length - 1
                                  ? false
                                  : item.for_robot,
                              // Update command based on position and manual settings
                              command: commandToUse
                                ? isCommandChanging
                                  ? {
                                      // Command is changing - reset all frames
                                      command_terminal: commandToUse,
                                      frame_1: 0,
                                      frame_2: 0,
                                      frame_3: 0,
                                      frame_4: 0,
                                      altitude: 0,
                                    }
                                  : {
                                      // Command same but update reference
                                      ...item.command,
                                      command_terminal: commandToUse,
                                    }
                                : item.command, // Keep existing if no commandToUse
                            };
                          });

                          setValue('terminals', updatedItems, {
                            shouldDirty: true,
                            shouldValidate: false, // Don't trigger validation on reorder
                          });

                          // Clear validation errors for terminals after reorder
                          setTimeout(() => {
                            clearErrors('terminals');
                          }, 0);
                        }}
                        renderItem={(item) => {
                          const isExpanded = expandedItemIds.includes(
                            item.order,
                          );

                          return (
                            <SortableList.Item id={item.order}>
                              <div
                                className="dropdown-terminal"
                                data-terminal-order={item.order}
                              >
                                <div
                                  className="dropdown-terminal__header"
                                  style={{
                                    borderBottom: isExpanded
                                      ? `1px solid ${theme === 'dark' ? '#444646' : '#E0E0E0'}`
                                      : 'none',
                                  }}
                                >
                                  <SortableList.DragHandle />
                                  <Box sx={{ flex: 1 }}>
                                    <Truncate
                                      content={`${item.order}. ${item.name}`}
                                      maxLengthContent={35}
                                      tooltipContent={`${item.order}. ${item.name}`}
                                    />
                                  </Box>
                                  <span
                                    onClick={() => {
                                      {
                                        toggleExpandItem(item.order);
                                      }
                                    }}
                                    className="dropdown-terminal__icon"
                                    style={{
                                      transform: isExpanded
                                        ? 'rotate(90deg)'
                                        : '',
                                    }}
                                  >
                                    <GearIcon
                                      color={`${
                                        isExpanded
                                          ? Colors.Primary
                                          : theme === 'dark'
                                            ? 'var(--ga-dark-theme-font-color)'
                                            : 'var( --ga-light-theme-font-color)'
                                      }`}
                                    />
                                  </span>
                                  <IoTrashOutline
                                    className="cursor-pointer"
                                    onClick={() =>
                                      handleRemoveTerminal(item.terminal_id)
                                    }
                                    color={`${
                                      theme === 'dark'
                                        ? 'var(--ga-dark-theme-font-color)'
                                        : 'var( --ga-light-theme-font-color)'
                                    }`}
                                    size={16}
                                  />
                                </div>
                                {isExpanded && (
                                  <div className="dropdown-terminal__content">
                                    <div
                                      style={{
                                        gridColumn: 'span 2',
                                        display: 'grid',
                                        gridTemplateColumns: '1fr 1fr 1fr',
                                      }}
                                    >
                                      <span>
                                        {t('Robot Line')}
                                        <ConfigProvider
                                          theme={{
                                            components: {
                                              Switch: {
                                                colorPrimary: Colors.Primary,
                                              },
                                            },
                                          }}
                                        >
                                          <Switch
                                            className={`custom-switch-disabled ${theme}`}
                                            style={{
                                              marginLeft: '8px',
                                              marginRight: '27px',
                                            }}
                                            disabled={
                                              item.order - 1 === lastTerminal
                                            }
                                            checked={
                                              item.order !==
                                              (watch('terminals')?.length || 0)
                                                ? item.for_robot
                                                : false
                                            }
                                            onChange={(checked) =>
                                              onChangeForRobot(
                                                checked,
                                                item.terminal_id,
                                              )
                                            }
                                          />
                                        </ConfigProvider>
                                      </span>
                                    </div>
                                    <div
                                      style={{
                                        gridColumn: 'span 2',
                                      }}
                                    >
                                      <CustomInputHookForm
                                        label={t('Cruise Speed (m/s)')}
                                        name={`terminals.${item.order - 1}.cruise_speed`}
                                        type="number"
                                        placeholder={t('Cruise Speed (m/s)')}
                                        required
                                      />
                                    </div>
                                    <CustomInputHookForm
                                      label={t('Operating Altitude (m)')}
                                      name={`terminals.${item.order - 1}.operating_altitude`}
                                      type="number"
                                      placeholder={t('Operating Altitude (m)')}
                                      required
                                      disabled={
                                        isEdit
                                          ? (
                                              terminals?.[item.order - 1]
                                                ?.command as
                                                | {
                                                    command_terminal?: {
                                                      value?: number;
                                                    };
                                                  }
                                                | undefined
                                            )?.command_terminal?.value !== 22
                                          : false
                                      }
                                      onKeyDown={(e) => {
                                        const allowedKeys = [
                                          'Backspace',
                                          'Delete',
                                          'ArrowLeft',
                                          'ArrowRight',
                                          'Tab',
                                        ];
                                        if (e.ctrlKey || e.metaKey) {
                                          return;
                                        }
                                        const value = e.currentTarget.value;
                                        const hasDot = value.includes('.');
                                        if (
                                          (e.key >= '0' && e.key <= '9') ||
                                          (e.key === '.' && !hasDot) ||
                                          allowedKeys.includes(e.key)
                                        ) {
                                          return;
                                        }
                                        e.preventDefault();
                                      }}
                                    />
                                    <CustomInputHookForm
                                      label={t('Hold Time (s)')}
                                      name={`terminals.${item.order - 1}.time_stops`}
                                      placeholder={t('Hold Time (s)')}
                                      required
                                      onChange={(e) => {
                                        const value = e.target.value;
                                        // Two-way binding: Update Param 1 when Hold Time changes
                                        setValue(
                                          `terminals.${item.order - 1}.command.frame_1`,
                                          value ? Number(value) : 0,
                                          { shouldDirty: true },
                                        );
                                      }}
                                      onKeyDown={(e) => {
                                        const allowedKeys = [
                                          'Backspace',
                                          'Delete',
                                          'ArrowLeft',
                                          'ArrowRight',
                                          'Tab',
                                        ];
                                        if (e.ctrlKey || e.metaKey) {
                                          return;
                                        }
                                        const value = e.currentTarget.value;
                                        const hasDot = value.includes('.');
                                        if (
                                          (e.key >= '0' && e.key <= '9') ||
                                          (e.key === '.' && !hasDot) ||
                                          allowedKeys.includes(e.key)
                                        ) {
                                          return;
                                        }
                                        e.preventDefault();
                                      }}
                                    />
                                    <PaginationSelect
                                      label={t('Command')}
                                      required
                                      name={`terminals.${item.order - 1}.command.command_terminal`}
                                      control={control}
                                      loadOptions={getOptionsCMD()}
                                      handleDroneChange={(value) => {
                                        // Update terminal name when command changes
                                        if (
                                          value &&
                                          typeof value === 'object' &&
                                          'value' in value
                                        ) {
                                          updateTerminalName(
                                            item.order - 1,
                                            value.value,
                                          );
                                        }
                                      }}
                                      placeholder={t('Select')}
                                    />
                                    <PaginationSelect
                                      label={t('Frame')}
                                      required
                                      name={`terminals.${item.order - 1}.frame`}
                                      control={control}
                                      loadOptions={getOptionsFrame()}
                                      placeholder={t('Select')}
                                    />
                                    <CustomInputHookForm
                                      label={t('Param 1')}
                                      name={`terminals.${item.order - 1}.command.frame_1`}
                                      type="number"
                                      placeholder={t('Param 1')}
                                      required
                                      onChange={(e) => {
                                        const value = e.target.value;
                                        // Two-way binding: Update Hold Time when Param 1 changes
                                        setValue(
                                          `terminals.${item.order - 1}.time_stops`,
                                          value ? Number(value) : 0,
                                          { shouldDirty: true },
                                        );
                                      }}
                                      onKeyDown={(e) => {
                                        const allowedKeys = [
                                          'Backspace',
                                          'Delete',
                                          'ArrowLeft',
                                          'ArrowRight',
                                          'Tab',
                                        ];
                                        if (e.ctrlKey || e.metaKey) {
                                          return;
                                        }
                                        const value = e.currentTarget.value;
                                        const hasDot = value.includes('.');
                                        if (
                                          (e.key >= '0' && e.key <= '9') ||
                                          (e.key === '.' && !hasDot) ||
                                          allowedKeys.includes(e.key)
                                        ) {
                                          return;
                                        }
                                        e.preventDefault();
                                      }}
                                    />
                                    <CustomInputHookForm
                                      label={t('Param 2')}
                                      name={`terminals.${item.order - 1}.command.frame_2`}
                                      type="number"
                                      placeholder={t('Param 2')}
                                      required
                                      onKeyDown={(e) => {
                                        const allowedKeys = [
                                          'Backspace',
                                          'Delete',
                                          'ArrowLeft',
                                          'ArrowRight',
                                          'Tab',
                                        ];
                                        if (e.ctrlKey || e.metaKey) {
                                          return;
                                        }
                                        const value = e.currentTarget.value;
                                        const hasDot = value.includes('.');
                                        if (
                                          (e.key >= '0' && e.key <= '9') ||
                                          (e.key === '.' && !hasDot) ||
                                          allowedKeys.includes(e.key)
                                        ) {
                                          return;
                                        }
                                        e.preventDefault();
                                      }}
                                    />
                                    <CustomInputHookForm
                                      label={t('Param 3')}
                                      name={`terminals.${item.order - 1}.command.frame_3`}
                                      type="number"
                                      placeholder={t('Param 3')}
                                      required
                                      onKeyDown={(e) => {
                                        const allowedKeys = [
                                          'Backspace',
                                          'Delete',
                                          'ArrowLeft',
                                          'ArrowRight',
                                          'Tab',
                                        ];
                                        if (e.ctrlKey || e.metaKey) {
                                          return;
                                        }
                                        const value = e.currentTarget.value;
                                        const hasDot = value.includes('.');
                                        if (
                                          (e.key >= '0' && e.key <= '9') ||
                                          (e.key === '.' && !hasDot) ||
                                          allowedKeys.includes(e.key)
                                        ) {
                                          return;
                                        }
                                        e.preventDefault();
                                      }}
                                    />
                                    <CustomInputHookForm
                                      label={t('Param 4')}
                                      name={`terminals.${item.order - 1}.command.frame_4`}
                                      type="number"
                                      placeholder={t('Param 4')}
                                      required
                                      onKeyDown={(e) => {
                                        const allowedKeys = [
                                          'Backspace',
                                          'Delete',
                                          'ArrowLeft',
                                          'ArrowRight',
                                          'Tab',
                                        ];
                                        if (e.ctrlKey || e.metaKey) {
                                          return;
                                        }
                                        const value = e.currentTarget.value;
                                        const hasDot = value.includes('.');
                                        if (
                                          (e.key >= '0' && e.key <= '9') ||
                                          (e.key === '.' && !hasDot) ||
                                          allowedKeys.includes(e.key)
                                        ) {
                                          return;
                                        }
                                        e.preventDefault();
                                      }}
                                    />
                                    <CustomInputHookForm
                                      name={`terminals.${item.order - 1}.latitude`}
                                      label={t('Param5/Latitude/X')}
                                      type="decimal"
                                      onKeyDown={(e) => {
                                        const allowedKeys = [
                                          'Backspace',
                                          'Delete',
                                          'ArrowLeft',
                                          'ArrowRight',
                                          'Tab',
                                        ];
                                        if (e.ctrlKey || e.metaKey) {
                                          return;
                                        }
                                        const value = e.currentTarget.value;
                                        const hasDot = value.includes('.');
                                        if (
                                          (e.key >= '0' && e.key <= '9') ||
                                          (e.key === '.' && !hasDot) ||
                                          allowedKeys.includes(e.key)
                                        ) {
                                          return;
                                        }
                                        e.preventDefault();
                                      }}
                                    />
                                    <CustomInputHookForm
                                      name={`terminals.${item.order - 1}.longitude`}
                                      label={t('Param6/Longitude/Y')}
                                      type="decimal"
                                      onKeyDown={(e) => {
                                        const allowedKeys = [
                                          'Backspace',
                                          'Delete',
                                          'ArrowLeft',
                                          'ArrowRight',
                                          'Tab',
                                        ];
                                        if (e.ctrlKey || e.metaKey) {
                                          return;
                                        }
                                        const value = e.currentTarget.value;
                                        const hasDot = value.includes('.');
                                        if (
                                          (e.key >= '0' && e.key <= '9') ||
                                          (e.key === '.' && !hasDot) ||
                                          allowedKeys.includes(e.key)
                                        ) {
                                          return;
                                        }
                                        e.preventDefault();
                                      }}
                                    />
                                    <div style={{ gridColumn: 'span 2' }}>
                                      <CustomInputHookForm
                                        name={`terminals.${item.order - 1}.command.altitude`}
                                        label={t('Param7/Altitude/Z')}
                                        type="decimal"
                                        onKeyDown={(e) => {
                                          const allowedKeys = [
                                            'Backspace',
                                            'Delete',
                                            'ArrowLeft',
                                            'ArrowRight',
                                            'Tab',
                                          ];

                                          if (e.ctrlKey || e.metaKey) {
                                            return;
                                          }

                                          const value = e.currentTarget.value;
                                          const hasDot = value.includes('.');
                                          const hasMinus = value.includes('-');

                                          // Allow numbers
                                          if (e.key >= '0' && e.key <= '9') {
                                            return;
                                          }

                                          // Allow one dot
                                          if (e.key === '.' && !hasDot) {
                                            return;
                                          }

                                          // Allow minus ONLY at first position and only one time
                                          if (
                                            e.key === '-' &&
                                            !hasMinus &&
                                            value.length === 0
                                          ) {
                                            return;
                                          }

                                          if (allowedKeys.includes(e.key)) {
                                            return;
                                          }

                                          e.preventDefault();
                                        }}
                                      />
                                    </div>
                                  </div>
                                )}
                              </div>
                            </SortableList.Item>
                          );
                        }}
                      />
                    ) : (
                      <span style={{ color: Colors.Gray5, fontSize: '1rem' }}>
                        {t('No terminal selected.')}
                      </span>
                    )}
                  </div>
                  <div className="d-flex flex-column mt-4">
                    <span
                      style={{
                        marginBottom: '16px',
                        fontSize: '1rem',
                        fontWeight: 600,
                      }}
                    >
                      {t('Map')}
                    </span>

                    <div
                      style={{
                        height: 'auto',
                        width: '100%',
                        objectFit: 'cover',
                        borderRadius: '8px',
                      }}
                    >
                      <MapForRouteUnified
                        markerData={
                          terminals && terminals.length > 0
                            ? terminals?.map((terminal) => ({
                                lat: terminal.latitude,
                                lng: terminal.longitude,
                                name: terminal.name,
                                for_robot: terminal.for_robot,
                              }))
                            : []
                        }
                        useAddLocation={true}
                        handleAddLocation={handleAddLocation}
                        onMarkerClick={handleMarkerClick}
                      />
                    </div>
                  </div>
                </FormBlock>
              )}
            </Box>
          </div>
        </Main>
      </form>
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
    </FormProvider>
  );
};

export default FormRoute;
