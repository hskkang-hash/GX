import { TFunction } from 'i18next';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { GoPlus } from 'react-icons/go';
import { useSelector } from 'react-redux';
import {
  NavigateFunction,
  useNavigate,
  useSearchParams,
} from 'react-router-dom';
import {
  checkHasReadPermission,
  Container,
  CustomBtn,
  getMenuByMainIdAndSubId,
  HeaderWithBtn,
  selectActiveMenuCombined,
  ToastTopHelper,
  useLoadingContext,
  useUserInfo,
} from 'rj-core';

import MainTabs from '@/components/Form/MainTabs';
import useSettings from '@/features/operationSetting/hooks/useSettings';
import { CustomRoutes } from '@/services/API';

import CancelledTab from './MainTabs/CancelledTab';
import CompletedTab from './MainTabs/CompletedTab';
import ProcessingTab from './MainTabs/ProcessingTab';
import ReturnedTab from './MainTabs/ReturnedTab';
import VerificationTab from './MainTabs/VerificationTab';

type TabKey =
  | 'verification'
  | 'processing'
  | 'completed'
  | 'returned'
  | 'cancelled';

interface TabConfig {
  label: string;
  content: React.ReactNode;
}

interface TabVisibility {
  key: TabKey;
  active: boolean;
}

const TAB_CONFIG: Record<TabKey, TabConfig> = {
  verification: {
    label: 'Verification',
    content: <VerificationTab />,
  },
  processing: {
    label: 'Processing',
    content: <ProcessingTab />,
  },
  completed: {
    label: 'Completed',
    content: <CompletedTab />,
  },
  returned: {
    label: 'Returned',
    content: <ReturnedTab />,
  },
  cancelled: {
    label: 'Cancelled',
    content: <CancelledTab />,
  },
} as const;

const ActionButton = ({
  tabKey,
  t,
  navigate,
  isSuperuser,
}: {
  tabKey: TabKey | undefined;
  t: TFunction;
  navigate: NavigateFunction;
  isSuperuser: boolean;
}) => {
  const actionMap = {
    verification: [
      <CustomBtn
        key="add-new-order"
        label={t('Add New Order')}
        icon={<GoPlus size={18} />}
        onClick={() =>
          isSuperuser
            ? ToastTopHelper.warning(
                t(
                  'System accounts cannot create orders. Please log in with a member account to use this feature.',
                ),
              )
            : navigate(
                CustomRoutes.deliveryOperation.subRoutes.addNewDeliveryInquiry
                  .path,
              )
        }
      />,
    ],
  };

  return tabKey ? actionMap[tabKey as keyof typeof actionMap] || [] : [];
};

export default function DeliveryOperation() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const headerPageRef = useRef(null);
  const { getOperationSettings } = useSettings();
  const [searchParams] = useSearchParams();

  const [activeTab, setActiveTab] = useState<TabKey>();
  const [visibleTabs, setVisibleTabs] = useState<TabKey[]>([]);
  const { activeItem, activeSubItem } = useSelector(selectActiveMenuCombined);
  const { showLoading, hideLoading } = useLoadingContext();
  const [isLoading, setIsLoading] = useState(true);
  const activeTabFromSearchParams = searchParams.get('tab') || '';
  const activeItemSession = activeItem;
  const activeSubItemSession = activeSubItem;
  const userInfo = useUserInfo();
  const isSuperuser = useMemo(
    () => userInfo?.roles?.some((role: any) => role.code === 'superuser'),
    [userInfo],
  );

  const currentMenu = getMenuByMainIdAndSubId(
    parseInt(activeItemSession),
    parseInt(activeSubItemSession),
  );

  const checkTabVisibility = async () => {
    const initialTabVisibility = [
      { key: 'verification', active: true },
      { key: 'processing', active: true },
      { key: 'completed', active: true },
      { key: 'returned', active: true },
      { key: 'cancelled', active: true },
    ];

    const { data } = await getOperationSettings({
      pageSize: 25,
      currentPage: 1,
    });

    let distinctActiveSettings: any[] = [];

    if (data?.length > 0) {
      const activeSettings = data.filter((item: any) => item.is_active);
      distinctActiveSettings = activeSettings.filter(
        (item, index, self) =>
          index === self.findIndex((t) => t.tab_name === item.tab_name),
      );
    }

    return initialTabVisibility.map((item) => ({
      ...item,
      active: distinctActiveSettings.some(
        (setting) => setting.tab_name.toLowerCase() === item.key.toLowerCase(),
      ),
    }));
  };

  const availableTabKeys = useMemo(() => {
    if (!currentMenu?.tabs) return [];
    return currentMenu.tabs
      .filter((tab) => checkHasReadPermission(tab))
      .map((tab) => {
        return {
          id: tab.id,
          path: tab.path.split('/')[2],
        };
      });
  }, [currentMenu?.tabs]);

  const tabItems = useMemo(() => {
    return availableTabKeys.map((key: { id: number; path: string }) => ({
      key: key.path,
      label: key.path,
      id: key.id,
    }));
  }, [availableTabKeys]);

  // Memoized translated tab items
  const translatedTabItems = useMemo(
    () =>
      tabItems.map((item: { key: TabKey; label: string; id: number }) => ({
        ...item,
        label: t(TAB_CONFIG[item.key as TabKey]?.label),
      })),
    [tabItems, t],
  );

  useEffect(() => {
    const fetchTabVisibility = async () => {
      showLoading();
      try {
        const tabVisibility = await checkTabVisibility();
        const activeTabs = tabVisibility
          .filter((tab) => tab.active)
          .map((tab) => tab.key);

        setVisibleTabs(activeTabs);
        // Set initial active tab to first visible tab
      } catch (error) {
        console.error('Failed to fetch tab visibility:', error);
        hideLoading();
      } finally {
        setIsLoading(false);
        hideLoading();
      }
    };

    fetchTabVisibility();
  }, []);

  const actionBtn = useMemo(() => {
    return ActionButton({ tabKey: activeTab, t, navigate, isSuperuser });
  }, [activeTab, t, navigate, isSuperuser]);

  // Set default tab if none is active
  useEffect(() => {
    if (
      (!activeTab ||
        activeTab === null ||
        !availableTabKeys?.find(
          (tab: { path: TabKey }) => tab.path === activeTab,
        )) &&
      availableTabKeys?.length > 0
    ) {
      let defaultTab = availableTabKeys[0];

      if (activeTab) {
        const savedTabId = parseInt(activeTab);
        const foundTab = availableTabKeys?.find(
          (tab: { id: number }) => tab.id === savedTabId,
        );
        if (foundTab) {
          defaultTab = foundTab;
        }
      }

      setActiveTab(defaultTab?.path);
    }
  }, [availableTabKeys, activeTab]);

  // Handle location state changes
  useEffect(() => {
    if (activeTab === undefined && activeTabFromSearchParams) {
      setActiveTab(activeTabFromSearchParams as TabKey);
    }
  }, [activeTabFromSearchParams]);

  const filteredTabs = useMemo(() => {
    return Object.entries(TAB_CONFIG)
      .filter(([key]) => visibleTabs.includes(key as TabKey))
      .map(([key, { label, content }]) => ({
        label,
        content,
        value: key,
      }));
  }, [visibleTabs]);

  // const ActiveTabComponent = useMemo(() => {
  //   const Component = TAB_CONFIG[activeTab as TabKey]?.content;
  //   return Component ? Component : null;
  // }, [activeTab]);

  return (
    <Container>
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={actionBtn}
        hasLineBottom={false}
      />
      <MainTabs
        items={filteredTabs}
        onTabChange={(key: string) => {
          setActiveTab(key as TabKey);
        }}
      />
      {/* <CustomTabs
        onChange={handleTabChange}
        size="small"
        items={translatedTabItems}
        activeKey={activeTab}
      /> */}
      {/* {ActiveTabComponent} */}
    </Container>
  );
}
