import React, { forwardRef, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import i18n from '../../../i18n';
import { useDateTimeFormat } from '../../Handover/hooks/useDateFormat';
import { formatDateTime } from '../../Handover/utils/dateFormat';
import { DataAnalysisState } from '../types';
import MediaGallery from './MediaGallery';

interface DownloadTemplateVideoAnalysisProps {
  detailDataAnalysis: DataAnalysisState | null;
  analysisType?: 'image' | 'video';
}

export const DownloadTemplateVideoAnalysis = forwardRef<
  HTMLDivElement,
  DownloadTemplateVideoAnalysisProps
>(({ detailDataAnalysis, analysisType }, ref) => {
  const { t } = useTranslation();
  const { dateFormat, timeFormat, timezoneCode } = useDateTimeFormat();

  const reportNumber = useMemo(() => {
    if (!detailDataAnalysis?.id) return '2025-1114-0001';
    const date = new Date();
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const monthDay = `${month}${day}`; // MMDD format
    const id = String(detailDataAnalysis.id).padStart(4, '0');
    return `${year}-${monthDay}-${id}`;
  }, [detailDataAnalysis?.id]);

  // Section 01: Basic Information
  const basicInfoData = useMemo(
    () => ({
      purpose: detailDataAnalysis?.purpose || '-',
      date: detailDataAnalysis?.start_time
        ? formatDateTime(
            detailDataAnalysis?.start_time,
            dateFormat,
            timeFormat,
            i18n.language,
            timezoneCode,
          )
        : '-',
      location: detailDataAnalysis?.mission_location || '-', // Not available in DataAnalysisState
      personInCharge: detailDataAnalysis?.operator_name || '-',
    }),
    [detailDataAnalysis, dateFormat, timeFormat, timezoneCode],
  );

  // Section 02: Detailed Information
  const detailedInfoData = useMemo(() => {
    const rawVideoPath = detailDataAnalysis?.video_path;
    const videoUrl = rawVideoPath
      ? rawVideoPath.startsWith('http://') ||
        rawVideoPath.startsWith('https://') ||
        rawVideoPath.startsWith('/')
        ? rawVideoPath
        : `https://${rawVideoPath}`
      : null;
    const isValidVideoUrl =
      videoUrl && videoUrl !== '-' && videoUrl.trim() !== '';

    return {
      aircraft: detailDataAnalysis?.drone_name || '-',
      operator: detailDataAnalysis?.operator_name || '-',
      registrationNumber: detailDataAnalysis?.register_number || '-',
      manufacturer: detailDataAnalysis?.manufacturer || '-',
      flightDistance: detailDataAnalysis?.flight_distance || '-',
      flightTime: detailDataAnalysis?.flight_time || '-',
      flightAltitude: detailDataAnalysis?.capture_altitude || '-',
      flightType: detailDataAnalysis?.purpose || '-',
      takeoffLocation: `${detailDataAnalysis?.start_point_x || '-'}, ${
        detailDataAnalysis?.start_point_y || '-'
      }`,
      landingLocation: `${detailDataAnalysis?.end_point_x || '-'}, ${
        detailDataAnalysis?.end_point_y || '-'
      }`,
      takeoffTime: detailDataAnalysis?.start_time
        ? formatDateTime(
            detailDataAnalysis?.start_time,
            dateFormat,
            timeFormat,
            i18n.language,
            timezoneCode,
          )
        : '-',
      landingTime: detailDataAnalysis?.end_time
        ? formatDateTime(
            detailDataAnalysis?.end_time,
            dateFormat,
            timeFormat,
            i18n.language,
            timezoneCode,
          )
        : '-',
      remarks: detailDataAnalysis?.remark || '-',
      videoUrl: isValidVideoUrl ? videoUrl : null,
      detectedImages:
        detailDataAnalysis?.analysis
          ?.slice(0, 2)
          .map((item) => item.detected_image_path)
          .filter((path) => path && path.trim() !== '') || [],
    };
  }, [detailDataAnalysis, dateFormat, timeFormat, timezoneCode]);

  // Format seconds to video timestamp (e.g., 65.5 -> "1:05", 0.5 -> "0:00")
  const formatVideoTimestamp = useCallback(
    (seconds: number | null | undefined): string => {
      if (seconds === null || seconds === undefined) return '-';
      const totalSeconds = Math.floor(seconds);
      const minutes = Math.floor(totalSeconds / 60);
      const secs = totalSeconds % 60;
      return `${minutes}:${secs.toString().padStart(2, '0')}`;
    },
    [],
  );

  // Render timestamp cell - shows video time for videos, '-' for images
  const renderTimestampCell = (timestamp) => {
    console.log('timestamp', timestamp);
    // For images or missing timestamp, show '-'
    if (
      analysisType === 'image' ||
      timestamp === null ||
      timestamp === undefined
    ) {
      return '-';
    }
    return formatVideoTimestamp(timestamp);
  };

  console.log('detailDataAnalysis', analysisType, detailDataAnalysis);
  // Section 03: AI Video Data Analysis
  const aiAnalysisData = useMemo(() => {
    const mappedData =
      detailDataAnalysis?.analysis?.map((item) => {
        const baseItem = {
          object: item.detections[0]?.label || '-',
          objectCount: item.detection_count || '-',
          objectLocation: '-', // Not available in analysis data
          detectedImagePath: item.detected_image_path || null,
        };

        if (analysisType) {
          return {
            ...baseItem,
            timestamp: renderTimestampCell(item.timestamp) || null,
          };
        }

        return baseItem;
      }) || [];
    console.log('mappedData', mappedData);
    // Only sort by timestamp if analysisType is 'video'
    if (analysisType === 'video') {
      return mappedData.sort((a, b) => (a.timestamp ?? 0) - (b.timestamp ?? 0));
    }

    return mappedData;
  }, [detailDataAnalysis, analysisType]);

  return (
    <>
      <style>{`
        @media print {
          @page {
            size: A4;
            margin: 0;
          }
          * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
            color-adjust: exact !important;
          }
          table {
            page-break-inside: avoid !important;
            break-inside: avoid !important;
          }
          tr {
            page-break-inside: avoid !important;
            break-inside: avoid !important;
          }
          thead {
            display: table-header-group;
          }
          tfoot {
            display: table-footer-group;
          }
        }
      `}</style>
      <div
        ref={ref}
        style={{
          width: '210mm',
          minHeight: '297mm',
          padding: '20mm',
          backgroundColor: '#ffffff',
          fontFamily: 'Arial, sans-serif',
          fontSize: '16px',
          lineHeight: '1.6',
          color: '#000000',
          pageBreakInside: 'avoid',
          breakInside: 'avoid',
        }}
      >
        {/* Report Number Header */}
        <div
          style={{
            textAlign: 'right',
            marginBottom: '5px',
            fontSize: '14px',
          }}
        >
          No. {reportNumber}
        </div>

        {/* Title */}
        <h1
          style={{
            textAlign: 'center',
            fontSize: '26px',
            fontWeight: 'bold',
            marginBottom: '20px',
            padding: '5px',
            border: '2px solid #000',
            backgroundColor: '#dae9f8',
          }}
        >
          {t('DataAnalysis.ReportTitle')}
        </h1>

        {/* Section 01: Basic Information */}
        <div
          style={{
            marginBottom: '15px',
            pageBreakInside: 'avoid',
            breakInside: 'avoid',
          }}
        >
          <h2
            style={{
              fontSize: '16px',
              fontWeight: 'bold',
              textAlign: 'center',
              borderTop: '2px solid #000',
              borderLeft: '2px solid #000',
              borderRight: '2px solid #000',
              padding: '5px',
              width: '200px',
              backgroundColor: '#a6c8eb',
            }}
          >
            {t('DataAnalysis.Section01Title')}
          </h2>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              border: '2px solid #000',
              marginBottom: '15px',
              pageBreakInside: 'avoid',
              breakInside: 'avoid',
            }}
          >
            <tbody>
              <tr
                style={{
                  pageBreakInside: 'avoid',
                  breakInside: 'avoid',
                }}
              >
                <th
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                    width: '15%',
                  }}
                >
                  {t('DataAnalysis.MissionPurpose')}
                </th>
                <td
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    width: '35%',
                    textAlign: 'center',
                  }}
                >
                  {basicInfoData.purpose}
                </td>
                <th
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                    width: '15%',
                  }}
                >
                  {t('DataAnalysis.PersonInCharge')}
                </th>
                <td
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    width: '35%',
                    textAlign: 'center',
                  }}
                >
                  {basicInfoData.personInCharge}
                </td>
              </tr>
              <tr
                style={{
                  pageBreakInside: 'avoid',
                  breakInside: 'avoid',
                }}
              >
                <th
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {t('DataAnalysis.MissionDateTime')}
                </th>
                <td
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {basicInfoData.date}
                </td>
                <th
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {t('DataAnalysis.MissionLocation')}
                </th>
                <td
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {basicInfoData.location}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Section 02: Detailed Information */}
        <div
          style={{
            marginBottom: '15px',
            pageBreakInside: 'avoid',
            breakInside: 'avoid',
          }}
        >
          <h2
            style={{
              fontSize: '16px',
              fontWeight: 'bold',
              textAlign: 'center',
              borderTop: '2px solid #000',
              borderLeft: '2px solid #000',
              borderRight: '2px solid #000',
              padding: '5px',
              width: '200px',
              backgroundColor: '#a6c8eb',
            }}
          >
            {t('DataAnalysis.Section02Title')}
          </h2>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              border: '2px solid #000',
              pageBreakInside: 'avoid',
              breakInside: 'avoid',
            }}
          >
            <tbody>
              <tr
                style={{
                  pageBreakInside: 'avoid',
                  breakInside: 'avoid',
                }}
              >
                <th
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                    width: '15%',
                  }}
                >
                  {t('DataAnalysis.Aircraft')}
                </th>
                <td
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    width: '35%',
                    textAlign: 'center',
                  }}
                >
                  {detailedInfoData.aircraft}
                </td>
                <th
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                    width: '15%',
                  }}
                >
                  {t('DataAnalysis.Operator')}
                </th>
                <td
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    width: '35%',
                    textAlign: 'center',
                  }}
                >
                  {detailedInfoData.operator}
                </td>
              </tr>
              <tr
                style={{
                  pageBreakInside: 'avoid',
                  breakInside: 'avoid',
                }}
              >
                <th
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {t('DataAnalysis.RegistrationNumber')}
                </th>
                <td
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {detailedInfoData.registrationNumber}
                </td>
                <th
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {t('DataAnalysis.Manufacturer')}
                </th>
                <td
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {detailedInfoData.manufacturer}
                </td>
              </tr>
              <tr
                style={{
                  pageBreakInside: 'avoid',
                  breakInside: 'avoid',
                }}
              >
                <th
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {t('DataAnalysis.FlightDistance')}
                </th>
                <td
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {detailedInfoData.flightDistance}
                </td>
                <th
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {t('DataAnalysis.FlightTime')}
                </th>
                <td
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {detailedInfoData.flightTime}
                </td>
              </tr>
              <tr
                style={{
                  pageBreakInside: 'avoid',
                  breakInside: 'avoid',
                }}
              >
                <th
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {t('DataAnalysis.FlightAltitude')}
                </th>
                <td
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {detailedInfoData.flightAltitude}
                </td>
                <th
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {t('DataAnalysis.FlightType')}
                </th>
                <td
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {detailedInfoData.flightType}
                </td>
              </tr>
              <tr
                style={{
                  pageBreakInside: 'avoid',
                  breakInside: 'avoid',
                }}
              >
                <th
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {t('DataAnalysis.TakeoffLocation')}
                </th>
                <td
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {detailedInfoData.takeoffLocation}
                </td>
                <th
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {t('DataAnalysis.LandingLocation')}
                </th>
                <td
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {detailedInfoData.landingLocation}
                </td>
              </tr>
              <tr
                style={{
                  pageBreakInside: 'avoid',
                  breakInside: 'avoid',
                }}
              >
                <th
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {t('DataAnalysis.TakeoffTime')}
                </th>
                <td
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {detailedInfoData.takeoffTime}
                </td>
                <th
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {t('DataAnalysis.LandingTime')}
                </th>
                <td
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {detailedInfoData.landingTime}
                </td>
              </tr>
              <tr
                style={{
                  pageBreakInside: 'avoid',
                  breakInside: 'avoid',
                }}
              >
                <th
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {t('DataAnalysis.Remarks')}
                </th>
                <td
                  colSpan={3}
                  style={{
                    border: '1px solid #000',
                    padding: '8px',
                    textAlign: 'center',
                  }}
                >
                  {detailedInfoData.remarks}
                </td>
              </tr>
            </tbody>
          </table>
          {/* Image Section - Two boxes side by side */}
          <div
            style={{
              display: 'flex',
              marginBottom: '10px',
              pageBreakInside: 'avoid',
              breakInside: 'avoid',
            }}
          >
            {/* First Image Box */}
            <div
              style={{
                flex: '1',
                border: '2px solid #000',
                minHeight: '250px',
                padding: '10px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: '#fafafa',
              }}
            >
              {detailedInfoData.detectedImages.length > 0 &&
              detailedInfoData.detectedImages[0] ? (
                <div
                  style={{
                    width: '100%',
                    maxWidth: '500px',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                  }}
                >
                  <div
                    className="image-container-fixed"
                    style={{
                      width: '100%',
                      aspectRatio: '16/9',
                      maxWidth: '500px',
                      position: 'relative',
                    }}
                  >
                    <MediaGallery
                      items={[
                        {
                          label: 'Detected Image',
                          value: detailedInfoData.detectedImages[0],
                          type: 'image',
                        },
                      ]}
                      theme="light"
                    />
                    <style>{`
                    .image-container-fixed .media-gallery .media-thumbnail {
                      width: 100% !important;
                      height: 100% !important;
                    }
                    .image-container-fixed .media-gallery .media-thumbnail img {
                      object-fit: contain !important;
                    }
                  `}</style>
                  </div>
                </div>
              ) : (
                <div
                  style={{
                    fontWeight: 'bold',
                    marginBottom: '10px',
                    color: '#666',
                  }}
                >
                  {t('DataAnalysis.AttachImage')}
                </div>
              )}
            </div>

            {/* Second Image Box */}
            <div
              style={{
                flex: '1',
                border: '2px solid #000',
                minHeight: '250px',
                padding: '10px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: '#fafafa',
              }}
            >
              {detailedInfoData.detectedImages.length > 1 &&
              detailedInfoData.detectedImages[1] ? (
                <div
                  style={{
                    width: '100%',
                    maxWidth: '500px',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                  }}
                >
                  <div
                    className="image-container-fixed"
                    style={{
                      width: '100%',
                      aspectRatio: '16/9',
                      maxWidth: '500px',
                      position: 'relative',
                    }}
                  >
                    <MediaGallery
                      items={[
                        {
                          label: 'Detected Image',
                          value: detailedInfoData.detectedImages[1],
                          type: 'image',
                        },
                      ]}
                      theme="light"
                    />
                    <style>{`
                    .image-container-fixed .media-gallery .media-thumbnail {
                      width: 100% !important;
                      height: 100% !important;
                    }
                    .image-container-fixed .media-gallery .media-thumbnail img {
                      object-fit: contain !important;
                    }
                  `}</style>
                  </div>
                </div>
              ) : (
                <div
                  style={{
                    fontWeight: 'bold',
                    marginBottom: '10px',
                    color: '#666',
                  }}
                >
                  {t('DataAnalysis.AttachImage')}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Section 03: AI Video Data Analysis */}
        <div
          style={{
            marginBottom: '15px',
            pageBreakInside: 'avoid',
            breakInside: 'avoid',
          }}
        >
          <h2
            style={{
              fontSize: '16px',
              fontWeight: 'bold',
              textAlign: 'center',
              borderTop: '2px solid #000',
              borderLeft: '2px solid #000',
              borderRight: '2px solid #000',
              padding: '5px',
              width: '200px',
              backgroundColor: '#a6c8eb',
            }}
          >
            {t('DataAnalysis.Section03Title')}
          </h2>
          {aiAnalysisData.length > 0 ? (
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                border: '2px solid #000',
                pageBreakInside: 'avoid',
                breakInside: 'avoid',
              }}
            >
              <tbody>
                {aiAnalysisData.map((item, index) => (
                  <React.Fragment key={index}>
                    <tr
                      style={{
                        pageBreakInside: 'avoid',
                        breakInside: 'avoid',
                      }}
                    >
                      <th
                        style={{
                          border: '1px solid #000',
                          padding: '8px',
                          textAlign: 'center',
                          width: '15%',
                        }}
                      >
                        {t('DataAnalysis.Object')}
                      </th>
                      <td
                        style={{
                          border: '1px solid #000',
                          padding: '8px',
                          width: '35%',
                          textAlign: 'center',
                        }}
                      >
                        {item.object}
                      </td>
                      <th
                        style={{
                          border: '1px solid #000',
                          padding: '8px',
                          textAlign: 'center',
                          width: '15%',
                        }}
                      >
                        {t('DataAnalysis.NumberOfObjects')}
                      </th>
                      <td
                        style={{
                          border: '1px solid #000',
                          padding: '8px',
                          width: '35%',
                          textAlign: 'center',
                        }}
                      >
                        {item.objectCount}
                      </td>
                    </tr>
                    <tr
                      style={{
                        pageBreakInside: 'avoid',
                        breakInside: 'avoid',
                      }}
                    >
                      <th
                        style={{
                          border: '1px solid #000',
                          padding: '8px',
                          textAlign: 'center',
                          width: '15%',
                        }}
                      >
                        {t('DataAnalysis.ObjectLocation')}
                      </th>
                      <td
                        colSpan={3}
                        style={{
                          border: '1px solid #000',
                          padding: '8px',
                          textAlign: 'center',
                        }}
                      >
                        {item.detectedImagePath ? (
                          <div
                            style={{
                              display: 'flex',
                              justifyContent: 'center',
                            }}
                          >
                            <div
                              className="image-container-table-large"
                              style={{ maxWidth: '200px', width: '100%' }}
                            >
                              <MediaGallery
                                items={[
                                  {
                                    label: item.object,
                                    value: item.detectedImagePath,
                                    type: 'image',
                                  },
                                ]}
                                theme="light"
                              />
                              <style>{`
                              .image-container-table-large .media-gallery .media-thumbnail {
                                width: 100% !important;
                                height: auto !important;
                                min-height: 100px !important;
                                aspect-ratio: 16/9 !important;
                              }
                              .image-container-table-large .media-gallery .media-thumbnail img {
                                object-fit: contain !important;
                              }
                            `}</style>
                            </div>
                          </div>
                        ) : (
                          item.objectLocation
                        )}
                      </td>
                    </tr>
                    {analysisType === 'video' && 'timestamp' in item && (
                      <tr>
                        <th
                          style={{
                            border: '1px solid #000',
                            padding: '8px',
                            textAlign: 'center',
                            width: '15%',
                          }}
                        >
                          {t('DataAnalysis.Detect Time')}
                        </th>
                        <td
                          colSpan={4}
                          style={{
                            border: '1px solid #000',
                            padding: '8px',
                            textAlign: 'center',
                          }}
                        >
                          {item.timestamp}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          ) : (
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                border: '2px solid #000',
                pageBreakInside: 'avoid',
                breakInside: 'avoid',
              }}
            >
              <tbody>
                <tr
                  style={{
                    pageBreakInside: 'avoid',
                    breakInside: 'avoid',
                  }}
                >
                  <th
                    style={{
                      border: '1px solid #000',
                      padding: '8px',
                      textAlign: 'center',
                    }}
                  >
                    {t('DataAnalysis.Object')}
                  </th>
                  <td
                    style={{
                      border: '1px solid #000',
                      padding: '8px',
                      textAlign: 'center',
                    }}
                  ></td>
                  <th
                    style={{
                      border: '1px solid #000',
                      padding: '8px',
                      textAlign: 'center',
                    }}
                  >
                    {t('DataAnalysis.NumberOfObjects')}
                  </th>
                  <td
                    style={{
                      border: '1px solid #000',
                      padding: '8px',
                      textAlign: 'center',
                    }}
                  ></td>
                </tr>
                <tr
                  style={{
                    pageBreakInside: 'avoid',
                    breakInside: 'avoid',
                  }}
                >
                  <th
                    style={{
                      border: '1px solid #000',
                      padding: '8px',
                      textAlign: 'center',
                    }}
                  >
                    {t('DataAnalysis.ObjectLocation')}
                  </th>
                  <td
                    colSpan={3}
                    style={{
                      border: '1px solid #000',
                      padding: '8px',
                      textAlign: 'center',
                    }}
                  ></td>
                </tr>
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
});

DownloadTemplateVideoAnalysis.displayName = 'DownloadTemplateVideoAnalysis';
