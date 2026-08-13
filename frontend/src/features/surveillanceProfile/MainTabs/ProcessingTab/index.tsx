import { Box } from '@mui/material';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';

import { Tabs } from '@/components/Form/Tabs';

import DeviceCheckTab from './DeviceCheckTab';
import SurveillanceGCSTab from './SurveillanceGCSTab';
import SurveillanceProfileTab from './SurveillanceProfileTab/SurveillanceProfileTabOptimized';

export default function ProcessingTab() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const subtabParam = searchParams.get('subtab');
  const [activeSubTab, setActiveSubTab] = useState<number>(
    subtabParam ? parseInt(subtabParam) : 0,
  );

  // Update active sub-tab when URL parameter changes
  useEffect(() => {
    if (subtabParam) {
      const tabIndex = parseInt(subtabParam);
      if (tabIndex >= 0 && tabIndex <= 2) {
        setActiveSubTab(tabIndex);
      }
    }
  }, [subtabParam]);

  const handleTabChange = (index: number) => {
    setActiveSubTab(index);
    // Update URL with subtab parameter
    const params = new URLSearchParams(searchParams);
    params.set('subtab', index.toString());
    setSearchParams(params);
  };

  return (
    <Box px={'0.5rem'}>
      <Tabs
        activeTab={activeSubTab}
        onTabChange={handleTabChange}
        items={[
          {
            label: t('Surveillance Profile'),
            content: <SurveillanceProfileTab />,
          },
          { label: t('Device Check'), content: <DeviceCheckTab /> },
          { label: t('Surveillance GCS'), content: <SurveillanceGCSTab /> },
        ]}
      />
    </Box>
  );
}
