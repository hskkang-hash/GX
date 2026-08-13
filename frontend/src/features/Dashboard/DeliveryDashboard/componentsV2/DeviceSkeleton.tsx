import { Box, Skeleton } from '@mui/material';
import React from 'react';
import { useTheme } from 'rj-core';

const DeviceSkeleton: React.FC = () => {
  const [theme] = useTheme();

  return (
    <Box
      display="flex"
      flexDirection="column"
      flex={1}
    >
      {/* Title skeleton */}
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
        <Skeleton
          variant="text"
          width={30}
          height={30}
          sx={{
            bgcolor:
              theme === 'dark'
                ? 'rgba(255, 255, 255, 0.1)'
                : 'rgba(0, 0, 0, 0.1)',
          }}
        />
      </div>
      {/* Data items skeleton */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '1.5rem',
          flex: 1,
          height: '100%',
        }}
      >
        <Box
          display="flex"
          flexDirection="row"
          flexWrap="nowrap"
          justifyContent="space-between"
          gap="1rem"
          overflowX="hidden"
          flex={1}
          height="100%"
        >
          {Array.from({ length: 3 }).map((_, index) => (
            <Box
              key={index}
              style={{
                background:
                  theme === 'dark'
                    ? 'rgba(255, 255, 255, 0.1)'
                    : 'rgba(0, 0, 0, 0.1)',
                padding: 'clamp(0.5rem, 0.75vw, 1rem)',
                borderRadius: 12,
                minWidth: 0,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'space-between',
                height: '100%',
                flex: 1,
              }}
            >
              <Skeleton
                variant="text"
                width="60%"
                height={32}
                sx={{
                  bgcolor:
                    theme === 'dark'
                      ? 'rgba(255, 255, 255, 0.2)'
                      : 'rgba(0, 0, 0, 0.1)',
                }}
              />
              <Skeleton
                variant="text"
                width="60%"
                height={32}
                sx={{
                  bgcolor:
                    theme === 'dark'
                      ? 'rgba(255, 255, 255, 0.2)'
                      : 'rgba(0, 0, 0, 0.1)',
                }}
              />
              <Skeleton
                variant="text"
                width="60%"
                height={32}
                sx={{
                  bgcolor:
                    theme === 'dark'
                      ? 'rgba(255, 255, 255, 0.2)'
                      : 'rgba(0, 0, 0, 0.1)',
                }}
              />
            </Box>
          ))}
        </Box>
      </div>
    </Box>
  );
};

export default DeviceSkeleton;
