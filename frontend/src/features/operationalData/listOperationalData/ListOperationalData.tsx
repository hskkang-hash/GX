import { Box } from '@mui/material';
import { t } from 'i18next';
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { BsUpload } from 'react-icons/bs';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  CustomBtn,
  CustomizableTable,
  HeaderWithBtn,
  Main,
  ToastTopHelper,
  useCalculateHeight,
  ROLE_PERMISSION,
} from 'rj-core';

import CustomFieldBtn from '@/components/Form/CustomFieldBtn';
import Truncate from '@/components/truncate/Truncate';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { remToPx } from '@/utils/utils';

import ErrorImage from '../../../assets/images/no-image.png';
import useAPI from '../useAPI/useAPI';
import './ListOperationalData.scss';

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

const ListOperationalData = () => {
  const [objSearch, setObjSearch] = useState({});
  const navigate = useNavigate();
  const [pageSize, setPageSize] = useState<number>(25);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [selectedRows, setSelectedRows] = useState<any[]>([]);
  const listId = selectedRows?.map((item: any) => item.id);
  const listTrackingCode = selectedRows?.map(
    (item: any) => item.delivery_operation_code,
  );
  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [itemType, setItemType] = useState<any[]>([]);
  const { getOptionsByModel } = useCommonAPI();
  const {
    getOperationalData,
    uploadFileOperationalData,
    donwloadFileOperationalDataAll,
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

  const fetchData = async ({
    objSearch,
    pageSize,
    currentPage,
  }: {
    objSearch: any;
    pageSize: number;
    currentPage: number;
  }) => {
    const { success, data, message } = await getOperationalData({
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

  const handleViewDetailOperationalData = (selectedRow: any) => {
    navigate(`/operational-data/detail-operational-data/${selectedRow.id}`, {
      state: { id: selectedRow.id },
    });
  };

  const handleDownloadFiles = async () => {
    const { success, message } = await donwloadFileOperationalDataAll({
      id: listId,
    });
    if (success) {
      // ToastTopHelper.success(message);
      setRefreshTable(true);
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

  useEffect(() => {
    const fetchItemType = async () => {
      try {
        const fetchFunction = getOptionsByModel({
          name_modal: 'OrderItemType',
          search_field: 'name',
        });
        const { options } = await fetchFunction('', [], {
          page: 1,
          page_size: 1000,
        });
        if (options) {
          setItemType([{ label: t('Select'), code: '' }, ...options]);
        }
      } catch (error) {
        console.log('Error fetch item type', error);
      }
    };
    fetchItemType();
  }, [itemType.length < 0]);

  const handleUploadFile = async ({
    id,
    files,
    type,
  }: {
    id: number;
    files: any;
    type:
      | 'uploadFileDrone'
      | 'uploadFileRobot'
      | 'uploadVideoDrone'
      | 'uploadVideoRobot';
  }) => {
    await uploadFileOperationalData({
      id,
      files,
      type,
    });
  };

  const HistoryBehaviorColumns = useMemo(() => {
    return [
      {
        Header: 'Tracking Number',
        accessor: 'delivery_operation_code',
        customStyle: {
          width: '120px',
        },
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
        Header: 'Delivery Date',
        accessor: 'delivered_at',
        filterVariant: 'datetime',
        customStyle: {
          width: '120px',
        },
      },

      {
        Header: 'Route',
        accessor: 'route',
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
        Header: 'Delivery Point',
        accessor: 'delivery_point',
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
        Header: t('Item Type'),
        accessor: 'item_type_code',
        filterVariant: 'select',
        customStyle: {
          width: '90px',
        },
        filterOptions:
          itemType.length > 0
            ? itemType?.map((item: any) => ({
                label: item.label,
                value: item.code,
              }))
            : [],
        cell: (row: any) => {
          return row?.row?.original?.item_type ? (
            <Truncate
              content={row?.row?.original?.item_type}
              tooltipContent={row?.row?.original?.item_type}
            />
          ) : (
            '-'
          );
        },
      },
      {
        Header: 'Weight',
        accessor: 'item_weight',
        customStyle: {
          width: '63px',
        },
        cell: (row: any) => {
          return row.getValue() ? (
            <span>
              {row.getValue().includes('null') ? '-' : row.getValue()}
            </span>
          ) : (
            '-'
          );
        },
      },
      {
        Header: 'Operation Log',
        accessor: 'operation_log',
        enableSorting: false,
        enableColumnFilter: false,
        customStyle: {
          width: '15rem',
        },
        cell: (info: any) => {
          return (
            <div className="d-flex gap-2">
              <CustomFieldBtn
                label={t('Drone')}
                icon={<BsUpload size={16} />}
                onClick={(value: any) => {
                  if (value.length >= 1) {
                    handleUploadFile({
                      id: info?.row?.original?.id,
                      files: value,
                      type: 'uploadFileDrone',
                    });
                  }
                }}
                action="upload"
                acceptFileType={['.bin', '.tlog', '.log']}
              />
              <CustomFieldBtn
                label={t('Robot')}
                icon={<BsUpload size={16} />}
                onClick={(value: any) => {
                  if (value.length >= 1) {
                    handleUploadFile({
                      id: info?.row?.original?.id,
                      files: value,
                      type: 'uploadFileRobot',
                    });
                  }
                }}
                action="upload"
                acceptFileType={['.log', '.bag']}
              />
            </div>
          );
        },
      },
      {
        Header: 'Video',
        accessor: 'video',
        enableSorting: false,
        enableColumnFilter: false,
        customStyle: {
          width: '15rem',
        },
        cell: (info: any) => {
          return (
            <div className="d-flex gap-2">
              <CustomFieldBtn
                label={t('Drone')}
                icon={<BsUpload size={16} />}
                action="upload"
                acceptFileType={['.mp4']}
                onClick={(value: any) => {
                  if (value.length >= 1) {
                    handleUploadFile({
                      id: info?.row?.original?.id,
                      files: value,
                      type: 'uploadVideoDrone',
                    });
                  }
                }}
              />
              <CustomFieldBtn
                label={t('Robot')}
                icon={<BsUpload size={16} />}
                action="upload"
                acceptFileType={['.mp4']}
                onClick={(value: any) => {
                  if (value.length >= 1) {
                    handleUploadFile({
                      id: info?.row?.original?.id,
                      files: value,
                      type: 'uploadVideoRobot',
                    });
                  }
                }}
              />
            </div>
          );
        },
      },
    ];
  }, [itemType, handleUploadFile]);

  return (
    <Container
      id="list-device"
      isOpenCanvas={openOffcanvas}
    >
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[]}
      />
      <Main>
        <div className="list-device__table-container">
          <CustomizableTable
            subTable
            stickyHeader
            availableHeight={spaceTableHeight}
            columns={HistoryBehaviorColumns}
            data={data || []}
            useSystemSetting
            objSearch={objSearch}
            setObjSearch={setObjSearch}
            onClickRow={handleViewDetailOperationalData}
            onSelectedRows={handleSelectionRows}
            refreshTable={refreshTable}
            setRefreshTable={setRefreshTable}
            buttons={[
              <CustomBtn
                label={t('Download Selected Item(s)')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.UPDATE}
                disabled={selectedRows.length === 0}
                onClick={() => handleDownloadFiles()}
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
    </Container>
  );
};
export default ListOperationalData;
