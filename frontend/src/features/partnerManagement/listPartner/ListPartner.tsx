import { Box } from '@mui/material';
import { t } from 'i18next';
import { useEffect, useMemo, useRef, useState } from 'react';
import { GoPlus } from 'react-icons/go';
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
  useTheme,
} from 'rj-core';

import CopyIcon from '@/assets/images/CopyIcon';
import Truncate from '@/components/truncate/Truncate';
import useAPI from '@/features/partnerManagement/useAPI/useAPI';
import { isEmptyObject } from '@/utils/fetchFromObject';
import { formatEnabled } from '@/utils/formatColumns';
import { remToPx } from '@/utils/utils';

import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import FormPartner, { FormPartnerProps } from '../components/FormPartner';

const ListPartner = () => {
  const [theme] = useTheme();
  const {
    getPartnerManagement,
    refreshTokenPartner,
    deletePartner,
    copyTokenPartner,
  } = useAPI();
  const headerPageRef = useRef(null);
  const searchCardRef = useRef(null);
  const [objSearch, setObjSearch] = useState({});

  const [open, setOpen] = useState(false);

  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [selectedRows, setSelectedRows] = useState<any[]>([]);

  const listId = useMemo(
    () => selectedRows?.map((item: any) => item.id).join(','),
    [selectedRows],
  );

  const [loading, setLoading] = useState<boolean>(false);
  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);
  const [refreshTable, setRefreshTable] = useState<boolean>(false);

  const [selectedSetting, setSelectedSetting] =
    useState<FormPartnerProps | null>(null);
  const [initialData, setInitialData] = useState<FormPartnerProps | null>(null);

  const [addNewPartner, setAddNewPartner] = useState(false);
  const [showModalRefreshAPIKey, setShowModalRefreshAPIKey] = useState({
    show: false,
    id: null,
    refresh_token: null,
    expired: null,
  });

  const [showModalDeletePartner, setShowModalDeletePartner] =
    useState<boolean>(false);

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef, searchCardRef],
    additionalHeights: [remToPx(8)],
  });

  const [data, setData] = useState<{
    data: any[];
    totalItem: number;
    totalPage: number;
  }>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });

  console.log('data_in_list_partner', data);

  const coppyRefreshToken = async (id: number) => {
    const { success, message, data } = await copyTokenPartner({ id });
    if (success) {
      navigator.clipboard.writeText(data?.api_key);
      ToastTopHelper.success(t(message));
    } else {
      console.log('Error copy refresh token', message);
      ToastTopHelper.error(message);
    }
  };

  const handleSelectionRows = (selectedData: any) => {
    setSelectedRows(selectedData);
  };

  const handleDrawerClose = () => {
    setOpenOffcanvas(false);
    setOpen(false);
    setSelectedSetting(null);
    setAddNewPartner(false);
    setInitialData(null);
  };

  const displayGroup = CheckRoleAccount('superuser');

  const handleCopy = (content: string) => {
    try {
      navigator.clipboard.writeText(content);
      ToastTopHelper.success(t('Copied to clipboard'));
    } catch (error) {
      console.error('Unable to copy to clipboard:', error);
    }
  };

  const HistoryBehaviorColumns = [
    {
      Header: 'Partner Name',
      accessor: 'name',
    },
    {
      Header: 'Partner Code',
      accessor: 'code',
      cell: (row: any) => {
        return row.getValue() ? (
          <Truncate
            content={row.getValue()}
            tooltipContent={row.getValue()}
          />
        ) : (
          '-'
        );
      },
    },
    {
      Header: 'ServiceKey',
      accessor: 'service_key',
      enableSorting: false,
      enableColumnFilter: false,
      customStyle: {
        width: '100px',
      },
      cell: (row: any) => {
        return (
          <div className="d-flex justify-content-between gap-2">
            <span>**********</span>
            <div
              className="cursor-pointer"
              onClick={(e) => {
                e.stopPropagation();
                handleCopy(row?.row?.original?.service_key);
              }}
            >
              <CopyIcon color={theme === 'dark' ? '#FFFFFF' : '#2D2E30'} />
            </div>
          </div>
        );
      },
    },
    {
      Header: 'Created Date',
      accessor: 'created_on',
      filterVariant: 'datetime',
    },
    {
      Header: 'In Use',
      accessor: 'in_use',
      filterVariant: 'checkbox',
      filterOptions: ['True', 'False'],
      customStyle: {
        width: '60px',
      },
      cell: (row: any) => {
        console.log('row?.row?.original?.in_use', row?.row?.original);
        return formatEnabled(row?.row?.original?.in_use);
      },
    },
    {
      Header: 'API Key',
      accessor: 'api_user',
      enableSorting: false,
      enableColumnFilter: false,
      customStyle: {
        width: '100px',
      },
      cell: (row: any) => {
        return (
          <div className="d-flex justify-content-between gap-2">
            <span>**********</span>
            <div
              className="cursor-pointer"
              onClick={(e) => {
                e.stopPropagation();
                coppyRefreshToken(row?.row?.original?.id);
              }}
            >
              {' '}
              <CopyIcon color={theme === 'dark' ? '#FFFFFF' : '#2D2E30'} />
            </div>
          </div>
        );
      },
    },
    {
      Header: 'API Key Expiry (days left)',
      accessor: 'remaining_days',
      cell: (row: any) => {
        console.log(
          'row?.row?.original?.remaining_days',
          row?.row?.original?.remaining_days,
        );
        return (
          <span>
            {row?.row?.original?.expired ? (
              <Box
                sx={{
                  background: theme === 'dark' ? '#3C3D3E' : '#F2F2F2',
                  fontWeight: '600',
                  color: '#9C9D9D',
                  fontSize: '1rem',
                  width: 'fit-content',
                  padding: '4px 8px',
                  borderRadius: '0.5rem',
                }}
              >
                {t('Expired')}
              </Box>
            ) : (
              row.getValue() || '-'
            )}{' '}
          </span>
        );
      },
    },

    {
      Header: '',
      accessor: 'action',
      enableSorting: false,
      enableColumnFilter: false,
      customStyle: {
        width: '120px',
      },
      notUseConfigTable: true,
      cell: (row: any) => {
        return (
          <>
            <CustomBtn
              label={t('Refresh API Key')}
              variant="outline"
              color="primary"
              size="sm"
              actionType={ROLE_PERMISSION.UPDATE}
              onClick={() => {
                setShowModalRefreshAPIKey({
                  show: true,
                  id: row?.row?.original?.id,
                  refresh_token: row?.row?.original?.refresh,
                  expired: row?.row?.original?.expired,
                });
              }}
            />
          </>
        );
      },
    },
  ];

  const [loadingDeletePartner, setLoadingDeletePartner] =
    useState<boolean>(false);
  const handleDeletePartner = async () => {
    setLoadingDeletePartner(true);
    const ids = selectedRows?.map((item: any) => item.id).join(',');
    const { success, message } = await deletePartner({
      ids,
    });
    if (success) {
      const updatedData = data.data.filter((item) => {
        const found = selectedRows.find((row: any) => row.id === item.id);
        return !found;
      });
      setData({
        ...data,
        data: updatedData,
      });
      setRefreshTable(true);
      ToastTopHelper.success(message);
    } else {
      ToastTopHelper.error(message);
    }
    setLoadingDeletePartner(false);
    setShowModalDeletePartner(false);
  };

  const handleViewOrderDetail = (row: any) => {
    setOpenOffcanvas(true);
    setOpen(true);
    setSelectedSetting(row);
    setAddNewPartner(false);
  };

  const fetchData = async () => {
    setLoading(true);
    const { success, data, message } = await getPartnerManagement({
      pageSize: pageSize,
      currentPage: currentPage,
      objSearch: objSearch,
    });

    if (success) {
      setLoading(false);
      setData(data);
    }

    if (!success) {
      ToastTopHelper.error(message);
    }
  };
  const handleRefreshAPIKey = async (id: number, refresh_token: string) => {
    const {
      success,
      message,
      data: dataRefreshToken,
    } = await refreshTokenPartner({
      id,
      refresh_token,
    });
    if (success) {
      const updatedData = data?.data?.map((item: any) => {
        if (item?.id === id) {
          return {
            ...item,
            api_user: dataRefreshToken?.api_key,
            refresh: dataRefreshToken?.refresh_token,
            // expired_days: dataRefreshToken?.remaining_days,
            expired: dataRefreshToken?.expired,
          };
        }
        return item;
      });

      setData({ ...data, data: updatedData });
      ToastTopHelper.success(message);
      setRefreshTable(true);
      setShowModalRefreshAPIKey({
        show: false,
        id: null,
        refresh_token: null,
        expired: null,
      });
    } else {
      console.log('Error refresh API key', message);
      ToastTopHelper.error(message);
    }
  };

  useEffect(() => {
    if (selectedSetting !== null) {
      setInitialData({
        name: selectedSetting?.name || '',
        expired_days: (selectedSetting as any)?.expired_days || 30,
        api_callback_url: {
          DroneUserNotice:
            selectedSetting?.api_callback_url?.DroneUserNotice || '',
          DroneBaseStation:
            selectedSetting?.api_callback_url?.DroneBaseStation || '',
          DeliveryStatusCallback:
            selectedSetting?.api_callback_url?.DeliveryStatusCallback || '',
        },
        service_key: selectedSetting?.service_key || '',
        group: {
          value: (selectedSetting as any)?.group_id,
          label: (selectedSetting as any)?.group__name,
        },
        id: (selectedSetting as any)?.id,
        api_key: (selectedSetting as any)?.api_user,
        code: (selectedSetting as any)?.code,
        is_active: (selectedSetting as any)?.is_active,
      });
    } else {
      setInitialData(null);
    }
  }, [selectedSetting]);

  useEffect(() => {
    pageSize && !isEmptyObject(objSearch) && fetchData();
  }, [pageSize, currentPage, objSearch]);

  useEffect(() => {
    if (refreshTable) {
      fetchData();
      setRefreshTable(false);
    }
  }, [refreshTable]);

  return (
    <Container
      id="list-packaging"
      isOpenCanvas={openOffcanvas}
    >
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[
          <CustomBtn
            label={t('Add New Partner')}
            icon={<GoPlus size={18} />}
            actionType={ROLE_PERMISSION.CREATE}
            onClick={() => {
              setAddNewPartner(true);
              setOpenOffcanvas(true);
              setOpen(true);
              setSelectedSetting(null);
            }}
          />,
        ]}
      />
      <Main>
        <div className="list-packaging__table-container">
          <CustomizableTable
            stickyHeader
            useSystemSetting
            availableHeight={spaceTableHeight}
            columns={HistoryBehaviorColumns}
            data={data}
            objSearch={objSearch}
            setObjSearch={setObjSearch}
            onClickRow={handleViewOrderDetail}
            onSelectedRows={handleSelectionRows}
            refreshTable={refreshTable}
            setRefreshTable={setRefreshTable}
            buttons={[
              <CustomBtn
                label={t('Delete')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.DELETE}
                disabled={selectedRows.length === 0}
                onClick={() => setShowModalDeletePartner(true)}
              />,
            ]}
            currentPage={currentPage}
            setCurrentPage={setCurrentPage}
            pageSize={pageSize}
            setPageSize={setPageSize}
            offcanvas={openOffcanvas}
            setOpenOffcanvas={(boolean) => {
              setOpen(false);
              // setAddNewPartner(false);
              setOpenOffcanvas(boolean);
            }}
            hightlidhtRow={
              data.data?.find((item) => {
                return item.id === (selectedSetting as any)?.id;
              }) || null
            }
          />
        </div>
      </Main>
      <FormPartner
        open={open}
        onClose={handleDrawerClose}
        data={selectedSetting ? initialData : null}
        refreshData={fetchData}
        isedit={!addNewPartner}
      />
      <CustomModal
        title={t('Refresh API Key')}
        show={showModalRefreshAPIKey.show}
        onHide={() =>
          setShowModalRefreshAPIKey({
            show: false,
            id: null,
            refresh_token: null,
            expired: null,
          })
        }
      >
        <div style={{ width: '25rem' }}>
          {t(
            !showModalRefreshAPIKey.expired
              ? 'This API key is still active. Refreshing it will reset its expiration time. Do you want to continue?'
              : 'This API key has already expired. Refreshing will generate a new API key. Do you want to continue?',
          )}
        </div>
        <ActionBtn
          leftButtons={[
            <CustomBtn
              type="submit"
              color="primary"
              size="lg"
              onClick={() => {
                // if (showModalRefreshAPIKey.id && showModalRefreshAPIKey.refresh_token) {
                handleRefreshAPIKey(
                  showModalRefreshAPIKey.id,
                  showModalRefreshAPIKey.refresh_token,
                );
                // }
              }}
              label={t('Refresh Key')}
            />,
          ]}
          rightButtons={[
            <CustomBtn
              type="button"
              variant="outline"
              color="secondary"
              size="lg"
              onClick={() => {
                setShowModalRefreshAPIKey({
                  show: false,
                  id: null,
                  refresh_token: null,
                });
              }}
              label={t('Cancel')}
            />,
          ]}
        />
      </CustomModal>

      <CustomModal
        title={t('Delete Partner')}
        show={showModalDeletePartner}
        onHide={() => setShowModalDeletePartner(false)}
        loading={loadingDeletePartner}
      >
        <div style={{ width: '25rem' }}>
          {t(
            'Are you sure you want to delete selected partner(s)? This action cannot be undone.',
          )}
        </div>
        <ActionBtn
          leftButtons={[
            <CustomBtn
              type="submit"
              color="primary"
              size="lg"
              disabled={loadingDeletePartner}
              loading={loadingDeletePartner}
              onClick={() => {
                handleDeletePartner();
              }}
              label={t('Delete')}
            />,
          ]}
          rightButtons={[
            <CustomBtn
              type="button"
              variant="outline"
              color="secondary"
              size="lg"
              disabled={loadingDeletePartner}
              onClick={() => {
                setShowModalDeletePartner(false);
              }}
              label={t('Cancel')}
            />,
          ]}
        />
      </CustomModal>
    </Container>
  );
};
export default ListPartner;
