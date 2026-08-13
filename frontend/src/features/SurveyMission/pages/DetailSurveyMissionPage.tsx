import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import {
  CustomBreadcrumb,
  CustomBtn,
  FormBlock,
  Main,
  ToastTopHelper,
  useLoadingContext,
  useTheme,
} from 'rj-core';
import { v4 as uuidv4 } from 'uuid';

import Colors from '../../../configs/Colors';
import { CustomRoutes } from '../../../services/API';
import { ApproveMissionModal } from '../components/ApproveMissionModal';
import { LeftDetailSurveyMission } from '../components/LeftDetailSurveyMission';
import { RejectMissionModal } from '../components/RejectMissionModal';
import { RightDetailSurveyMission } from '../components/RightDetailSurveyMission';
import { useSurveyMission } from '../hooks/useSurveyMission';
import { useDrawingModeStore } from '../stores/drawingModeStore';
import { SurveyMissionState, Waypoint } from '../types/surveyMission.types';

interface ChartDataItem {
  waypointName: string;
  cruise_speed: number;
  operating_altitude: number;
  cumulativeDistance: number;
  order: number;
}

interface ChartDataPoint {
  name: string;
  cruise_speed: number;
  operating_altitude: number;
  distance: number;
  order: number;
}

export const DetailSurveyMissionPage = () => {
  const { t } = useTranslation();
  const { id } = useParams();
  const navigate = useNavigate();
  const { showLoading, hideLoading } = useLoadingContext();
  const [theme] = useTheme();
  const [surveyMission, setSurveyMission] = useState<SurveyMissionState | null>(
    null,
  );
  const [
    hasPermissionActionSurveyMission,
    setHasPermissionActionSurveyMission,
  ] = useState(false);
  const [showApproveMissionModal, setShowApproveMissionModal] = useState(false);
  const [showRejectMissionModal, setShowRejectMissionModal] = useState(false);
  const {
    getDetailSurveyMission,
    approveSurveyMission,
    rejectSurveyMission,
    checkPermissionActionSurveyMission,
  } = useSurveyMission();
  const [chartData, setChartData] = useState<ChartDataItem[]>([]);
  const [markerData, setMarkerData] = useState<
    Array<{
      lat: number;
      lng: number;
      name?: string;
      color?: string;
      routeId?: string | number;
    }>
  >([]);

  const setCurrentShape = useDrawingModeStore((state) => state.setCurrentShape);
  const clearAll = useDrawingModeStore((state) => state.clearAll);

  // Only clear store when component unmounts, not when mounting
  useEffect(() => {
    return () => {
      clearAll(); // Clear when component unmounts
    };
  }, [clearAll]);

  const checkHasPermissionActionSurveyMission = useCallback(async () => {
    const result = await checkPermissionActionSurveyMission();
    setHasPermissionActionSurveyMission(result);
  }, [checkPermissionActionSurveyMission]);

  const getDetailData = useCallback(async () => {
    const { data } = await getDetailSurveyMission({ id: Number(id) });
    if (data) {
      setSurveyMission(data);

      console.log(
        'markerData',
        data.qgc_mission_data?.mission?.items
          .find((item: any) => item.type === 'ComplexItem')
          ?.TransectStyleComplexItem?.VisualTransectPoints?.map(
            (waypoint: [number, number]) => ({
              lat: waypoint[0],
              lng: waypoint[1],
            }),
          ),
      );

      const markerDataLine = data.line_mission
        ? data.all_waypoints.map((waypoint: Waypoint) => ({
            lat: Number(waypoint.latitude),
            lng: Number(waypoint.longitude),
          }))
        : data.qgc_mission_data?.mission?.items
            .find((item: any) => item.type === 'ComplexItem')
            ?.TransectStyleComplexItem?.VisualTransectPoints?.map(
              (waypoint: [number, number]) => ({
                lat: waypoint[0],
                lng: waypoint[1],
              }),
            );

      setMarkerData(markerDataLine);

      const points = data.line_mission
        ? data.all_waypoints.map((waypoint: Waypoint) => ({
            lat: Number(waypoint.latitude),
            lng: Number(waypoint.longitude),
          }))
        : data.polygon?.map((point: [number, number]) => ({
            lat: point[0],
            lng: point[1],
          })) || [];

      const newShape = {
        id: uuidv4(),
        type: (data.line_mission
          ? 'LINE'
          : data.polygon?.length === 16
            ? 'CIRCULAR'
            : data.polygon?.length === 4
              ? 'POLYGON'
              : 'TRACE') as 'LINE' | 'CIRCULAR' | 'POLYGON' | 'TRACE',
        points,
        pointsLength: data.line_mission ? points.length : null,
        return: data.return_to_home || false,
      };

      setCurrentShape(newShape);

      // Process chart data to calculate cumulative distances
      const processedChartData = data.chart_data
        .sort((a: ChartDataPoint, b: ChartDataPoint) => a.order - b.order)
        .map(
          (
            item: ChartDataPoint,
            index: number,
            array: ChartDataPoint[],
          ): ChartDataItem => {
            // Calculate cumulative distance up to this waypoint
            const cumulativeDistance = array
              .slice(0, index + 1)
              .reduce((sum, waypoint) => sum + (waypoint.distance || 0), 0);

            return {
              waypointName: item?.name || '',
              cruise_speed: item?.cruise_speed || 0,
              operating_altitude: item?.operating_altitude || 0,
              cumulativeDistance: Math.round(cumulativeDistance * 100) / 100, // Round to 2 decimal places
              order: item?.order || 0,
            };
          },
        );

      setChartData(processedChartData);
    }
  }, [id, getDetailSurveyMission, setCurrentShape]);

  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (id) {
      timeoutRef.current = setTimeout(() => {
        getDetailData();
        checkHasPermissionActionSurveyMission();
      }, 1000);
    }
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (surveyMission) {
      hideLoading();
    } else {
      showLoading();
    }
  }, [surveyMission, hideLoading, showLoading]);

  const handleRejectMission = useCallback(
    async (values: { reason: string }) => {
      const { success, message } = await rejectSurveyMission({
        id: Number(id),
        data: { reason: values.reason },
      });
      if (success) {
        ToastTopHelper.success(message);
        getDetailData();
        setShowRejectMissionModal(false);
      } else {
        ToastTopHelper.error(message);
      }
    },
    [id, rejectSurveyMission, getDetailData],
  );

  const handleApproveMission = useCallback(async () => {
    const { success, message } = await approveSurveyMission({ id: Number(id) });
    if (success) {
      ToastTopHelper.success(message);
      getDetailData();
      setShowApproveMissionModal(false);
    } else {
      ToastTopHelper.error(message);
    }
  }, [id, approveSurveyMission, getDetailData]);

  const handleApproveMissionModal = useCallback(
    (show: boolean) => {
      setShowApproveMissionModal(show);
    },
    [setShowApproveMissionModal],
  );

  const handleRejectMissionModal = useCallback(
    (show: boolean) => {
      setShowRejectMissionModal(show);
    },
    [setShowRejectMissionModal],
  );

  const RenderButtons = useMemo(() => {
    if (surveyMission?.status__code === 'approved') {
      return [];
    }
    if (surveyMission?.status__code === 'rejected') {
      return [
        <CustomBtn
          variant="outline"
          color="primary"
          label={t('Edit')}
          onClick={() =>
            navigate(
              CustomRoutes.surveyMission.subRoutes.editSurveyMission.path.replace(
                ':id',
                id || '',
              ),
            )
          }
        />,
      ];
    }
    return [
      <CustomBtn
        variant="outline"
        color="primary"
        label={t('Edit')}
        onClick={() =>
          navigate(
            CustomRoutes.surveyMission.subRoutes.editSurveyMission.path.replace(
              ':id',
              id || '',
            ),
          )
        }
      />,
      ...(hasPermissionActionSurveyMission
        ? [
            <CustomBtn
              variant="outline"
              color="primary"
              label={t('Reject')}
              onClick={() => handleRejectMissionModal(true)}
            />,
            <CustomBtn
              variant="outline"
              color="primary"
              label={t('Approve')}
              onClick={() => handleApproveMissionModal(true)}
            />,
          ]
        : []),
    ];
  }, [
    id,
    navigate,
    surveyMission,
    hasPermissionActionSurveyMission,
    handleRejectMissionModal,
    handleApproveMissionModal,
    t,
  ]);

  console.log('markerData', markerData);

  return (
    <>
      <CustomBreadcrumb
        items={[
          { url: CustomRoutes.surveyMission.path },
          { text: 'Detailed Information' },
        ]}
        buttons={surveyMission ? RenderButtons : []}
      />
      <Main>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '1rem',
          }}
        >
          {surveyMission?.status__code === 'rejected' && (
            <FormBlock
              style={{
                backgroundColor: theme === 'dark' ? '#513D2B' : '#FBEBDD',
                color: theme === 'dark' ? '#ECECEF' : Colors.Gray7,
                fontWeight: 'normal',
                padding: '8px 12px',
                gridColumn: 'span 2',
              }}
            >
              {surveyMission?.rejection_reason || '-'}
            </FormBlock>
          )}
          <div>
            {surveyMission && (
              <LeftDetailSurveyMission
                detailSurveyMission={surveyMission}
                chartData={chartData}
              />
            )}
          </div>
          <div>
            <RightDetailSurveyMission markerData={markerData} />
          </div>

          {showApproveMissionModal && (
            <ApproveMissionModal
              show={showApproveMissionModal}
              onClose={() => handleApproveMissionModal(false)}
              onApprove={handleApproveMission}
            />
          )}

          {showRejectMissionModal && (
            <RejectMissionModal
              show={showRejectMissionModal}
              onClose={() => handleRejectMissionModal(false)}
              onReject={handleRejectMission}
            />
          )}
        </div>
      </Main>
    </>
  );
};
