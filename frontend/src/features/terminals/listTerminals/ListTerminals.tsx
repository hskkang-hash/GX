import { Box } from '@mui/material';
import { t } from 'i18next';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { GoPlus } from 'react-icons/go';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  CustomBtn,
  CustomizableTable,
  HeaderWithBtn,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useCalculateHeight,
} from 'rj-core';

import SwitchBtn from '@/components/Form/SwitchBtn';
import { CustomRoutes } from '@/services/API';
import { remToPx } from '@/utils/utils';

import ErrorImage from '../../../assets/images/no-image.png';
import useAPI from '../useAPI/useAPI';
import OperatingTimeModal from '../components/OperatingTimeModal';

const TerminalImage = React.memo<{
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
TerminalImage.displayName = 'TerminalImage';

const ListTerminals = () => {
  const [objSearch, setObjSearch] = useState({});
  const navigate = useNavigate();
  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [selectedRows, setSelectedRows] = useState<any[]>([]);
  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const {
    getListTerminalsAPI,
    activeDeactiveTerminalAPI,
    activeTerminalAPI,
    deactiveTerminalAPI,
    getOperatingTimeTerminalAPI,
  } = useAPI();
  const [loadingTerminalId, setLoadingTerminalId] = useState<string | null>(
    null,
  );
  const headerPageRef = useRef(null);
  const searchCardRef = useRef(null);

  // console.log("pageSize_in_list", pageSize)

  const [data, setData] = useState<{
    data: any[];
    totalItem: number;
    totalPage: number;
  }>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });

  const fetchData = async () => {
    const { data, totalItem, totalPage } = await getListTerminalsAPI({
      pageSize: pageSize,
      currentPage: currentPage,
      objSearch: objSearch,
    });

    setData({
      data: data,
      totalItem: totalItem,
      totalPage: totalPage,
    });
  };

  console.log('data_list_terminals', data);

  useEffect(() => {
    if (pageSize) fetchData();
  }, [pageSize, currentPage, objSearch]);

  const handleSelectionRows = (selectedData: any) => {
    setSelectedRows(selectedData);
  };

  const handleViewDetailDevice = (selectedRow: any) => {
    if (selectedRow.active) {
      navigate(`/terminals/edit-terminals/${selectedRow.id}`, {
        state: { data: selectedRow },
      });
    }
  };

  const handleActionTerminals = useCallback(
    async (action: 'activate' | 'deactivate', info?: any) => {
      const listId =
        selectedRows?.map((item: any) => item.id).join(',') || String(info?.id);
      setLoadingTerminalId(info?.id);
      const { success, message } = await (
        action === 'activate' ? activeTerminalAPI : deactiveTerminalAPI
      )({
        ids: listId,
        useLoading: true,
      });
      if (success) {
        const updatedData = data.data.map((item) => {
          const found = selectedRows.find((row: any) => row.id === item.id);
          const isTargetItem = info && item?.id === info?.id;
          if (found || isTargetItem) {
            return {
              ...item,
              active: action === 'activate' ? true : false,
            };
          }
          return item;
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
      setLoadingTerminalId(null);
    },
    [data.data, selectedRows], // eslint-disable-line react-hooks/exhaustive-deps
  );

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef, searchCardRef],
    additionalHeights: [remToPx(8)],
  });

  const StatusCell = useCallback(
    ({ info }: { info: any }) => {
      console.log('info_in_status_cell', info?.row?.original);
      return (
        <SwitchBtn
          actionType={ROLE_PERMISSION.UPDATE}
          statusValue={info?.row?.original?.active}
          onChange={() => {
            handleSelectionRows([info?.row?.original]);
            handleActionTerminals(
              info?.row?.original?.active
                ? 'deactivate'
                : ('activate' as 'activate' | 'deactivate'),
              info?.row?.original,
            );
          }}
          loading={
            loadingTerminalId
              ? loadingTerminalId === info?.row?.original?.id
              : false
          }
        />
      );
    },
    [handleActionTerminals, loadingTerminalId],
  );


  const [showDetailModal, setShowDetailModal] = useState<{ show: boolean, data: any }>({
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

  const HistoryBehaviorColumns = [
    {
      Header: 'Image',
      accessor: 'image',
      enableSorting: false,
      enableColumnFilter: false,
      cell: (row: any) => {
        return (
          <TerminalImage
            imageUrl={row?.row?.original?.avatar__file_url || ErrorImage}
            alt="terminal"
          />
        );
      },
      width: 120,
      minWidth: 120,
      maxWidth: 120,
    },
    {
      Header: 'Status',
      accessor: 'active',
      enableSorting: false,
      enableColumnFilter: false,
      cell: (info: any) => <StatusCell info={info} />,
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
              onClick={() =>
                handleViewOperatingTime(info?.row?.original?.id)
              }
            />
          </>
        );
      },
    },

  ];

  return (
    <Container
      id="list-packaging"
      isOpenCanvas={openOffcanvas}
    >
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[
          <CustomBtn
            label={t('Add New Terminal')}
            icon={<GoPlus size={18} />}
            actionType={ROLE_PERMISSION.CREATE}
            onClick={() =>
              navigate(CustomRoutes.terminals.subRoutes.addNewTerminals.path)
            }
          />,
        ]}
      />
      <Main>
        <div className="list-packaging__table-container">
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
                onClick={() => handleActionTerminals('activate')}
              />,
              <CustomBtn
                label={t('Deactivate')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.UPDATE}
                disabled={selectedRows.length === 0}
                onClick={() => handleActionTerminals('deactivate')}
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
      <OperatingTimeModal
        show={showDetailModal.show}
        onHide={() => setShowDetailModal({ show: false, data: {} })}
        data={showDetailModal.data} />
    </Container>
  );
};
export default ListTerminals;
