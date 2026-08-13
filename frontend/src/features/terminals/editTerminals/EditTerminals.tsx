import i18n from 'i18next';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { ToastTopHelper, useConfigGroupSystem, useConfigSystem, useUserInfo } from 'rj-core';
import { CustomRoutes } from '@/services/API';
import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import FormTerminalsV2 from '../components/FormTerminalV2';
import {
  formatFullAddressFromFields,
  formatFullAddressFromFieldsGoogle,
} from '../hooks/utils';
import useAPI from '../useAPI/useAPI';
import dayjs from 'dayjs';
import 'dayjs/locale/ko';
import 'dayjs/locale/th';
import { FormData } from '../components/FormTerminalV2.d';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';

const EditTerminals = () => {
  const { t } = useTranslation();
  const { id } = useParams();
  const navigate = useNavigate();
  const [initialData, setInitialData] = useState<FormData | null>(null);
  const [isDirtyEdit, setIsDirtyEdit] = useState<boolean>(false);
  const { updateTerminalAPI, getDetailTerminalAPI } = useAPI();


  const userInfo = useUserInfo();
  const [configSystem] = useConfigSystem();
  const unitPreferences =
    configSystem && configSystem['system_default_formats'];
  const dateFormat = userInfo?.settings?.date_format__code ?? unitPreferences?.date_format ?? 'YYYY/MM/DD';
  const { timeFormat } = useConvertDate();
  console.log('dateFormat', dateFormat);

  const isRoleSuperuser = CheckRoleAccount('superuser');

  const { configGroupSystem } = useConfigGroupSystem();
  const isGoogleMap =
    configGroupSystem?.use_map?.select_map?.google_map || false;
  const isEmptyConfigGroupSystem =
    !configGroupSystem || Object.keys(configGroupSystem).length === 0;
  const handleSubmit = async (data: any) => {
    const formattedData = isRoleSuperuser
      ? {
        code: data.code,
        name: data.name,
        group_id: data.group?.value || null,
        terminal_type_ids: data?.terminal_type_ids?.map((item: any) =>
          Number(item?.value),
        ),
        function_ids: data?.function_ids?.map((item: any) => item?.value),
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
        avatar: data.avatar,
        delete_avatar: data.avatar ? false : true,
        terminal_purpose_id: data?.terminal_purpose_id?.value || null,
        purpose_type_id: data?.purpose_type_id?.value || null,
        operating_times: data?.operating_times?.map((item: any) => ({
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
      }
      : {
        code: data.code,
        name: data.name,
        terminal_type_ids: data?.terminal_type_ids?.map((item: any) =>
          Number(item?.value),
        ),
        function_ids: data?.function_ids?.map((item: any) => item?.value),
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
        avatar: data.avatar,
        delete_avatar: data.avatar ? false : true,
        terminal_purpose_id: data?.terminal_purpose_id?.value || null,
        purpose_type_id: data?.purpose_type_id?.value || null,
        operating_times: data?.operating_times?.map((item: any) => ({
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
    console.log('formattedData', formattedData);
    const { success, message } = await updateTerminalAPI(
      Number(id),
      formattedData,
    );
    if (success) {
      ToastTopHelper.success(message);
      navigate(CustomRoutes.terminals.path);
    } else {
      ToastTopHelper.error(message);
    }
  };

  const handleCancel = () => {
    navigate(CustomRoutes.terminals.path.replace(':id', id || ''));
  };

  const { getDayOfWeek } = useCommonAPI();


  useEffect(() => {
    const fetchData = async () => {
      if (!id) return;
      const { success, data, message } = await getDetailTerminalAPI(Number(id));

      let dayOfWeekData = [];
      if (!data.operating_times || data.operating_times.length === 0) {
        const { data: dow, status, message: msg } = await getDayOfWeek();
        if (!status) {
          console.log('Error fetch day of week:', msg);
          ToastTopHelper.error(msg);
          return;
        }
        dayOfWeekData = dow;
      }

      if (success && data) {
        setInitialData({
          code: data.code,
          name: data.name || '',
          terminal_type_ids:
            data?.terminal_types?.length > 0
              ? data?.terminal_types?.map((item: any) => ({
                label: t(item.name),
                value: item.id,
                code: item.code,
              }))
              : [],
          terminal_purpose_id: {
            label: t(data?.terminal_purpose__name),
            value: data?.terminal_purpose_id,
          },
          purpose_type_id: {
            label: t(data?.purpose_type__name),
            value: data?.purpose_type_id,
          },
          function_ids:
            data?.functions?.length > 0
              ? data?.functions?.map((item: any) => ({
                label: item.name_translations?.[i18n.language] || item.name,
                value: item.id,
                function_type: item.function_type,
              }))
              : [],
          time_stops: {
            value: data?.time_stops?.value || null,
            unit: data?.time_stops?.unit || 'mins',
          },
          group: {
            label: data?.group__name,
            value: data?.group__id,
          },
          address_type: 'geographic_coordinates',
          latitude: data.latitude || null,
          longitude: data.longitude || null,
          city_province: data.city_province,
          city_county_district: data.city_county_district,
          ward_town_township: data.ward_town_township,
          street_address: data.street_address,
          full_address:
            isGoogleMap || isEmptyConfigGroupSystem
              ? formatFullAddressFromFieldsGoogle({
                street_address: data?.street_address,
                ward_town_township: data?.ward_town_township,
                city_county_district: data?.city_county_district,
                city_province: data?.city_province,
              })
              : formatFullAddressFromFields({
                city_province: data.city_province,
                city_county_district: data.city_county_district,
                ward_town_township: data.ward_town_township,
                street_address: data.street_address,
              }),
          address_note: data.address_note || '',
          postal_code: data.postal_code || '',
          manager_name: data.manager_name || '',
          manufacturer: data.manufacturer || '',
          year_of_manufacture: data.year_of_manufacture || '',
          url: data.url || '',
          note: data.note || '',
          avatar: data.avatar__file_url,
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
          exceptions: (data?.exceptions || []).map((item: any) => ({
            exception_date: item?.exception_date,
            start_time: item?.start_time,
            end_time: item?.end_time,
            is_all_day: item?.is_all_day,
            reason: item?.reason,
            id: item?.id,
          })),
        });
      } else {
        ToastTopHelper.error(message);
        setInitialData(null);
      }
    };

    fetchData();
  }, [id]);

  return (
    <FormTerminalsV2
      initialData={initialData}
      onSubmit={handleSubmit}
      onCancel={handleCancel}
      title={t('Edit Packaging Specification')}
      breadcrumbItems={[
        { url: CustomRoutes.terminals.path },
        { text: t('Edit') },
      ]}
      isDirtyEdit={isDirtyEdit}
      setIsDirtyEdit={setIsDirtyEdit}
      editMode={true}
    />
  );
};

export default EditTerminals;
