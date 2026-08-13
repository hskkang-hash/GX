import { Box } from '@mui/material';
import React, {
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
} from 'react';
import { useTranslation } from 'react-i18next';
import { GoPlus } from 'react-icons/go';
import { useNavigate } from 'react-router-dom';
import {
  ActionBtn,
  Container,
  CustomBtn,
  CustomizableTable,
  CustomModal,
  HeaderWithBtn,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useCalculateHeight,
} from 'rj-core';

import ErrorImage from '@/assets/images/no-image.png';
import SwitchBtn from '@/components/Form/SwitchBtn';
import OperatingTimeModal from '@/features/terminals/components/OperatingTimeModal';
import useAPI from '@/features/terminals/useAPI/useAPI';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { CustomRoutes } from '@/services/API';
import { SearchObject } from '@/types/paramAPI';
import { remToPx } from '@/utils/utils';

import { useDeliveryHubs } from '../hooks/useDeliveryHubs';
import {
  DeliveryHubsPageReducer,
  initialDeliveryHubsPageState,
} from '../reducers/DeliveryHubs.reducer';
import { useDeliveryHubsStore } from '../store';
import { DeliveryHubsState } from '../types/IDeliveryHubs';

// Memoized Image Component to prevent unnecessary re-renders
const DeliveryHubImage = React.memo<{
  imageUrl: string;
  alt: string;
}>(({ imageUrl, alt }) => {
  const handleImageError = useCallback(
    (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
      (e.target as HTMLImageElement).src = ErrorImage;
    },
    [],
  );

  return (
    <Box p={'0.375rem 0.25rem'}>
      <img
        src={imageUrl}
        alt={alt}
        onError={handleImageError}
        className="list-device__image"
        style={{
          width: '100%',
          aspectRatio: '2/1',
          objectFit: 'cover',
        }}
      />
    </Box>
  );
});

DeliveryHubImage.displayName = 'DeliveryHubImage';

// Type for table row
interface TableRow {
  row: {
    original: DeliveryHubsState;
  };
}

export const DeliveryHubs = (): React.ReactElement => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const headerPageRef = useRef<HTMLDivElement>(null);
  const [objSearch, setObjSearch] = useState<SearchObject | null>(null);
  const [state, dispatch] = useReducer(
    DeliveryHubsPageReducer,
    initialDeliveryHubsPageState,
  );
  const [loadingHubId, setLoadingHubId] = useState<string | null>(null);
  const [showDeactivateModal, setShowDeactivateModal] = useState(false);
  const [selectedDeactivateReason, setSelectedDeactivateReason] = useState<
    number | null
  >(null);
  const [deactivateReasons, setDeactivateReasons] = useState<any[]>([]);
  const [pendingDeactivateInfo, setPendingDeactivateInfo] = useState<any>(null);
  const {
    pageSize,
    currentPage,
    selectedRows,
    refreshTable,
    openOffcanvas,
    data,
  } = state;

  const { setDeliveryHub } = useDeliveryHubsStore();
  const { getDeliveryHubsAPI, activeDeliveryHubsAPI, deactiveDeliveryHubsAPI } =
    useDeliveryHubs();
  const { getDataByModel } = useCommonAPI();

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8)],
  });

  // Fetch deactivation reasons on mount
  useEffect(() => {
    (async () => {
      const { data, status } = await getDataByModel({
        name_modal: 'deactivatereason',
      });
      if (status) {
        setDeactivateReasons(data);
      }
    })();
  }, []);

  useEffect(() => {
    if (pageSize) {
      handleGetDeliveryHubs({ pageSize, currentPage, objSearch });
    }
  }, [pageSize, currentPage, objSearch]);

  const handleGetDeliveryHubs = async ({
    pageSize,
    currentPage,
    objSearch,
  }: {
    pageSize: number;
    currentPage: number;
    objSearch?: SearchObject | null;
  }): Promise<void> => {
    const { data, totalPage, totalItem } = await getDeliveryHubsAPI({
      pageSize,
      currentPage,
      objSearch,
    });

    dispatch({
      type: 'SET_DATA',
      payload: {
        data,
        totalPage,
        totalItem,
      },
    });
  };

  const handleSelectionRows = useCallback((rows: DeliveryHubsState[]): void => {
    dispatch({ type: 'SET_SELECTED_ROWS', payload: rows });
  }, []);

  const handleViewDetailDevice = useCallback(
    (row: DeliveryHubsState): void => {
      if (row?.active) {
        setDeliveryHub(row);
        navigate(
          CustomRoutes.deliveryHubs.subRoutes.editDeliveryHubs.path.replace(
            ':id',
            row.id,
          ),
        );
      }
    },
    [navigate, setDeliveryHub],
  );

  const handleActionDeliveryHubs = useCallback(
    async (
      action: 'activate' | 'deactivate',
      info?: any,
      deactivateReasonId?: number,
    ) => {
      const listId =
        selectedRows?.map((item: { id: string }) => item.id).join(',') ||
        String(info?.id);
      setLoadingHubId(info?.id);
      const { success, message } = await (
        action === 'activate' ? activeDeliveryHubsAPI : deactiveDeliveryHubsAPI
      )({
        ids: listId,
        useLoading: true,
        ...(action === 'deactivate' &&
          deactivateReasonId && { deactive_reason_id: deactivateReasonId }),
      });

      if (success && data?.data) {
        const updatedData = data.data.map((item) => {
          const found = selectedRows.find(
            (row: DeliveryHubsState) => row.id === item.id,
          );
          const isTargetItem = info && item?.id === info?.id;
          if (found || isTargetItem) {
            return {
              ...item,
              active: action === 'activate' ? true : false,
            };
          }
          return item;
        });

        dispatch({
          type: 'SET_DATA',
          payload: {
            data: updatedData,
            totalPage: data.totalPage,
            totalItem: data.totalItem,
          },
        });

        dispatch({
          type: 'TOGGLE_REFRESH',
          payload: true,
        });
        ToastTopHelper.success(message);
      } else {
        ToastTopHelper.error(message);
      }
      setLoadingHubId(null);
    },
    [data.data, selectedRows, activeDeliveryHubsAPI, deactiveDeliveryHubsAPI], // eslint-disable-line react-hooks/exhaustive-deps
  );

  const StatusCell = useCallback(
    ({ info }: { info: any }) => {
      return (
        <SwitchBtn
          actionType={ROLE_PERMISSION.UPDATE}
          statusValue={info?.row?.original?.active}
          onChange={() => {
            handleSelectionRows([info?.row?.original]);
            const action = info?.row?.original?.active
              ? 'deactivate'
              : 'activate';

            if (action === 'deactivate') {
              // Show modal for deactivate
              setPendingDeactivateInfo(info?.row?.original);
              setShowDeactivateModal(true);
            } else {
              // Direct call for activate
              handleActionDeliveryHubs(action, info?.row?.original);
            }
          }}
          loading={
            loadingHubId ? loadingHubId === info?.row?.original?.id : false
          }
        />
      );
    },
    [handleActionDeliveryHubs, loadingHubId, handleSelectionRows],
  );

  const ImageCell = useMemo(
    () =>
      ({ info }: { info: any }) => {
        return (
          <DeliveryHubImage
            imageUrl={info?.row?.original?.avatar__file_url || ErrorImage}
            alt="delivery hub"
          />
        );
      },
    [],
  );
  const { getFunctionTypes, useFetchOptions } = useCommonAPI();

  const mainTypeConfig = useMemo(
    () => ({
      type: 'function' as const,
      params: { function_type: 'delivery_hub' },
      defaultLabel: t('Select'),
    }),
    [],
  );
  const mainType = useFetchOptions(getFunctionTypes, mainTypeConfig);

  const { getOperatingTimeTerminalAPI } = useAPI();

  const [showDetailModal, setShowDetailModal] = useState<{
    show: boolean;
    data: any;
  }>({
    show: false,
    data: {},
  });

  const handleViewOperatingTime = async (id: number) => {
    const { success, message, data } = await getOperatingTimeTerminalAPI(id);
    console.log('data_operating_time', data);
    if (success) {
      setShowDetailModal({ show: true, data: data });
    } else {
      ToastTopHelper.error(message);
    }
  };

  const columnsOther = [
    {
      Header: 'Image',
      accessor: 'image',
      enableSorting: false,
      enableColumnFilter: false,
      cell: (info: any) => <ImageCell info={info} />,
      width: 120,
      minWidth: 120,
      maxWidth: 120,
    },
    {
      Header: t('Active'),
      accessor: 'active',
      enableSorting: true,
      enableColumnFilter: false,
      cell: (info: any) => <StatusCell info={info} />,
    },
    {
      Header: t('Type'),
      accessor: 'function',
      filterVariant: 'select',
      filterOptions:
        mainType.length > 0
          ? mainType?.map((item: any) => ({
              label: item.label,
              value:
                item.label == 'Select' ||
                item.label == '선택' ||
                item.label == 'เลือก'
                  ? ''
                  : item.label,
            }))
          : [],
      cell: (row: TableRow) => {
        return <>{row.getValue() || '-'}</>;
      },
    },
    {
      Header: 'Operating Time',
      accessor: 'operating_times',
      enableSorting: false,
      enableColumnFilter: false,
      customStyle: { maxWidth: 120, textAlign: 'center' },
      notUseConfigTable: true,
      cell: (info: any) => {
        return (
          <>
            <CustomBtn
              label={t('View Detail')}
              variant="outline"
              style={{ border: '1px solid #1d9be2', color: '#1d9be2' }}
              actionType={ROLE_PERMISSION.CREATE}
              onClick={() => handleViewOperatingTime(info?.row?.original?.id)}
            />
          </>
        );
      },
    },
  ];

  return (
    <>
      <Container
        id="list-device"
        isOpenCanvas={openOffcanvas}
      >
        <HeaderWithBtn
          ref={headerPageRef}
          buttons={[
            <CustomBtn
              key="register-btn"
              label={t('hubs_delivery.register')}
              icon={<GoPlus size={18} />}
              actionType={ROLE_PERMISSION.CREATE}
              onClick={() =>
                navigate(
                  CustomRoutes.deliveryHubs.subRoutes.registerDeliveryHubs.path,
                )
              }
            />,
          ]}
        />
        <Main>
          <CustomizableTable
            stickyHeader
            availableHeight={spaceTableHeight}
            columns={columnsOther}
            data={data}
            objSearch={objSearch}
            setObjSearch={setObjSearch}
            onClickRow={handleViewDetailDevice}
            onSelectedRows={handleSelectionRows}
            refreshTable={refreshTable}
            setRefreshTable={(refresh: boolean) => {
              dispatch({ type: 'TOGGLE_REFRESH', payload: refresh });
            }}
            buttons={[
              <CustomBtn
                key="activate-btn"
                label={t('Activate')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.UPDATE}
                disabled={selectedRows.length === 0}
                onClick={() => handleActionDeliveryHubs('activate')}
              />,
              <CustomBtn
                key="deactivate-btn"
                label={t('Deactivate')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.UPDATE}
                disabled={selectedRows.length === 0}
                onClick={() => {
                  setPendingDeactivateInfo(null);
                  setShowDeactivateModal(true);
                }}
              />,
            ]}
            currentPage={currentPage}
            setCurrentPage={(page: number) => {
              dispatch({ type: 'SET_CURRENT_PAGE', payload: page });
            }}
            pageSize={pageSize}
            setPageSize={(size: number) => {
              dispatch({ type: 'SET_PAGE_SIZE', payload: size });
            }}
            offcanvas={openOffcanvas}
            setOpenOffcanvas={(boolean: boolean) => {
              dispatch({ type: 'OPEN_OFFCANVAS', payload: boolean });
            }}
          />
        </Main>

        {/* Deactivation Reason Modal */}
        <CustomModal
          title={t('Select Deactivation Reason')}
          show={showDeactivateModal}
          onHide={() => {
            setShowDeactivateModal(false);
            setSelectedDeactivateReason(null);
          }}
        >
          <div style={{ minWidth: '25rem' }}>
            <div style={{ marginBottom: '1rem' }}>
              {t('Please select a reason for deactivation.')}
            </div>
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.75rem',
                maxHeight: '20rem',
                overflowY: 'auto',
              }}
            >
              {deactivateReasons.map((reason) => (
                <label
                  key={reason.value}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    cursor: 'pointer',
                    padding: '0.5rem',
                    border:
                      selectedDeactivateReason === reason.value
                        ? '2px solid var(--ga-primary)'
                        : '1px solid #E0E0E0',
                    borderRadius: '8px',
                    backgroundColor: 'transparent',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selectedDeactivateReason === reason.value}
                    onChange={() => {
                      setSelectedDeactivateReason(
                        selectedDeactivateReason === reason.value
                          ? null
                          : reason.value,
                      );
                    }}
                    style={{ marginRight: '0.75rem' }}
                  />
                  <span>{reason.label}</span>
                </label>
              ))}
            </div>
          </div>
          <ActionBtn
            leftButtons={[
              <CustomBtn
                key="modal-deactivate-btn"
                type="button"
                color="primary"
                size="lg"
                actionType={ROLE_PERMISSION.UPDATE}
                disabled={!selectedDeactivateReason}
                onClick={() => {
                  if (selectedDeactivateReason) {
                    handleActionDeliveryHubs(
                      'deactivate',
                      pendingDeactivateInfo,
                      selectedDeactivateReason,
                    );
                    setShowDeactivateModal(false);
                    setSelectedDeactivateReason(null);
                    setPendingDeactivateInfo(null);
                  }
                }}
                label={t('Deactivate')}
              />,
            ]}
            rightButtons={[
              <CustomBtn
                key="modal-cancel-btn"
                type="button"
                variant="outline"
                color="secondary"
                size="lg"
                onClick={() => {
                  setShowDeactivateModal(false);
                  setSelectedDeactivateReason(null);
                  setPendingDeactivateInfo(null);
                }}
                label={t('Cancel')}
              />,
            ]}
          />
        </CustomModal>
        <OperatingTimeModal
          show={showDetailModal.show}
          onHide={() => setShowDetailModal({ show: false, data: {} })}
          data={showDetailModal.data}
        />
      </Container>
    </>
  );
};
