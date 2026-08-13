import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { ToastTopHelper, useConfigGroupSystem, useConfigSystem, useUserInfo } from 'rj-core';
import i18n from 'i18next';

import { CustomRoutes } from '@/services/API';

import {
  formatFullAddressFromFields,
  formatFullAddressFromFieldsGoogle,
} from '../terminals/hooks/utils';
import FormInfrastruture from './components/FormInfrastruture';
import useInfrastructure from './hooks/useInfrastructure';
import dayjs from 'dayjs';
import 'dayjs/locale/ko';
import 'dayjs/locale/th';
import useCommonAPI from '../useCommonAPI/useAPI';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';

export default function Detail() {
  const { id } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [infrastructureDetail, setInfrastructureDetail] = useState<FormData>(null);
  const { getDetailInfrastructure, updateInfrastructure } = useInfrastructure();
  const { configGroupSystem } = useConfigGroupSystem();
  const isEmptyConfigGroupSystem =
    !configGroupSystem || Object.keys(configGroupSystem).length === 0;
  const isGoogleMap =
    configGroupSystem?.use_map?.select_map?.google_map || false;
  const { dateFormat } = useConvertDate();
  const handleSubmit = async (data: any) => {
    setLoading(true);
    const formattedData = {
      code: data.code,
      name: data.name,
      group_id: data?.group?.value,
      terminal_type_id: data?.terminal_type_id?.value,
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
      city_province: data.city_province,
      city_county_district: data.city_county_district,
      ward_town_township: data.ward_town_township,
      postal_code: data.postal_code,
      purpose_type_id: data.purpose_type_id.value,
      manager_name: data.manager_name,
      url: data.url,
      note: data.note,
      avatar: data.avatar,
      delete_avatar: data.delete_avatar,
      address_note: data.address_note,
      operating_times: data.operating_times.map((item: any) => ({
        day_of_week_id: item?.day_of_week_id,
        is_active: item?.is_active,
        start_time: item?.start_time,
        end_time: item?.end_time,
      })),
      exceptions: data?.exceptions?.map((item: any) => {
        let date = dayjs(item.exception_date);
        if (!date.isValid()) {
          date = dayjs(item.exception_date, dateFormat);
        }
        return {
          exception_date: date.isValid() ? date.format("YYYY-MM-DD") : "",
          start_time: item.start_time,
          end_time: item.end_time,
          is_all_day: item.is_all_day,
          reason: item.reason,
          id: item.id,
        };
      })
    };
    const { success, message } = await updateInfrastructure(formattedData, id);
    if (success) {
      setLoading(false);
      ToastTopHelper.success(message);
      fetchInfrastructureDetail(Number(id));
      navigate(CustomRoutes.infrastructure.path);
    } else {
      setLoading(false);
      ToastTopHelper.error(message);
    }
  };

  const { getDayOfWeek } = useCommonAPI();

  const { timeFormat } = useConvertDate();
  const fetchInfrastructureDetail = async (id: number) => {
    const { success, message, data } = await getDetailInfrastructure(id);

    let dayOfWeekData = [];
    if (!data?.operating_times || data?.operating_times?.length === 0) {
      const { data: dow, status, message: msg } = await getDayOfWeek();
      if (!status) {
        console.log('Error fetch day of week:', msg);
        ToastTopHelper.error(msg);
        return;
      }
      dayOfWeekData = dow;
    }

    console.log('data_infrastructure_detail', data);

    if (success) {
      const formattedData = {
        code: data?.code,
        name: data?.name,
        group: data?.group__id
          ? {
            value: data?.group__id,
            label: data?.group__name,
          }
          : null,
        terminal_purpose_id: data?.terminal_purpose_id,
        purpose_type_id: data?.purpose_type_id,
        terminal_type_ids: data?.terminal_types.map((item: any) => ({
          value: item?.id,
          label: item?.name,
          code: item?.code,
        })),
        function_ids: data?.functions?.map((item: any) => ({
          value: item?.id,
          label: item?.name,
          function_type: item?.function_type,
        }))[0],
        latitude: data?.latitude,
        longitude: data?.longitude,
        city_province: data?.city_province,
        city_county_district: data?.city_county_district,
        ward_town_township: data?.ward_town_township,
        street_address: data?.street_address,
        full_address:
          isGoogleMap || isEmptyConfigGroupSystem
            ? formatFullAddressFromFieldsGoogle({
              street_address: data?.street_address,
              ward_town_township: data?.ward_town_township,
              city_county_district: data?.city_county_district,
              city_province: data?.city_province,
            })
            : formatFullAddressFromFields({
              city_province: data?.city_province,
              city_county_district: data?.city_county_district,
              ward_town_township: data?.ward_town_township,
              street_address: data?.street_address,
            }),
        note: data?.note,
        postal_code: data?.postal_code,
        manufacturer: data?.manufacturer,
        year_of_manufacture: data?.year_of_manufacture,
        manager_name: data?.manager_name,
        url: data?.url,
        avatar: data?.avatar__file_url,
        address_note: data?.address_note,
        operating_times: data?.operating_times?.length > 0 ? data?.operating_times.map((item: any) => ({
          day_of_week_id: item?.day_of_week_id,
          is_active: item?.is_active,
          start_time: item?.start_time || null,
          end_time: item?.end_time || null,
          name: item?.day_of_week,
        })) : dayOfWeekData?.map((item: any) => ({
          day_of_week_id: item?.day_of_week_id,
          is_active: false,
          start_time: null,
          end_time: null,
          name: item.name,
        })),
        exceptions: data?.exceptions.map((item: any) => ({
          exception_date: item?.exception_date,
          start_time: item?.start_time,
          end_time: item?.end_time,
          is_all_day: item?.is_all_day,
          reason: item?.reason,
          id: item?.id,
        })),
      };
      setInfrastructureDetail(formattedData);
    }
  };
  useEffect(() => {
    if (id) {
      fetchInfrastructureDetail(id);
    }
  }, [id]);

  console.log('infrastructureDetail', infrastructureDetail);

  return (
    <>
      {/* {isEditMode ? ( */}
      <FormInfrastruture
        initialData={infrastructureDetail}
        loading={loading}
        onSubmit={handleSubmit}
        onCancel={() => navigate(CustomRoutes.infrastructure.path)}
        breadcrumbItems={[
          { url: CustomRoutes.infrastructure.path },
          { text: t('Edit') },
        ]}
        isEdit={true}
      />
    </>
  );
}
