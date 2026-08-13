import { useTranslation } from 'react-i18next';
import { ActionBtn, CustomBtn, CustomModal } from 'rj-core';

interface UnsavedChangesModalProps {
  show: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export const UnsavedChangesModal = ({
  show,
  onConfirm,
  onCancel,
}: UnsavedChangesModalProps): React.ReactElement => {
  const { t } = useTranslation();

  return (
    <CustomModal
      title={t('Save changes')}
      show={show}
      onHide={onCancel}
    >
      <div style={{ width: '25rem' }}>
        <p>
          {t(
            'Your unsaved changes will be lost. Do you want to save changes before leaving?',
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
            label={t('Save Changes')}
            onClick={onConfirm}
          />,
        ]}
        rightButtons={[
          <CustomBtn
            type="button"
            variant="outline"
            color="secondary"
            size="lg"
            onClick={onCancel}
            label={t('Cancel')}
          />,
        ]}
      />
    </CustomModal>
  );
};
