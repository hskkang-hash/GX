import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { ToastTopHelper } from 'rj-core';

import { CustomRoutes } from '@/services/API';

import FormDockingStation from './components/FormDockingStation';
import useDockingStation from './hooks/useDockingStation';
import dayjs from 'dayjs';
import { useConvertDate } from '../Dashboard/utils/formatDateTime';

export default function RegisterDockingStation() {
  const { t } = useTranslation();
  const { dateFormat } = useConvertDate();
  const navigate = useNavigate();
  const { createDockingStation } = useDockingStation();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (data: any) => {
    console.log("data_form_docking_station", data);
    setLoading(true);
    const formattedData = {
      group_id: data.group?.value || null,
      code: data.code,
      name: data.name,
      terminal_type_ids: data.terminal_type_ids.map((item: any) => item.value),
      function_ids: [data.function_ids.value],
      manufacturer: data.manufacturer,
      year_of_manufacture: data.year_of_manufacture
        ? typeof data.year_of_manufacture === 'string'
          ? data.year_of_manufacture
          : data.year_of_manufacture.format('YYYY')
        : null,
      latitude: data.latitude,
      longitude: data.longitude,
      street_address: data.street_address,
      full_address: data.full_address,
      city_province: data.city_province,
      city_county_district: data.city_county_district,
      ward_town_township: data.ward_town_township,
      postal_code: data.postal_code,
      manager_name: data.manager_name,
      url: data.url,
      note: data.note,
      avatar: data.avatar,
      delete_avatar: data.delete_avatar,
      address_note: data.address_note,
      time_stops: `${data.time_stops.value} ${data.time_stops.unit}`,
      compatible_drone: data.compatible_drone,
      swap_time: data.swap_time,
      temperature_range:
        data.temperature_range.from?.value && data.temperature_range.to?.value
          ? `${data.temperature_range.from?.value} to ${data.temperature_range.to?.value
          } ${data.temperature_range?.from.unit}`
          : null,
      weight: `${data.weight.value} ${data.weight.unit}`,
      weather_resistant: data?.weather_resistant,
      operating_times: data?.operating_times?.map((item: any) => ({
        day_of_week_id: item?.day_of_week_id,
        is_active: item?.is_active,
        start_time: item?.start_time,
        end_time: item?.end_time,
      })),
      exceptions: data?.exceptions?.map((item: any) => ({
        exception_date: item?.exception_date,
        start_time: item?.start_time,
        end_time: item?.end_time,
        is_all_day: item?.is_all_day,
        reason: item?.reason,
      })),
    };
    console.log({ formattedData });
    const { success, message } = await createDockingStation(formattedData);
    if (success) {
      setLoading(false);
      ToastTopHelper.success(message);
      navigate(CustomRoutes.dockingStation.path);
    } else {
      setLoading(false);
      ToastTopHelper.error(message);
    }
  };
  const handleCancel = () => {
    navigate(CustomRoutes.dockingStation.path);
  };

  return (
    <FormDockingStation
      loading={loading}
      onSubmit={handleSubmit}
      onCancel={handleCancel}
      breadcrumbItems={[
        { url: CustomRoutes.dockingStation.path },
        { text: t('Register') },
      ]}
      isEdit={false}
    />
  );
}
