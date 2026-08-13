import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  CustomBtn,
  CustomizableTable,
  HeaderWithBtn,
  Main,
  ToastTopHelper,
  useCalculateHeight,
  useLoadingContext,
} from 'rj-core';

import { CustomRoutes } from '../../../services/API';
import { downloadElementAsPDF } from '../../../utils/pdfUtils';
import { formatBytes, remToPx } from '../../../utils/utils';
import { DownloadTemplateVideoAnalysis } from '../components/DownloadTemplateVideoAnalysis';
import { useDataAnalysis } from '../hooks/useDataAnalysis';
import { DataAnalysisState } from '../types';

export const DataAnalysisPage = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const headerPageRef = useRef<HTMLDivElement>(null);
  const downloadTemplateRef = useRef<HTMLDivElement>(null);

  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8)],
  });
  const {
    dataAnalysis,
    pageSize,
    currentPage,
    objSearch,
    setObjSearch,
    setCurrentPage,
    setPageSize,
    getDataAnalysisAPI,
    getDetailDataAnalysisAPI,
    detailDataAnalysis,
  } = useDataAnalysis();
  const { showLoading, hideLoading } = useLoadingContext();
  const [downloadingIds, setDownloadingIds] = useState<Set<number>>(new Set());

  const handleDownloadPDF = async (id: number): Promise<void> => {
    if (!downloadTemplateRef.current) {
      return;
    }

    try {
      showLoading();
      setDownloadingIds((prev) => new Set(prev).add(id));

      // Wait for the collapse animation to complete
      await new Promise((resolve) => setTimeout(resolve, 500));

      // Generate filename
      const videoFileName =
        detailDataAnalysis?.video_path?.split('/')?.pop() || 'report';
      const filename = `DataAnalysis_${videoFileName}_${id}.pdf`;

      // Download as PDF with landscape orientation and full width
      await downloadElementAsPDF(downloadTemplateRef.current, filename, {
        margin: 10,
        format: 'a4',
        orientation: 'portrait',
        forceFullWidth: true,
      });

      ToastTopHelper.success(t('Report downloaded successfully'));
    } catch (error) {
      console.error('Error downloading PDF:', error);
      ToastTopHelper.error(t('Failed to download report'));
    } finally {
      setDownloadingIds((prev) => {
        const newSet = new Set(prev);
        newSet.delete(id);
        return newSet;
      });
      hideLoading();
    }
  };

  useEffect(() => {
    if (pageSize) {
      getDataAnalysisAPI();
    }
  }, [pageSize, currentPage, objSearch]);

  const handleGetDetailDataAnalysis = async (id: number) => {
    await getDetailDataAnalysisAPI(id, false);

    await handleDownloadPDF(id);
  };

  const columns = [
    {
      Header: 'File Name',
      accessor: 'video_path',
      cell: (row: { row: { original: { video_path: string } } }) => {
        const videoPath = row.row.original.video_path;
        const videoName = videoPath?.split('/')?.pop();
        return <div>{videoName || '-'}</div>;
      },
    },
    {
      Header: 'From',
      accessor: 'drone_name',
    },
    {
      Header: 'Last Modified',
      accessor: 'updated_at',
      filterVariant: 'datetime',
    },
    {
      Header: 'Size',
      accessor: 'video_size',
      enableColumnFilter: false,
      enableSorting: false,
      cell: (row: { row: { original: { video_size: number } } }) => {
        return (
          <div>
            {row.row.original.video_size
              ? formatBytes(row.row.original.video_size)
              : '-'}
          </div>
        );
      },
    },
    {
      Header: ' ',
      accessor: 'id',
      enableColumnFilter: false,
      enableSorting: false,
      notUseConfigTable: true,

      cell: (row: { row: { original: { id: string } } }) => {
        const rowId = Number(row.row.original.id);
        const isDownloading = downloadingIds.has(rowId);

        return (
          <div style={{ width: '8rem' }}>
            <CustomBtn
              variant="outline"
              color="primary"
              label={t('Download Report')}
              type="button"
              size="sm"
              onClick={() => handleGetDetailDataAnalysis(rowId)}
              disabled={isDownloading}
            />
          </div>
        );
      },
    },
  ];

  const handleClickRow = (row: DataAnalysisState) => {
    navigate(
      CustomRoutes.dataAnalysis.subRoutes.detailDataAnalysis.path.replace(
        ':id',
        row.id.toString(),
      ),
    );
  };

  return (
    <Container>
      <HeaderWithBtn
        ref={headerPageRef}
        buttons={[]}
      />
      <Main>
        <CustomizableTable
          subTable
          stickyHeader
          notShowSelectRow
          useSystemSetting
          availableHeight={spaceTableHeight}
          columns={columns}
          data={dataAnalysis}
          objSearch={objSearch}
          setObjSearch={setObjSearch}
          currentPage={currentPage}
          setCurrentPage={setCurrentPage}
          pageSize={pageSize}
          setPageSize={setPageSize}
          onClickRow={handleClickRow}
        />
      </Main>
      {/* Hidden component for PDF download */}
      <div style={{ position: 'absolute', left: '-9999px', top: '-9999px' }}>
        <DownloadTemplateVideoAnalysis
          ref={downloadTemplateRef}
          detailDataAnalysis={detailDataAnalysis || null}
        />
      </div>
    </Container>
  );
};
