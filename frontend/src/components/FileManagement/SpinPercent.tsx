import { ConfigProvider, Spin } from 'antd';
import React from 'react';

import Colors from '../../configs/Colors';

const SpinPercent: React.FC = () => {
  return (
    <ConfigProvider
      theme={{
        components: {
          Spin: {
            colorPrimary: Colors.Primary,
          },
        },
      }}
    >
      <Spin
        size="small"
        percent={'auto'}
      />
    </ConfigProvider>
  );
};

export default SpinPercent;
