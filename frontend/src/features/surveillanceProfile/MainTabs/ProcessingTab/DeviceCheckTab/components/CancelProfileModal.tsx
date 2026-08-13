import { Box, Typography } from '@mui/material';
import React, { useEffect } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  ActionBtn,
  CustomBtn,
  CustomInputHookForm,
  CustomModal,
} from 'rj-core';

interface CancelProfileModalProps {
  show: boolean;
  onClose: () => void;
  onCancelProfile: (reason: string) => void;
  reasonNote: string;
  onReasonChange: (reason: string) => void;
}

interface CancelProfileFormValues {
  reason: string;
}

const CancelProfileModal = ({
  show,
  onClose,
  onCancelProfile,
  reasonNote,
  onReasonChange,
}: CancelProfileModalProps) => {
  const { t } = useTranslation();
  const methods = useForm<CancelProfileFormValues>({
    defaultValues: {
      reason: '',
    },
  });

  const {
    control,
    handleSubmit,
    setValue,
    watch,
    formState: { isSubmitting, isValid },
  } = methods;

  // Sync form value with parent state
  useEffect(() => {
    setValue('reason', reasonNote);
  }, [reasonNote, setValue]);

  // Watch for changes and notify parent
  useEffect(() => {
    const subscription = watch((value) => {
      if (value.reason !== undefined) {
        onReasonChange(value.reason);
      }
    });
    return () => subscription.unsubscribe();
  }, [watch, onReasonChange]);

  const handleConfirm = handleSubmit((data) => {
    onCancelProfile(data.reason);
  });

  return (
    <CustomModal
      title={t('Cancel Profile')}
      show={show}
      onHide={onClose}
    >
      <FormProvider {...methods}>
        <form onSubmit={handleConfirm}>
          <div style={{ width: '40rem' }}>
            <p>
              {t(
                'Please tell us the reason why you want to cancel this profile.',
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
                loading={isSubmitting || !isValid}
                disabled={isSubmitting || !watch('reason')}
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
                  onClose();
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

export default CancelProfileModal;
