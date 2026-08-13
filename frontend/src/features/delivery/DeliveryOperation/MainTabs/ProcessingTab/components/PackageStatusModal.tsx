import { Box } from '@mui/material';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { CenterBtn, CustomBtn, CustomModal, useTheme } from 'rj-core';

import Colors from '@/configs/Colors';

import { Package, PackageAttribute, PackageList } from '../PackageStatusTab';
import './OrderDetailModal.scss';

function PackageStatusModal({
  show,
  onHide,
  detailData,
  handleCompletePackage,
  loadingPackages,
}: {
  show: boolean;
  onHide: () => void;
  detailData: PackageList;
  handleCompletePackage: (packageRequest: Package) => void;
  loadingPackages: Set<string>;
}) {
  const { t } = useTranslation();
  const [theme] = useTheme();

  const isPackageIncomplete = (pkg: Package): boolean => {
    return pkg.some(
      (item) =>
        (item.name === 'Package Status (Device)' &&
          (item.value === '-' || !item.value)) ||
        (item.name === 'Package Status (User)' &&
          (item.value === '-' || !item.value)),
    );
  };

  const RenderItem = (item: PackageAttribute) => {
    return (
      <Box
        key={item.id}
        sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr' }}
      >
        <div>{t(item.name)}</div>
        <span>{item.value || '-'}</span>
      </Box>
    );
  };

  const RenderCard = (items: Package, index: number) => {
    const packageIdAttr = items.find((attr) => attr.name === 'Package ID');
    const packageId = packageIdAttr?.value || '';
    const isLoading = loadingPackages.has(packageId);
    console.log('loadingPackages', loadingPackages);

    return (
      <div
        key={index}
        style={{
          // convert px to rem
          columnGap: '24px',
          rowGap: '8px',
          padding: '16px',
          backgroundColor:
            theme === 'light' ? Colors.Gray1 : Colors.PrimaryText,
          borderRadius: '8px',
        }}
      >
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '0.8rem',
          }}
        >
          {items?.map((item: PackageAttribute) => RenderItem(item))}
        </Box>
        {isPackageIncomplete(items) && (
          <div className="mt-3">
            <CustomBtn
              type="submit"
              color="primary"
              size="lg"
              onClick={() => handleCompletePackage(items)}
              label={t('Confirm')}
              loading={isLoading}
            />
          </div>
        )}
      </div>
    );
  };

  return (
    <CustomModal
      id="order-detail-modal"
      title={t('Package List Status')}
      show={show}
      onHide={onHide}
    >
      {detailData && (
        <Box
          sx={{
            display: 'grid',
            rowGap: '20px',
            pb: '20px',
          }}
        >
          {detailData?.map((items: Package, index: number) =>
            RenderCard(items, index),
          )}
        </Box>
      )}
      <CenterBtn
        color="secondary"
        type="button"
        variant="outline"
        size="lg"
        onClick={onHide}
        label={t('Close')}
      />
    </CustomModal>
  );
}

export default React.memo(PackageStatusModal);
