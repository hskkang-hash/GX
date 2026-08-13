import React from 'react';
import { useTranslation } from 'react-i18next';
import { ActionBtn, CustomBtn, CustomModal } from 'rj-core';

const DeleteRoute = ({
  showModal,
  setHideModal,
  onDelete,
}: {
  showModal: boolean;
  setHideModal: () => void;
  onDelete: () => void;
}) => {
  const { t } = useTranslation();
  return (
    <CustomModal
      title={t('Delete Route')}
      show={showModal}
      onHide={setHideModal}
    >
      <div style={{ width: '25rem' }}>
        <p className="mb-0">
          {t('Are you sure you want to delete selected route(s)?')}
        </p>
      </div>

      <ActionBtn
        leftButtons={[
          <CustomBtn
            variant="outline"
            color="primary"
            size="lg"
            type="button"
            label={t('Delete')}
            onClick={() => {
              onDelete();
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

export default DeleteRoute;
