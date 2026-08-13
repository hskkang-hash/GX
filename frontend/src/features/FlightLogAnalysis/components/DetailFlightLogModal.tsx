import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { CenterBtn, CustomModal, useTheme } from 'rj-core';

import { Tabs } from '../../../components/Form/Tabs';
import { FlightLogAnalysisState } from '../types/flightLogAnalysis.types';
import { convertDataChart } from '../utils/convertDataChart';
import { CustomChartLogAnalysis } from './CustomChartLogAnalysis';
import CustomCollapse from './CustomCollapse';
import { InformationFlightLogDetail } from './InformationFlightLogDetail';

const DetailFlightLogModal = ({
  show,
  onHide,
  detailData,
  detailInfo,
}: {
  show: boolean;
  onHide: () => void;
  detailData: FlightLogAnalysisState | null;
  detailInfo: FlightLogAnalysisState | null;
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const { i18n } = useTranslation();

  const convertedData = useMemo(
    () => (detailData ? convertDataChart(detailData, i18n.language) : []),
    [detailData, i18n.language],
  );

  const convertItems = useMemo(
    () =>
      convertedData.map((item, index) => ({
        key: index + 1,
        label: t(item.label),
        children: (
          <div
            style={{
              width: '78rem',
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              gap: '1.25rem',
            }}
          >
            {item.data.map((data, index) => (
              <CustomChartLogAnalysis
                key={`${index + 1}-${item.label}`}
                data={data}
              />
            ))}
          </div>
        ),
      })),
    [convertedData, t],
  );

  const tabs = useMemo(() => {
    return [
      {
        label: t('Log Chart'),
        content: (
          <CustomCollapse
            defaultActiveKey={[1]}
            items={convertItems}
            theme={theme === 'dark' ? 'dark' : 'light'}
          />
        ),
      },
      {
        label: t('Information'),
        content: <InformationFlightLogDetail detailInfo={detailInfo} />,
      },
    ];
  }, [t, convertItems, theme, detailInfo]);

  return (
    <CustomModal
      show={show}
      onHide={onHide}
      title={t('Log Analysis')}
    >
      <div
        className="mb-4"
        style={{ height: '50rem', width: '80rem', overflowY: 'auto' }}
      >
        <Tabs items={tabs} />
        {/* <CustomCollapse
          defaultActiveKey={[1]}
          items={convertItems}
          theme={theme === 'dark' ? 'dark' : 'light'}
        /> */}
      </div>

      <CenterBtn
        label={t('Close')}
        onClick={onHide}
        variant="outline"
        color="secondary"
        size="lg"
        type="button"
        className="mb-3"
      />
    </CustomModal>
  );
};

export default React.memo(DetailFlightLogModal);
