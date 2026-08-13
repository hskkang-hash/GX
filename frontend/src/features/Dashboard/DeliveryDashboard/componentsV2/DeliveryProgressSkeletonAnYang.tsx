import { Box, Skeleton } from '@mui/material';
import React from 'react';
import { useTheme } from 'rj-core';

const DeliveryProgressSkeletonAnYang: React.FC = () => {
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

      <div style={{ display: 'flex', flexDirection: 'row', height: '100%' }}>
        <div
          style={{
            flex: 1,
            display: 'flex',
            padding: '0 10px',
            gap: '3rem',
            margin: '0',
          }}
        >
          {/* Circle */}
          <div style={{ position: 'relative', width: '60%', height: '100%' }}>
            <Box
              sx={{
                position: 'relative',
                width: '100%',
                height: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Skeleton
                variant="circular"
                width="100%"
                height="100%"
                sx={{
                  bgcolor:
                    theme === 'dark'
                      ? 'rgba(255, 255, 255, 0.1)'
                      : 'rgba(0, 0, 0, 0.1)',
                }}
              />
              <Box
                sx={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  textAlign: 'center',
                }}
              >
                <Skeleton
                  variant="text"
                  width={60}
                  height={48}
                  sx={{
                    bgcolor:
                      theme === 'dark'
                        ? 'rgba(255, 255, 255, 0.1)'
                        : 'rgba(0, 0, 0, 0.1)',
                  }}
                />
              </Box>
            </Box>
          </div>
          <Box
            sx={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Skeleton
              variant="text"
              width="80%"
              height={30}
              sx={{
                bgcolor:
                  theme === 'dark'
                    ? 'rgba(255, 255, 255, 0.1)'
                    : 'rgba(0, 0, 0, 0.1)',
              }}
            />
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
          </Box>
        </div>

        <Box
          display="flex"
          flexDirection="column"
          flex={1}
        >
          <Box
            display="flex"
            flexDirection="row"
            flex={1}
            gap="1rem"
          >
            <Box
              flex={1}
              display="grid"
              gap="1rem"
              gridTemplateColumns={{
                xs: '1fr',
                sm: 'repeat(2, 1fr)',
              }}
              gridAutoRows="1fr"
            >
              {Array.from({ length: 3 }).map((_, index) => (
                <Box
                  key={index}
                  style={{
                    background:
                      theme === 'dark'
                        ? 'rgba(255, 255, 255, 0.1)'
                        : 'rgba(0, 0, 0, 0.1)',
                    gridColumn: index === 2 ? 'span 2' : 'auto',
                    padding: '0 15px',
                    borderRadius: 8,
                    display: 'flex',
                    flexDirection: index === 2 ? 'row' : 'column',
                    justifyContent: 'space-between',
                    alignItems: index === 2 ? 'center' : 'flex-start',
                  }}
                >
                  <Skeleton
                    variant="text"
                    width="40%"
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
                    width="20%"
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
      </div>
    </div>
  );
};

export default DeliveryProgressSkeletonAnYang;
