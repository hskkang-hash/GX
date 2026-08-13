import { Box, Skeleton } from '@mui/material';
import React from 'react';
import { useTheme } from 'rj-core';

const NotificationsSkeleton: React.FC = () => {
    const [theme] = useTheme();

    return (
        <Box
            display="flex"
            flexDirection="column"
            flex={1}
            gap="1rem"
        >
            {/* Title skeleton */}
            <div
                style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
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
                flexDirection="column"
                flex={1}
                gap="1rem"
            >
                <Box
                    flex={1}
                    display="flex"
                    flexDirection="column"
                    gap="1rem"
                >
                    {Array.from({ length: 4 }).map((_, index) => (
                        <Box
                            key={index}
                            style={{
                                background:
                                    theme === 'dark'
                                        ? 'rgba(255, 255, 255, 0.1)'
                                        : 'rgba(0, 0, 0, 0.1)',
                                padding: '0 15px',
                                borderRadius: 8,
                            }}
                        >
                            <div style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                            }}>
                                <Skeleton
                                    variant="text"
                                    width={30}
                                    height={50}
                                    sx={{
                                        bgcolor:
                                            theme === 'dark'
                                                ? 'rgba(255, 255, 255, 0.2)'
                                                : 'rgba(0, 0, 0, 0.1)',
                                    }}
                                />
                                <Skeleton
                                    variant="text"
                                    width="40%"
                                    height={40}
                                    sx={{
                                        bgcolor:
                                            theme === 'dark'
                                                ? 'rgba(255, 255, 255, 0.2)'
                                                : 'rgba(0, 0, 0, 0.1)',
                                    }}
                                />
                            </div>
                            <Skeleton
                                variant="text"
                                width="100%"
                                height={40}
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

export default NotificationsSkeleton;
