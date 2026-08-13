import { yupResolver } from '@hookform/resolvers/yup';
import { Box } from '@mui/material';
import i18n from 'i18next';
import { useEffect, useMemo, useRef, useState } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { Trans, useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ActionBtn,
  Container,
  CustomBreadcrumb,
  CustomBtn,
  CustomModal,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useConfigGroupSystem,
  useConfigSystem,
  useLoadingContext,
  useUserInfo,
} from 'rj-core';
import UnitInput from '@/components/Form/UnitInput';
import PaginationSelect from '@/components/selects/PaginationSelect';
import FormRegister from '@/features/DeliveryHubs/components/FormRegister';
import {
  formatFullAddressFromFields,
  formatFullAddressFromFieldsGoogle,
} from '@/features/terminals/hooks/utils';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { useFormNavigationBlocker } from '@/hooks/useFormNavigationBlocker';
import { CustomRoutes } from '@/services/API';
import { formRegisterDeliveryHubs } from '@/services/schemaForm';

import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import { useDeliveryHubs } from '../hooks/useDeliveryHubs';
import { FormRegisterData } from '../types/IDeliveryHubs';
import dayjs from 'dayjs';
import 'dayjs/locale/ko';
import 'dayjs/locale/th';
import { OperatingTimeData } from '@/components/HelperCellOperatingTime';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';

export const EditDeliveryHubs = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const isFetchingRef = useRef(false);
  const { id } = useParams<{ id: string }>();
  const { getDetailDeliveryHubsAPI, updateDeliveryHubsAPI } = useDeliveryHubs();
  const { getFunctionTypes, getOptionsByModel } = useCommonAPI();
  const { configGroupSystem } = useConfigGroupSystem();
  const isGoogleMap =
    configGroupSystem?.use_map?.select_map?.google_map || false;
  const isEmptyConfigGroupSystem =
    !configGroupSystem || Object.keys(configGroupSystem).length === 0;
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const methods = useForm<FormRegisterData>({
    resolver: yupResolver(formRegisterDeliveryHubs(t, isRoleSuperuser)) as any,
    defaultValues: {},
  });

  const userInfo = useUserInfo();
  const [configSystem] = useConfigSystem();
  const unitPreferences =
    configSystem && configSystem['system_default_formats'];
  const dateFormat = userInfo?.settings?.date_format__code ?? unitPreferences?.date_format ?? 'YYYY/MM/DD';
  const { timeFormat } = useConvertDate();
  const [operatingTimes, setOperatingTimes] = useState<OperatingTimeData[]>();
  const [operatingTimeErrors, setOperatingTimeErrors] = useState<any>({});

  const [detailData, setDetailData] = useState<FormRegisterData>();

  const {
    handleSubmit,
    reset,
    watch,
    control,
    setValue,
    formState: { isValid, isSubmitting, isDirty },
  } = methods;
  useEffect(() => {
    const getTerminalCodeIdForFunction = async () => {
      try {
        const loadOptions = getOptionsByModel({
          name_modal: 'terminalType',
        });
        const result = await loadOptions('', [], { page: 1 });
        setValue('terminal_type_ids_docking', [
          result.options.find((item: any) => item.code === 'DOCKING_STATION'),
        ]);
      } catch (error) {
        console.error('Failed to fetch options:', error);
      }
    };
    getTerminalCodeIdForFunction();
  }, []);

  const { getDayOfWeek } = useCommonAPI();

  useEffect(() => {
    const fetchDetail = async () => {
      if (!id || isFetchingRef.current) return;
      try {
        isFetchingRef.current = true;
        const response = await getDetailDeliveryHubsAPI(Number(id));
        if (!response.success) {
          navigate(CustomRoutes.deliveryHubs.path);
          return;
        }

        const data = response.data;
        const deliveryHubType = data.functions?.find(
          (item: any) => item.function_type === 'delivery_hub',
        );
        const dockingStationType = data.functions?.find(
          (item: any) => item.function_type === 'docking_station',
        );

        const currentTerminalTypeIdsDocking = watch(
          'terminal_type_ids_docking',
        );

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

        const formData: FormRegisterData = {
          code: data.code,
          name: data.name,
          avatar: data.avatar__file_url || null,
          group: data.group__id
            ? {
              value: data.group__id,
              label: data.group__name,
            }
            : null,
          terminal_type_ids:
            data.terminal_types
              ?.filter((item: any) => item.code === 'DELIVERY_HUB')
              .map((item: any) => ({
                label: item.name,
                value: item.id,
                code: item.code,
              })) || [],
          function_ids: deliveryHubType
            ? {
              label:
                deliveryHubType.name_translations?.[i18n.language] ||
                deliveryHubType.name,
              value: deliveryHubType.id,
              function_type: deliveryHubType.function_type,
            }
            : null,
          is_docking_station: !!dockingStationType,
          manager: data.manager_name || '',
          address:
            isGoogleMap || isEmptyConfigGroupSystem
              ? formatFullAddressFromFieldsGoogle({
                street_address: data.street_address,
                ward_town_township: data.ward_town_township,
                city_county_district: data.city_county_district,
                city_province: data.city_province,
              })
              : formatFullAddressFromFields({
                city_province: data.city_province,
                city_county_district: data.city_county_district,
                ward_town_township: data.ward_town_township,
                street_address: data.street_address,
              }),
          city_province: data.city_province,
          city_county_district: data.city_county_district,
          ward_town_township: data.ward_town_township,
          street_address: data.street_address,
          latitude: data.latitude,
          longitude: data.longitude,
          postal_code: data.postal_code,
          url: data.url || '',
          note: data.note || '',
          address_note: data.address_note || '',
          time_stops: data.time_stops || { value: null, unit: 'mins' },
          temp_function_ids:
            data.functions?.map((item: any) => ({
              label: item.name,
              value: item.id,
              function_type: item.function_type,
            })) || [],
          temp_terminal_type_ids:
            data.terminal_types?.map((item: any) => ({
              label: item.name,
              value: item.id,
              function_type: item.function_type,
            })) || [],
          terminal_type_ids_docking: currentTerminalTypeIdsDocking || null,
          function_ids_docking: null,
          delete_avatar: false,
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
        setDetailData(formData);
        reset(formData);
      } catch (err) {
        console.error('Error fetching detail delivery hub', err);
      } finally {
        isFetchingRef.current = false;
      }
    };

    fetchDetail();
  }, [id, reset, navigate]);

  const temp_function_ids = watch('temp_function_ids');
  const isHaveDocking = (temp_function_ids?.length || 0) > 1;
  const { showLoading, hideLoading } = useLoadingContext();

  const onCancel = () => {
    navigate(CustomRoutes.deliveryHubs.path);
  };


  const isOperatingTimesEdited = useMemo(() => {
    return JSON.stringify(operatingTimes) !==
      JSON.stringify(detailData?.operating_times);
  }, [operatingTimes, detailData?.operating_times]);

  const [clickSave, setClickSave] = useState(false);
  const { showModal, setShowModal, handleModalSave, handleModalCancel } =
    useFormNavigationBlocker({
      isDirty: clickSave == false && (isDirty || isOperatingTimesEdited),
      onSave: async () => {
        const data = watch();
        await handleFormSubmit(data);
        reset(data, {
          keepDirty: false,
          keepValues: true,
        });
      },
      onCancel,
      handleSubmit,
    });

  const handleFormSubmit = async (formData: any) => {
    const data = {
      ...formData,
      operating_times: operatingTimes,
    }
    showLoading();
    setClickSave(true);
    try {
      const oldFunctionId = data.temp_function_ids?.find(
        (item: any) => item.function_type === 'delivery_hub',
      )?.value;
      const updatedFunctionIdss = data.is_docking_station
        ? [
          ...(data.temp_function_ids || []).filter(
            (item: any) => item.value !== oldFunctionId,
          ),
          data.function_ids,
        ].map((item: any) => item.value)
        : [data.function_ids?.value];

      const updatedFunctionIds = [];
      if (data.is_docking_station && !isHaveDocking) {
        const deliveryHubFunction = data.function_ids?.value;
        const dockingFunction = data.function_ids_docking?.value;

        if (deliveryHubFunction) {
          updatedFunctionIds.push(deliveryHubFunction);
        }
        if (dockingFunction) {
          updatedFunctionIds.push(dockingFunction);
        }
      } else {
        if (data.function_ids?.value) {
          updatedFunctionIds.push(data.function_ids.value);
        }
      }

      let terminalTypeIds = [];
      if (data.is_docking_station && !isHaveDocking) {
        terminalTypeIds.push(Number(data.temp_terminal_type_ids?.[0]?.value));
        terminalTypeIds.push(
          Number(data.terminal_type_ids_docking?.[0]?.value),
        );
      } else if (data.is_docking_station && isHaveDocking) {
        terminalTypeIds = (data.temp_terminal_type_ids || []).map(
          (item: any) => item.value,
        );
      } else {
        terminalTypeIds = (data.terminal_type_ids || []).map(
          (item: any) => item.value,
        );
      }

      const formattedData = {
        code: data.code,
        name: data.name,
        manager_name: data.manager || '',
        terminal_type_ids: terminalTypeIds,
        group_id: data.group?.value || null,
        function_ids:
          data.is_docking_station && isHaveDocking
            ? updatedFunctionIdss
            : updatedFunctionIds,
        city_province: data.city_province,
        city_county_district: data.city_county_district,
        ward_town_township: data.ward_town_township,
        street_address: data.street_address,
        latitude: data.latitude,
        longitude: data.longitude,
        postal_code: data.postal_code?.toString() || null,
        address_note: data.address_note || '',
        url: data.url || '',
        note: data.note || '',
        avatar: data.avatar || null,
        delete_avatar: data.avatar ? false : true,
        ...(data.is_docking_station && {
          time_stops: `${data.time_stops?.value} ${data.time_stops?.unit}`,
        }),
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
      console.log('formattedData_dadadad345345345', formattedData);
      const formData = new FormData();
      if (data.avatar) formData.append('avatar', data.avatar);
      formData.append('data', JSON.stringify(formattedData));

      const { success, message } = await updateDeliveryHubsAPI({
        id: Number(id),
        data: formData as any,
      });
      if (success) {
        ToastTopHelper.success(message);
        navigate(CustomRoutes.deliveryHubs.path);
      } else {
        ToastTopHelper.error(message);
      }
      hideLoading();
    } catch (error) {
      console.error('Submit error:', error);
      ToastTopHelper.error(t('An error occurred. Please try again.'));
      hideLoading();
    }
  };
  const handleSaveClick = () => {
    if (watch('is_docking_station') && !isHaveDocking) {
      const timeStopsValue = watch('time_stops.value');
      const functionIdsDocking = watch('function_ids_docking');

      if (!timeStopsValue || !functionIdsDocking) {
        setShowModalDockingStation(true);
      } else {
        handleSubmit(handleFormSubmit)();
      }
    } else {
      handleSubmit(handleFormSubmit)();
    }
  };
  const [showModalDockingStation, setShowModalDockingStation] = useState(false);
  console.log('detailData_dadadad', operatingTimes);

  useEffect(() => {
    if (detailData?.operating_times) {
      setOperatingTimes(detailData?.operating_times || []);
    }
  }, [detailData?.operating_times]);



  return (
    <Container>
      <FormProvider {...methods}>
        <form
          onSubmit={handleSubmit(handleFormSubmit)}
          className="form-add-new-device"
        >
          <CustomBreadcrumb
            items={[
              { url: CustomRoutes.deliveryHubs.path },
              { text: t('Edit') },
            ]}
            buttons={[
              <CustomBtn
                key="cancel"
                variant="outline"
                color="secondary"
                size="md"
                type="button"
                label={t('Cancel')}
                onClick={() => navigate(CustomRoutes.deliveryHubs.path)}
              />,
              <CustomBtn
                key="save"
                color="primary"
                size="md"
                label={t('Save')}
                type="button"
                disabled={
                  !isValid || isSubmitting || !watch('address') ||
                  (!isDirty && !isOperatingTimesEdited) ||
                  Object.keys(operatingTimeErrors).length > 0
                }
                actionType={ROLE_PERMISSION.UPDATE}
                onClick={handleSaveClick}
              />,
            ]}
          />
          <Main>
            <FormRegister editMode={true}
              setOperatingTimes={setOperatingTimes}
              setOperatingTimeErrors={setOperatingTimeErrors}
              operatingTimes={operatingTimes}
              operatingTimeErrors={operatingTimeErrors} />
          </Main>
        </form>
        {/* SAVE DOCKING STATION */}
        <CustomModal
          title={t('Additional Information Required')}
          show={showModalDockingStation}
          onHide={() => {
            setValue('time_stops', { value: null, unit: 'mins' });
            setValue('function_ids_docking', null);
            setValue('is_docking_station', false);
            setShowModalDockingStation(false);
          }}
        >
          <div style={{ width: '37.5rem', paddingBottom: '1.6rem' }}>
            <Trans
              i18nKey="dockingMessage"
              components={{ bold: <strong className="font-bold" /> }}
            />
          </div>
          <Box
            sx={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}
          >
            <UnitInput
              name="time_stops.value"
              unit={watch('time_stops.unit')}
              type="number"
              isRequired
              placeholder={t('0')}
              label={t('Waiting Time')}
            />
            <PaginationSelect
              required
              label={t('Type')}
              name="function_ids_docking"
              control={control}
              disabled={!watch('terminal_type_ids')}
              loadOptions={getFunctionTypes({
                function_type: watch('terminal_type_ids_docking')
                  ?.map((item) => item?.code)
                  .join()
                  .toLowerCase(),
              })}
              placeholder={t('Select')}
            />
          </Box>
          <ActionBtn
            styles={{ maxWidth: '100%' }}
            leftButtons={[
              <CustomBtn
                key="modal-save-btn"
                type="button"
                color="primary"
                size="lg"
                onClick={() => {
                  handleSubmit(handleFormSubmit)();
                  setShowModalDockingStation(false);
                }}
                label={t('Save')}
                disabled={
                  !watch('time_stops.value') || !watch('function_ids_docking')
                }
              />,
            ]}
            rightButtons={[
              <CustomBtn
                key="modal-cancel-btn"
                type="button"
                variant="outline"
                color="secondary"
                size="lg"
                onClick={() => {
                  setValue('time_stops', { value: null, unit: 'mins' });
                  setValue('function_ids_docking', null);
                  setValue('is_docking_station', false);
                  setShowModalDockingStation(false);
                }}
                label={t('Cancel')}
              />,
            ]}
          />
        </CustomModal>

        {/* SAVE WHEN RETURN */}
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
                type="button"
                color="primary"
                size="lg"
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
    </Container>
  );
};
