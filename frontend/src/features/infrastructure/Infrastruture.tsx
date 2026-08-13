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

import ErrorImage from '@/assets/images/no-image.png';
import SwitchBtn from '@/components/Form/SwitchBtn';
import { CustomRoutes } from '@/services/API';
import { isEmptyObject, remToPx } from '@/utils/utils';

import useCommonAPI from '../useCommonAPI/useAPI';
import useInfrastructure from './hooks/useInfrastructure';
import useAPI from '../terminals/useAPI/useAPI';
import OperatingTimeModal from '../terminals/components/OperatingTimeModal';

const InfrastructureImage = React.memo<{
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

InfrastructureImage.displayName = 'InfrastructureImage';

interface InfrastructureState {
  id: string;
  code: string;
  avatar__file_url?: string;
  name: string;
  active?: boolean;
  created_on?: string;
  terminal_base_type: string;
  full_address: string;
  address?: string;
  latitude: number;
  longitude: number;
  postal_code?: number | null | undefined;
  url?: string;
  manager?: string;
  manager_name?: string;
  note?: string;
  terminal_purpose__name?: string;
  infrastructure_type__name?: string;
  purpose_type__name?: string;
}

// Type for table row
interface TableRow {
  row: {
    original: InfrastructureState;
  };
}

const Infrastruture = () => {
  const [objSearch, setObjSearch] = useState({});
  const navigate = useNavigate();
  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [selectedRows, setSelectedRows] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const {
    getInfrastructureList,
    changeStatusInfrastructure,
    activeInfrastructureAPI,
    deactiveInfrastructureAPI,
  } = useInfrastructure();

  const [data, setData] = useState<{
    data: any[];
    totalItem: number;
    totalPage: number;
  }>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });

  const fetchInfrastructureList = async () => {
    setLoading(true);

    const { success, message, data, total_items, total_pages } =
      await getInfrastructureList({
        pageSize,
        currentPage,
        objSearch,
      });
    if (success) {
      setData({
        data: data,
        totalItem: total_items,
        totalPage: total_pages,
      });
    } else {
      ToastTopHelper.error(message);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (pageSize && !isEmptyObject(objSearch)) {
      fetchInfrastructureList();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageSize, currentPage, objSearch]);

  const handleSelectionRows = (selectedData: any) => {
    console.log(selectedData.id);
    setSelectedRows(selectedData);
  };

  const handleActionInfrastructure = useCallback(
    async (action: 'activate' | 'deactivate', info?: any) => {
      const listId =
        selectedRows?.map((item: any) => item.id).join(',') || String(info?.id);
      setLoadingInfrastructureId(info?.id);
      const { success, message } = await (
        action === 'activate'
          ? activeInfrastructureAPI
          : deactiveInfrastructureAPI
      )({
        ids: listId,
        useLoading: true,
      });
      if (success) {
        const updatedData = data?.data?.map((item) => {
          const found = selectedRows?.find((row: any) => row?.id === item?.id);
          const isTargetItem = info && item?.id === info?.id;
          if (found || isTargetItem) {
            return {
              ...item,
              active: action === 'activate' ? true : false,
            };
          }
          return item;
        });
        setData((prevData) => ({
          ...prevData,
          data: updatedData,
        }));
        setRefreshTable(true);
        ToastTopHelper.success(message);
      } else {
        ToastTopHelper.error(message);
      }
      setLoadingInfrastructureId(null);
    },
    [selectedRows, activeInfrastructureAPI, deactiveInfrastructureAPI], // eslint-disable-line react-hooks/exhaustive-deps
  );

  const handleViewDetailInfrastructure = (selectedRow: any) => {
    if (selectedRow?.active) {
      navigate(
        CustomRoutes.infrastructure.subRoutes.detailInfrastructure.path.replace(
          ':id',
          selectedRow.id.toString(),
        ),
      );
    }
  };

  const headerPageRef = useRef(null);

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8)],
  });

  const handleregister = () => {
    navigate(CustomRoutes.infrastructure.subRoutes.register.path);
  };

  const [loadingInfrastructureId, setLoadingInfrastructureId] = useState<
    string | null
  >(null);

  const StatusCell = useCallback(
    ({ info }: { info: any }) => {
      return (
        <SwitchBtn
          actionType={ROLE_PERMISSION.UPDATE}
          statusValue={info?.row?.original?.active}
          onChange={() => {
            setSelectedRows([info?.row?.original]);
            handleActionInfrastructure(
              info?.row?.original?.active
                ? 'deactivate'
                : ('activate' as 'activate' | 'deactivate'),
              info?.row?.original,
            );
          }}
          loading={
            loadingInfrastructureId
              ? loadingInfrastructureId === info?.row?.original?.id
              : false
          }
        />
      );
    },
    [handleActionInfrastructure, loadingInfrastructureId],
  );

  const ImageCell = useMemo(
    () =>
      ({ info }: { info: any }) => {
        return (
          <InfrastructureImage
            imageUrl={info?.row?.original?.avatar__file_url || ErrorImage}
            alt="infrastructure"
          />
        );
      },
    [],
  );

  const { getOptionsByModel, getFunctionTypes, useFetchOptions } =
    useCommonAPI();

  const majorCategoryConfig = useMemo(
    () => ({
      type: 'model' as const,
      params: { name_modal: 'TerminalPurpose', search_field: 'name' },
      defaultLabel: t('Select'),
    }),
    [],
  );

  const minorCategoryConfig = useMemo(
    () => ({
      type: 'function' as const,
      params: { function_type: 'infrastructure' },
      defaultLabel: t('Select'),
    }),
    [],
  );

  const purposeTypeConfig = useMemo(
    () => ({
      type: 'model' as const,
      params: { name_modal: 'purposeType', search_field: 'name' },
      defaultLabel: t('Select'),
    }),
    [],
  );

  const majorCategory = useFetchOptions(getOptionsByModel, majorCategoryConfig);
  const minorCategory = useFetchOptions(getFunctionTypes, minorCategoryConfig);
  const purposeType = useFetchOptions(getOptionsByModel, purposeTypeConfig);
  console.log({ majorCategory, minorCategory, purposeType });

  const [showDetailModal, setShowDetailModal] = useState<{ show: boolean, data: any }>({
    show: false,
    data: {},
  });
  const {
    getOperatingTimeTerminalAPI,
  } = useAPI();

  const handleViewOperatingTime = async (id: number) => {
    const { success, message, data } = await getOperatingTimeTerminalAPI(id);
    console.log('data_operating_time', data);
    if (success) {
      setShowDetailModal({ show: true, data: data });
    } else {
      ToastTopHelper.error(message);
    }
  };

  // Memoized columns to prevent unnecessary re-renders
  const columns = [
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
      Header: 'Major Category',
      accessor: 'terminal_purpose__name',
      filterVariant: 'select',
      filterOptions:
        majorCategory.length > 0
          ? majorCategory?.map((item: any) => ({
            label: item.label,
            value:
              item.label == 'Select' ||
                item.label == '선택' ||
                item.label == 'เลือก'
                ? ''
                : item.label,
          }))
          : [],
      cell: (info: any) => <span>{info.getValue() || '-'}</span>,
    },
    {
      Header: 'Minor Category',
      accessor: 'function',
      filterVariant: 'select',
      filterOptions:
        minorCategory.length > 0
          ? minorCategory?.map((item: any) => ({
            label: item.label,
            value:
              item.label == 'Select' ||
                item.label == '선택' ||
                item.label == 'เลือก'
                ? ''
                : item.label,
          }))
          : [],
      cell: (info: any) => {
        console.log('info', info?.row?.original?.function);
        return <span>{info.getValue() || '-'}</span>;
      },
    },

    {
      Header: 'Purpose',
      accessor: 'purpose_type__name',
      filterVariant: 'select',
      filterOptions:
        purposeType.length > 0
          ? purposeType?.map((item: any) => ({
            label: t(item.label),
            value:
              item.label == 'Select' ||
                item.label == '선택' ||
                item.label == 'เลือก'
                ? ''
                : item.label,
          }))
          : [],
      cell: (info: any) => {
        console.log('info', info?.row?.original?.purpose_type_id);
        return <span>{info.getValue() || '-'}</span>;
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
      id="list-infrastructure"
      isOpenCanvas={openOffcanvas}
    >
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[
          <CustomBtn
            label={t('Register')}
            icon={<GoPlus size={18} />}
            actionType={ROLE_PERMISSION.CREATE}
            onClick={handleregister}
          />,
        ]}
      />

      <Main>
        <div className="list-infrastructure__table-container">
          <CustomizableTable
            stickyHeader
            availableHeight={spaceTableHeight}
            columns={columns}
            data={data}
            objSearch={objSearch}
            setObjSearch={setObjSearch}
            onClickRow={handleViewDetailInfrastructure}
            onSelectedRows={handleSelectionRows}
            refreshTable={refreshTable}
            setRefreshTable={setRefreshTable}
            currentPage={currentPage}
            setCurrentPage={setCurrentPage}
            buttons={[
              <CustomBtn
                label={t('Activate')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.UPDATE}
                disabled={selectedRows.length === 0}
                onClick={() => handleActionInfrastructure('activate')}
              />,
              <CustomBtn
                label={t('Deactivate')}
                type="button"
                variant="outline"
                color="primary"
                size="sm"
                actionType={ROLE_PERMISSION.UPDATE}
                disabled={selectedRows.length === 0}
                onClick={() => handleActionInfrastructure('deactivate')}
              />,
            ]}
            pageSize={pageSize}
            setPageSize={setPageSize}
            offcanvas={openOffcanvas}
            setOpenOffcanvas={(boolean: boolean) => {
              setOpenOffcanvas(boolean);
            }}
          />
        </div>
        <OperatingTimeModal
          show={showDetailModal.show}
          onHide={() => setShowDetailModal({ show: false, data: {} })}
          data={showDetailModal.data} />
      </Main>
    </Container>
  );
};
export default Infrastruture;
