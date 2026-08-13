import { CircularProgress, Backdrop } from '@mui/material';
import React from 'react';

import Colors from '@/configs/Colors';

const LoadingModal: React.FC = () => {
  return (
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
        backgroundColor: 'rgba(255, 255, 255, 0.3)',
      }}
    >
      <CircularProgress
        color="inherit"
        sx={{ color: Colors.Primary }}
      />
    </Backdrop>
  );
};

export default LoadingModal;
