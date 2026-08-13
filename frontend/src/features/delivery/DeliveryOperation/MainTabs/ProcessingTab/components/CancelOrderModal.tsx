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

interface CancelOrderModalProps {
  show: boolean;
  onClose: () => void;
  onCancelOrder: (reason: string) => void;
  reasonNote: string;
  onReasonChange: (reason: string) => void;
}

interface CancelOrderFormValues {
  reason: string;
}

const CancelOrderModal = ({
  show,
  onClose,
  onCancelOrder,
  reasonNote,
  onReasonChange,
}: CancelOrderModalProps) => {
  const { t } = useTranslation();
  const methods = useForm<CancelOrderFormValues>({
    defaultValues: {
      reason: '',
    },
  });

  const { control, handleSubmit, setValue, watch } = methods;

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
    onCancelOrder(data.reason);
  });

  return (
    <CustomModal
      title={t('Cancel Order')}
      show={show}
      onHide={onClose}
    >
      <FormProvider {...methods}>
        <form onSubmit={handleConfirm}>
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
            }}
          >
            <Typography variant="body1">
              {t(
                'Are you sure you want to cancel this order? All orders assigned to this drone will also be canceled.',
              )}
            </Typography>

            <CustomInputHookForm
              name="reason"
              placeholder={t('Reason')}
              control={control}
            />

            <ActionBtn
              leftButtons={[
                <CustomBtn
                  type="submit"
                  size="lg"
                  color="primary"
                  label={t('Confirm')}
                />,
              ]}
              rightButtons={[
                <CustomBtn
                  type="button"
                  variant="outline"
                  size="lg"
                  color="secondary"
                  label={t('Cancel')}
                  onClick={onClose}
                />,
              ]}
            />
          </Box>
        </form>
      </FormProvider>
    </CustomModal>
  );
};

export default CancelOrderModal;
