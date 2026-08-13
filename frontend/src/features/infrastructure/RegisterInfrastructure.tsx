import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { ToastTopHelper } from 'rj-core';
import { CustomRoutes } from '@/services/API';
import FormInfrastruture from './components/FormInfrastruture';
import useInfrastructure from './hooks/useInfrastructure';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';
import dayjs from 'dayjs';

export default function RegisterInfrastructure() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { createInfrastructure } = useInfrastructure();
  const [loading, setLoading] = useState(false);
  const [isDirtyEdit, setIsDirtyEdit] = useState(false);
  const { dateFormat } = useConvertDate();
  const handleSubmit = async (data: any) => {
    setLoading(true);
    const formattedData = {
      code: data.code,
      name: data.name,
      group_id: data.group?.value,
      // terminal_type_id: data.terminal_type_id.value,
      // infrastructure_type_id: data.infrastructure_type_id.value,
      terminal_purpose_id: Number(data.terminal_purpose_id.value),
      terminal_type_ids: data.terminal_type_ids.map((item: any) => item.value),
      function_ids: [Number(data.function_ids.value)],
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
      address: data.full_address,
      city_province: data.city_province,
      city_county_district: data.city_county_district,
      ward_town_township: data.ward_town_township,
      postal_code: data.postal_code,
      address_note: data.address_note,
      purpose_type_id: Number(data.purpose_type_id.value),
      manager_name: data.manager_name,
      url: data.url,
      note: data.note,
      avatar: data.avatar,
      delete_avatar: data.delete_avatar,
      operating_times: data.operating_times.map((item: any) => ({
        day_of_week_id: item?.day_of_week_id,
        is_active: item?.is_active,
        start_time: item?.start_time,
        end_time: item?.end_time,
      })),
      exceptions: data.exceptions.map((item: any) => ({
        exception_date: item?.exception_date,
        start_time: item?.start_time,
        end_time: item?.end_time,
        is_all_day: item?.is_all_day,
        reason: item?.reason,
      })),
    };
    const { success, message } = await createInfrastructure(formattedData);

    if (success) {
      setLoading(false);
      ToastTopHelper.success(message);
      navigate(CustomRoutes.infrastructure.path);
    } else {
      setLoading(false);
      ToastTopHelper.error(message);
    }
  };

  const handleCancel = () => {
    navigate(CustomRoutes.infrastructure.path);
  };

  return (
    <FormInfrastruture
      loading={loading}
      onSubmit={handleSubmit}
      onCancel={handleCancel}
      breadcrumbItems={[
        { url: CustomRoutes.infrastructure.path },
        { text: t('Register') },
      ]}
      setIsDirtyEdit={setIsDirtyEdit}
      isDirtyEdit={isDirtyEdit}
    />
  );
}
