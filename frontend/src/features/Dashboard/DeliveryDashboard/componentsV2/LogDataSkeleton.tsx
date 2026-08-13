import { Box, Skeleton } from '@mui/material';
import React from 'react';
import { useTheme } from 'rj-core';

const LogDataSkeleton: React.FC = () => {
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

      <Box
        display="flex"
        flexDirection="row"
        flex={1}
        gap="1rem"
      >
        {/* Data items skeleton */}
        <Box
          display="grid"
          gridTemplateColumns="repeat(2, 1fr)"
          gap="1rem"
          style={{
            marginTop: '0.5rem',
            flex: 1,
            width: '100%',
            height: '100%',
          }}
        >
          {Array.from({ length: 2 }).map((_, index) => (
            <Box
              key={index}
              style={{
                background:
                  theme === 'dark'
                    ? 'rgba(255, 255, 255, 0.1)'
                    : 'rgba(0, 0, 0, 0.1)',
                justifyContent: 'center',
                alignItems: 'center',
                borderRadius: 12,
                display: 'flex',
                height: '100%',
                flex: 1,
                flexDirection: 'column',
                gap: '0.5rem',
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
      </Box>
    </Box>
  );
};

export default LogDataSkeleton;
