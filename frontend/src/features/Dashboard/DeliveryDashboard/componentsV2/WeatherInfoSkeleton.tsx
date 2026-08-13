import { Box, Skeleton } from '@mui/material';
import React from 'react';
import { useTheme } from 'rj-core';

const WeatherInfoSkeleton: React.FC = () => {
  const [theme] = useTheme();

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flex: 1,
      }}
    >
      {/* Updated Section Skeleton */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <Skeleton
            variant="text"
            width={60}
            height={24}
            sx={{
              bgcolor:
                theme === 'dark'
                  ? 'rgba(255, 255, 255, 0.1)'
                  : 'rgba(0, 0, 0, 0.1)',
            }}
          />
          <Skeleton
            variant="text"
            width={120}
            height={24}
            sx={{
              bgcolor:
                theme === 'dark'
                  ? 'rgba(255, 255, 255, 0.1)'
                  : 'rgba(0, 0, 0, 0.1)',
            }}
          />
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <Skeleton
            variant="text"
            width={60}
            height={24}
            sx={{
              bgcolor:
                theme === 'dark'
                  ? 'rgba(255, 255, 255, 0.1)'
                  : 'rgba(0, 0, 0, 0.1)',
            }}
          />
          <Skeleton
            variant="text"
            width={120}
            height={24}
            sx={{
              bgcolor:
                theme === 'dark'
                  ? 'rgba(255, 255, 255, 0.1)'
                  : 'rgba(0, 0, 0, 0.1)',
            }}
          />
        </Box>
        <Box
          sx={{
            paddingLeft: '1rem',
            borderLeft: `1px solid ${
              theme === 'dark'
                ? 'rgba(255, 255, 255, 0.1)'
                : 'rgba(0, 0, 0, 0.1)'
            }`,
          }}
        >
          <Skeleton
            variant="rectangular"
            width={27}
            height={27}
            sx={{
              borderRadius: '0.5rem',
              bgcolor:
                theme === 'dark'
                  ? 'rgba(255, 255, 255, 0.1)'
                  : 'rgba(0, 0, 0, 0.1)',
            }}
          />
        </Box>
      </Box>

      {/* Weather Section Skeleton */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
        <Skeleton
          variant="text"
          width={60}
          height={24}
          sx={{
            bgcolor:
              theme === 'dark'
                ? 'rgba(255, 255, 255, 0.1)'
                : 'rgba(0, 0, 0, 0.1)',
          }}
        />
        <Box sx={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <Skeleton
            variant="circular"
            width={20}
            height={20}
            sx={{
              bgcolor:
                theme === 'dark'
                  ? 'rgba(255, 255, 255, 0.1)'
                  : 'rgba(0, 0, 0, 0.1)',
            }}
          />
          <Skeleton
            variant="text"
            width={40}
            height={16}
            sx={{
              bgcolor:
                theme === 'dark'
                  ? 'rgba(255, 255, 255, 0.1)'
                  : 'rgba(0, 0, 0, 0.1)',
            }}
          />
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <Skeleton
            variant="circular"
            width={20}
            height={20}
            sx={{
              bgcolor:
                theme === 'dark'
                  ? 'rgba(255, 255, 255, 0.1)'
                  : 'rgba(0, 0, 0, 0.1)',
            }}
          />
          <Skeleton
            variant="text"
            width={40}
            height={16}
            sx={{
              bgcolor:
                theme === 'dark'
                  ? 'rgba(255, 255, 255, 0.1)'
                  : 'rgba(0, 0, 0, 0.1)',
            }}
          />
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <Skeleton
            variant="circular"
            width={20}
            height={20}
            sx={{
              bgcolor:
                theme === 'dark'
                  ? 'rgba(255, 255, 255, 0.1)'
                  : 'rgba(0, 0, 0, 0.1)',
            }}
          />
          <Skeleton
            variant="text"
            width={50}
            height={16}
            sx={{
              bgcolor:
                theme === 'dark'
                  ? 'rgba(255, 255, 255, 0.1)'
                  : 'rgba(0, 0, 0, 0.1)',
            }}
          />
        </Box>
      </Box>

      {/* Region Section Skeleton */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <Skeleton
          variant="text"
          width={60}
          height={24}
          sx={{
            bgcolor:
              theme === 'dark'
                ? 'rgba(255, 255, 255, 0.1)'
                : 'rgba(0, 0, 0, 0.1)',
          }}
        />
        <Skeleton
          variant="text"
          width={80}
          height={24}
          sx={{
            bgcolor:
              theme === 'dark'
                ? 'rgba(255, 255, 255, 0.1)'
                : 'rgba(0, 0, 0, 0.1)',
          }}
        />
      </Box>
    </Box>
  );
};

export default WeatherInfoSkeleton;
