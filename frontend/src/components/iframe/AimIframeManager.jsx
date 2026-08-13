import React, { useState } from 'react';

import AimIframe from './AimIframe';

export default function AimIframeManager({ onLoadingChange }) {
  const [url, setUrl] = useState(
    'https://aim.koca.go.kr/eaipPub/Package/2025-11-26-AIRAC/html/index-en-GB.html?ver=2025',
  );

  console.log('AimIframeManager rendered with url:', url);

  return (
    <div style={{ width: '100%', height: '100vh' }}>
      <AimIframe
        url={url}
        onLoadingChange={onLoadingChange}
      />
    </div>
  );
}
