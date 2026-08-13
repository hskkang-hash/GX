import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  Container,
  CustomBreadcrumb,
  CustomBtn,
  FormBlock,
  Main,
  ToastTopHelper,
  useLoadingContext,
  useTheme,
} from 'rj-core';

import Colors from '../../../../../configs/Colors';
import { CustomRoutes } from '../../../../../services/API';
import { useSurveillanceProfile } from '../../../hooks/useSurveillanceProfile';
import { useDrawingModeStore } from '../../../stores/drawingModeStore';
import { DroneAssignment, SurveillanceProfileState } from '../../../types';
import { LeftProfileDetail } from './LeftProfileDetail';
import { RightProfileDetail } from './RightProfileDetail';

export const ProfileDetailPage = () => {
  const { t } = useTranslation();
  const { id } = useParams();
  const navigate = useNavigate();
  const [theme] = useTheme();
  const [searchParams] = useSearchParams();
  const [loadingDownloadReport, setLoadingDownloadReport] =
    useState<boolean>(false);
  const activeTabFromSearchParams = searchParams.get('tab') || null;

  const { showLoading, hideLoading } = useLoadingContext();

  const {
    detailSurveillanceProfile,
    fetchDetailSurveillanceProfile,
    markerData,
    downloadReportProfile,
  } = useSurveillanceProfile();

  const clearAll = useDrawingModeStore((state) => state.clearAll);

  useEffect(() => {
    return () => {
      clearAll();
    };
  }, [clearAll]);

  useEffect(() => {
    if (detailSurveillanceProfile) {
      showLoading();
    } else {
      hideLoading();
    }
  }, []);

  useEffect(() => {
    if (Number(id)) {
      fetchDetailSurveillanceProfile(Number(id));
    }
  }, [id]);

  const droneRoutes = useMemo(() => {
    if (
      !detailSurveillanceProfile?.drone_assignments ||
      detailSurveillanceProfile?.drone_assignments.length === 0
    ) {
      return [];
    }
    return detailSurveillanceProfile?.drone_assignments.map((assignment) => ({
      route_path:
        assignment.route_path?.map((item) => ({
          lat: item.latitude,
          lng: item.longitude,
          name: item.name,
          altitude: item.altitude ?? 0,
          command: Object.keys(item?.command_name)?.[0] ?? 'WAYPOINT',
          frame: item.frame_name ?? 'FRAME',
          param_1: Object.values(item?.params)?.[0]?.[0] ?? 0,
          param_2: Object.values(item?.params)?.[0]?.[1] ?? 0,
          param_3: Object.values(item?.params)?.[0]?.[2] ?? 0,
          param_4: Object.values(item?.params)?.[0]?.[3] ?? 0,
        })) || [],
      device: {
        id: assignment.device__id,
        name: '',
        color: assignment.color,
      },
    }));
  }, [detailSurveillanceProfile?.drone_assignments]);

  console.log(
    'droneRoutes34234344567_profiledetailpage',
    detailSurveillanceProfile,
  );

  const handleDownloadReport = async () => {
    setLoadingDownloadReport(true);
    const result = await downloadReportProfile({ profile_id: Number(id) });
    if (result.success) {
      ToastTopHelper.success(
        result.message || t('Download request queued successfully'),
      );
    } else {
      ToastTopHelper.error(result.message || t('Failed to initiate download'));
    }
    setLoadingDownloadReport(false);
  };

  return (
    <>
      <Container>
        <CustomBreadcrumb
          items={[
            {
              url:
                CustomRoutes.surveyProfile.path +
                '?tab=' +
                activeTabFromSearchParams,
            },
            { text: t('Detailed Information') },
          ]}
          buttons={[
            ...(detailSurveillanceProfile?.cancel_reason ||
            detailSurveillanceProfile?.rejection_reason
              ? [
                  <CustomBtn
                    key="recreate"
                    label={t('Recreate Profile')}
                    color="primary"
                    type="button"
                    onClick={() => {
                      navigate(
                        `${CustomRoutes.surveyProfile.subRoutes.addNewSurveyProfile.path}?tab=cancelled&id=${id}`,
                      );
                    }}
                  />,
                ]
              : []),
            ...(detailSurveillanceProfile?.has_video_analysis
              ? [
                  <CustomBtn
                    key="download"
                    label={t('Download Report')}
                    color="primary"
                    type="button"
                    variant="outline"
                    disabled={loadingDownloadReport}
                    onClick={handleDownloadReport}
                  />,
                ]
              : []),
          ]}
        />
        <Main>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '1rem',
            }}
          >
            {(detailSurveillanceProfile?.cancel_reason ||
              detailSurveillanceProfile?.rejection_reason) && (
              <FormBlock
                style={{
                  backgroundColor: theme === 'dark' ? '#513D2B' : '#FBEBDD',
                  color: theme === 'dark' ? '#ECECEF' : Colors.Gray7,
                  fontWeight: 'normal',
                  padding: '8px 12px',
                  gridColumn: 'span 2',
                }}
              >
                <>
                  <span style={{ fontWeight: '600' }}>{t('Reason')}: </span>
                  {detailSurveillanceProfile?.cancel_reason ||
                    detailSurveillanceProfile?.rejection_reason ||
                    '-'}
                </>
              </FormBlock>
            )}
            <LeftProfileDetail
              detailSurveyMission={
                detailSurveillanceProfile as SurveillanceProfileState | null
              }
              chartData={detailSurveillanceProfile?.chart_data || []}
            />
            <RightProfileDetail
              markerData={markerData}
              droneRoutes={droneRoutes}
              droneList={detailSurveillanceProfile?.drone_assignments || []}
            />
          </div>
        </Main>
      </Container>
    </>
  );
};
