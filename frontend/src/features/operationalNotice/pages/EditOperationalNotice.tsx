import { yupResolver } from '@hookform/resolvers/yup';
import { useCallback, useEffect, useRef, useState } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ActionBtn,
  CustomBreadcrumb,
  CustomBtn,
  CustomModal,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useCalculateHeight,
} from 'rj-core';

import { useFormNavigationBlocker } from '@/hooks/useFormNavigationBlocker';

import { CustomRoutes } from '../../../services/API';
import { schemaOperationalNotice } from '../../../services/schemaForm';
import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import { remToPx } from '../../../utils/utils';
import FormOperatinalNotice from '../components/FormOperatinalNotice';
import useOperationalNotice from '../hooks/useOperationalNotice';
import { OperationalNoticeFormValues } from '../types/operationalNotice.types';
import { invalidPatterns } from './AddOperationalNotice';

// import { hasValidContent } from './AddOperationalNotice';

const EditOperationalNotice = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id } = useParams();
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const { getOperationalNoticeDetail, updateOperationalNotice } =
    useOperationalNotice();

  const methods = useForm({
    defaultValues: {
      name: '',
      active: true,
      group: null,
      contentSections: [
        { id: '1', title: t('Content 1'), content: '' },
        { id: '2', title: t('Content 2'), content: '' },
        { id: '3', title: t('Content 3'), content: '' },
      ],
    },
    resolver: yupResolver(schemaOperationalNotice(isRoleSuperuser)),
  });

  const headerPageRef = useRef(null);
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(1.5)],
  });
  const [isContentValid, setIsContentValid] = useState(false);
  const {
    handleSubmit,
    formState: { isValid, isSubmitting, isDirty, errors },
    watch,
    reset,
  } = methods;
  const isFormValid = isValid && isContentValid;

  console.log('form_data', watch());
  console.log('form_data_error', errors);
  useEffect(() => {
    if (id) {
      (async () => {
        const { data: reportTemplateData } =
          await getOperationalNoticeDetail(id);
        if (reportTemplateData) {
          methods.reset({
            name: reportTemplateData.name,
            active: reportTemplateData.active,
            group: reportTemplateData?.group__id
              ? {
                  value: reportTemplateData?.group__id,
                  label: reportTemplateData?.group__name,
                }
              : null,
            contentSections: [
              {
                id: '1',
                title: t('Content 1'),
                content: reportTemplateData.content1,
              },
              {
                id: '2',
                title: t('Content 2'),
                content: reportTemplateData.content2,
              },
              {
                id: '3',
                title: t('Content 3'),
                content: reportTemplateData.content3,
              },
            ],
          });
        }
      })();
    }
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleCancel = () => {
    navigate(CustomRoutes.operationalNotice.path);
  };

  const onSubmit = useCallback(
    async (data: OperationalNoticeFormValues) => {
      setClickSave(true);
      const filteredData = data.contentSections?.map((section) => ({
        content: invalidPatterns.some((pattern) =>
          section.content?.includes(pattern),
        )
          ? ''
          : section.content,
      }));
      const body = isRoleSuperuser
        ? {
            name: data.name,
            active: data.active,
            group_id: data.group?.value || null,
            ...Object.fromEntries(
              filteredData && filteredData.length > 0
                ? filteredData.map((section, index) => [
                    `content${index + 1}`,
                    section.content,
                  ])
                : [],
            ),
          }
        : {
            name: data.name,
            active: data.active,
            ...Object.fromEntries(
              filteredData && filteredData.length > 0
                ? filteredData.map((section, index) => [
                    `content${index + 1}`,
                    section.content,
                  ])
                : [],
            ),
          };
      const { message, success } = await updateOperationalNotice(
        Number(id),
        body,
      );
      if (success) {
        navigate(CustomRoutes.operationalNotice.path);
        ToastTopHelper.success(message);
      } else {
        ToastTopHelper.error(message);
      }
    },
    [id, updateOperationalNotice, navigate, isRoleSuperuser],
  );

  const [clickSave, setClickSave] = useState(false);

  const { showModal, setShowModal, handleModalSave, handleModalCancel } =
    useFormNavigationBlocker({
      isDirty: clickSave == false && isDirty,
      onSave: async () => {
        const formData = watch();
        await onSubmit(formData as OperationalNoticeFormValues);
        reset(formData, {
          keepDirty: false,
          keepValues: true,
        });
      },
      onCancel: () => {
        navigate(CustomRoutes.operationalNotice.path);
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
              url: CustomRoutes.operationalNotice.path,
            },
            { text: t('Edit Notice') },
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
              disabled={!isValid}
              type="submit"
              loading={isSubmitting}
              disabled={!isFormValid || isSubmitting}
              actionType={ROLE_PERMISSION.UPDATE}
            />,
          ]}
        />
        <Main>
          <FormOperatinalNotice
            spaceTableHeight={spaceTableHeight}
            onContentValidationChange={setIsContentValid}
          />
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

export default EditOperationalNotice;
