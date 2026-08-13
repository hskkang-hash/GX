import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { GoPlus } from 'react-icons/go';
import { useLocation, useNavigate } from 'react-router-dom';
import { CustomizableTable, Main, ToastTopHelper } from 'rj-core';
import {
  Container,
  CustomBtn,
  HeaderWithBtn,
  ROLE_PERMISSION,
  useCalculateHeight,
} from 'rj-core';

import { CustomRoutes } from '@/services/API';
import { formatEnabled } from '@/utils/formatColumns';
import { remToPx } from '@/utils/utils';

import useCommonAPI from '../useCommonAPI/useAPI';
import useLibrary from './hooks/useLibrary';
import { LibraryData, LibraryListRequest, LibraryListResponse } from './type';

const LibraryDroneList = () => {
  const { t } = useTranslation();
  const [objSearch, setObjSearch] = useState({});
  const navigate = useNavigate();
  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [selectedRows, setSelectedRows] = useState<LibraryData[]>([]);

  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);
  const [showAdvancedSearch, setShowAdvancedSearch] = useState<boolean>(false);
  const [refreshTable, setRefreshTable] = useState<boolean>(false);

  const { getLibrary, deleteLibrary } = useLibrary();

  const [data, setData] = useState<LibraryListResponse>({
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

  const handleGetLibrary = async ({
    objSearch,
    pageSize,
    currentPage,
  }: LibraryListRequest) => {
    const response = await getLibrary({
      pageSize: pageSize,
      currentPage: currentPage,
      objSearch: objSearch,
    });

    console.log('response_list_library', response);

    setData(response);
  };

  const handleSelectionRows = (selectedData: any) => {
    setSelectedRows(selectedData);
  };

  const handleViewDetailDevice = (selectedRow: any) => {
    navigate(
      CustomRoutes.library.subRoutes.editLibrary.path.replace(
        ':id',
        selectedRow.id.toString(),
      ),
      {
        state: { id: selectedRow.id },
      },
    );
  };

  const headerPageRef = useRef(null);
  const searchCardRef = useRef(null);

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef, searchCardRef],
    additionalHeights: [remToPx(8)],
  });

  const [refreshLibrary, setRefreshLibrary] = useState(false);
  const handleDeleteLibrary = async () => {
    const ids = selectedRows?.map((item: any) => item.id).join(',');

    const { success, message } = await deleteLibrary({
      ids,
    });

    if (success) {
      setRefreshLibrary(true);
      ToastTopHelper.success(message);
      setRefreshTable(true);
    } else {
      ToastTopHelper.error(message);
    }
  };
  useEffect(() => {
    if (pageSize) {
      handleGetLibrary({ objSearch, pageSize, currentPage });
    }
    if (refreshLibrary && pageSize) {
      handleGetLibrary({ objSearch, pageSize, currentPage });
      setRefreshLibrary(false);
    }
  }, [pageSize, currentPage, objSearch, refreshLibrary]);

  const [mainType, setMainType] = useState<any[]>([]);
  const { getMainType } = useCommonAPI();
  useEffect(() => {
    const fetchMainType = async () => {
      try {
        const { data: dataMainType } = await getMainType();
        setMainType([{ label: t('Select'), value: '' }, ...dataMainType]);
      } catch (error) {
        console.log('Error fetch status type', error);
      }
    };
    fetchMainType();
  }, [mainType.length < 0]);

  const ListLibraryColumns = [
    {
      Header: 'In Use',
      accessor: 'in_use',
      enableColumnFilter: false,
      cell: (row: any) => formatEnabled(row?.row?.original?.in_use),
    },
    {
      Header: 'Type',
      accessor: 'main_type__name',
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
      cell: (row: any) => {
        return row.getValue() ? <span>{row.getValue()}</span> : '-';
      },
    },
  ];
  return (
    <Container
      id="list-library"
      isOpenCanvas={openOffcanvas || showAdvancedSearch}
    >
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[
          <CustomBtn
            label={t('Add New Template')}
            icon={<GoPlus size={18} />}
            actionType={ROLE_PERMISSION.CREATE}
            onClick={() => navigate('/library/add-new-library')}
          />,
        ]}
      />

      <Main>
        <div className="list-device__table-container">
          <CustomizableTable
            stickyHeader
            availableHeight={spaceTableHeight}
            columns={ListLibraryColumns}
            data={data}
            objSearch={objSearch}
            setObjSearch={setObjSearch}
            onClickRow={handleViewDetailDevice}
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
                onClick={() => handleDeleteLibrary()}
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

export default LibraryDroneList;
