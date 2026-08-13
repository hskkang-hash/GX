import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { ToastTopHelper } from 'rj-core';

import { CustomRoutes } from '@/services/API';

import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import FormTerminalsV2 from '../components/FormTerminalV2';
import useAPI from '../useAPI/useAPI';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';
import dayjs from 'dayjs';

export default function AddNewTerminals() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { createTerminalAPI } = useAPI();
  const [loading, setLoading] = useState(false);
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const { dateFormat } = useConvertDate();
  const handleSubmit = async (data: any) => {
    setLoading(true);

    const formattedData = isRoleSuperuser
      ? {
        code: data?.code,
        name: data?.name,
        group_id: data?.group?.value,
        terminal_type_ids: data?.terminal_type_ids?.map((item: any) =>
          Number(item?.value),
        ),
        function_ids: data?.function_ids?.map((item: any) =>
          Number(item?.value),
        ),
        postal_code: data?.postal_code,
        time_stops: `${data?.time_stops?.value} ${data?.time_stops?.unit}`,
        manager_name: data?.manager_name,
        manufacturer: data?.manufacturer,
        year_of_manufacture: data?.year_of_manufacture,
        url: data?.url,
        note: data?.note,
        latitude: data?.latitude,
        longitude: data?.longitude,
        city_province: data?.city_province,
        city_county_district: data?.city_county_district,
        ward_town_township: data?.ward_town_township,
        street_address: data?.street_address || '',
        full_address: data?.full_address,
        address_note: data?.address_note,
        avatar: data?.avatar,
        terminal_purpose_id: data?.terminal_purpose_id?.value,
        purpose_type_id: data?.purpose_type_id?.value,
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
      }
      : {
        code: data?.code,
        name: data?.name,
        terminal_type_ids: data?.terminal_type_ids?.map((item: any) =>
          Number(item?.value),
        ),
        function_ids: data?.function_ids?.map((item: any) =>
          Number(item?.value),
        ),
        postal_code: data?.postal_code,
        time_stops: `${data?.time_stops?.value} ${data?.time_stops?.unit}`,
        manager_name: data?.manager_name,
        manufacturer: data?.manufacturer,
        year_of_manufacture: data?.year_of_manufacture,
        url: data?.url,
        note: data?.note,
        latitude: data?.latitude,
        longitude: data?.longitude,
        city_province: data?.city_province,
        city_county_district: data?.city_county_district,
        ward_town_township: data?.ward_town_township,
        street_address: data?.street_address || '',
        full_address: data?.full_address,
        address_note: data?.address_note,
        avatar: data?.avatar,
        terminal_purpose_id: data?.terminal_purpose_id?.value,
        purpose_type_id: data?.purpose_type_id?.value,
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
    console.log('formattedData', formattedData);
    const { success, message } = await createTerminalAPI(formattedData);
    if (success) {
      setLoading(false);
      ToastTopHelper.success(message);
      navigate(CustomRoutes.terminals.path);
    } else {
      setLoading(false);
      ToastTopHelper.error(message);
    }
  };

  const handleCancel = () => {
    navigate(CustomRoutes.terminals.path);
  };

  return (
    <FormTerminalsV2
      loading={loading}
      onSubmit={handleSubmit}
      onCancel={handleCancel}
      breadcrumbItems={[
        { url: CustomRoutes.terminals.path },
        { text: t('Add New Terminal') },
      ]}
    />
  );
}
