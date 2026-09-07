import dayjs from 'dayjs';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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

import { CustomRoutes } from '../../../services/API';
import { CsvSettingsModal } from '../components/CsvSettingsModal';
import {
  COLUMNS_COMPLETED_NOTICE,
  COLUMNS_NOTICE_MANAGEMENT,
} from '../dataExample';
import { useHandover } from '../hooks/useHandover';
import CompletedNotice from './tabs/CompletedNotice';
import HandoverManagement from './tabs/HandoverManagement';
import NoticeManagement from './tabs/NoticeManagement';
import { failureLine } from '@/features/session/apiFailure';

type TabKey = 'handover-management' | 'notice-management' | 'completed-notice';

interface TabConfig {
  label: string;
  content: React.ReactNode;
}

const isValidTabKey = (value: string | null): value is TabKey => {
  return (
    value === 'handover-management' ||
    value === 'notice-management' ||
    value === 'completed-notice'
  );
};

export const HandoverPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTabFromSearchParams = searchParams.get('tab');
  const [activeKey, setActiveKey] = useState<TabKey | null>(
    isValidTabKey(activeTabFromSearchParams) ? activeTabFromSearchParams : null,
  );
  const [searchDateTime, setSearchDateTime] = useState<{
    startDate: dayjs.Dayjs | null;
    endDate: dayjs.Dayjs | null;
  }>({
    startDate: dayjs().subtract(7, 'day'),
    endDate: dayjs(),
  });
  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);
  const [showCreateHandover, setShowCreateHandover] = useState<boolean>(false);
  const [showCsvSettingsModal, setShowCsvSettingsModal] =
    useState<boolean>(false);
  const [objSearchNotice, setObjSearchNotice] = useState<any>({});
  const [objSearchCompleted, setObjSearchCompleted] = useState<any>({});
  const headerPageRef = useRef<HTMLElement | null>(null);
  const { activeItem, activeSubItem } = useSelector(
    selectActiveMenuCombined,
  ) as {
    activeItem: string;
    activeSubItem: string;
  };
  const activeItemSession = activeItem;
  const activeSubItemSession = activeSubItem;
  const currentMenu = getMenuByMainIdAndSubId(
    parseInt(activeItemSession),
    parseInt(activeSubItemSession),
  );

  const {
    sliderData,
    getSliderDataAPI,
    downloadHandoverAPI,
    downloadNoticeAPI,
    downloadCompletedNoticeAPI,
  } = useHandover();

  useEffect(() => {
    getSliderDataAPI();
  }, []);

  const TAB_CONFIG: Record<TabKey, TabConfig> = useMemo(
    () => ({
      'handover-management': {
        label: 'handover.Handover Management',
        content: (
          <HandoverManagement
            headerPageRef={headerPageRef}
            openOffcanvas={openOffcanvas}
            setOpenOffcanvas={setOpenOffcanvas}
            showCreateHandover={showCreateHandover}
            setShowCreateHandover={setShowCreateHandover}
            sliderData={sliderData}
            getSliderDataAPI={getSliderDataAPI}
            searchDateTime={searchDateTime}
            setSearchDateTime={setSearchDateTime}
          />
        ),
      },
      'notice-management': {
        label: 'handover.Notice Management',
        content: (
          <NoticeManagement
            headerPageRef={headerPageRef}
            openOffcanvas={openOffcanvas}
            setOpenOffcanvas={setOpenOffcanvas}
            sliderData={sliderData}
            getSliderDataAPI={getSliderDataAPI}
            onObjSearchChange={setObjSearchNotice}
          />
        ),
      },
      'completed-notice': {
        label: 'handover.Completed Notice',
        content: (
          <CompletedNotice
            headerPageRef={headerPageRef}
            openOffcanvas={openOffcanvas}
            setOpenOffcanvas={setOpenOffcanvas}
            sliderData={sliderData}
            getSliderDataAPI={getSliderDataAPI}
            onObjSearchChange={setObjSearchCompleted}
          />
        ),
      },
    }),
    [
      showCreateHandover,
      openOffcanvas,
      headerPageRef,
      setOpenOffcanvas,
      setShowCreateHandover,
      sliderData,
      getSliderDataAPI,
      searchDateTime,
      setSearchDateTime,
    ],
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

  const handleDownloadHandover = useCallback(async () => {
    if (searchDateTime.startDate && searchDateTime.endDate) {
      // ★ [SEC-11a ② · 2026-09-07 턴 J · 차선 C] **돌려준 값을 버리고 있었다.**
      //   `downloadHandoverAPI` 는 `{success, message}` 를 돌려주는데 종전에는 그것을
      //   **읽지도 않았다** — 내려받기가 실패해도 화면은 한 자도 말하지 않았고,
      //   사람은 파일이 오는 줄 알고 기다렸다. 그리고 `try` 도 없어 거절은 예외로 샜다.
      try {
        const { success, message } = await downloadHandoverAPI({
          start_date: searchDateTime.startDate.format('YYYY-MM-DD'),
          end_date: searchDateTime.endDate.format('YYYY-MM-DD'),
        });
        if (!success) {
          ToastTopHelper.error(message);
        }
      } catch (error) {
        ToastTopHelper.error(failureLine('HandoverPage.downloadHandover', error));
      }
    }
  }, [downloadHandoverAPI, searchDateTime]);

  const handleDownloadCsv = useCallback(
    async (selectedFields: string[]) => {
      // ★ [SEC-11a ② · 턴 J · 차선 C] 위와 같은 자리 — 돌려준 값을 버렸고 `try` 가 없었다.
      try {
        const result =
          activeKey === 'notice-management'
            ? await downloadNoticeAPI({
                selectedFields,
                objSearch: objSearchNotice,
              })
            : activeKey === 'completed-notice'
              ? await downloadCompletedNoticeAPI({
                  selectedFields,
                  objSearch: objSearchCompleted,
                })
              : null;
        if (result && !result.success) {
          ToastTopHelper.error(result.message);
        }
      } catch (error) {
        ToastTopHelper.error(failureLine('HandoverPage.downloadCsv', error));
      }
    },
    [
      activeKey,
      downloadNoticeAPI,
      downloadCompletedNoticeAPI,
      objSearchNotice,
      objSearchCompleted,
    ],
  );

  const buttonsViewInTab = useMemo(
    () => (activeKey: TabKey) => {
      const buttonViewInTab = {
        'handover-management': [
          <CustomBtn
            key="download-handover"
            label={t('handover.Download CSV')}
            variant="outline"
            color="primary"
            type="button"
            actionType={ROLE_PERMISSION.READ}
            onClick={handleDownloadHandover}
          />,
          <CustomBtn
            key="create-handover"
            label={t('handover.Create A Handover')}
            icon={<GoPlus size={18} />}
            type="button"
            actionType={ROLE_PERMISSION.CREATE}
            onClick={() => {
              setShowCreateHandover(true);
            }}
          />,
        ],
        'notice-management': [
          <CustomBtn
            key="download-notice"
            label={t('handover.Download CSV')}
            variant="outline"
            color="primary"
            type="button"
            actionType={ROLE_PERMISSION.READ}
            onClick={() => {
              setShowCsvSettingsModal(true);
            }}
          />,
          <CustomBtn
            key="create-notice"
            label={t('handover.Create Notice')}
            icon={<GoPlus size={18} />}
            type="button"
            actionType={ROLE_PERMISSION.CREATE}
            onClick={() => {
              navigate(
                CustomRoutes.handover.subRoutes.addNoticeManagement.path,
              );
            }}
          />,
        ],
        'completed-notice': [
          <CustomBtn
            key="download-completed-notice"
            label={t('handover.Download CSV')}
            variant="outline"
            color="primary"
            type="button"
            actionType={ROLE_PERMISSION.READ}
            onClick={() => {
              setShowCsvSettingsModal(true);
            }}
          />,
          <CustomBtn
            key="create-notice-completed"
            label={t('handover.Create Notice')}
            icon={<GoPlus size={18} />}
            type="button"
            actionType={ROLE_PERMISSION.CREATE}
            onClick={() => {
              navigate(
                CustomRoutes.handover.subRoutes.addNoticeManagement.path,
              );
            }}
          />,
        ],
      };
      return activeKey ? buttonViewInTab[activeKey] : [];
    },
    [t, navigate, handleDownloadHandover, setShowCsvSettingsModal],
  );

  useEffect(() => {
    if (activeKey) {
      setOpenOffcanvas(false);
    }
  }, [activeKey]);

  return (
    <Container
      id="handover-page"
      isOpenCanvas={openOffcanvas}
    >
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={buttonsViewInTab(activeKey as TabKey)}
        hasLineBottom={false}
      />
      <CustomTabs
        onChange={(key: string) => {
          if (!isValidTabKey(key)) {
            return;
          }

          const params = Object.fromEntries(searchParams);

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
      <CsvSettingsModal
        show={showCsvSettingsModal}
        onHide={() => setShowCsvSettingsModal(false)}
        onDownload={handleDownloadCsv}
        CSV_FIELDS={
          activeKey === 'notice-management'
            ? COLUMNS_NOTICE_MANAGEMENT
            : COLUMNS_COMPLETED_NOTICE
        }
      />
    </Container>
  );
};
