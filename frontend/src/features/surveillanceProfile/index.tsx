import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { GoPlus } from 'react-icons/go';
import { useSelector } from 'react-redux';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  checkHasReadPermission,
  Container,
  CustomBtn,
  CustomTabs,
  getMenuByMainIdAndSubId,
  HeaderWithBtn,
  ROLE_PERMISSION,
  selectActiveMenuCombined,
  ToastTopHelper,
} from 'rj-core';

import { CheckRoleAccount } from '@/utils/CheckRoleAccount';

import { CustomRoutes } from '../../services/API';
import CancelledTab from './MainTabs/CancelledTab';
import CompletedTab from './MainTabs/CompletedTab';
import ProcessingTab from './MainTabs/ProcessingTab';

type TabKey = 'processing' | 'completed' | 'cancelled';

interface TabConfig {
  label: string;
  content: React.ReactNode;
}

const isValidTabKey = (value: string | null): value is TabKey => {
  return (
    value === 'processing' || value === 'completed' || value === 'cancelled'
  );
};

export default function SurveillanceProfile() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const headerPageRef = useRef<HTMLDivElement | null>(null);
  const { activeItem, activeSubItem } = useSelector(selectActiveMenuCombined);
  const activeTabFromSearchParams = searchParams.get('tab');
  const activeItemSession = activeItem;
  const activeSubItemSession = activeSubItem;
  const currentMenu = getMenuByMainIdAndSubId(
    parseInt(activeItemSession),
    parseInt(activeSubItemSession),
  );

  const TAB_CONFIG: Record<TabKey, TabConfig> = useMemo(
    () => ({
      processing: {
        label: 'Processing',
        content: <ProcessingTab />,
      },
      completed: {
        label: 'Completed',
        content: (
          <CompletedTab
            headerPageRef={headerPageRef as React.RefObject<HTMLDivElement>}
          />
        ),
      },
      cancelled: {
        label: 'Cancelled/Rejected',
        content: (
          <CancelledTab
            headerPageRef={headerPageRef as React.RefObject<HTMLDivElement>}
          />
        ),
      },
    }),
    [headerPageRef],
  );

  const [activeKey, setActiveKey] = useState<TabKey | null>(
    isValidTabKey(activeTabFromSearchParams) ? activeTabFromSearchParams : null,
  );

  const availableTabKeys = useMemo(() => {
    if (!currentMenu?.tabs) return [];
    return currentMenu.tabs
      .filter((tab: { id: number; path: string }) =>
        checkHasReadPermission(tab),
      )
      .map((tab: { id: number; path: string }) => ({
        id: tab.id,
        path: tab.path.split('/')[2],
      }));
  }, [currentMenu?.tabs]);

  // Validate and set correct tab from URL or default
  useEffect(() => {
    if (availableTabKeys.length === 0) return;

    const tabParam = searchParams.get('tab');
    const isValidTab = isValidTabKey(tabParam);
    const isTabInAvailableTabs =
      isValidTab &&
      availableTabKeys.some((tab: { path: string }) => tab.path === tabParam);

    // Case 1: Invalid tab or tab not in available tabs - set default
    if ((tabParam && !isValidTab) || (tabParam && !isTabInAvailableTabs)) {
      const defaultTab = availableTabKeys[0];
      const validTabKey = isValidTabKey(defaultTab.path)
        ? defaultTab.path
        : null;

      if (validTabKey) {
        setActiveKey(validTabKey);
        setSearchParams((prev) => {
          const params = Object.fromEntries(prev);
          // Only update if the tab param is different to avoid infinite loop
          if (params.tab !== validTabKey) {
            params.tab = validTabKey;
            return params;
          }
          return prev;
        });
      }
    }
    // Case 2: Valid tab in available tabs - sync activeKey
    else if (isValidTab && isTabInAvailableTabs && activeKey !== tabParam) {
      setActiveKey(tabParam);
    }
    // Case 3: No tab in URL and no activeKey - set default
    else if (!tabParam && !activeKey) {
      const defaultTab = availableTabKeys[0];
      const validTabKey = isValidTabKey(defaultTab.path)
        ? defaultTab.path
        : null;

      if (validTabKey) {
        setActiveKey(validTabKey);
        setSearchParams((prev) => {
          const params = Object.fromEntries(prev);
          params.tab = validTabKey;
          return params;
        });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [availableTabKeys, activeTabFromSearchParams]);

  const tabItems = useMemo(() => {
    return availableTabKeys.map((key: { id: number; path: string }) => ({
      key: key.path,
      label: t(TAB_CONFIG[key.path as TabKey]?.label),
      id: key.id,
    }));
  }, [availableTabKeys, t, TAB_CONFIG]);

  const filteredTabs = useMemo(() => {
    return Object.entries(TAB_CONFIG)
      .filter(([key]) =>
        availableTabKeys
          .map((tab: { path: string }) => tab.path)
          .includes(key as TabKey),
      )
      .map(([key, { label, content }]) => ({
        label,
        content,
        value: key,
      }));
  }, [availableTabKeys, TAB_CONFIG]);

  const ActiveTabComponent = useMemo(() => {
    const Component = filteredTabs.find(
      (item) => item.value === activeKey,
    )?.content;
    return Component || null;
  }, [activeKey, filteredTabs]);

  const isRoleSuperuser = CheckRoleAccount('superuser');

  return (
    <Container>
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[
          <CustomBtn
            label={t('Add New Profile')}
            icon={<GoPlus size={18} />}
            actionType={ROLE_PERMISSION.CREATE}
            onClick={() => {
              if (isRoleSuperuser) {
                ToastTopHelper.warning(
                  t(
                    'System accounts cannot create profiles. Please log in with a member account to use this feature.',
                  ),
                );
                return;
              } else {
                navigate(
                  CustomRoutes.surveyProfile.subRoutes.addNewSurveyProfile
                    .path +
                    '?tab=' +
                    (activeKey || 'processing'),
                );
              }
            }}
          />,
        ]}
        hasLineBottom={false}
      />
      <CustomTabs
        onChange={(key: string) => {
          if (!isValidTabKey(key)) {
            return;
          }

          const params = Object.fromEntries(searchParams);

          // Remove subtab parameter when switching to Completed or Cancelled tabs
          // (only Processing tab has subtabs)
          if (key !== 'processing' && params.subtab) {
            delete params.subtab;
          }

          setSearchParams({
            ...params,
            tab: key,
          });
          setActiveKey(key);
        }}
        size="small"
        items={tabItems}
        activeKey={activeKey || undefined}
      />
      {ActiveTabComponent}
    </Container>
  );
}
