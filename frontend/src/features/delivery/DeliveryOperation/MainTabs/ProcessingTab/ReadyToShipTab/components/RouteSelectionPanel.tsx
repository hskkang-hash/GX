import { Box, CircularProgress, Radio, Typography } from '@mui/material';
import { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '@/configs/Colors';

interface Route {
  id: number;
  route_name: string;
  route_description: string;
  route_distance?: string;
  route_duration?: string;
  routes: string;
}

interface RouteSelectionPanelProps {
  routes: Route[];
  selectedRouteId: number | null;
  isLoading: boolean;
  onRouteSelect: (routeId: number) => void;
}

export const RouteSelectionPanel = memo(
  ({
    routes,
    selectedRouteId,
    isLoading,
    onRouteSelect,
  }: RouteSelectionPanelProps) => {
    const { t } = useTranslation();
    const [theme] = useTheme();

    return (
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <Typography
          variant="h6"
          fontWeight={600}
          fontSize={'1.25rem'}
        >
          {t('Select Route')}
        </Typography>

        <Box sx={{ flex: 1, overflowY: 'auto' }}>
          {routes.length === 0 && !isLoading && (
            <Box
              sx={{
                marginTop: '1rem',
                color: theme === 'dark' ? Colors.Gray5 : '#9C9D9D',
              }}
            >
              {t(
                "Sorry! We couldn't find a matching route for your selected order. Please review your order details or try again shortly.",
              )}
            </Box>
          )}
          {routes.map((route, index) => (
            <Box
              key={`${route.id}-${index}`}
              mb={2}
              p={0}
              onClick={() => onRouteSelect(route.id)}
              sx={{
                border: '1.5px solid',
                borderColor: theme === 'dark' ? '#444646' : '#DDDFE2',
                borderRadius: 2,
                background:
                  selectedRouteId === route.id
                    ? theme === 'dark'
                      ? '#2D2E30'
                      : '#f7fafd'
                    : theme === 'dark'
                      ? '#2D2E30'
                      : '#fafbfc',
                transition: 'border-color 0.2s, background 0.2s',
              }}
            >
              <Box
                display="flex"
                alignItems="center"
                sx={{ cursor: 'pointer' }}
              >
                <Radio
                  checked={selectedRouteId === route.id}
                  className={`custom-radio1 ${theme}`}
                />
                <Typography
                  variant="body1"
                  sx={{
                    color: theme === 'dark' ? Colors.Gray3 : Colors.Gray6,
                  }}
                >
                  {route.route_name}
                  {route.route_distance && route.route_duration
                    ? ` - ${route.route_distance} - ${route.route_duration}`
                    : ''}
                </Typography>
              </Box>
              {selectedRouteId === route?.id && (
                <Box
                  px={2}
                  py={1}
                  color="#b0b0b0"
                  fontSize="0.95rem"
                  sx={{
                    borderTop: '1.5px solid',
                    borderColor: theme === 'dark' ? '#444646' : '#DDDFE2',
                    background: theme === 'dark' ? '#1F1F20' : '#fff',
                    borderRadius: 2,
                    borderTopLeftRadius: 0,
                    borderTopRightRadius: 0,
                  }}
                >
                  {route.routes}
                </Box>
              )}
            </Box>
          ))}

          {isLoading && (
            <Box
              display="flex"
              justifyContent="center"
              p={2}
            >
              <CircularProgress size={24} />
            </Box>
          )}
        </Box>
      </Box>
    );
  },
);

RouteSelectionPanel.displayName = 'RouteSelectionPanel';
