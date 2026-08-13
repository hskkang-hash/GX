import { useTranslation } from 'react-i18next';
import { CustomBtn, ActionBtn, CustomModal } from 'rj-core';

export const ApproveMissionModal = ({
  show,
  loading = false,
  onClose,
  onApprove,
}: {
  show: boolean;
  loading?: boolean;
  onClose: () => void;
  onApprove: () => void;
}) => {
  const { t } = useTranslation();
  return (
    <CustomModal
      title={t('SurveyMission.Approve Mission')}
      show={show}
      onHide={onClose}
    >
      <div style={{ width: '25rem' }}>
        <p>
          {t('SurveyMission.Are you sure you want to approve this mission?')}
        </p>
      </div>

      <ActionBtn
        leftButtons={[
          <CustomBtn
            variant="contained"
            color="primary"
            size="lg"
            type="button"
            label={t('Approve')}
            loading={loading}
            disabled={loading}
            onClick={onApprove}
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
    </CustomModal>
  );
};
