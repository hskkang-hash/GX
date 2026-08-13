import { CircularProgress, Backdrop } from '@mui/material';
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { CustomBtn, useTheme } from 'rj-core';

import AimIframeManager from '@/components/iframe/AimIframeManager';
import Colors from '@/configs/Colors';

export default function AimPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [theme] = useTheme();
  const [loading, setLoading] = useState(true);
  console.log('AimProxyPage component rendered');

  const handleGoBack = () => {
    console.log('handleGoBack called');
    // Sử dụng window.history.back() trực tiếp vì đơn giản và đáng tin cậy hơn
    if (window.history.length > 1) {
      window.history.back();
    } else {
      // Nếu không có history, thử dùng navigate
      navigate(-1);
    }
  };

  const handleLoadingChange = (isLoading: boolean) => {
    setLoading(isLoading);
  };

  return (
    <div style={{ height: '100vh', position: 'relative' }}>
      <div
        style={{
          position: 'absolute',
          top: '10px',
          left: '10px',
          zIndex: 1000,
        }}
      >
        <CustomBtn
          label={t('Back')}
          variant="outline"
          color="secondary"
          onClick={handleGoBack}
          type="button"
        />
      </div>
      <AimIframeManager onLoadingChange={handleLoadingChange} />
      {loading && (
        <Backdrop
          open={true}
          sx={{
            color: '#fff',
            zIndex: (theme) => theme.zIndex.modal + 1,
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            backgroundColor: theme === 'dark' ? '#1f1f20' : 'white',
          }}
        >
          <CircularProgress
            color="inherit"
            sx={{ color: Colors.Primary }}
          />
        </Backdrop>
      )}
    </div>
  );
}
