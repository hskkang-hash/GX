import { Box } from '@mui/material';
import React, { useState, useEffect, useRef } from 'react';
import {
  CustomizableTable,
  useLoadingContext,
  useCalculateHeight,
  HeaderWithBtn,
  Main,
  Container,
} from 'rj-core';

import Truncate from '@/components/truncate/Truncate';
import {
  searchValidNotam,
  getDefaultSearchParams,
  type NotamSearchParams,
  type NotamData,
} from '@/services/notamService';
import { remToPx } from '@/utils/utils';

import './NoTam.scss';
import NotamDetailModal from './components/NotamDetailModal';
import NotamSearchForm from './components/NotamSearchForm';

const NoTam: React.FC = () => {
  const { showLoadingGlobal, hideLoadingGlobal } = useLoadingContext();

  const [tableData, setTableData] = useState<{
    data: NotamData[];
    totalItem: number;
    totalPage: number;
  }>({
    data: [],
    totalItem: 0,
    totalPage: 0,
  });

  const [searchParams, setSearchParams] = useState<NotamSearchParams>(
    getDefaultSearchParams(),
  );
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number | null>(20);
  const [loading, setLoading] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedNotam, setSelectedNotam] = useState<NotamData | null>(null);

  const headerPageRef = useRef(null);
  const searchFormRef = useRef(null);

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef, searchFormRef],
    additionalHeights: [remToPx(6)],
  });

  // Table columns configuration
  const columns = [
    {
      Header: 'ISSUE TIME',
      accessor: 'ISSUE_TIME',
      enableSorting: false,
      enableColumnFilter: false,
    },
    {
      Header: 'LOCATION',
      accessor: 'LOCATION',
      enableSorting: false,
      enableColumnFilter: false,
    },
    {
      Header: 'NOTAM NO',
      accessor: 'NOTAM_NO',
      enableSorting: false,
      enableColumnFilter: false,
    },
    {
      Header: 'QCODE',
      accessor: 'QCODE',
      enableSorting: false,
      enableColumnFilter: false,
    },
    {
      Header: 'START TIME',
      accessor: 'EFFECTIVESTART',

      enableSorting: false,
      enableColumnFilter: false,
    },
    {
      Header: 'END TIME',
      accessor: 'EFFECTIVEEND',
      enableSorting: false,
      enableColumnFilter: false,
    },
    {
      Header: 'FULL TEXT',
      accessor: 'FULL_TEXT',
      enableSorting: false,
      enableColumnFilter: false,
      customStyle: { minWidth: '200px', width: '250px' },
      cell: (row: { getValue: () => string }) => {
        const fullText = row.getValue();
        return (
          <div
            style={{
              whiteSpace: 'pre-wrap',
              fontSize: '0.875rem',
            }}
          >
            <Truncate
              content={fullText}
              maxLengthContent={100}
            />
          </div>
        );
      },
    },
  ];

  // Fetch NOTAM data
  const fetchNotamData = async (params: NotamSearchParams, page: number) => {
    setLoading(true);
    showLoadingGlobal();

    try {
      const response = await searchValidNotam({
        ...params,
        ibpage: page,
      });

      console.log('NOTAM API response type:', typeof response);
      console.log('NOTAM API response:', response);
      console.log('response.DATA:', response?.DATA);
      console.log('response.Total:', response?.Total);

      const totalPages =
        pageSize && response?.Total ? Math.ceil(response.Total / pageSize) : 1;

      setTableData({
        data: response?.DATA || [],
        totalItem: response?.Total || 0,
        totalPage: totalPages,
      });
    } catch (error) {
      console.error('Error fetching NOTAM data:', error);
      console.error('Error details:', error);
      setTableData({
        data: [],
        totalItem: 0,
        totalPage: 0,
      });
    } finally {
      setLoading(false);
      hideLoadingGlobal();
    }
  };

  // Initial load
  useEffect(() => {
    fetchNotamData(searchParams, 1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle page change
  useEffect(() => {
    if (currentPage > 1) {
      fetchNotamData(searchParams, currentPage);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage]);

  // Handle search
  const handleSearch = (params: NotamSearchParams) => {
    setSearchParams(params);
    setCurrentPage(1);
    fetchNotamData(params, 1);
  };

  const handleViewDetail = (selectedRowData: NotamData) => {
    if (selectedRowData) {
      setSelectedNotam(selectedRowData);
      setShowDetailModal(true);
    }
  };

  return (
    <Container className="notam-page">
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[]}
      />

      <Main>
        <Box
          className="notam-page__content"
          sx={{
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* Search Form */}
          <NotamSearchForm
            ref={searchFormRef}
            onSearch={handleSearch}
            loading={loading}
          />

          {/* Data Table */}
          <CustomizableTable
            availableHeight={spaceTableHeight}
            columns={columns}
            data={tableData}
            currentPage={currentPage}
            setCurrentPage={setCurrentPage}
            // pageSize={pageSize}
            // setPageSize={setPageSize}
            hasPagination={true}
            useSystemSetting={true}
            stickyHeader={true}
            notShowSelectRow={true}
            onClickRow={handleViewDetail}
          />
        </Box>
      </Main>

      {/* NOTAM Detail Modal */}
      <NotamDetailModal
        show={showDetailModal}
        onHide={() => {
          setShowDetailModal(false);
          setSelectedNotam(null);
        }}
        notamData={selectedNotam}
        inorout={searchParams.sch_inorout || 'D'}
      />
    </Container>
  );
};

export default NoTam;
