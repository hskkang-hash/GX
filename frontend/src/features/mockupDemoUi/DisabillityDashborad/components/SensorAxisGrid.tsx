import { Box } from '@mui/material';
import React from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

const SensorAxisGrid = ({ label, axisData }) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  return (
    <Box
      display="flex"
      flexDirection="column"
      p={1}
      border={1}
      borderColor={theme === 'dark' ? 'white' : '#e0e0e0'}
      bgcolor={theme === 'dark' ? Colors.Black : '#fff'}
      borderRadius={'10px'}
      marginBottom={'20px'}
    >
      {label && (
        <h3
          style={{
            fontSize: 18,
            margin: 0,
            marginBottom: 5,
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
          {label}
        </h3>
      )}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 10,
          margin: '10px 0',
        }}
      >
        {axisData.map((item) => (
          <div
            key={item.label}
            style={{
              background: theme === 'dark' ? '#2D2E30' : '#f8f8f8',
              border: '1px solid #e0e0e0',
              borderRadius: 3,
              padding: 20,
              position: 'relative',
              textAlign: 'center',
            }}
          >
            <div
              style={{
                position: 'absolute',
                left: '50%',
                top: 10,
                transform: 'translateX(-50%)',
                width: 81,
                height: 81,
                borderBottom: '2px solid #1D9BE2',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <span
                style={{
                  color: '#1D9BE2',
                  fontWeight: 'bold',
                  fontSize: 38,
                  margin: 10,
                }}
              >
                {item.icon}
              </span>
            </div>
            <span
              style={{
                fontWeight: 'bold',
                fontSize: 16,
                marginTop: 86,
                display: 'inline-block',
                color: theme === 'dark' ? Colors.Gray3 : '#333',
              }}
            >
              {item.label}
            </span>
            <br />
            <span
              style={{
                color: '#1D9BE2',
                fontSize: 16,
                marginTop: 5,
                display: 'inline-block',
              }}
            >
              {item.value}
            </span>
          </div>
        ))}
      </div>
    </Box>
  );
};

export default SensorAxisGrid;
