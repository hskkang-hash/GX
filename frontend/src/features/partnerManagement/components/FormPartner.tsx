import { yupResolver } from '@hookform/resolvers/yup';
import { Box } from '@mui/material';
import { memo, useEffect, useState, useMemo } from 'react';
import { FormProvider, useForm, useController } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  CustomBtn,
  CustomInputHookForm,
  OffCanvas,
  ROLE_PERMISSION,
  ToastTopHelper,
  useTheme,
  useUserInfo,
} from 'rj-core';

import UnitInput from '@/components/Form/UnitInput';
import PaginationSelect from '@/components/selects/PaginationSelect';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { schemaPartner } from '@/services/schemaForm';

import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import useAPI from '../useAPI/useAPI';

export interface FormPartnerProps {
  id?: number;
  api_key?: string;
  code?: string;
  is_active?: boolean;
  name: string;
  expired_days: number;
  group: {
    value?: number;
    label?: string;
  };
  api_callback_url: {
    DroneUserNotice: string;
    DroneBaseStation: string;
    DeliveryStatusCallback: string;
  };
  service_key: string;
}

export default memo(function FormPartner({
  open,
  onClose,
  data,
  refreshData,
  isedit,
}: {
  open: boolean;
  onClose: () => void;
  data: any; // API data với objects
  refreshData: () => void;
  isedit: boolean;
}) {
  const [theme] = useTheme();
  const { t } = useTranslation();
  const { getListGroup } = useCommonAPI();
  const { createPartner, updatePartner } = useAPI();

  const userInfo = useUserInfo();

  console.log('userInfo_in_form_partner', userInfo?.roles);

  const displayGroup = CheckRoleAccount('superuser');

  // const displayGroup = (usetInfo as any)?.profile__group_id ? false : true;
  // const displayGroup = true;

  // console.log({ displayGroup })

  const initialValues = {
    name: '',
    expired_days: 30,
    api_callback_url: {
      DroneUserNotice: '',
      DroneBaseStation: '',
      DeliveryStatusCallback: '',
    },
    service_key: '',
    ...(displayGroup && { group: null }),
  };

  // Create resolver with current translation function that updates reactively
  const resolver = useMemo(() => yupResolver(schemaPartner(t)) as any, [t]);

  const methods = useForm<FormPartnerProps>({
    defaultValues: data !== null ? data : initialValues,
    resolver,
    mode: 'onChange',
    reValidateMode: 'onChange',
  });

  const {
    handleSubmit,
    control,
    watch,
    reset,
    trigger,
    clearErrors,
    formState: { isValid, isDirty, errors, isSubmitting },
  } = methods;

  // Reset form when data changes
  useEffect(() => {
    if (data !== null) {
      reset(data);
    } else {
      reset(initialValues);
    }
  }, [data, reset]);

  // Re-trigger validation when language changes to update error messages
  useEffect(() => {
    // Only trigger if there are existing errors to translate
    const hasErrors = Object.keys(errors).length > 0;
    if (hasErrors) {
      trigger();
    }
  }, [t, trigger]);

  console.log('data_in_form_partner', data);
  console.log('form_partner_watch', watch());

  const onSubmit = async (formData: FormPartnerProps) => {
    const formDataSubmit = {
      name: formData.name,
      expired_days: formData.expired_days,
      api_callback_url: {
        DroneUserNotice: formData.api_callback_url.DroneUserNotice,
        DroneBaseStation: formData.api_callback_url.DroneBaseStation,
        DeliveryStatusCallback:
          formData.api_callback_url.DeliveryStatusCallback,
      },
      service_key: formData.service_key,
      ...(displayGroup && { group_id: formData.group?.value || null }),
      ...(isedit && {
        api_key: formData?.api_key,
        code: formData?.code,
        is_active: true,
      }),
    };
    console.log('form_data_submit', formDataSubmit);
    console.log('form_data_submit_isedit', formData?.id);

    const { success, message } = isedit
      ? await updatePartner({ id: formData?.id, data: formDataSubmit })
      : await createPartner(formDataSubmit);
    if (success) {
      ToastTopHelper.success(message);
      reset({
        name: '',
        expired_days: 30,
        service_key: '',
        api_callback_url: {
          DroneUserNotice: '',
          DroneBaseStation: '',
          DeliveryStatusCallback: '',
        },
        ...(displayGroup && { group: { value: undefined, label: undefined } }),
      });
      onClose();
      refreshData();
    } else {
      ToastTopHelper.error(message);
    }
  };

  return (
    <OffCanvas
      show={open}
      title={isedit ? t('Edit Partner') : t('Add New Partner')}
      onHide={() => {
        onClose();
        reset();
      }}
      id="operation-setting"
    >
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
        }}
      >
        <FormProvider {...methods}>
          <form
            onSubmit={handleSubmit(onSubmit)}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              height: '100%',
            }}
          >
            {/* Scrollable content */}
            <Box
              sx={{
                flex: 1,
                overflow: 'scroll',
                maxHeight: 'calc(100vh - 45px - 60px - 1rem)',
                display: 'flex',
                flexDirection: 'column',
                px: '1rem',
                gap: '1rem',
              }}
            >
              <Box
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '1rem',
                }}
              >
                <CustomInputHookForm
                  required
                  name="name"
                  label={t('Partner Name')}
                  placeholder={t('Partner Name')}
                />
                {displayGroup && (
                  <PaginationSelect
                    required
                    label={t('Group')}
                    name="group"
                    control={control}
                    loadOptions={getListGroup() as any}
                    placeholder={t('Select')}
                  />
                )}
                <UnitInput
                  name="expired_days"
                  label={t('API Key Expiry ')}
                  placeholder="30"
                  unit={t('days')}
                  type="number"
                  isRequired
                  min={1}
                />

                <Box
                  sx={{
                    fontSize: '1.2em',
                    fontWeight: 'bold',
                  }}
                >
                  {t('API Call Back')}
                </Box>

                <CustomInputHookForm
                  name="api_callback_url.DeliveryStatusCallback"
                  label={t('DeliveryStatusCallback​')}
                  placeholder={t('Value')}
                  type="text"
                  required
                />
                <CustomInputHookForm
                  name="api_callback_url.DroneBaseStation"
                  label={t('DroneBaseStation​')}
                  placeholder={t('Value')}
                  type="text"
                  required
                />
                <CustomInputHookForm
                  name="api_callback_url.DroneUserNotice"
                  label={t('DroneUserNotice​')}
                  placeholder={t('Value')}
                  type="text"
                  required
                />
                <CustomInputHookForm
                  name="service_key"
                  label={t('ServiceKey​')}
                  placeholder={t('Value')}
                  type="text"
                  required
                />
              </Box>
            </Box>

            {/* Footer always visible */}
            <Box
              sx={{
                mt: '1rem',
                p: '1rem',
                borderTop:
                  theme === 'dark' ? '1px solid #444646' : '1px solid #E0E0E0',
                background: theme === 'dark' ? '#212529' : '#fff',
              }}
            >
              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '16px',
                }}
              >
                <CustomBtn
                  label={t('Save')}
                  actionType={ROLE_PERMISSION.UPDATE}
                  type="submit"
                  variant="contained"
                  color="primary"
                  size="lg"
                  loading={isSubmitting}
                  disabled={!isDirty || !isValid || isSubmitting}
                />
                <CustomBtn
                  label={t('Cancel')}
                  type="button"
                  onClick={() => {
                    onClose();
                    reset();
                  }}
                  variant="outline"
                  color="secondary"
                  size="lg"
                />
              </Box>
            </Box>
          </form>
        </FormProvider>
      </Box>
    </OffCanvas>
  );
});
