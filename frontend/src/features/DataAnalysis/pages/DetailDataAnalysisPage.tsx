import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useTranslation } from 'react-i18next';
import { BsDash } from 'react-icons/bs';
import { useParams } from 'react-router-dom';
import {
  Container,
  CustomBreadcrumb,
  CustomBtn,
  CustomizableTable,
  Main,
  ToastTopHelper,
  useTheme,
} from 'rj-core';

import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';

import { CustomRoutes } from '../../../services/API';
import { downloadElementAsPDF } from '../../../utils/pdfUtils';
import CustomCollapse from '../../FlightLogAnalysis/components/CustomCollapse';
import '../assets/styles/DataAnalysis.scss';
import { DownloadTemplateVideoAnalysis } from '../components/DownloadTemplateVideoAnalysis';
import MediaGallery from '../components/MediaGallery';
import { useDataAnalysis } from '../hooks/useDataAnalysis';

const MAX_ITEMS_PER_ROW = 4;
const TOTAL_COLS = 8;
const COL_COUNT = 8;
const COLLAPSE_ANIMATION_DELAY = 500;
const DEFAULT_ACTIVE_KEYS = [1, 2, 3] as const;

// Helper function to format point coordinates
const formatPoint = (x: number | undefined, y: number | undefined): string => {
  const xValue = x ?? '-';
  const yValue = y ?? '-';
  return `${xValue}, ${yValue}`;
};

// Helper function to validate and build video URL
const buildVideoUrl = (
  rawVideoPath: string | undefined | null,
): { videoUrl: string | null; videoFileName: string } => {
  if (!rawVideoPath || typeof rawVideoPath !== 'string') {
    return { videoUrl: null, videoFileName: '-' };
  }

  const videoUrl =
    rawVideoPath.startsWith('http://') ||
    rawVideoPath.startsWith('https://') ||
    rawVideoPath.startsWith('/')
      ? rawVideoPath
      : `https://${rawVideoPath}`;

  const isValidVideoUrl =
    videoUrl !== '-' && typeof videoUrl === 'string' && videoUrl.trim() !== '';

  const videoFileName = isValidVideoUrl
    ? videoUrl.split('/').pop() || 'Video'
    : '-';

  return { videoUrl: isValidVideoUrl ? videoUrl : null, videoFileName };
};

export const DetailDataAnalysisPage = () => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const themeValue = useMemo(
    () => (theme === 'dark' ? 'dark' : 'light'),
    [theme],
  );
  const params = useParams();
  const id = useMemo(() => (params.id ? Number(params.id) : null), [params.id]);
  const isValidId = useMemo(() => id !== null && !isNaN(id) && id > 0, [id]);
  const refItem1 = useRef<HTMLDivElement>(null);
  const refItem2 = useRef<HTMLDivElement>(null);
  const refItem3 = useRef<HTMLDivElement>(null);
  const downloadTemplateRef = useRef<HTMLDivElement>(null);
  const [activeKeys, setActiveKeys] = useState<number[]>([
    ...DEFAULT_ACTIVE_KEYS,
  ]);
  const [isDownloading, setIsDownloading] = useState(false);
  const { getDetailDataAnalysisAPI, detailDataAnalysis } = useDataAnalysis();
  const { converRawDateToDateTimeFormat } = useConvertDate();

  useEffect(() => {
    if (isValidId && id !== null) {
      getDetailDataAnalysisAPI(id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, isValidId]);
  console.log('detailDataAnalysis', detailDataAnalysis);

  const BasicInfoData = useMemo(() => {
    let profileDate = '-';
    try {
      profileDate =
        converRawDateToDateTimeFormat(
          detailDataAnalysis?.profile_device__created_on,
        ) || '-';
    } catch (error) {
      console.error('Error formatting profile date:', error);
    }

    return {
      name: {
        label: 'Name',
        value:
          detailDataAnalysis?.profile_name ||
          detailDataAnalysis?.stream_monitor__external_drone_name ||
          '-',
      },
      purpose: {
        label: 'Purpose',
        value: detailDataAnalysis?.purpose || '-',
      },
      profile_date: {
        label: 'Profile Date',
        value: profileDate,
      },
    };
  }, [detailDataAnalysis, converRawDateToDateTimeFormat]);

  const DetailedInfoData = useMemo(() => {
    const { videoUrl, videoFileName } = buildVideoUrl(
      detailDataAnalysis?.video_path,
    );

    return {
      data: {
        drone: {
          label: 'Drone',
          value: detailDataAnalysis?.drone_name || '-',
        },
        operator: {
          label: 'Operator',
          value: detailDataAnalysis?.operator_name || '-',
        },
        registration_number: {
          label: 'Registration Number',
          value: detailDataAnalysis?.register_number || '-',
        },
        manufacturer: {
          label: 'Manufacturer',
          value: detailDataAnalysis?.manufacturer || '-',
        },
        flight_distance: {
          label: 'Flight Distance',
          value: detailDataAnalysis?.flight_distance || '-',
        },
        flight_time: {
          label: 'Flight Time',

          value: detailDataAnalysis?.flight_time || '-',
        },
        flight_altitude: {
          label: 'Flight Altitude',
          value: detailDataAnalysis?.capture_altitude || '-',
        },
        start_point: {
          label: 'Takeoff Location',
          value: formatPoint(
            detailDataAnalysis?.start_point_x,
            detailDataAnalysis?.start_point_y,
          ),
        },
        end_point: {
          label: 'Landing Location',
          value: formatPoint(
            detailDataAnalysis?.end_point_x,
            detailDataAnalysis?.end_point_y,
          ),
        },
        start_time: {
          label: 'Takeoff Time',
          value: (() => {
            try {
              return (
                converRawDateToDateTimeFormat(detailDataAnalysis?.start_time) ||
                '-'
              );
            } catch (error) {
              console.error('Error formatting start time:', error);
              return '-';
            }
          })(),
        },
        end_time: {
          label: 'Landing Time',
          value: (() => {
            try {
              return (
                converRawDateToDateTimeFormat(detailDataAnalysis?.end_time) ||
                '-'
              );
            } catch (error) {
              console.error('Error formatting end time:', error);
              return '-';
            }
          })(),
        },
        remarks: {
          label: 'Remarks',
          value: detailDataAnalysis?.remark || '-',
        },
      },
      video_data: videoUrl
        ? [
            {
              label: videoFileName,
              value: videoUrl,
            },
          ]
        : [],
    };
  }, [detailDataAnalysis, converRawDateToDateTimeFormat]);

  const AIVideoAnalysisData = useMemo(() => {
    if (
      !detailDataAnalysis?.analysis ||
      !Array.isArray(detailDataAnalysis.analysis)
    ) {
      return [];
    }
    return detailDataAnalysis.analysis.map((item) => {
      let detectTime = '-';
      try {
        detectTime = item.datetime
          ? converRawDateToDateTimeFormat(item.datetime) || '-'
          : '-';
      } catch (error) {
        console.error('Error formatting detect time:', error);
      }

      return {
        object:
          (Array.isArray(item.detections) &&
            item.detections.length > 0 &&
            item.detections[0]?.label) ||
          '-',
        object_count: item.detection_count || '-',
        detected_image_path: item.detected_image_path || '-',
        detect_time: detectTime,
      };
    });
  }, [detailDataAnalysis, converRawDateToDateTimeFormat]);

  const renderImageCell = useCallback(
    (row: {
      getValue: () => string;
      row: { original: { detected_image_path?: string } };
    }) => {
      const imagePath = row?.row?.original?.detected_image_path;
      if (
        !imagePath ||
        typeof imagePath !== 'string' ||
        imagePath.trim() === ''
      ) {
        return null;
      }
      return (
        <MediaGallery
          items={[
            {
              label: imagePath,
              value: imagePath,
              type: 'image',
            },
          ]}
          theme={themeValue}
        />
      );
    },
    [themeValue],
  );

  const COLUMNS_AIVideoAnalysis = useMemo(
    () => [
      {
        Header: 'Model',
        accessor: 'object',
        enableSorting: false,
        enableColumnFilter: false,
      },
      {
        Header: 'Object Count',
        accessor: 'object_count',
        enableSorting: false,
        enableColumnFilter: false,
      },
      {
        Header: 'Object',
        accessor: 'detected_image_path',
        enableSorting: false,
        enableColumnFilter: false,
        cell: renderImageCell,
      },
      {
        Header: 'Detect Time',
        accessor: 'detect_time',
        enableSorting: false,
        enableColumnFilter: false,
      },
    ],
    [renderImageCell],
  );

  // Convert object to array and chunk into rows of max 4 items
  const renderDynamicTable = useCallback(
    (
      data: Record<string, { label: string; value: string | null | undefined }>,
    ): React.ReactElement => {
      if (!data || typeof data !== 'object') {
        return <div />;
      }
      const entries = Object.entries(data);
      const rows: Array<
        Array<[string, { label: string; value: string | null | undefined }]>
      > = [];

      // Chunk entries into rows
      for (let i = 0; i < entries.length; i += MAX_ITEMS_PER_ROW) {
        rows.push(entries.slice(i, i + MAX_ITEMS_PER_ROW));
      }

      return (
        <div
          className="shipment-table"
          data-theme={theme}
        >
          <table>
            <colgroup>
              {Array.from({ length: COL_COUNT }).map((_, index) => (
                <col
                  key={index}
                  style={{ width: index % 2 === 0 ? '8%' : '17%' }}
                />
              ))}
            </colgroup>
            <tbody>
              {rows.map((row, rowIndex) => {
                const itemsInRow = row.length;
                const remainingCols = TOTAL_COLS - itemsInRow * 2;

                return (
                  <tr key={rowIndex}>
                    {row.flatMap(([key, item], itemIndex) => {
                      const isLastItem = itemIndex === itemsInRow - 1;
                      const tdColSpan =
                        isLastItem && remainingCols > 0 ? 1 + remainingCols : 1;

                      const itemLabel = item?.label || '';
                      const itemValue = item?.value;

                      return [
                        <th key={`${key}-th`}>{t(itemLabel)}</th>,
                        <td
                          key={`${key}-td`}
                          colSpan={tdColSpan}
                        >
                          {itemValue != null && itemValue !== '' ? (
                            itemValue
                          ) : (
                            <BsDash />
                          )}
                        </td>,
                      ];
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      );
    },
    [theme, t],
  );

  const convertItems = useMemo(
    () => [
      {
        key: 1,
        label: t('Basic Information'),
        children: <div ref={refItem1}>{renderDynamicTable(BasicInfoData)}</div>,
      },
      {
        key: 2,
        label: t('Detailed Information'),
        children: (
          <div
            ref={refItem2}
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '1.25rem',
            }}
          >
            <div>{renderDynamicTable(DetailedInfoData?.data || {})}</div>
            {Array.isArray(DetailedInfoData?.video_data) &&
              DetailedInfoData.video_data.length > 0 && (
                <MediaGallery
                  items={DetailedInfoData.video_data.filter(
                    (item) =>
                      item &&
                      typeof item === 'object' &&
                      typeof item.value === 'string' &&
                      item.value.trim() !== '',
                  )}
                  theme={themeValue}
                />
              )}
          </div>
        ),
      },
      {
        key: 3,
        label: t('AI Video Data Analysis'),
        children: (
          <div ref={refItem3}>
            <CustomizableTable
              columns={COLUMNS_AIVideoAnalysis}
              data={{
                data: AIVideoAnalysisData,
              }}
              stickyHeader
              availableHeight={375}
              hasPagination={false}
              notUseGroupColumn
              useSystemSetting
              subTable
              notShowSelectRow
            />
          </div>
        ),
      },
    ],
    [
      t,
      renderDynamicTable,
      BasicInfoData,
      DetailedInfoData,
      themeValue,
      COLUMNS_AIVideoAnalysis,
      AIVideoAnalysisData,
    ],
  );

  const handleDownloadPDF = useCallback(async (): Promise<void> => {
    if (!downloadTemplateRef.current) {
      return;
    }

    try {
      setIsDownloading(true);

      // Ensure all collapses are open
      setActiveKeys([...DEFAULT_ACTIVE_KEYS]);

      // Wait for the collapse animation to complete
      await new Promise((resolve) =>
        setTimeout(resolve, COLLAPSE_ANIMATION_DELAY),
      );

      // Generate filename
      const { videoFileName } = buildVideoUrl(detailDataAnalysis?.video_path);
      const safeId = id !== null && !isNaN(id) ? id : 'unknown';
      const filename = `DataAnalysis_${videoFileName === '-' ? 'report' : videoFileName}_${safeId}.pdf`;

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
      setIsDownloading(false);
    }
  }, [detailDataAnalysis, id, t]);

  const breadcrumbItems = useMemo(
    () => [
      { url: CustomRoutes.dataAnalysis?.path || '/data-analysis' },
      { text: t('Detailed Information') },
    ],
    [t],
  );

  const handleSetActiveKey = useCallback(
    (key: (string | number)[] | null | undefined) => {
      if (!key || !Array.isArray(key)) {
        return;
      }
      setActiveKeys(key.map((k) => (typeof k === 'string' ? Number(k) : k)));
    },
    [],
  );

  const downloadButton = useMemo(
    () => (
      <CustomBtn
        key="download-btn"
        variant="outline"
        color="primary"
        label={t('Download Report')}
        onClick={handleDownloadPDF}
        disabled={isDownloading}
        loading={isDownloading}
      />
    ),
    [t, handleDownloadPDF, isDownloading],
  );

  return (
    <Container>
      <CustomBreadcrumb
        items={breadcrumbItems}
        buttons={[downloadButton]}
      />
      <Main>
        <CustomCollapse
          activeKey={activeKeys}
          setActiveKey={handleSetActiveKey}
          items={convertItems}
          showExpandAll={true}
          colorLight="#FFFFFF"
          colorDark="#1F1F20"
          theme={themeValue}
        />
        {/* Hidden component for PDF download */}
        <div style={{ position: 'absolute', left: '-9999px', top: '-9999px' }}>
          <DownloadTemplateVideoAnalysis
            ref={downloadTemplateRef}
            detailDataAnalysis={detailDataAnalysis || null}
          />
        </div>
      </Main>
    </Container>
  );
};
