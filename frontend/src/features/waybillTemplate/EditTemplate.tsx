import { yupResolver } from '@hookform/resolvers/yup';
import { useEffect, useRef, useState } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import {
  CustomBreadcrumb,
  CustomBtn,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  ActionBtn,
  CustomModal,
} from 'rj-core';

import { useFormNavigationBlocker } from '@/hooks/useFormNavigationBlocker';
import { CustomRoutes } from '@/services/API';
import { schemaWaybillTemplate } from '@/services/schemaForm';

import { CheckRoleAccount } from '../../utils/CheckRoleAccount';
import ContentForm from './components/ContentForm';
import useWaybill from './hooks/useWaybill';
import { WaybillTemplateFormValues } from './type';

const EditTemplate = () => {
  const { t } = useTranslation();
  const { id } = useParams();
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const navigate = useNavigate();
  const headerPageRef = useRef<HTMLElement>(
    null,
  ) as React.RefObject<HTMLElement>;

  const methods = useForm<WaybillTemplateFormValues>({
    defaultValues: {
      name: '',
      group: null,
      template: '',
      css: '',
      is_default: false,
      is_enabled: true,
    },
    resolver: yupResolver(schemaWaybillTemplate(isRoleSuperuser)) as any,
  });

  const {
    handleSubmit,
    reset,
    watch,
    formState: { isValid, isSubmitting, isDirty },
  } = methods;

  const { getWaybillTemplate, updateWaybillTemplate } = useWaybill();

  useEffect(() => {
    if (id) {
      getWaybillTemplate(id).then((res) => {
        reset(res);
      });
    }
  }, [id]);

  const onSubmit = async (data: WaybillTemplateFormValues) => {
    setClickSave(true);
    const bodyData = isRoleSuperuser
      ? {
          template: data.template || '',
          name: data.name || '',
          is_default: data.is_default || false,
          is_enabled: data.is_enabled || true,
          css: data.css || '',
          group_id: data.group?.value || null,
        }
      : {
          template: data.template || '',
          name: data.name || '',
          is_default: data.is_default || false,
          is_enabled: data.is_enabled || true,
          css: data.css || '',
        };
    const { success, message } = await updateWaybillTemplate(
      Number(id),
      bodyData,
    );
    if (success) {
      ToastTopHelper.success(message);
      navigate(CustomRoutes.waybillTemplate.path);
    } else {
      ToastTopHelper.error(message);
    }
  };

  const handleCancel = () => {
    navigate(CustomRoutes.waybillTemplate.path);
  };

  const [clickSave, setClickSave] = useState(false);

  const { showModal, setShowModal, handleModalSave, handleModalCancel } =
    useFormNavigationBlocker({
      isDirty: clickSave == false && isDirty,
      onSave: async () => {
        const formData = watch();
        await onSubmit(formData);
        reset(formData, {
          keepDirty: false,
          keepValues: true,
        });
      },
      onCancel: () => {
        navigate(CustomRoutes.waybillTemplate.path);
      },
      handleSubmit,
    });
  return (
    <FormProvider {...methods}>
      <form onSubmit={handleSubmit(onSubmit)}>
        <CustomBreadcrumb
          headerPageRef={headerPageRef}
          items={[
            {
              url: CustomRoutes.waybillTemplate.path,
            },
            { text: t('Edit Template') },
          ]}
          buttons={[
            <CustomBtn
              label={t('Cancel')}
              variant="outline"
              color="secondary"
              size="md"
              style={{ width: '6rem' }}
              type="button"
              onClick={handleCancel}
            />,
            <CustomBtn
              size="md"
              style={{ width: '6rem' }}
              label={t('Save')}
              type="submit"
              actionType={ROLE_PERMISSION.UPDATE}
              loading={isSubmitting}
              disabled={!isValid || isSubmitting}
            />,
          ]}
        />
        <Main>
          <ContentForm headerPageRef={headerPageRef} />
        </Main>
      </form>
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
              type="submit"
              color="primary"
              size="lg"
              actionType={ROLE_PERMISSION.UPDATE}
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
  );
};

export default EditTemplate;
