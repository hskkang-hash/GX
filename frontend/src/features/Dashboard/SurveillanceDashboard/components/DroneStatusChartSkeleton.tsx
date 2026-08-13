import { Box, Skeleton } from '@mui/material';
import React from 'react';
import { useTheme } from 'rj-core';

const DroneStatusChartSkeleton: React.FC = () => {
    const [theme] = useTheme();
    return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Skeleton
                variant="text"
                width="60%"
                height={32}
                sx={{
                    mb: 2,
                    bgcolor:
                        theme === 'dark'
                            ? 'rgba(255, 255, 255, 0.1)'
                            : 'rgba(0, 0, 0, 0.1)',
                }}
            />
            <div style={{ flex: 1 }}>
                {/* Chart area skeleton */}
                <Box
                    sx={{
                        width: '100%',
                        height: '100%',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                    }}
                >
                    {/* Y-axis labels */}
                    <Box
                        sx={{
                            display: 'flex',
                            flexDirection: 'column',
                            gap: 1,
                            height: '100%',
                        }}
                    >
                        {Array.from({ length: 5 }).map((_, index) => (
                            <Box
                                key={index}
                                sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
                            >
                                <Skeleton
                                    variant="text"
                                    width={30}
                                    height={16}
                                    sx={{
                                        bgcolor:
                                            theme === 'dark'
                                                ? 'rgba(255, 255, 255, 0.1)'
                                                : 'rgba(0, 0, 0, 0.1)',
                                    }}
                                />
                                <Skeleton
                                    variant="rectangular"
                                    width="100%"
                                    height={1}
                                    sx={{
                                        bgcolor:
                                            theme === 'dark'
                                                ? 'rgba(255, 255, 255, 0.1)'
                                                : 'rgba(0, 0, 0, 0.1)',
                                    }}
                                />
                            </Box>
                        ))}
                    </Box>

                    {/* X-axis labels */}
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                        {Array.from({ length: 4 }).map((_, index) => (
                            <Skeleton
                                key={index}
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
                        ))}
                    </Box>
                </Box>
            </div>
        </div>
    );
};

export default DroneStatusChartSkeleton;
