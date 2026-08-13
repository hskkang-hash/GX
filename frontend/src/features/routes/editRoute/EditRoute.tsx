import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { ToastTopHelper } from 'rj-core';

import { CustomRoutes } from '@/services/API';
import { formatWithUnit } from '@/utils/utils';

import FormRoute, { FormDataRoute, Terminal } from '../components/FormRoute';
import { useZustandRoutes } from '../stores/useZustandRoutes';
import useAPI from '../useAPI/useAPI';
import { useRoute } from '../useAPI/useRoute';
import { generateMapImage } from '../utils/generateMapImage';

interface RouteData {
  id: number;
  name: string;
  code: string;
  group__id: number;
  group__name: string;
  route_service_id?: number | string | null;
  route_service__name?: string;
  route_service?: { id?: number | string; name?: string } | number | string | null;
  note?: string;
  total_distance?: any;
  estimated_time?: any;
  terminals: Terminal[];
  two_way: boolean;
}

export const ConvertCommandOutput = (
  command: Record<string, string | number | null | undefined> | undefined,
  defaultCMD: {
    label: string;
    value: string;
  } | null,
) => {
  if (!command) {
    return {
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
      frame_1: (values?.[0] as number) ?? 0,
      frame_2: (values?.[1] as number) ?? 0,
      frame_3: (values?.[2] as number) ?? 0,
      frame_4: (values?.[3] as number) ?? 0,
      altitude: (values?.[6] as number) ?? 0,
    };
  } catch (error) {
    return {
      command_terminal: defaultCMD,
      frame_1: 0,
      frame_2: 0,
      frame_3: 0,
      frame_4: 0,
      altitude: 0,
    };
  }
};

export const ConvertCommandInput = (terminal: Terminal): object => {
  const values = [
    (terminal as any).command?.frame_1 || 0,
    (terminal as any).command?.frame_2 || 0,
    (terminal as any).command?.frame_3 || 0,
    (terminal as any).command?.frame_4 || 0,
    terminal.latitude,
    terminal.longitude,
    (terminal as any).command?.altitude || 0,
  ];

  const cmdValue =
    (terminal as any).command?.command_terminal?.value ?? '0';
  const cmdLabel =
    (terminal as any).command?.command_terminal?.label ?? 'WAYPOINT';

  const result = {
    [cmdValue as any]: {
      [cmdLabel as any]: values,
    },
  };

  return result;
};

export const ConvertFrameInput = (terminal: Terminal): object | null => {
  if (!terminal.frame) {
    return null;
  }

  const result = {
    [terminal.frame?.value]: terminal.frame?.label,
  };

  return result;
};

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
          label: String(frameObj),
          value: Number(frameId),
        }
      : defaultFrame;
  } catch (error) {
    return defaultFrame;
  }
};

const buildServiceOption = (
  route: RouteData | undefined,
): { label: string; value: number | string } | null => {
  if (!route) return null;

  const routeServiceObj =
    route.route_service && typeof route.route_service === 'object'
      ? route.route_service
      : undefined;

  const value =
    route.route_service_id ??
    routeServiceObj?.id ??
    (typeof route.route_service === 'string' ||
    typeof route.route_service === 'number'
      ? route.route_service
      : null);

  if (value === null || value === undefined) {
    return null;
  }

  const label =
    route.route_service__name ||
    routeServiceObj?.name ||
    String(value);

  return { label, value };
};

const EditRoute = () => {
  const { t } = useTranslation();
  const { id } = useParams();
  const navigate = useNavigate();
  const [initialData, setInitialData] = useState<FormDataRoute | undefined>(
    undefined,
  );
  const [defaultCMD, setDefaultCMD] = useState<{
    label: string;
    value: string;
  } | null>(null);
  const [defaultFrame, setDefaultFrame] = useState<{
    label: string;
    value: string;
  } | null>(null);
  const location = useLocation();
  const { getDetailRouteAPI, updateRouteAPI } = useAPI();
  const baselineTerminalsRef = useRef<Terminal[] | null>(null);

  const { getDefaultCMD, getDefaultFrame } = useRoute();

  const getDetailRoute = useCallback(
    async (id: number) => {
      const { success, data, message } = await getDetailRouteAPI(id);
      if (!success) {
        ToastTopHelper.error(message);
        return;
      }

      setInitialData({
        name: data.route.name,
        code: data.route.code,
        group: data.route.group__id
          ? { label: data.route?.group__name, value: data.route?.group__id }
          : null,
        service: buildServiceOption(data.route),
        note: data.route.note || '',
        total_distance:
          `${formatWithUnit({
            value: data.route.total_distance?.value || 0,
            unit: data.route.total_distance?.unit || '',
          })}` || '',
        estimated_time:
          `${formatWithUnit({
            value: data.route.estimated_time?.value || 0,
            unit: data.route.estimated_time?.unit || '',
          })}` || '',
        terminals: data.route_terminals.map(
          (stop: any, index: number) => ({
            route_terminal_id: (stop as any).route_terminal_id,
            terminal_id: stop.terminal_id,
            name: stop.name,
            stop: stop.stop || false,
            order: index + 1,
            longitude: stop.longitude,
            latitude: stop.latitude,
            time_stops: stop.time_stops,
            is_temp: (stop as any).terminal_type__name === 'Temp',
            for_robot: stop?.for_robot,
            cruise_speed: stop.cruise_speed,
            operating_altitude: stop.operating_altitude,
            // takeoff_support: stop.takeoff_support,
            command: ConvertCommandOutput(stop.command_line, defaultCMD) as any,
            frame: ConvertFrameOutput(stop.frame, defaultFrame),
            is_edit: true,
          }),
        ),
        // two_way: data.route.two_way || false,
      });
    },
    [defaultCMD, defaultFrame],
  );

  useEffect(() => {
    // Capture baseline terminals once for diff-based patch submission
    if (initialData?.terminals && !baselineTerminalsRef.current) {
      baselineTerminalsRef.current = initialData.terminals;
    }
  }, [initialData]);

  useEffect(() => {
    (async () => {
      const { options: cmdOptions } = await getDefaultCMD('WAYPOINT');
      setDefaultCMD(cmdOptions.length > 0 ? cmdOptions[0] : null);
      const { options: frameOptions } = await getDefaultFrame('GLOBAL');
      setDefaultFrame(frameOptions.length > 0 ? frameOptions[0] : null);
    })();
  }, []);

  // Check if location.state is null or undefined
  useEffect(() => {
    if (!location.state) {
      getDetailRoute(Number(id));
      return;
    }

    // Safely access the state after confirming it exists
    const { route, stops } = location.state as {
      route: RouteData;
      stops: any[];
    };

    if (route && stops) {
      setInitialData({
        name: route.name,
        group: route?.group__id
          ? { label: route?.group__name, value: route?.group__id }
          : null,
        service: buildServiceOption(route),
        code: route.code,
        note: route.note || '',
        total_distance:
          `${formatWithUnit({
            value: route.total_distance?.value || 0,
            unit: route.total_distance?.unit || '',
          })}` || '',
        estimated_time:
          `${formatWithUnit({
            value: route.estimated_time?.value || 0,
            unit: route.estimated_time?.unit || '',
          })}` || '',
        terminals: stops.map((stop: any) => ({
          route_terminal_id: stop.route_terminal_id,
          terminal_id: stop.terminal_id,
          name: stop.terminal_name,
          stop: stop.stop || false,
          order: stop.order,
          longitude: stop.lng,
          latitude: stop.lat,
          time_stops: stop.time_stops,
          is_temp: stop.is_temp,
          for_robot: stop?.for_robot,
          cruise_speed: stop.cruise_speed,
          operating_altitude: stop.operating_altitude,
          // takeoff_support: stop?.takeoff_support || false,
          command: ConvertCommandOutput(stop?.command_line, defaultCMD) as any,
          frame: ConvertFrameOutput(stop?.frame, defaultFrame),
          is_edit: true,
        })),
        // two_way: route.two_way || false,
      });
    }
  }, [location.state, navigate, t, defaultCMD, defaultFrame]);

  const handleSubmit = useCallback(
    async (data: FormDataRoute): Promise<void> => {
      const normalizeWithUnit = (v: unknown, unit: string) => {
        if (v === null || v === undefined) return null;
        const s = String(v).trim();
        if (!s) return null;
        return s.includes(unit) ? s : `${s} ${unit}`;
      };

      const buildPayloadForTerminal = (terminal: Terminal) => {
        const base = {
          stop: terminal.stop,
          order: terminal.order,
          latitude: terminal.latitude,
          longitude: terminal.longitude,
          for_robot: terminal.for_robot,
          time_stops: normalizeWithUnit(terminal.time_stops, 's'),
          cruise_speed: normalizeWithUnit(terminal.cruise_speed, 'm/s'),
          operating_altitude: normalizeWithUnit(terminal.operating_altitude, 'm'),
          command_line: ConvertCommandInput(terminal || {}),
          frame: ConvertFrameInput(terminal || {}),
        };

        if (terminal.is_temp && terminal.is_new) {
          return {
            ...base,
            name: terminal.name,
          };
        }

        return {
          ...base,
          terminal_id: terminal.terminal_id,
        };
      };

      const baseline = baselineTerminalsRef.current || [];
      const baselineByRtId = new Map<number, Terminal>();
      baseline.forEach((t) => {
        if (t.route_terminal_id) baselineByRtId.set(t.route_terminal_id, t);
      });

      const currentTerminals = data.terminals || [];
      const currentRtIds = new Set<number>();
      currentTerminals.forEach((t) => {
        if (t.route_terminal_id) currentRtIds.add(t.route_terminal_id);
      });

      const deleteIds = baseline
        .map((t) => t.route_terminal_id)
        .filter((id): id is number => Boolean(id) && !currentRtIds.has(id as number));

      const createItems = currentTerminals
        .filter((t) => !t.route_terminal_id)
        .map((t) => buildPayloadForTerminal(t));

      const updateItems: any[] = [];
      currentTerminals.forEach((t) => {
        if (!t.route_terminal_id) return;
        const base = baselineByRtId.get(t.route_terminal_id);
        if (!base) return;

        const currPayload = buildPayloadForTerminal(t) as Record<string, unknown>;
        const basePayload = buildPayloadForTerminal(base) as Record<string, unknown>;

        const keysToDiff = [
          'terminal_id',
          'stop',
          'order',
          'latitude',
          'longitude',
          'for_robot',
          'time_stops',
          'cruise_speed',
          'operating_altitude',
          'command_line',
          'frame',
        ];

        const patch: Record<string, unknown> = {
          route_terminal_id: t.route_terminal_id,
        };
        let changed = false;
        keysToDiff.forEach((k) => {
          if (!(k in currPayload)) return;
          const a = JSON.stringify(currPayload[k]);
          const b = JSON.stringify(basePayload[k]);
          if (a !== b) {
            patch[k] = currPayload[k];
            changed = true;
          }
        });

        if (changed) updateItems.push(patch);
      });

      const terminalsChanged =
        deleteIds.length > 0 || createItems.length > 0 || updateItems.length > 0;
      const mapNeedsUpdate =
        deleteIds.length > 0 ||
        createItems.length > 0 ||
        updateItems.some((u) =>
          ['order', 'latitude', 'longitude', 'terminal_id'].some((k) => k in u),
        );

      const formData = {
        name: data.name,
        code: data.code,
        group_id: data.group?.value || null,
        route_service_id: data.service?.value || null,
        note: data.note || '',
        total_distance: data.total_distance || '',
        total_stops: data.total_stops,
        estimated_time: data.estimated_time || '',
        // two_way: data.two_way || false,
        terminals_patch: {
          create: createItems.length > 0 ? createItems : undefined,
          update: updateItems.length > 0 ? updateItems : undefined,
          delete: deleteIds.length > 0 ? deleteIds : undefined,
        },
      };

      const coordsForMap = currentTerminals.map((terminal) => ({
        lat: terminal.latitude,
        lng: terminal.longitude,
      }));

      const bodyFormData = new FormData();
      bodyFormData.append('data', JSON.stringify(formData));

      if (mapNeedsUpdate) {
        const mapImageBlob = await generateMapImage(coordsForMap);
        const mapImageBlobHorizontal = await generateMapImage(coordsForMap, {
          width: '800px',
        });

        // Gửi blob dưới dạng binary file
        bodyFormData.append('img_map', mapImageBlob as Blob, 'map.png');
        bodyFormData.append(
          'img_route',
          mapImageBlobHorizontal as Blob,
          'map_horizontal.png',
        );
      }

      const { success, message } = await updateRouteAPI(
        Number(id),
        bodyFormData,
      );

      if (success) {
        navigate(
          CustomRoutes.routes.subRoutes.detailRoute.path.replace(
            ':id',
            id || '',
          ),
        );
        ToastTopHelper.success(message);
      } else {
        ToastTopHelper.error(message);
      }
    },
    [updateRouteAPI, navigate, id],
  );

  const handleCancel = () => {
    navigate(
      CustomRoutes.routes.subRoutes.detailRoute.path.replace(':id', id || ''),
    );
  };

  return (
    <FormRoute
      initialData={initialData}
      onSubmit={handleSubmit}
      onCancel={handleCancel}
      isEdit={true}
      breadcrumbItems={[
        {
          url: CustomRoutes.routes.subRoutes.detailRoute.path.replace(
            ':id',
            id || '',
          ),
        },
        { text: t('Edit Route') },
      ]}
    />
  );
};

export default EditRoute;
