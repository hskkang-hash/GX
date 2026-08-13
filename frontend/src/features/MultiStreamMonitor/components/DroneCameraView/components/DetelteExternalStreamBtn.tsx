import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BsTrash } from 'react-icons/bs';
import { ActionBtn, CustomBtn, CustomModal } from 'rj-core';

interface DetelteExternalStreamBtnProps {
  currentMode: 'draw' | 'capture' | 'record' | 'ai' | null;
  onDeleteExternalStream: () => void;
}

export const DetelteExternalStreamBtn: React.FC<
  DetelteExternalStreamBtnProps
> = ({ currentMode, onDeleteExternalStream }) => {
  const { t } = useTranslation();
  const [showConfirmationModal, setShowConfirmationModal] = useState(false);

  return (
    <React.Fragment>
      <button
        onClick={() => setShowConfirmationModal(true)}
        style={{
          width: '32px',
          height: '32px',
          backgroundColor: 'rgba(255, 255, 255, 0.9)',
          color: '#374151',
          border: 'none',
          borderRadius: '50%',
          cursor: 'pointer',
          fontSize: '18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all 0.3s ease',
          boxShadow: '0 4px 16px rgba(0, 0, 0, 0.15)',
          backdropFilter: 'blur(8px)',
        }}
        onMouseEnter={(e) => {
          if (currentMode !== 'draw') {
            e.currentTarget.style.transform = 'scale(1.05)';
          }
        }}
        onMouseLeave={(e) => {
          if (currentMode !== 'draw') {
            e.currentTarget.style.transform = 'scale(1)';
          }
        }}
        title={t('Delete External Stream')}
      >
        <BsTrash />
      </button>

      <CustomModal
        title={t('Delete')}
        show={showConfirmationModal}
        onHide={() => setShowConfirmationModal(false)}
      >
        <div style={{ width: '25rem' }}>
          {t('Are you sure you want to delete this stream?')}
        </div>
        <ActionBtn
          leftButtons={[
            <CustomBtn
              type="button"
              variant="outline"
              color="primary"
              size="lg"
              label={t('Delete')}
              onClick={() => {
                onDeleteExternalStream();
                setShowConfirmationModal(false);
              }}
            />,
          ]}
          rightButtons={[
            <CustomBtn
              type="button"
              variant="outline"
              color="secondary"
              size="lg"
              label={t('Cancel')}
              onClick={() => setShowConfirmationModal(false)}
            />,
          ]}
        />
      </CustomModal>
    </React.Fragment>
  );
};
