import React from 'react';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

interface AltitudePanelProps {
  altitude: number;
}

const AltitudePanel: React.FC<AltitudePanelProps> = ({ altitude }) => {
  const [theme] = useTheme();

  return (
    <div
      style={{
        background: theme === 'dark' ? Colors.Black : '#f8f8f8',
        border: '1px solid #e0e0e0',
        borderRadius: 5,
        padding: 15,
        marginTop: 10,
        textAlign: 'center',
        position: 'relative',
        height: 120,
        marginBottom: 20,
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: 10,
          right: 10,
          bottom: 10,
          height: 60,
          background:
            theme === 'dark'
              ? '#2D2E30'
              : 'linear-gradient(to top, #f8f8f8, #fff)',
          border: '1px solid #e0e0e0',
          borderRadius: 3,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: 10,
          right: 10,
          bottom: `${(altitude / 200) * 60 + 5}px`,
          height: 3,
          background: '#1D9BE2',
          boxShadow: '0 0 10px #1D9BE2',
        }}
      />
      <div
        style={{
          position: 'absolute',
          top: 10,
          left: 0,
          width: '100%',
          textAlign: 'center',
          fontSize: 18,
          fontWeight: 'bold',
          color: theme === 'dark' ? Colors.Gray3 : '#333',
        }}
      >
        {altitude}m
      </div>
    </div>
  );
};

export default AltitudePanel;
