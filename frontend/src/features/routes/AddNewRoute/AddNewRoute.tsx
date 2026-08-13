import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { ToastTopHelper } from 'rj-core';

import { CustomRoutes } from '@/services/API';

import FormRoute from '../components/FormRoute';
import { ConvertCommandInput, ConvertFrameInput } from '../editRoute/EditRoute';
import useAPI, { FormDataSubmitRoute, Terminal } from '../useAPI/useAPI';
import { generateMapImage } from '../utils/generateMapImage';

export default function AddNewRoute() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { addNewRouteAPI } = useAPI();

  const handleSubmit = useCallback(
    async (data: FormDataSubmitRoute) => {
      const formData = {
        name: data.name,
        code: data.code,
        group_id: data.group?.value || null,
        route_service_id: data.service?.value || null,
        note: data.note,
        total_distance: data.total_distance,
        estimated_time: data.estimated_time,
        total_stops: data.total_stops,
        // two_way: data.two_way,
        terminals: data.terminals.map((terminal: Terminal) => {
          if (terminal.is_temp && terminal.is_new) {
            return {
              stop: false,
              order: terminal.order,
              latitude: terminal.latitude,
              longitude: terminal.longitude,
              name: terminal.name,
              for_robot: terminal.for_robot || false,
              cruise_speed: terminal.cruise_speed + ' m/s',
              operating_altitude: terminal.operating_altitude + ' m',
              altitude: terminal.altitude || 0,
              command_line: ConvertCommandInput(terminal),
              time_stops: terminal.time_stops + ' s',
              frame: ConvertFrameInput(terminal || {}),
            };
          }
          return {
            terminal_id: terminal.terminal_id,
            stop: terminal.stop,
            order: terminal.order,
            for_robot: terminal.for_robot || false,
            cruise_speed: terminal.cruise_speed + ' m/s',
            operating_altitude: terminal.operating_altitude + ' m',
            latitude: terminal.latitude || "",
            longitude: terminal.longitude || "",
            altitude: terminal.altitude || 0,
            command_line: ConvertCommandInput(terminal || {}),
            time_stops: terminal.time_stops + ' s',
            frame: ConvertFrameInput(terminal || {}),
          };
        }),
      };

      const mapImageBlob = await generateMapImage(
        formData.terminals.map((terminal) => ({
          lat: terminal.latitude,
          lng: terminal.longitude,
        })),
      );

      const mapImageBlobHorizontal = await generateMapImage(
        formData.terminals.map((terminal) => ({
          lat: terminal.latitude,
          lng: terminal.longitude,
        })),
        {
          width: '800px',
        },
      );

      const bodyFormData = new FormData();
      bodyFormData.append('data', JSON.stringify(formData));
      // Gửi blob dưới dạng binary file
      bodyFormData.append('img_map', mapImageBlob as Blob, 'map.png');

      bodyFormData.append(
        'img_route',
        mapImageBlobHorizontal as Blob,
        'map_horizontal.png',
      );

      const { success, message } = await addNewRouteAPI(bodyFormData);
      if (success) {
        navigate(CustomRoutes.routes.path);
        ToastTopHelper.success(message);
      } else {
        ToastTopHelper.error(message);
      }
    },
    [addNewRouteAPI, navigate],
  );

  const handleCancel = () => {
    navigate(CustomRoutes.routes.path);
  };

  return (
    <FormRoute
      onSubmit={handleSubmit}
      onCancel={handleCancel}
      breadcrumbItems={[{ url: '/routes' }, { text: t('Add New Route') }]}
    />
  );
}
