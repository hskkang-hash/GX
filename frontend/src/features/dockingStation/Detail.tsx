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
import FormDockingStation, { FormData } from './components/FormDockingStation';
import useDockingStation from './hooks/useDockingStation';
import dayjs from 'dayjs';
import 'dayjs/locale/ko';
import 'dayjs/locale/th';
import useCommonAPI from '../useCommonAPI/useAPI';
import { useConvertDate } from '../Dashboard/utils/formatDateTime';

export default function Detail() {
  const { id } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [dockingStationDetail, setDockingStationDetail] = useState<FormData | null>(null);
  const { getDetailDockingStation, updateDockingStation } = useDockingStation();
  const { configGroupSystem } = useConfigGroupSystem();
  const isEmptyConfigGroupSystem =
    !configGroupSystem || Object.keys(configGroupSystem).length === 0;
  const isGoogleMap =
    configGroupSystem?.use_map?.select_map?.google_map || false;



  const userInfo = useUserInfo();
  const [configSystem] = useConfigSystem();
  const unitPreferences =
    configSystem && configSystem['system_default_formats'];
  const dateFormat = userInfo?.settings?.date_format__code ?? unitPreferences?.date_format ?? 'YYYY/MM/DD';
  const { timeFormat } = useConvertDate();
  const { convertDateFormatToUTC } = useConvertDate();

  const handleEdit = () => {
    setIsEditMode(true);
  };

  const handleSubmit = async (data: any) => {
    setLoading(true);
    const oldFunctionIds = data.temp_function_ids?.find(
      (item: any) => item.function_type === 'docking_station',
    ).value;
    const existFunction =
      data.temp_function_ids
        .filter((item: any) => item.value !== oldFunctionIds)
        ?.map((item: any) => item.value) || [];
    const newFunctionIds = [...existFunction, Number(data.function_ids.value)];
    const formattedData = {
      code: data.code,
      name: data.name,
      group_id: data.group?.value || null,
      terminal_type_ids: data.terminal_type_ids.map((item: any) => item.value),
      function_ids: newFunctionIds,
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
      time_stops: `${data?.time_stops?.value} ${data?.time_stops?.unit}`,
      compatible_drone: data.compatible_drone,
      swap_time: data.swap_time,
      temperature_range:
        data.temperature_range.from?.value && data.temperature_range.to?.value
          ? `${data.temperature_range.from?.value} to ${data.temperature_range.to?.value
          } ${data.temperature_range.from.unit}`
          : null,
      weight: `${data.weight.value} ${data.weight.unit}`,
      weather_resistant: data?.weather_resistant,
      operating_times: data?.operating_times?.map((item: any) => ({
        day_of_week_id: item?.day_of_week_id,
        is_active: item?.is_active,
        start_time: item?.start_time,
        end_time: item?.end_time
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

    const { success, message } = await updateDockingStation(formattedData, id);
    if (success) {
      setLoading(false);
      ToastTopHelper.success(message);
      fetchDockingStationDetail(Number(id));
      // setIsEditMode(false);
      navigate(CustomRoutes.dockingStation.path);
    } else {
      setLoading(false);
      ToastTopHelper.error(message);
    }
  };


  const { getDayOfWeek } = useCommonAPI();

  const [isDirtyEdit, setIsDirtyEdit] = useState<boolean>(false);

  const fetchDockingStationDetail = async (id: number) => {
    const { success, message, data } = await getDetailDockingStation(id);

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
    if (success) {
      const dockingDetail = {
        code: data?.code,
        name: data?.name,
        group: data?.group__id
          ? {
            value: data?.group__id,
            label: data?.group__name,
          }
          : null,
        terminal_type_ids: data?.terminal_types?.map((item: any) => ({
          value: item?.id,
          label: item?.name,
          code: item?.code,
        })),
        function_ids: data?.functions
          ?.filter((item: any) => item.function_type === 'docking_station')
          .map((item: any) => ({
            value: item?.id,
            label: item?.name,
            function_type: item?.function_type,
          }))[0],
        temp_function_ids: data?.functions?.map((item: any) => ({
          value: item?.id,
          label: item?.name,
          function_type: item?.function_type,
        })),
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
        time_stops: {
          value: data?.time_stops?.value,
          unit: data?.time_stops?.unit,
        },
        compatible_drone: data?.compatible_drone || '',
        swap_time: data?.swap_time || null,
        temperature_range: {
          from: {
            value: data?.temperature_range?.min || null,
            unit: data?.temperature_range?.unit || '°C',
          },
          to: {
            value: data?.temperature_range?.max || null,
            unit: data?.temperature_range?.unit || '°C',
          },
        },
        weight: {
          value: data?.weight?.value || null,
          unit: data?.weight?.unit || 'kg',
        },
        weather_resistant: data?.weather_resistant || '',
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
      };
      setDockingStationDetail(dockingDetail);
    }
  };

  useEffect(() => {
    if (id) {
      fetchDockingStationDetail(Number(id));
    }
  }, [id]);


  return (
    <>
      <FormDockingStation
        initialData={dockingStationDetail}
        loading={loading}
        onSubmit={handleSubmit}
        onCancel={() => navigate(CustomRoutes.dockingStation.path)}
        breadcrumbItems={[
          { url: CustomRoutes.dockingStation.path },
          { text: t('Edit') },
        ]}
        isEdit={true}
        isDirtyEdit={isDirtyEdit}
        setIsDirtyEdit={setIsDirtyEdit}
      />
    </>
  );
}
