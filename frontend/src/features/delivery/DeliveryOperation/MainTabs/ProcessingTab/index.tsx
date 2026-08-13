import { Box } from '@mui/material';
import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';

import { Tabs } from '@/components/Form/Tabs';

import DeviceCheckTab from './DeviceCheckTab';
import PackageStatusTab from './PackageStatusTab';
import ReadyToShipTab from './ReadyToShipTab';
import SelectRouteTab from './SelectRouteTab';
import SelectTransitTab from './SelectTransitTab';

export default function ProcessingTab() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState(0);
  const [selectedOrderForNextTab, setSelectedOrderForNextTab] = useState<any>(
    null,
  );

  // Callback to navigate to a specific tab with order data
  const handleNavigateToTab = useCallback(
    (tabIndex: number, orderData?: any) => {
      console.log('📌 Navigating to tab:', tabIndex, 'with order:', orderData);
      setActiveTab(tabIndex);
      if (orderData) {
        setSelectedOrderForNextTab(orderData);
      }
    },
    [],
  );

  return (
    <Box px={'0.5rem'}>
      <Tabs
        activeTab={activeTab}
        onTabChange={setActiveTab}
        items={[
          {
            label: t('Ready to Ship'),
            content: (
              <ReadyToShipTab onNavigateToDeviceCheck={handleNavigateToTab} />
            ),
          },
          {
            label: t('Device Check'),
            content: (
              <DeviceCheckTab
                selectedOrderFromPrevTab={selectedOrderForNextTab}
                onNavigateToInTransit={handleNavigateToTab}
              />
            ),
          },
          {
            label: t('In Transit'),
            content: (
              <SelectTransitTab
                selectedOrderFromPrevTab={selectedOrderForNextTab}
              />
            ),
          },
          { label: t('Package Status'), content: <PackageStatusTab /> },
        ]}
      />
    </Box>
  );
}
