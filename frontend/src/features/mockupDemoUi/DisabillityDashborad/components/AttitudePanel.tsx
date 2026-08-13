import React from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

const AttitudePanel = ({ data }) => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  return (
    <div
      style={{
        background: theme === 'dark' ? Colors.Gray9 : '#fff',
        borderRadius: 5,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        border: '1px solid #e0e0e0',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
      }}
    >
      <h4
        style={{
          margin: '10px 0',
          fontSize: 16,
          color: theme === 'dark' ? Colors.Gray3 : '#333',
          textAlign: 'left',
        }}
      >
        <span
          style={{
            display: 'inline-block',
            width: 24,
            height: 24,
            background: theme === 'dark' ? '#2D2E30' : '#f8f8f8',
            borderRadius: '50%',
            marginRight: 5,
            verticalAlign: 'middle',
            position: 'relative',
          }}
        >
          <span
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%,-50%)',
              width: 12,
              height: 12,
              background: '#1D9BE2',
              borderRadius: '50%',
            }}
          />
        </span>
        {t('Aircraft attitude')}
      </h4>
      {[
        {
          label: 'Roll',
          icon: '⟳',
          value: `${data.roll}° ~ ${(parseFloat(data.roll) + 2).toFixed(2)}°`,
        },
        {
          label: 'Pitch',
          icon: '⟰',
          value: `${data.pitch}° ~ ${(parseFloat(data.pitch) + 2).toFixed(2)}°`,
        },
        {
          label: 'Yaw',
          icon: '↻',
          value: `${data.yaw}° ~ ${(parseFloat(data.yaw) + 2).toFixed(2)}°`,
        },
      ].map((item) => (
        <div
          key={item.label}
          style={{
            background: theme === 'dark' ? '#2D2E30' : '#f8f8f8',
            border: '1px solid #e0e0e0',
            borderRadius: 3,
            padding: 20,
            marginBottom: 20,
            position: 'relative',
            textAlign: 'center',
          }}
        >
          <div
            style={{
              position: 'absolute',
              left: 10,
              top: '50%',
              transform: 'translateY(-50%)',
              width: 30,
              height: 30,
              border: '2px solid #1D9BE2',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <span
              style={{
                color: '#1D9BE2',
                fontWeight: 'bold',
                fontSize: 14,
              }}
            >
              {item.icon}
            </span>
          </div>
          <span
            style={{
              fontWeight: 'bold',
              fontSize: 16,
              color: theme === 'dark' ? Colors.Gray3 : '#333',
            }}
          >
            {item.label}
          </span>
          <br />
          <span
            style={{
              color: '#1D9BE2',
              fontSize: 18,
              marginTop: 15,
              display: 'inline-block',
            }}
          >
            {item.value}
          </span>
        </div>
      ))}
    </div>
  );
};

export default AttitudePanel;
