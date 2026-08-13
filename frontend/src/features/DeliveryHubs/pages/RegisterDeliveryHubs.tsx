import { yupResolver } from '@hookform/resolvers/yup';
import { Box } from '@mui/material';
import { useEffect, useState } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { Trans, useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  ActionBtn,
  Container,
  CustomBreadcrumb,
  CustomBtn,
  CustomModal,
  Main,
  ToastTopHelper,
  useConfigSystem,
  useUserInfo,
} from 'rj-core';

import UnitInput from '@/components/Form/UnitInput';
import PaginationSelect from '@/components/selects/PaginationSelect';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { useFormNavigationBlocker } from '@/hooks/useFormNavigationBlocker';
import { CustomRoutes } from '@/services/API';
import { formRegisterDeliveryHubs } from '@/services/schemaForm';

import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import FormRegister from '../components/FormRegister';
import { useDeliveryHubs } from '../hooks/useDeliveryHubs';
import { FormRegisterData } from '../types/IDeliveryHubs';
import { ExceptionData, OperatingTimeData } from '@/components/HelperCellOperatingTime';
import dayjs from 'dayjs';
import { getDateFormatStringForDayjs, useConvertDate } from '@/features/Dashboard/utils/formatDateTime';

const defaultFormValues: FormRegisterData = {
  code: '',
  name: '',
  avatar: null,
  terminal_type_ids: null,
  terminal_type_ids_docking: null,
  function_ids: null,
  function_ids_docking: null,
  manager: '',
  address: '',
  city_province: '',
  city_county_district: '',
  ward_town_township: '',
  street_address: '',
  latitude: null,
  longitude: null,
  postal_code: null,
  url: '',
  note: '',
  address_note: '',
  delete_avatar: false,
  is_docking_station: false,
  time_stops: {
    value: null,
    unit: 'mins',
  },
  temp_terminal_type_ids: null,
  temp_function_ids: null,
  exceptions: [] as ExceptionData[],
};

export const RegisterDeliveryHubs = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { getFunctionTypes } = useCommonAPI();
  const { createDeliveryHubsAPI } = useDeliveryHubs();
  const { dateFormat } = useConvertDate();
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const methods = useForm<FormRegisterData>({
    defaultValues: {
      ...defaultFormValues,
      ...(isRoleSuperuser && { group: null }),
    },
    resolver: yupResolver(formRegisterDeliveryHubs(t, isRoleSuperuser)) as any,
  });
  const {
    handleSubmit,
    watch,
    setValue,
    control,
    formState: { isValid, isSubmitting, isDirty },
    reset,
  } = methods;

  const onCancel = () => {
    navigate(CustomRoutes.deliveryHubs.path);
  };

  const [clickSave, setClickSave] = useState(false);
  const { showModal, setShowModal, handleModalSave, handleModalCancel } =
    useFormNavigationBlocker({
      isDirty: clickSave == false && isDirty,
      onSave: async () => {
        const formData = watch();
        const formDataSubmit = {
          ...formData,
          operating_times: operatingTimes
        };
        await handleFormSubmit(formDataSubmit);
        reset(formDataSubmit, {
          keepDirty: false,
          keepValues: true,
        });
      },
      onCancel,
      handleSubmit,
    });

  const handleFormSubmit = async (data: FormRegisterData) => {
    setClickSave(true);
    const functionIdsAll = data?.function_ids_docking
      ? [data?.function_ids, data?.function_ids_docking]
      : [data?.function_ids];
    const terminalTypeIds =
      data?.terminal_type_ids?.map((item) => item?.value) || [];
    const terminalTypeIdsDocking =
      data?.terminal_type_ids_docking?.map((item) => item?.value) || [];
    const terminalTypeIdAll = data?.is_docking_station
      ? [...terminalTypeIds, ...terminalTypeIdsDocking]
      : terminalTypeIds;
    const formattedData = {
      code: data.code,
      name: data.name,
      group_id: data.group?.value || null,
      manager_name: data.manager || '',
      function_ids: functionIdsAll.map((item) => item?.value),
      terminal_type_ids: terminalTypeIdAll,
      city_province: data.city_province || '',
      city_county_district: data.city_county_district || '',
      ward_town_township: data.ward_town_township || '',
      street_address: data.street_address || '',
      latitude: data.latitude || null,
      longitude: data.longitude || null,
      postal_code: data.postal_code?.toString() || null,
      url: data.url || '',
      note: data.note || '',
      address_note: data.address_note || '',
      delete_avatar: data.delete_avatar || false,
      ...(data.time_stops?.value && {
        time_stops: `${data?.time_stops?.value} ${data?.time_stops?.unit}`,
      }),
      operating_times: operatingTimes?.map((item: any) => ({
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

    console.log('formattedData_submit', formattedData);

    const formData = new FormData();
    if (data.avatar) {
      formData.append('avatar', data.avatar);
    } else {
      formData.append('avatar', '');
    }
    formData.append('data', JSON.stringify(formattedData));

    const { success, message } = await createDeliveryHubsAPI(formData);
    if (success) {
      navigate(CustomRoutes.deliveryHubs.path);
      ToastTopHelper.success(message);
    } else {
      ToastTopHelper.error(message);
    }
  };

  const handleSaveClick = () => {
    if (watch('is_docking_station')) {
      setShowModalDockingStation(true);
    } else {
      handleModalSave();
    }
  };
  const [showModalDockingStation, setShowModalDockingStation] = useState(false);



  const [operatingTimes, setOperatingTimes] = useState<OperatingTimeData[]>([]);
  const [operatingTimeErrors, setOperatingTimeErrors] = useState<any>({});
  const { getDayOfWeek } = useCommonAPI();

  useEffect(() => {
    const fetchDayOfWeek = async () => {
      const { data, status, message } = await getDayOfWeek();
      console.log('data_day_of_week', data);
      if (status) {
        setOperatingTimes(data);
      } else {
        ToastTopHelper.error(message);
      }
    }
    fetchDayOfWeek()
  }, []);

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
              { text: t('hubs_delivery.register') },
            ]}
            buttons={[
              <CustomBtn
                variant="outline"
                color="secondary"
                size="md"
                type="button"
                label={t('Cancel')}
                onClick={onCancel}
              />,
              <CustomBtn
                color="primary"
                size="md"
                label={t('Save')}
                type="button"
                disabled={
                  !watch('address') ||
                  !watch('latitude') ||
                  !watch('longitude') ||
                  !watch('function_ids') ||
                  (isRoleSuperuser && !watch('group')?.value) ||
                  !watch('name') ||
                  !isValid ||
                  !isDirty ||
                  Object.keys(operatingTimeErrors).length > 0 ||
                  isSubmitting
                }
                loading={isSubmitting}
                onClick={handleSaveClick}
              />,
            ]}
          />
          <Main>
            <FormRegister editMode={false}
              setOperatingTimes={setOperatingTimes}
              setOperatingTimeErrors={setOperatingTimeErrors}
              operatingTimes={operatingTimes}
              operatingTimeErrors={operatingTimeErrors} />
          </Main>
        </form>

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
                onClick={handleModalSave}
                label={t('Save')}
                disabled={
                  isSubmitting ||
                  !isValid ||
                  !isDirty ||
                  !watch('time_stops.value') ||
                  !watch('function_ids_docking')
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
      </FormProvider>
    </Container>
  );
};
