import { Box, Typography } from '@mui/material';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { ActionBtn, CustomBtn, CustomModal } from 'rj-core';

const ApproveFlightModal = ({
  show,
  onClose,
  onApproveFlight,
  onNotYet,
}: {
  show: boolean;
  onClose: () => void;
  onApproveFlight: () => void;
  onNotYet: () => void;
}) => {
  const { t } = useTranslation();
  return (
    <CustomModal
      title={t('Flight Approved')}
      show={show}
      onHide={onClose}
    >
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
        }}
      >
        <Typography variant="body1">
          {t(
            'This drone has passed the check and the flight is approved. Do you want to start the flight now?',
          )}
        </Typography>

        <ActionBtn
          leftButtons={[
            <CustomBtn
              type="submit"
              size="lg"
              color="primary"
              label={t('Flight Now')}
              onClick={onApproveFlight}
            />,
          ]}
          rightButtons={[
            <CustomBtn
              type="button"
              variant="outline"
              size="lg"
              color="secondary"
              label={t('Not Yet')}
              onClick={onNotYet}
            />,
          ]}
        />
      </Box>
    </CustomModal>
  );
};

export default ApproveFlightModal;
