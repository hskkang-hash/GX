import { GCSFlight, DroneNotificationPanel } from '@GCS';
import '@GCS/pages/flight/styles/index.scss';
import { Box } from '@mui/material';
import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';
import { Container, CustomBreadcrumb, Main, useTheme } from 'rj-core';

import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';
import i18n from '@/i18n';
import { CustomRoutes } from '@/services/API';

import AIDetectionPanel from './components/AIDetectionPanel';

/**
 * Surveillance GCS (Ground Control Station) Page Component
 *
 * This component renders the GCS interface with telemetry filtered by surveillance profile group ID.
 * The groupId is passed via URL search params (e.g., ?groupId=123)
 */
const SurveillanceGCSPage: React.FC = () => {
  const [theme] = useTheme();
  const lng = i18n.language || 'en';
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();

  // Get URL params
  const profileId = searchParams.get('profileId');
  const groupId = searchParams.get('groupId');
  const missionName = searchParams.get('mission');
  const accessKey = searchParams.get('accessKey') ?? import.meta.env.VITE_CGS_APIKEY ?? undefined;
  const { timeZoneFormat } = useConvertDate();
  // Get AI stream URL from environment
  const aiStreamUrl =
    import.meta.env.VITE_AI_STREAM_WS_URL || 'wss://media-ai-svc.gaion.dev';

  // State to store selected drone IDs from GCS-FE
  const [selectedDroneIds, setSelectedDroneIds] = React.useState<string[]>([]);

  // Callback to receive selected drone IDs from GCS-FE
  const handleSelectedDronesChange = React.useCallback((droneIds: string[]) => {
    console.log('📡 Selected drones from GCS-FE:', droneIds);
    setSelectedDroneIds(droneIds);
  }, []);

  return (
    <Container
      id="surveillance-gcs-page"
      className={`gcs-page surveillance-gcs-page bg-${theme === 'dark' ? 'black' : 'light'}`}
    >
      <CustomBreadcrumb
        items={[
          {
            url: CustomRoutes.surveyProfile.path,
          },
          {
            text: t('Surveillance GCS'),
            url: CustomRoutes.surveyProfile.path + '?tab=processing&subtab=2',
          },
          { text: missionName ?? undefined },
        ]}
      />
      <Main>
        <Box
          sx={{
            display: 'flex',
            height: '100vh',
            gap: 2,
          }}
        >
          {/* GCS Flight Section */}
          <Box
            sx={{
              flex: 1,
              borderRadius: '10px',
              minWidth: 0,
              overflow: 'hidden',
            }}
          >
            <div
              className="gcs-container gcs-page-content"
              style={{ height: '100%', position: 'relative' }}
            >
              <GCSFlight
                theme={theme}
                lng={lng}
                profileId={profileId || undefined}
                viewMode="mission"
                onSelectedDronesChange={handleSelectedDronesChange}
                accessKey={accessKey}
              />
            </div>
          </Box>

          {/* Notification Panel Section */}
          <Box
            sx={{
              width: '18%',
              maxWidth: '350px',
              flexShrink: 0,
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
            }}
          >
            {/* Drone Notifications - 50% height (SSE-based) */}
            <Box
              sx={{
                height: 'calc(50% - 0.5rem)',
              }}
            >
              <DroneNotificationPanel
                droneIds={selectedDroneIds}
                maxNotifications={100}
                title={t('Drone Notifications')}
                timeZoneFormat={timeZoneFormat}
              />
            </Box>

            {/* AI Detection Notifications - 50% height */}
            <Box
              sx={{
                height: 'calc(50% - 0.5rem)',
              }}
            >
              <AIDetectionPanel
                droneIds={selectedDroneIds}
                aiStreamUrl={aiStreamUrl}
                maxNotifications={100}
                title={t('AI Detections')}
              />
            </Box>
          </Box>
        </Box>
      </Main>
    </Container>
  );
};

export default SurveillanceGCSPage;
