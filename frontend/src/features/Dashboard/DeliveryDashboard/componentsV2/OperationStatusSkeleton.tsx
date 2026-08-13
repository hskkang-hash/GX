import { Box, Skeleton } from '@mui/material';
import React from 'react';
import { useTheme } from 'rj-core';

const OperationStatusSkeleton: React.FC = () => {
  const [theme] = useTheme();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Title */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 15,
        }}
      >
        <Skeleton
          variant="text"
          width={150}
          height={32}
          sx={{
            bgcolor:
              theme === 'dark'
                ? 'rgba(255, 255, 255, 0.1)'
                : 'rgba(0, 0, 0, 0.1)',
          }}
        />
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton
              key={index}
              variant="text"
              width={50}
              height={30}
              sx={{
                bgcolor:
                  theme === 'dark'
                    ? 'rgba(255, 255, 255, 0.1)'
                    : 'rgba(0, 0, 0, 0.1)',
              }}
            />
          ))}
        </div>
      </div>
      {/* Data items skeleton */}
      <Box
        display="flex"
        flexDirection="row"
        flex={1}
        gap="1.5rem"
      >
        <Box
          flex={1}
          display="flex"
          flexDirection="column"
          gap="1rem"
        >
          {Array.from({ length: 2 }).map((_, index) => (
            <Box
              key={index}
              style={{
                background:
                  theme === 'dark'
                    ? 'rgba(255, 255, 255, 0.1)'
                    : 'rgba(0, 0, 0, 0.1)',
                padding: '0 clamp(0.5rem, 1vw, 2rem)',
                borderRadius: 12,
                display: 'flex',
                gap: '1rem',
                justifyContent: 'space-between',
                alignItems: 'center',
                height: '100%',
              }}
            >
              <Box
                style={{
                  background:
                    theme === 'dark'
                      ? 'rgba(255, 255, 255, 0.1)'
                      : 'rgba(0, 0, 0, 0.1)',
                  borderRadius: 12,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  height: '80%',
                  width: '25%',
                }}
              ></Box>
              <Box
                style={{
                  background:
                    theme === 'dark'
                      ? 'rgba(255, 255, 255, 0.1)'
                      : 'rgba(0, 0, 0, 0.1)',
                  borderRadius: 12,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  height: '80%',
                  width: '50%',
                }}
              ></Box>
              <Box
                style={{
                  background:
                    theme === 'dark'
                      ? 'rgba(255, 255, 255, 0.1)'
                      : 'rgba(0, 0, 0, 0.1)',
                  // padding: '0 clamp(0.5rem, 1vw, 2rem)',
                  borderRadius: 12,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  height: '80%',
                  width: '30%',
                }}
              ></Box>
              <Box
                style={{
                  background:
                    theme === 'dark'
                      ? 'rgba(255, 255, 255, 0.1)'
                      : 'rgba(0, 0, 0, 0.1)',
                  // padding: '0 clamp(0.5rem, 1vw, 2rem)',
                  borderRadius: 12,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  height: '80%',
                  width: '30%',
                }}
              ></Box>
            </Box>
          ))}
        </Box>
      </Box>
    </div>
  );
};

export default OperationStatusSkeleton;
