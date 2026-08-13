import { Box } from '@mui/material';
import { t } from 'i18next';
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { GoPlus } from 'react-icons/go';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Container,
  CustomBtn,
  CustomizableTable,
  CustomModal,
  HeaderWithBtn,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useCalculateHeight,
  ActionBtn,
} from 'rj-core';

import SwitchBtn from '@/components/Form/SwitchBtn';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { formatEnabled } from '@/utils/formatColumns';
import { remToPx } from '@/utils/utils';

import ErrorImage from '../../../assets/images/no-image.png';
import useAPI from '../useAPI/useAPI';
import './ListDevice.scss';

const DeviceImage = React.memo<{
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

DeviceImage.displayName = 'DeviceImage';

const ListDevice = () => {
  const [objSearch, setObjSearch] = useState({});
  const navigate = useNavigate();
  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [selectedRows, setSelectedRows] = useState<any[]>([]);

  const listId = useMemo(
    () => selectedRows?.map((item: any) => item.id).join(','),
    [selectedRows],
  );

  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);
  const [refreshTable, setRefreshTable] = useState<boolean>(false);

  const {
    getDeviceManagement,
    actionDevice,
    activeDevice,
    deactiveDevice,
    deleteDevices,
  } = useAPI();

  const [data, setData] = useState<{
    data: any[];
    totalItem: number;
    totalPage: number;
  }>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });

  // use for save searchcondition
  const location = useLocation();
  const { data: dataSearchCondition } = location.state || {};

  useEffect(() => {
    if (dataSearchCondition) {
      setObjSearch(dataSearchCondition);
    }
  }, [dataSearchCondition]);
  //end

  const fetchData = async ({
    objSearch,
    pageSize,
    currentPage,
  }: {
    objSearch: any;
    pageSize: number;
    currentPage: number;
  }) => {
    const { success, data, message } = await getDeviceManagement({
      pageSize: pageSize,
      currentPage: currentPage,
      objSearch: objSearch,
    });

    if (success) {
      setData(data);
    }

    if (!success) {
      ToastTopHelper.error(message || 'Expected error');
    }
  };

  useEffect(() => {
    if (pageSize) {
      fetchData({ objSearch, pageSize, currentPage });
    }
  }, [pageSize, currentPage, objSearch]);

  const handleSelectionRows = (selectedData: any) => {
    setSelectedRows(selectedData);
  };

  const handleViewDetailDevice = (selectedRow: any) => {
    if (selectedRow.active) {
      navigate(`/device/detail-device/${selectedRow.id}`, {
        state: { id: selectedRow.id },
      });
    }
  };

  const handleActionDevices = async (action: 'activate' | 'deactivate') => {
    const { success, message } = await (
      action === 'activate' ? activeDevice : deactiveDevice
    )({
      ids: listId,
      useLoading: true,
    });

    if (success) {
      fetchData({ objSearch, pageSize, currentPage });
      setRefreshTable(true);
      // setHideDeactivateModal();
      ToastTopHelper.success(message);
    } else {
      ToastTopHelper.error(message);
    }
  };

  const headerPageRef = useRef(null);
  const searchCardRef = useRef(null);

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef, searchCardRef],
    additionalHeights: [remToPx(8)],
  });

  const [loadingDeviceId, setLoadingDeviceId] = useState<number | null>(null);

  const handleStatusChange = useCallback(async (deviceId: number) => {
    setLoadingDeviceId(deviceId);
    try {
      const { success, message } = await actionDevice({
        ids: deviceId.toString(),
      });
      if (success) {
        fetchData({ objSearch, pageSize, currentPage });

        ToastTopHelper.success(message);
      } else {
        ToastTopHelper.error(message);
      }
    } catch (error) {
      console.error('Error changing user status:', error);
    }
    setLoadingDeviceId(null);
  }, []);

  const StatusCell = ({ info }: { info: any }) => {
    return (
      <SwitchBtn
        actionType={ROLE_PERMISSION.UPDATE}
        statusValue={info?.row?.original?.active}
        onChange={() => handleStatusChange(info?.row?.original?.id)}
        loading={
          loadingDeviceId ? loadingDeviceId === info?.row?.original?.id : false
        }
      />
    );
  };

  const ImageCell = ({ info }: { info: any }) => {
    return (
      <DeviceImage
        imageUrl={info?.row?.original?.avatar__file_url || ErrorImage}
        alt="device"
      />
    );
  };
  const [statusType, setItemType] = useState<any[]>([]);
  const { getOptionsByModel } = useCommonAPI();

  const [showModalDeleteDevice, setShowModalDeleteDevice] =
    useState<boolean>(false);
  const [loadingDeleteDevice, setLoadingDeleteDevice] =
    useState<boolean>(false);

  const handleDeletePartner = async () => {
    const ids = selectedRows?.map((item: any) => item.id).join(',');
    setLoadingDeleteDevice(true);
    const { success, message } = await deleteDevices({
      ids,
    });
    if (success) {
      setShowModalDeleteDevice(false);
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
      setShowModalDeleteDevice(false);
      ToastTopHelper.error(message);
    }
    setLoadingDeleteDevice(false);
  };

  useEffect(() => {
    const fetchStatusType = async () => {
      try {
        const fetchFunction = getOptionsByModel({
          name_modal: 'devicestatus',
          search_field: 'name',
        });
        const { options } = await fetchFunction('', [], {
          page: 1,
          page_size: 1000,
        });
        console.log('result_fetch_status_type', options);
        if (options) {
          setItemType([{ label: t('Select'), value: '' }, ...options]);
        }
      } catch (error) {
        console.log('Error fetch status type', error);
      }
    };
    fetchStatusType();
  }, [statusType.length < 0]);

  const HistoryBehaviorColumns = [
    {
      Header: 'Status',
      accessor: 'active',
      enableSorting: false,
      enableColumnFilter: false,
      cell: (info: any) => <StatusCell info={info} />,
    },
    {
      Header: 'In Use',
      accessor: 'in_use',
      enableColumnFilter: false,
      cell: (row: any) => formatEnabled(row?.row?.original?.in_use),
    },
    {
      Header: t('Status'),
      accessor: 'status__name',
      filterVariant: 'select',
      filterOptions:
        statusType.length > 0
          ? statusType?.map((item: any) => ({
            label: t(item.label),
            value: item.label,
          }))
          : [],
      cell: (row: any) => {
        return row.getValue() ? <span>{row.getValue()}</span> : '-';
      },
    },
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
      Header: 'Color',
      accessor: 'color',
      enableSorting: false,
      enableColumnFilter: false,
      cell: (info: any) =>
        info?.row?.original?.color ? (
          <div
            style={{
              height: 24,
              width: 24,
              backgroundColor: info?.row?.original?.color,
              borderRadius: 4,
            }}
          ></div>
        ) : (
          '-'
        ),
    },
  ];

  return (
    <Container
      id="list-device"
      isOpenCanvas={openOffcanvas}
    >
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[
          <CustomBtn
            label={t('Add New Device')}
            icon={<GoPlus size={18} />}
            actionType={ROLE_PERMISSION.CREATE}
            onClick={() => navigate('/device/add-new-device')}
          />,
        ]}
      />

      <Main>
        <div className="list-device__table-container">
          <CustomizableTable
            stickyHeader
            availableHeight={spaceTableHeight}
            columns={HistoryBehaviorColumns}
            data={data}
            objSearch={objSearch}
            setObjSearch={setObjSearch}
            onClickRow={handleViewDetailDevice}
            onSelectedRows={handleSelectionRows}
            refreshTable={refreshTable}
            setRefreshTable={setRefreshTable}
            buttons={[
              <CustomBtn
                label={t('Activate')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.UPDATE}
                disabled={selectedRows.length === 0}
                onClick={() => handleActionDevices('activate')}
              />,
              <CustomBtn
                label={t('Deactivate')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.UPDATE}
                disabled={selectedRows.length === 0}
                onClick={() => handleActionDevices('deactivate')}
              />,
              <CustomBtn
                label={t('Delete')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.DELETE}
                disabled={
                  selectedRows.length === 0 ||
                  selectedRows.some((item: any) => item.in_use === true)
                }
                onClick={() => {
                  setShowModalDeleteDevice(true);
                }}
              />,
            ]}
            currentPage={currentPage}
            setCurrentPage={setCurrentPage}
            pageSize={pageSize}
            setPageSize={setPageSize}
            offcanvas={openOffcanvas}
            setOpenOffcanvas={(boolean: boolean) => {
              setOpenOffcanvas(boolean);
            }}
          />
        </div>
        <CustomModal
          title={t('Delete Device')}
          show={showModalDeleteDevice}
          onHide={() => setShowModalDeleteDevice(false)}
          loading={loadingDeleteDevice}
        >
          <div style={{ width: '25rem' }}>
            {t(
              'Are you sure you want to delete selected device(s)? This action cannot be undone.',
            )}
          </div>
          <ActionBtn
            leftButtons={[
              <CustomBtn
                type="submit"
                color="primary"
                size="lg"
                disabled={loadingDeleteDevice}
                loading={loadingDeleteDevice}
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
                disabled={loadingDeleteDevice}
                onClick={() => {
                  setShowModalDeleteDevice(false);
                }}
                label={t('Cancel')}
              />,
            ]}
          />
        </CustomModal>
      </Main>
    </Container>
  );
};
export default ListDevice;
