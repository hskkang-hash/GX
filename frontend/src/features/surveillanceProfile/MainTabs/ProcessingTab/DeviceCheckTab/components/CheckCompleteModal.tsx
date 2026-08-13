import { Box, Typography } from '@mui/material';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { ActionBtn, CustomBtn, CustomModal, ROLE_PERMISSION } from 'rj-core';

const CheckCompleteModal = ({
    show,
    onClose,
    onStartNow,
    onWait,
    isLate
}: {
    show: boolean;
    onClose: () => void;
    onStartNow: () => void;
    onWait: () => void;
    isLate: boolean;
}) => {
    const { t } = useTranslation();
    return (
        <CustomModal
            title={t('Start Surveillance')}
            show={show}
            onHide={onClose}
        >
            <div style={{ width: '25rem' }}>
                {!isLate
                    ?
                    t(
                        'This profile has completed the device check. The scheduled start time has not yet arrived. Would you like to wait until the scheduled time or start the mission immediately?'
                    )
                    :
                    t(
                        'This profile has completed the device check. The scheduled start time has already passed, so the mission will begin surveillance immediately.'
                    )}

            </div>

            {!isLate ?
                <ActionBtn
                    leftButtons={[
                        <CustomBtn
                            key="modal-save-btn"
                            type="submit"
                            color="primary"
                            size="lg"
                            actionType={ROLE_PERMISSION.UPDATE}
                            onClick={onWait}
                            label={t('Wait')}
                        />,
                    ]}
                    rightButtons={[
                        <CustomBtn
                            key="modal-cancel-btn"
                            type="button"
                            style={{ border: '1px solid #1d9be2', color: '#1d9be2' }}
                            variant="outline"
                            color="secondary"
                            size="lg"
                            onClick={onStartNow}
                            label={t('Start Now')}
                        />,
                    ]}
                /> : <ActionBtn
                    styles={{ maxWidth: '100%' }}
                    middleButtons={[
                        <CustomBtn
                            key="modal-save-btn"
                            type="submit"
                            color="primary"
                            size="lg"
                            actionType={ROLE_PERMISSION.UPDATE}
                            onClick={onStartNow}
                            label={t('OK')}
                        />,
                    ]}
                />}
        </CustomModal>
    );
};

export default CheckCompleteModal;
