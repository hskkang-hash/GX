import { Box, Tab as MUITab, Tabs as MUITabs } from '@mui/material';
import { styled } from '@mui/material/styles';
import { ReactNode, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSelector } from 'react-redux';
import { useSearchParams } from 'react-router-dom';
import {
  checkHasReadPermission,
  CustomTabs,
  getMenuByMainIdAndSubId,
  selectActiveMenuCombined,
} from 'rj-core';

const StyledMainTabs = styled(MUITabs)({
  minHeight: '48px',
  borderBottom: '1px solid #E5E7EB', // xám nhạt
  '.MuiTabs-indicator': {
    display: 'none', // Ẩn indicator mặc định
  },
  background: 'transparent',
});

const StyledMainTab = styled(MUITab)({
  textTransform: 'none',
  minHeight: '48px',
  fontWeight: 400,
  fontSize: '1.25rem',
  color: '#B0B0B0',
  background: 'transparent',
  border: 'none',
  borderRadius: '12px 12px 0 0',
  padding: '0 1rem',

  zIndex: 1,
  '&:first-of-type': {
    marginLeft: '0.5rem',
  },
  '&.Mui-selected': {
    color: '#222',
    border: '1.5px solid #E5E7EB',
    borderBottom: 'none',
    fontWeight: 600,
    boxShadow: '0px 2px 8px 0px rgba(0,0,0,0.02)',
  },
});

export interface MainTabItem {
  label: string;
  content: ReactNode;
  value: string;
}

interface MainTabsProps {
  items: MainTabItem[];
  activeTab?: number;
  onTabChange?: (key: string) => void;
}

export default function MainTabs({
  items,
  activeTab,
  onTabChange,
}: MainTabsProps) {
  const { t } = useTranslation();
  const [internalValue, setInternalValue] = useState(0);
  const [searchParams, setSearchParams] = useSearchParams();
  const value = activeTab ?? internalValue;

  const {
    activeItem,
    activeSubItem,
    activeTab: activeTabFromSession,
  } = useSelector(selectActiveMenuCombined);

  const activeItemSession = activeItem;
  const activeSubItemSession = activeSubItem;
  const activeTabSession = activeTabFromSession;

  const currentMenu = getMenuByMainIdAndSubId(
    parseInt(activeItemSession),
    parseInt(activeSubItemSession),
  );

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
    const itemValues = new Set(items.map((item) => item.value));
    return availableTabKeys
      .filter((key) => itemValues.has(key.path))
      .map((key) => {
        const tab = items.find((item) => item.value === key.path);
        return {
          key: key.path,
          label: tab ? t(tab.label) : '',
          id: key.id,
        };
      });
  }, [availableTabKeys, items]);

  // Lấy activeKey từ searchParams, nếu không hợp lệ thì lấy tab đầu tiên
  const activeKey = useMemo(() => {
    const tabParam = searchParams.get('tab');
    const foundTab = tabItems.find((tab) => tab.key === tabParam);
    if (foundTab) return tabParam;
    if (tabItems.length > 0) return tabItems[0].key;
    return null;
  }, [searchParams, tabItems]);

  useEffect(() => {
    onTabChange?.(activeKey);
  }, [activeKey]);

  // Khi tabItems thay đổi, đảm bảo searchParams hợp lệ
  useEffect(() => {
    const tabParam = searchParams.get('tab');
    const foundTab = tabItems.find((tab) => tab.key === tabParam);
    if (!foundTab && tabItems.length > 0) {
      setSearchParams({
        ...Object.fromEntries(searchParams),
        tab: tabItems[0].key,
      });
      onTabChange?.(tabItems[0].key);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tabItems]);

  const ActiveTabComponent = useMemo(() => {
    const Component = items.find((item) => item.value === activeKey)?.content;
    return Component ? Component : null;
  }, [activeKey, items]);
  return (
    <Box>
      {activeKey && (
        <>
          <CustomTabs
            onChange={(key) => {
              setSearchParams({
                ...Object.fromEntries(searchParams),
                tab: key,
              });
              onTabChange?.(key);
            }}
            size="small"
            items={tabItems}
            activeKey={activeKey}
          />
          {ActiveTabComponent}
        </>
      )}
    </Box>
  );
}
