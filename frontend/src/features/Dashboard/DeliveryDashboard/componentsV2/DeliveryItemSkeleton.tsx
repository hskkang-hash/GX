import { Box, Skeleton } from '@mui/material';
import React from 'react';
import { useTheme } from 'rj-core';

const DeliveryItemSkeleton: React.FC = () => {
  const [theme] = useTheme();

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
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

      <Box
        flex={1}
        display="grid"
        gridTemplateColumns="repeat(3, 1fr)"
        gap="1rem"
        gridAutoRows="1fr"
      >
        {Array.from({ length: 6 }).map((_, index) => (
          <Box
            key={index}
            style={{
              background:
                theme === 'dark'
                  ? 'rgba(255, 255, 255, 0.1)'
                  : 'rgba(0, 0, 0, 0.1)',
              padding: 'clamp(0.5rem, 0.75vw, 1rem)',
              borderRadius: 12,
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              height: '100%',
              width: '100%',
            }}
          >
            <Skeleton
              variant="text"
              width="100%"
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
  );
};

export default DeliveryItemSkeleton;
