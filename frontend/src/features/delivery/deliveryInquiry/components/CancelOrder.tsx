import { yupResolver } from '@hookform/resolvers/yup';
import { useEffect } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  ActionBtn,
  CustomBtn,
  CustomInputHookForm,
  CustomModal,
} from 'rj-core';
import * as yup from 'yup';

export const CancelOrder = ({
  showModal,
  loading,
  setHideModal,
  handleCancelOrder,
}: {
  showModal: boolean;
  setHideModal: () => void;
  handleCancelOrder: (reason: string) => void;
  loading?: boolean;
}) => {
  const { t } = useTranslation();
  const methods = useForm({
    resolver: yupResolver(
      yup.object().shape({
        reason: yup.string().required(t('SurveyMission.Reason is required')),
      }),
    ),
  });

  const { handleSubmit } = methods;

  useEffect(() => {
    if (showModal) {
      methods.reset({
        reason: '',
      });
    }
  }, [showModal]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <CustomModal
      title={t('Cancel Order')}
      show={showModal}
      onHide={setHideModal}
    >
      <FormProvider {...methods}>
        <form
          onSubmit={handleSubmit((values) => handleCancelOrder(values.reason))}
        >
          <div style={{ width: '40rem' }}>
            <p>
              {t(
                "We'd love to know why you're cancelling—please share your reason.",
              )}
            </p>

            <CustomInputHookForm
              name="reason"
              placeholder={t('Reason')}
            />
          </div>
          <ActionBtn
            styles={{
              maxWidth: '100%',
              margin: 'unset',
              padding: '0.5rem 0 1rem 0',
            }}
            leftButtons={[
              <CustomBtn
                variant="contained"
                color="primary"
                size="lg"
                type="submit"
                loading={loading}
                disabled={loading}
                label={t('Confirm')}
              />,
            ]}
            rightButtons={[
              <CustomBtn
                type="button"
                variant="outline"
                color="secondary"
                size="lg"
                onClick={() => {
                  setHideModal();
                }}
                label={t('Cancel')}
              />,
            ]}
          />
        </form>
      </FormProvider>
    </CustomModal>
  );
};
