import { GCSFlight } from '@GCS';
import '@GCS/pages/flight/styles/index.scss';
// import '@GCS/pages/flight/styles/scoped-wrapper.scss';
import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { Container, useTheme } from 'rj-core';

import i18n from '@/i18n';

/**
 * GCS (Ground Control Station) Page Component
 */

const GCSPage: React.FC = () => {
  const [theme] = useTheme();
  const lng = i18n.language || 'en';
  const [searchParams] = useSearchParams();

  // Get accessKey from URL params or environment variable
  const accessKey = searchParams.get('accessKey') ?? import.meta.env.VITE_CGS_APIKEY ?? undefined;

  return (
    <Container
      id="gcs-page"
      className={`gcs-page bg-${theme === 'dark' ? 'black' : 'light'}`}
    >
      <div
        className="gcs-container gcs-page-content"
        style={{ width: '100%', height: '100vh' }}
      >
        <GCSFlight
          theme={theme}
          lng={lng}
          accessKey={accessKey}
        />
      </div>
    </Container>
  );
};

export default GCSPage;
