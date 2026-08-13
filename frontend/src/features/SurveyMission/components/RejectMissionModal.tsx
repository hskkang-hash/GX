import { yupResolver } from '@hookform/resolvers/yup';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  ActionBtn,
  CustomBtn,
  CustomInputHookForm,
  CustomModal,
} from 'rj-core';
import * as yup from 'yup';

import { RejectMissionFormValues } from '../types/surveyMission.types';

export const RejectMissionModal = ({
  show,
  loading = false,
  onClose,
  onReject,
}: {
  show: boolean;
  loading?: boolean;
  onClose: () => void;
  onReject: (values: RejectMissionFormValues) => void;
}) => {
  const { t } = useTranslation();
  const methods = useForm<RejectMissionFormValues>({
    defaultValues: {
      reason: '',
    },
    resolver: yupResolver(
      yup.object().shape({
        reason: yup.string().required(t('SurveyMission.Reason is required')),
      }),
    ),
  });

  const { handleSubmit } = methods;

  return (
    <CustomModal
      title={t('SurveyMission.Reject Mission')}
      show={show}
      onHide={onClose}
    >
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onReject)}>
          <div style={{ width: '25rem' }}>
            <p>
              {t(
                'SurveyMission.Enter the reason or feedback so the creator can revise and resubmit.',
              )}
            </p>
          </div>

          <CustomInputHookForm
            name="reason"
            placeholder={t('Reason')}
          />

          <ActionBtn
            leftButtons={[
              <CustomBtn
                variant="contained"
                color="primary"
                size="lg"
                type="submit"
                label={t('SurveyMission.Confirm')}
                loading={loading}
                disabled={loading}
              />,
            ]}
            rightButtons={[
              <CustomBtn
                type="button"
                variant="outline"
                color="secondary"
                size="lg"
                onClick={onClose}
                label={t('Cancel')}
              />,
            ]}
          />
        </form>
      </FormProvider>
    </CustomModal>
  );
};
