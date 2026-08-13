import React from 'react';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

interface BatteryBarProps {
  batteryLevel: number;
}

const BatteryBar: React.FC<BatteryBarProps> = ({ batteryLevel }) => {
  const [theme] = useTheme();

  return (
    <div
      style={{
        width: '100%',
        height: 30,
        background: theme === 'dark' ? '#2D2E30' : '#f8f8f8',
        border: '1px solid #e0e0e0',
        borderRadius: 3,
        position: 'relative',
        marginTop: 10,
        marginBottom: 20,
      }}
    >
      <div
        style={{
          height: '100%',
          width: `${batteryLevel}%`,
          background: 'linear-gradient(to right, #cc0000, #cccc00, #1D9BE2)',
          borderRadius: 2,
        }}
      />
    </div>
  );
};

export default BatteryBar;
