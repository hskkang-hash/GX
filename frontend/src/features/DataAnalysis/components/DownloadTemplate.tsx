import React, { forwardRef, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { BsDash } from 'react-icons/bs';

import CustomCollapse from '../../FlightLogAnalysis/components/CustomCollapse';
import { DataAnalysisState } from '../types';
import { CustomTableAnalysis } from './CustomTableAnalysis';
import MediaGallery from './MediaGallery';

interface DownloadTemplateProps {
  activeKeys: number[];
  setActiveKeys: (key: number[]) => void;
  detailDataAnalysis: DataAnalysisState | null;
}

export const DownloadTemplate = forwardRef<
  HTMLDivElement,
  DownloadTemplateProps
>(({ activeKeys, setActiveKeys, detailDataAnalysis }, ref) => {
  const { t } = useTranslation();

  const BasicInfoData = useMemo(
    () => ({
      name: {
        label: 'Name',
        value:
          detailDataAnalysis?.profile_name ||
          detailDataAnalysis?.stream_monitor__external_drone_name ||
          '-',
      },
      purpose: {
        label: 'Purpose',
        value: 'Surveillance',
      },
      profile_date: {
        label: 'Profile Date',
        value: detailDataAnalysis?.profile_device__created_on || '-',
      },
    }),
    [detailDataAnalysis],
  );

  const DetailedInfoData = useMemo(() => {
    const rawVideoPath = detailDataAnalysis?.video_path;
    // Build video URL - add https:// if not already present
    const videoUrl = rawVideoPath
      ? rawVideoPath.startsWith('http://') ||
        rawVideoPath.startsWith('https://') ||
        rawVideoPath.startsWith('/')
        ? rawVideoPath
        : `https://${rawVideoPath}`
      : null;
    const isValidVideoUrl =
      videoUrl && videoUrl !== '-' && videoUrl.trim() !== '';
    const videoFileName = isValidVideoUrl
      ? videoUrl.split('/').pop() || 'Video'
      : '-';

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
          value: detailDataAnalysis?.flight_altitude || '-',
        },
        start_point: {
          label: 'Start Point',
          value: `${detailDataAnalysis?.start_point_x}, ${detailDataAnalysis?.start_point_y}`,
        },
        end_point: {
          label: 'End Point',
          value: `${detailDataAnalysis?.end_point_x}, ${detailDataAnalysis?.end_point_y}`,
        },
        start_time: {
          label: 'Start Time',
          value: detailDataAnalysis?.start_time || '-',
        },
        end_time: {
          label: 'End Time',
          value: detailDataAnalysis?.end_time || '-',
        },
        remarks: {
          label: 'Remarks',
          value: detailDataAnalysis?.remark || '-',
        },
      },
      video_data: isValidVideoUrl
        ? [
            {
              label: videoFileName,
              value: videoUrl,
            },
          ]
        : [],
    };
  }, [detailDataAnalysis]);

  const AIVideoAnalysisData = useMemo(() => {
    return (
      detailDataAnalysis?.analysis?.map((item) => ({
        object: item.detections[0].label,
        object_count: item.detection_count,
        detected_image_path: item.detected_image_path,
        detect_time: item.datetime,
      })) || []
    );
  }, [detailDataAnalysis]);

  const COLUMNS_AIVideoAnalysis = [
    {
      title: 'Model',
      dataIndex: 'object',
      key: 'object',
    },
    {
      title: 'Object Count',
      dataIndex: 'object_count',
      key: 'object_count',
    },
    {
      title: 'Object',
      dataIndex: 'detected_image_path',
      key: 'detected_image_path',
      render: (text: string) => {
        return (
          <MediaGallery
            items={[{ label: text, value: text, type: 'image' }]}
            theme="light"
          />
        );
      },
    },
    {
      title: 'Detect Time',
      dataIndex: 'detect_time',
      key: 'detect_time',
    },
  ];

  // Convert object to array and chunk into rows of max 4 items
  const renderDynamicTable = (
    data: Record<string, { label: string; value: string | null | undefined }>,
  ): React.ReactElement => {
    const entries = Object.entries(data);
    const maxItemsPerRow = 4;
    const rows: Array<
      Array<[string, { label: string; value: string | null | undefined }]>
    > = [];

    // Chunk entries into rows
    for (let i = 0; i < entries.length; i += maxItemsPerRow) {
      rows.push(entries.slice(i, i + maxItemsPerRow));
    }

    return (
      <div
        className="shipment-table"
        data-theme={'light'}
      >
        <table>
          <colgroup>
            {Array.from({ length: 8 }).map((_, index) => (
              <col
                key={index}
                style={{ width: index % 2 === 0 ? '12.5%' : '12.5%' }}
              />
            ))}
          </colgroup>
          <tbody>
            {rows.map((row, rowIndex) => {
              const totalCols = 8; // 4 pairs of th+td = 8 columns
              const itemsInRow = row.length;
              const remainingCols = totalCols - itemsInRow * 2;

              return (
                <tr key={rowIndex}>
                  {row.flatMap(([key, item], itemIndex) => {
                    const isLastItem = itemIndex === itemsInRow - 1;
                    const tdColSpan =
                      isLastItem && remainingCols > 0 ? 1 + remainingCols : 1;

                    return [
                      <th
                        key={`${key}-th`}
                        style={{
                          textAlign: 'left',
                          whiteSpace: 'normal',
                          wordBreak: 'normal',
                          overflowWrap: 'normal',
                        }}
                      >
                        {t(item.label)}
                      </th>,
                      <td
                        key={`${key}-td`}
                        colSpan={tdColSpan}
                      >
                        {item.value || <BsDash />}
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
  };

  const convertItems = [
    {
      key: 1,
      label: t('Basic Information'),
      children: <div>{renderDynamicTable(BasicInfoData)}</div>,
    },
    {
      key: 2,
      label: t('Detailed Information'),
      children: (
        <div
          style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}
        >
          <div>{renderDynamicTable(DetailedInfoData.data)}</div>
          {DetailedInfoData.video_data.length > 0 && (
            <MediaGallery items={DetailedInfoData.video_data} />
          )}
        </div>
      ),
    },
    {
      key: 3,
      label: t('AI Video Data Analysis'),
      children: (
        <div>
          <CustomTableAnalysis
            columns={COLUMNS_AIVideoAnalysis}
            data={AIVideoAnalysisData}
          />
        </div>
      ),
    },
  ];

  return (
    <div ref={ref}>
      <CustomCollapse
        activeKey={activeKeys}
        setActiveKey={(key) => {
          setActiveKeys(
            key.map((k) => (typeof k === 'string' ? Number(k) : k)),
          );
        }}
        items={convertItems}
        showExpandAll={true}
        colorLight="#FFFFFF"
        colorDark="#1F1F20"
        theme="light"
      />
    </div>
  );
});

DownloadTemplate.displayName = 'DownloadTemplate';
