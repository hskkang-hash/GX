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

import SwitchBtn from '@/components/Form/SwitchBtn';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { CustomRoutes } from '@/services/API';
import { remToPx } from '@/utils/utils';

import ErrorImage from '../../../assets/images/no-image.png';
import '../assets/style/OperationalNotice.scss';
import useOperationalNotice from '../hooks/useOperationalNotice';
import { OperationalNoticeState } from '../types/operationalNotice.types';

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

const OperationalNotice = () => {
  const [
    showModalDeleteOperationalNotice,
    setShowModalDeleteOperationalNotice,
  ] = useState<boolean>(false);
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
    getOperationalNotice,
    deleteOperationalNotice,
    changeStatusOperationalNotice,
  } = useOperationalNotice();

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
    const { success, data, message } = await getOperationalNotice({
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

  const handleViewDetailOperationalNotice = (selectedRow: any) => {
    navigate(
      CustomRoutes.operationalNotice.subRoutes.editOperationalNotice.path.replace(
        ':id',
        selectedRow.id,
      ),
    );
  };

  const [loadingDeleteOperationalNotice, setLoadingDeleteOperationalNotice] =
    useState<boolean>(false);
  const handleDeletePartner = async () => {
    const ids = selectedRows?.map((item: any) => item.id).join(',');
    setLoadingDeleteOperationalNotice(true);
    const { success, message } = await deleteOperationalNotice(ids);
    if (success) {
      const updatedData = data.data.filter((item) => {
        const found = selectedRows.find((row: any) => row.id === item.id);
        return !found;
      });
      setData({
        ...data,
        data: updatedData,
      });
      setShowModalDeleteOperationalNotice(false);
      setRefreshTable(true);
      ToastTopHelper.success(message);
    } else {
      setShowModalDeleteOperationalNotice(false);
      ToastTopHelper.error(message);
    }
    setLoadingDeleteOperationalNotice(false);
  };
  const headerPageRef = useRef(null);
  const searchCardRef = useRef(null);

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef, searchCardRef],
    additionalHeights: [remToPx(8)],
  });

  const [loadingDeviceId, setLoadingDeviceId] = useState<number | null>(null);

  const handleStatusChange = useCallback(
    async (data: OperationalNoticeState) => {
      setLoadingDeviceId(Number(data.id));
      try {
        const { success, message } = await changeStatusOperationalNotice(
          Number(data.id),
        );
        if (success) {
          setData((prev) => ({
            ...prev,
            data: prev.data.map((item) => ({
              ...item,
              active: item.id === data.id ? !data.active : false,
            })),
          }));

          setRefreshTable(true);
          ToastTopHelper.success(message);
        } else {
          ToastTopHelper.error(message);
        }
      } catch (error) {
        console.error('Error changing user status:', error);
      }
      setLoadingDeviceId(null);
    },
    [],
  );

  const StatusCell = ({ info }: { info: any }) => {
    console.log('info_in_status_cell', info?.row?.original);
    return (
      <SwitchBtn
        actionType={ROLE_PERMISSION.UPDATE}
        statusValue={info?.row?.original?.active}
        onChange={() => handleStatusChange(info?.row?.original)}
        loading={
          loadingDeviceId ? loadingDeviceId === info?.row?.original?.id : false
        }
      />
    );
  };
  const [statusType, setItemType] = useState<any[]>([]);
  const { getOptionsByModel } = useCommonAPI();
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
      Header: 'Notice Name',
      accessor: 'name',
      customStyle: {
        width: '70%',
      },
    },
    {
      Header: 'Status',
      accessor: 'active',
      enableSorting: false,
      enableColumnFilter: false,
      customStyle: {
        width: '10%',
      },
      cell: (info: any) => <StatusCell info={info} />,
    },
    {
      Header: 'Created Date',
      accessor: 'created_on',
      filterVariant: 'datetime',
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
            label={t('Add New Notice')}
            icon={<GoPlus size={18} />}
            actionType={ROLE_PERMISSION.CREATE}
            onClick={() =>
              navigate(
                CustomRoutes.operationalNotice.subRoutes.addNewOperationalNotice
                  .path,
              )
            }
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
            onClickRow={handleViewDetailOperationalNotice}
            onSelectedRows={handleSelectionRows}
            refreshTable={refreshTable}
            useSystemSetting
            setRefreshTable={setRefreshTable}
            buttons={[
              <CustomBtn
                label={t('Delete')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.UPDATE}
                disabled={selectedRows.length === 0}
                onClick={() => setShowModalDeleteOperationalNotice(true)}
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
      </Main>
      <CustomModal
        title={t('Delete Notice')}
        show={showModalDeleteOperationalNotice}
        onHide={() => setShowModalDeleteOperationalNotice(false)}
        loading={loadingDeleteOperationalNotice}
      >
        <div style={{ width: '25rem' }}>
          {t('Are you sure you want to delete selected notice(s)?')}
        </div>
        <ActionBtn
          leftButtons={[
            <CustomBtn
              type="submit"
              color="primary"
              size="lg"
              variant="outline"
              disabled={loadingDeleteOperationalNotice}
              loading={loadingDeleteOperationalNotice}
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
              disabled={loadingDeleteOperationalNotice}
              onClick={() => {
                setShowModalDeleteOperationalNotice(false);
              }}
              label={t('Cancel')}
            />,
          ]}
        />
      </CustomModal>
    </Container>
  );
};
export default OperationalNotice;
