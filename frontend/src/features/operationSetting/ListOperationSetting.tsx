import { useTheme } from '@mui/material/styles';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  CustomizableTable,
  HeaderWithBtn,
  Main,
  useCalculateHeight,
} from 'rj-core';

import { formatEnabled } from '@/utils/formatColumns';
import { remToPx } from '@/utils/utils';

import EditOperationSetting from './EditOperationSetting/EditOperationSetting';
import useSettings from './hooks/useSettings';

// Types
interface OrderRow {
  id: number;
  order_id: string;
  current_status__code: string;
  order_time: string;
  sender: string;
  recipient: string;
  creator: string;
  number_of_package: number;
}

interface TableData {
  data: OrderRow[];
  totalItem: number;
  totalPage: number;
}

interface SearchParams {
  pageSize: number;
  currentPage: number;
  objSearch: Record<string, any>;
}

const COLUMNS = [
  { Header: 'Menu Type', accessor: 'mainType' },
  { Header: 'Step', accessor: 'step' },
  { Header: 'Group', accessor: 'group' },
  {
    Header: 'Is Active',
    accessor: 'isActive',
    filterVariant: 'checkbox',
    filterOptions: ['True', 'False'],
    cell: (row: any) => formatEnabled(row?.row?.original?.isActive),
  },
  { Header: 'API URL', accessor: 'apiUrl' },
  { Header: 'Updated Time', accessor: 'updatedTime' },
  { Header: 'Updater', accessor: 'updater' },
] as const;

export default function ListOperationSetting() {
  const theme = useTheme();
  const [open, setOpen] = useState(false);

  const handleDrawerOpen = () => {
    setOpen(true);
  };

  const handleDrawerClose = () => {
    setOpenOffcanvas(false);
    setOpen(false);
    setSelectedSetting(null);
  };

  const [selectedRows, setSelectedRows] = useState<OrderRow[]>([]);
  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [objSearch, setObjSearch] = useState<Record<string, any>>({});
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [data, setData] = useState<TableData>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });
  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);
  const [selectedSetting, setSelectedSetting] = useState(null);

  // Hooks
  const { t } = useTranslation();
  const navigate = useNavigate();
  const headerPageRef = useRef<HTMLDivElement>(null);
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8), remToPx(4)],
  });
  const { getOperationSettings } = useSettings();

  const fetchData = async () => {
    const response = await getOperationSettings({
      pageSize,
      currentPage,
      objSearch,
    });
    setData(
      response || {
        data: [],
        totalItem: 0,
        totalPage: 0,
      },
    );
  };

  useEffect(() => {
    if (pageSize) {
      fetchData();
    }
  }, [pageSize, currentPage, objSearch]);

  // Constants
  const handleViewOrderDetail = (row: any) => {
    setOpenOffcanvas(true);
    setOpen(true);
    setSelectedSetting(row);
  };

  return (
    <Container isOpenCanvas={openOffcanvas}>
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[]}
      />
      <Main>
        <CustomizableTable
          notShowSelectRow
          columns={COLUMNS}
          data={data}
          refreshTable={refreshTable}
          setRefreshTable={setRefreshTable}
          objSearch={objSearch}
          setObjSearch={setObjSearch}
          onSelectedRows={setSelectedRows}
          currentPage={currentPage}
          setCurrentPage={setCurrentPage}
          pageSize={pageSize}
          setPageSize={setPageSize}
          stickyHeader
          availableHeight={spaceTableHeight}
          onClickRow={handleViewOrderDetail}
          offcanvas={openOffcanvas}
          setOpenOffcanvas={(boolean) => {
            setOpen(false);
            setOpenOffcanvas(boolean);
          }}
          hightlidhtRow={
            data.data?.find((item) => {
              return item.id === selectedSetting?.id;
            }) || null
          }
        />
      </Main>
      <EditOperationSetting
        open={open}
        onClose={handleDrawerClose}
        data={selectedSetting}
        refreshData={fetchData}
      />
    </Container>
  );
}
