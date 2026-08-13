import { yupResolver } from '@hookform/resolvers/yup';
import { useCallback, useRef, useState } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  CustomBreadcrumb,
  CustomBtn,
  CustomModal,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useCalculateHeight,
  ActionBtn,
} from 'rj-core';

import { useFormNavigationBlocker } from '@/hooks/useFormNavigationBlocker';

import { CustomRoutes } from '../../../services/API';
import { reportTemplateSchema } from '../../../services/schemaForm';
import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import { remToPx } from '../../../utils/utils';
import FormReportTemplate from '../components/FormReportTemplate';
import useReportTemplate from '../hooks/useReportTemplate';
import {
  BodyRequestReportTemplate,
  ReportTemplateFormValues,
} from '../types/reportTemplate.types';

const AddReportTemplate = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const [clickSave, setClickSave] = useState(false);

  const headerPageRef = useRef(null);
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(1.5)],
  });

  const { createReportTemplate } = useReportTemplate();

  const methods = useForm({
    defaultValues: {
      name: '',
      is_enabled: true,
      is_default: true,
      template: '',
      group: null,
    },
    resolver: yupResolver(reportTemplateSchema(isRoleSuperuser)),
  });

  const {
    handleSubmit,
    watch,
    reset,
    formState: { isValid, isDirty, isSubmitting, errors },
  } = methods;

  console.log('form_data', watch());
  console.log('form_data_error', errors);

  const handleCancel = () => {
    navigate(CustomRoutes.reportTemplate.path);
  };

  const onSubmit = useCallback(
    async (data: ReportTemplateFormValues) => {
      setClickSave(true);
      const body: BodyRequestReportTemplate = isRoleSuperuser
        ? {
            name: data.name,
            is_enabled: data.is_enabled,
            is_default: data.is_default,
            template: data.template,
            group_id: data?.group?.value || null,
          }
        : {
            name: data.name,
            is_enabled: data.is_enabled,
            is_default: data.is_default,
            template: data.template,
          };

      const { message, success } = await createReportTemplate(body);
      if (success) {
        ToastTopHelper.success(message);
        navigate(CustomRoutes.reportTemplate.path);
      } else {
        ToastTopHelper.error(message);
      }
    },
    [createReportTemplate, navigate, isRoleSuperuser],
  );

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
        navigate(CustomRoutes.reportTemplate.path);
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
              url: CustomRoutes.reportTemplate.path,
            },
            { text: t('Add Template') },
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
              disabled={!isValid || isSubmitting || !isDirty || !isValid}
              loading={isSubmitting}
              actionType={ROLE_PERMISSION.CREATE}
            />,
          ]}
        />
        <Main>
          <FormReportTemplate spaceTableHeight={spaceTableHeight} />
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
        </Main>
      </form>
    </FormProvider>
  );
};

export default AddReportTemplate;
