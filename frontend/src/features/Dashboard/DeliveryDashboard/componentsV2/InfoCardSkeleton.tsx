import { Box, Skeleton } from '@mui/material';
import React from 'react';
import { useTheme } from 'rj-core';

const InfoCardSkeleton: React.FC = () => {
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
                justifyContent: 'space-between',
                alignItems: 'center',
                height: '100%',
              }}
            >
              <Skeleton
                variant="text"
                width={60}
                height={30}
                sx={{
                  bgcolor:
                    theme === 'dark'
                      ? 'rgba(255, 255, 255, 0.2)'
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
                      ? 'rgba(255, 255, 255, 0.2)'
                      : 'rgba(0, 0, 0, 0.1)',
                }}
              />
            </Box>
          ))}
        </Box>

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
            width: 80,
            height: 80,
            margin: 'auto 0',
          }}
        >
          <Skeleton
            variant="circular"
            width={40}
            height={30}
            sx={{
              bgcolor:
                theme === 'dark'
                  ? 'rgba(255, 255, 255, 0.2)'
                  : 'rgba(0, 0, 0, 0.1)',
            }}
          />
        </Box>
      </Box>
    </Box>
  );
};

export default InfoCardSkeleton;
