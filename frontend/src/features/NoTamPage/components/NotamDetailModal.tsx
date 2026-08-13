import { Spin } from 'antd';
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ActionBtn, CustomBtn, CustomModal } from 'rj-core';

import {
  getNotamDetailKr,
  type NotamData,
  type NotamDetailItem,
} from '@/services/notamService';

import './NotamDetailModal.scss';

interface NotamDetailModalProps {
  show: boolean;
  onHide: () => void;
  notamData: NotamData | null;
  inorout?: string; // 'D' for DOM, 'I' for INT
}

const NotamDetailModal: React.FC<NotamDetailModalProps> = ({
  show,
  onHide,
  notamData,
  inorout = 'D',
}) => {
  const { t } = useTranslation();
  const [detailData, setDetailData] = useState<NotamDetailItem[]>([]);
  const [loading, setLoading] = useState(false);

  // Determine notam_gubun from AIS_TYPE
  const getNotamGubun = (aisType: string): string => {
    // N = NOTAMN = 'NR', C = NOTAMC = 'CR', R = NOTAMR = 'RR'
    const mapping: Record<string, string> = {
      N: 'NR',
      C: 'CR',
      R: 'RR',
    };
    return mapping[aisType] || 'NR';
  };

  // Handle Map View button click
  const handleMapView = () => {
    if (!notamData?.SEQ) return;

    const notamGubun = getNotamGubun(notamData.AIS_TYPE || 'N');

    // Construct map URL with parameters
    // The map page should read these from URL query string via JavaScript
    // Based on network request, the page calls notamDetail3.do with:
    // - notam_seq, notam_gubun, inorout, snowtam_seq
    const mapUrl = new URL('https://aim.koca.go.kr/google/xNotamViewMap.jsp');
    mapUrl.searchParams.set('notam_seq', notamData.SEQ);
    mapUrl.searchParams.set('notam_gubun', notamGubun);
    mapUrl.searchParams.set('inorout', inorout);
    mapUrl.searchParams.set('snowtam_seq', '');

    // Open map page in new tab
    // Note: The page might read URL parameters via JavaScript on load
    // If the page doesn't read URL params, it may need to be configured
    // to read from sessionStorage or make an API call with these values
    window.open(mapUrl.toString(), '_blank');
  };

  // Fetch detail data when modal opens
  useEffect(() => {
    if (show && notamData?.SEQ) {
      setLoading(true);
      getNotamDetailKr(notamData.SEQ)
        .then((response) => {
          setDetailData(response.DATA || []);
        })
        .catch((error) => {
          console.error('Error fetching NOTAM detail:', error);
          setDetailData([]);
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setDetailData([]);
    }
  }, [show, notamData?.SEQ]);

  if (!notamData) return null;

  const notamNo = notamData.NOTAM_NO || '';

  return (
    <CustomModal
      title={`NOTAM NO. ${notamNo}`}
      show={show}
      onHide={onHide}
    >
      <div className="notam-detail-modal">
        {/* Raw NOTAM Text Section */}
        <div className="notam-raw-text">
          <pre className="notam-raw-content">{notamData.FULL_TEXT}</pre>
        </div>

        {/* Parsed Details Table */}
        {loading ? (
          <div
            style={{
              textAlign: 'center',
              padding: '3rem',
            }}
          >
            <Spin size="large" />
            <div
              style={{
                marginTop: '1rem',
                color: '#9c9d9d',
              }}
            >
              {t('Loading...')}
            </div>
          </div>
        ) : (
          <div className="notam-details-table">
            <table className="notam-details-table__table">
              <tbody>
                {detailData
                  .filter(
                    (item) =>
                      !item.ITEM.includes('B-ITEM') &&
                      !item.ITEM.includes('C-ITEM'),
                  )
                  .map((item, index) => (
                    <tr key={index}>
                      <td
                        className="notam-details-table__label"
                        dangerouslySetInnerHTML={{
                          __html: item.ITEM,
                        }}
                      />
                      <td className="notam-details-table__value">
                        {item.MEAN || ' '}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <ActionBtn
        leftButtons={[
          <CustomBtn
            variant="contained"
            color="primary"
            size="lg"
            type="button"
            label={t('Map View')}
            onClick={handleMapView}
          />,
        ]}
        rightButtons={[
          <CustomBtn
            type="button"
            variant="outline"
            color="secondary"
            size="lg"
            onClick={() => {
              onHide();
            }}
            label={'Close'}
          />,
        ]}
      />
    </CustomModal>
  );
};

export default NotamDetailModal;
