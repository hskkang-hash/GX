import { useTranslation } from 'react-i18next';
import { ActionBtn, CustomBtn, CustomModal } from 'rj-core';

export const ChangeStatus = ({
  showModal,
  loading = false,
  setHideModal,
  handleChangeStatus,
}: {
  showModal: boolean;
  loading?: boolean;
  setHideModal: () => void;
  handleChangeStatus: () => void;
}) => {
  const { t } = useTranslation();
  return (
    <CustomModal
      title={t('Change Status')}
      show={showModal}
      onHide={setHideModal}
    >
      <div style={{ width: '25rem' }}>
        <p>
          {t(
            "Do you want to change the status from 'Received' to 'Awaiting Delivery'?",
          )}
        </p>
      </div>

      <ActionBtn
        leftButtons={[
          <CustomBtn
            variant="contained"
            color="primary"
            size="lg"
            type="button"
            label={t('Yes')}
            loading={loading}
            disabled={loading}
            onClick={() => {
              handleChangeStatus();
            }}
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
    </CustomModal>
  );
};
