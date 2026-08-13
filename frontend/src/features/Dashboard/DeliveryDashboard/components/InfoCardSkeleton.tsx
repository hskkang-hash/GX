import { Box, Skeleton } from '@mui/material';
import React from 'react';
import { useTheme } from 'rj-core';

const InfoCardSkeleton: React.FC = () => {
  const [theme] = useTheme();

  return (
    <Box
      display="flex"
      flexDirection="column"
      gap="1.25rem"
      flex={1}
    >
      {/* Icon skeleton */}
      <Box
        style={{
          background:
            theme === 'dark'
              ? 'rgba(255, 255, 255, 0.1)'
              : 'rgba(0, 0, 0, 0.1)',
          borderRadius: '50%',
          padding: '2rem',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 64,
          height: 64,
        }}
      >
        <Skeleton
          variant="circular"
          width={32}
          height={32}
          sx={{
            bgcolor:
              theme === 'dark'
                ? 'rgba(255, 255, 255, 0.2)'
                : 'rgba(0, 0, 0, 0.2)',
          }}
        />
      </Box>

      {/* Title skeleton */}
      <Skeleton
        variant="text"
        width="80%"
        height={32}
        sx={{
          bgcolor:
            theme === 'dark'
              ? 'rgba(255, 255, 255, 0.1)'
              : 'rgba(0, 0, 0, 0.1)',
        }}
      />

      {/* Data items skeleton */}
      <Box
        display="flex"
        flexDirection="column"
        gap="1rem"
        style={{ marginTop: '0.5rem', flex: 1 }}
      >
        {Array.from({ length: 3 }).map((_, index) => (
          <Box
            key={index}
            style={{
              background:
                theme === 'dark'
                  ? 'rgba(255, 255, 255, 0.1)'
                  : 'rgba(0, 0, 0, 0.1)',
              padding: '1rem 1.25rem',
              borderRadius: 12,
              display: 'flex',
              flex: 1,
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <Skeleton
              variant="text"
              width="60%"
              height={24}
              sx={{
                bgcolor:
                  theme === 'dark'
                    ? 'rgba(255, 255, 255, 0.2)'
                    : 'rgba(0, 0, 0, 0.2)',
              }}
            />
            <Skeleton
              variant="text"
              width={40}
              height={32}
              sx={{
                bgcolor:
                  theme === 'dark'
                    ? 'rgba(255, 255, 255, 0.2)'
                    : 'rgba(0, 0, 0, 0.2)',
              }}
            />
          </Box>
        ))}
      </Box>
    </Box>
  );
};

export default InfoCardSkeleton;
