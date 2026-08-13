import { CloseOutlined } from '@ant-design/icons';
import { Scanner } from '@yudiel/react-qr-scanner';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BsQrCodeScan } from 'react-icons/bs';
import { useLocation } from 'react-router-dom';
import {
  useAPILogin,
  useLogout,
  CustomModal,
  ActionBtn,
  CustomBtn,
  ToastTopHelper,
} from 'rj-core';

import logoExpandedLightModeDefault from '@/assets/images/Full Version-Black.png';

import { useOperationOrder } from '../delivery/DeliveryOperation/hooks/useOperationOrder';
import './ScanQRMobile.scss';

const ScanQRMobile = () => {
  const { t } = useTranslation();
  const { logoutAPI } = useAPILogin();
  const logout = useLogout();
  const [isOpenScanQR, setIsOpenScanQR] = useState(false);
  const [infoPackage, setInfoPackage] = useState<{
    order_id?: number;
    package_id?: number;
    terminal_name?: string;
  }>({});
  const [confirmModal, setConfirmModal] = useState(false);
  const [errorModal, setErrorModal] = useState(false);
  const location = useLocation();
  const currentParams = new URLSearchParams(location.search);
  const dataValue = currentParams.get('dataQRCode');

  const { confirmPackage } = useOperationOrder();

  useEffect(() => {
    if (dataValue) {
      const resultData = JSON.parse(decodeURIComponent(dataValue));
      if (resultData.qr_status === 'verified_order') {
        setInfoPackage({
          order_id: resultData.qr_order_code,
          package_id: resultData.qr_package_id,
          terminal_name: resultData.qr_terminal_name,
        });
        setConfirmModal(true);
      } else {
        setErrorModal(true);
      }
    }
  }, [dataValue]);

  const handleLogOut = useCallback(async () => {
    const { success, message } = await logoutAPI();
    if (success) {
      logout();
    } else {
      console.log(message);
    }
  }, [logoutAPI, logout]);

  const handleConfirm = useCallback(async () => {
    const { success, message } = await confirmPackage({
      package_id: infoPackage.package_id || 0,
    });
    if (success) {
      setConfirmModal(false);
      ToastTopHelper.success(message);
    } else {
      ToastTopHelper.error(message);
    }
  }, [infoPackage, confirmPackage]);

  return (
    <>
      {isOpenScanQR ? (
        <div>
          <CloseOutlined
            onClick={() => setIsOpenScanQR(false)}
            style={{
              position: 'absolute',
              top: '1rem',
              left: '1rem',
              zIndex: 1000,
              fontSize: '2rem',
            }}
          />
          <Scanner
            onScan={(result) => {
              const resultData = result[0].rawValue;

              if (resultData) {
                const url = new URL(resultData);
                const encodedData = url.searchParams.get('dataQRCode');

                const decodedData = decodeURIComponent(encodedData || '');
                const qrData = JSON.parse(decodedData);

                if (qrData.qr_status === 'verified_order') {
                  setInfoPackage({
                    order_id: qrData.qr_order_code,
                    package_id: qrData.qr_package_id,
                    terminal_name: qrData.qr_terminal_name,
                  });
                  setIsOpenScanQR(false);
                  setConfirmModal(true);
                } else {
                  setIsOpenScanQR(false);
                  setErrorModal(true);
                }
              }
            }}
            constraints={{
              facingMode: 'environment',
            }}
            styles={{
              container: {
                width: '100vw',
                height: '100vh',
                position: 'relative',
              },
            }}
          />
        </div>
      ) : (
        <div
          className="d-flex flex-column justify-content-between align-items-center min-vh-100 p-4"
          style={{ backgroundColor: '#f8f9fa' }}
        >
          {/* Header with Logo */}
          <div className="text-center mt-3">
            <img
              className="logo-image"
              src={logoExpandedLightModeDefault}
              alt="GuardianX Logo"
              style={{ maxWidth: '200px', height: 'auto' }}
            />
          </div>

          {/* Main Content - QR Code Section */}
          <div
            style={{
              width: '13.5rem',
              height: '14.5rem',
              borderRadius: '0.5rem',
              backgroundColor: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            onClick={() => setIsOpenScanQR(true)}
          >
            <div className="d-flex flex-column align-items-center justify-content-center gap-4">
              {/* QR Code Icon */}

              <BsQrCodeScan size={60} />

              {/* Scan QR Code Text */}
              <h4 className="text-dark fw-normal mb-0">{t('Scan QR Code')}</h4>
            </div>
          </div>

          {/* Footer - Log Out Button */}
          <div className="w-100 mb-4">
            <button
              onClick={handleLogOut}
              className="btn w-100 py-3"
              style={{
                backgroundColor: 'transparent',
                border: 'none',
                color: 'var(--ga-primary)',
                fontSize: '1.5rem',
                fontWeight: '600',
              }}
            >
              {t('Log Out')}
            </button>
          </div>
        </div>
      )}

      {confirmModal && (
        <CustomModal
          title={t('Package Arrival Confirmation')}
          show={confirmModal}
          onHide={() => setConfirmModal(false)}
          id="confirm-qr-modal"
        >
          <div>
            <p>
              <span className="fw-bold">Order ID:</span> {infoPackage.order_id}
            </p>
            <p>
              <span className="fw-bold">Package ID:</span>{' '}
              {infoPackage.package_id}
            </p>
            <p>
              {t(
                'Please confirm that this package has arrived at the {{terminalName}}.',
                {
                  terminalName: infoPackage.terminal_name || '',
                },
              )}
            </p>
          </div>
          <ActionBtn
            leftButtons={[
              <CustomBtn
                type="submit"
                color="primary"
                size="lg"
                onClick={handleConfirm}
                label={t('Confirm')}
              />,
            ]}
            rightButtons={[
              <CustomBtn
                type="button"
                variant="outline"
                color="secondary"
                size="lg"
                onClick={() => setConfirmModal(false)}
                label={t('Cancel')}
              />,
            ]}
          />
        </CustomModal>
      )}

      {errorModal && (
        <CustomModal
          title={t('Package Status Mismatch')}
          show={errorModal}
          onHide={() => setErrorModal(false)}
          id="error-qr-modal"
        >
          <div>
            <p className="mb-4">
              {t(
                'The scanned package is not in a valid status. Please verify the package and try again.',
              )}
            </p>
            <CustomBtn
              type="button"
              variant="outline"
              color="secondary"
              size="lg"
              className="w-100 mb-2"
              onClick={() => setErrorModal(false)}
              label={t('Close')}
            />
          </div>
        </CustomModal>
      )}
    </>
  );
};

export default ScanQRMobile;
