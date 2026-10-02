import { GCSFlight } from '@GCS';
import '@GCS/pages/flight/styles/index.scss';
// import '@GCS/pages/flight/styles/scoped-wrapper.scss';
import React from 'react';
import { Container, useTheme } from 'rj-core';

import i18n from '@/i18n';

import { gcsAccessKey } from './gcsAccess';

/**
 * GCS (Ground Control Station) Page Component
 */

const GCSPage: React.FC = () => {
  const [theme] = useTheme();
  const lng = i18n.language || 'en';

  // Get accessKey from URL params or environment variable
  // [WO-GRDX-20261002-10] GCS 키는 화면에 없다 — 우리 로그인 토큰 + 같은 출처 경유(`gcsAccess.ts`).
  const accessKey = gcsAccessKey();

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
