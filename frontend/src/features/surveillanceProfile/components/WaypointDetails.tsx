import { DownOutlined } from '@ant-design/icons';
import { Collapse, ConfigProvider } from 'antd';
import { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AiOutlineClose } from 'react-icons/ai';
import { useTheme } from 'rj-core';

export interface WaypointDetailsProps {
  command?: string;
  frame?: string;
  param_1?: string;
  param_2?: string;
  param_3?: string;
  param_4?: string;
  latitude?: string;
  longitude?: string;
  altitude?: string;
}

export const WaypointDetails = ({
  waypointDetails,
  setWaypointDetails,
}: {
  waypointDetails?: WaypointDetailsProps | null;
  setWaypointDetails?: (
    waypointDetails: WaypointDetailsProps | null,
  ) => void | null;
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [isExpanded, setIsExpanded] = useState(true);

  const handleToggleExpand = useCallback(() => {
    setIsExpanded(!isExpanded);
  }, [isExpanded]);

  const content = useMemo(() => {
    const details = [
      { label: t('Command'), value: waypointDetails?.command || '-' },
      { label: t('Frame'), value: waypointDetails?.frame || '-' },
      { label: t('Param 1'), value: waypointDetails?.param_1 || '-' },
      { label: t('Param 2'), value: waypointDetails?.param_2 || '-' },
      { label: t('Param 3'), value: waypointDetails?.param_3 || '-' },
      { label: t('Param 4'), value: waypointDetails?.param_4 || '-' },
      { label: t('Latitude'), value: waypointDetails?.latitude || '-' },
      { label: t('Longitude'), value: waypointDetails?.longitude || '-' },
      { label: t('Altitude'), value: waypointDetails?.altitude || '-' },
    ];

    return details.map((detail, index) => (
      <div
        key={index}
        className="d-flex align-items-center"
        style={{
          borderBottom:
            index === details.length - 1 ? 'none' : '1px solid #DDDFE2',
        }}
      >
        <p
          className={` ${index === details.length - 1 ? 'mt-2 mb-0' : index === 0 ? 'mb-2 mt-0' : 'mb-2 mt-2'}`}
        >
          {detail.label}
        </p>
        <p
          className={` ${index === details.length - 1 ? 'mt-2 mb-0' : index === 0 ? 'mb-2 mt-0' : 'mb-2 mt-2'} ms-auto`}
        >
          {detail.value}
        </p>
      </div>
    ));
  }, [waypointDetails, t]);

  const items = useMemo(() => {
    return [
      {
        key: '1',
        label: t('SurveyMission.Waypoint Details'),
        children: content,
        styles: {
          header: {
            fontWeight: '600',
            padding: '0.75rem',
            alignItems: 'center',
          },
          body: {
            padding: '0.75rem ',
          },
        },
        extra: (
          <div className="d-flex gap-3 align-items-center">
            <DownOutlined
              style={{
                transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                transition: 'transform 0.3s ease',
              }}
            />
            <AiOutlineClose
              onClick={(e) => {
                e.stopPropagation();
                setWaypointDetails?.(null);
              }}
              style={{
                cursor: 'pointer',
                fontSize: '14px',
                opacity: 0.7,
                transition: 'opacity 0.2s ease',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.opacity = '1')}
              onMouseLeave={(e) => (e.currentTarget.style.opacity = '0.7')}
            />
          </div>
        ),
        showArrow: false,
      },
    ];
  }, [content, setWaypointDetails, t, isExpanded]);

  return (
    <>
      {waypointDetails && (
        <ConfigProvider
          theme={{
            components: {
              Collapse: {
                headerBg: theme === 'dark' ? '#2D2E30' : '#ECECEF',
              },
            },
            token: {
              colorText: theme === 'dark' ? '#ECECEF' : '#2D2E30',
            },
          }}
        >
          <Collapse
            style={{
              width: '24rem',
              padding: 'unset',
              maxWidth: '90vw',
              position: 'absolute',
              bottom: 8,
              right: 8,
              opacity: 0.9,
              boxShadow:
                theme === 'dark'
                  ? '0 4px 12px rgba(0, 0, 0, 0.8)'
                  : '0 4px 12px rgba(0, 0, 0, 0.15)',
              borderRadius: '8px',
              zIndex: 500,
            }}
            bordered={false}
            accordion
            onChange={handleToggleExpand}
            activeKey={isExpanded ? ['1'] : []}
            items={items}
          />
        </ConfigProvider>
      )}
    </>
  );
};
