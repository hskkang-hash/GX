import { Box } from '@mui/material';
import {
  useEffect,
  useMemo,
  useState,
  type CSSProperties,
  type ReactElement,
} from 'react';
import { useTranslation } from 'react-i18next';
import { BsEye } from 'react-icons/bs';
import { BsDownload } from 'react-icons/bs';
import { useNavigate } from 'react-router-dom';
import {
  CustomBtn,
  CustomizableTable,
  ToastTopHelper,
  useCalculateHeight,
} from 'rj-core';

import Truncate from '@/components/truncate/Truncate';
import useCommonAPI from '@/features/useCommonAPI/useAPI';

import { CustomRoutes } from '../../../../services/API';
import { formatEnabled } from '../../../../utils/formatColumns';
import { remToPx } from '../../../../utils/utils';
import { useSurveillanceProfile } from '../../hooks/useSurveillanceProfile';
import { useDrawingModeStore } from '../../stores/drawingModeStore';
import { SurveillanceProfileState } from '../../types';
import { ProfileDetailModal } from './components/ProfileDetailModal';
import { useCompletedSurveillanceProfiles } from './hooks/useCompletedSurveillanceProfiles';

const ACTION_COLUMN_STYLE: CSSProperties = {
  maxWidth: 20,
  textAlign: 'center',
};

export default function CompletedTab({
  headerPageRef,
}: {
  headerPageRef?: React.RefObject<HTMLDivElement> | null;
}): ReactElement {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [showProfileDetailModal, setShowProfileDetailModal] =
    useState<boolean>(false);
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const spaceTableHeight = useCalculateHeight({
    refElements: [headerPageRef],
    additionalHeights: [remToPx(8)],
  });
  const {
    surveillanceProfiles,
    pageSize,
    setPageSize,
    currentPage,
    setCurrentPage,
    objSearch,
    setObjSearch,
    fetchCompletedSurveillanceProfiles,
  } = useCompletedSurveillanceProfiles();

  const {
    fetchDetailSurveillanceProfile,
    detailSurveillanceProfile,
    markerData,
    downloadReportProfile,
  } = useSurveillanceProfile();

  const clearAll = useDrawingModeStore((state) => state.clearAll);

  // Clear drawing mode store when component unmounts
  useEffect(() => {
    return () => {
      clearAll(); // Clear drawing mode store when component unmounts
    };
  }, [clearAll]);

  useEffect(() => {
    if (pageSize) {
      fetchCompletedSurveillanceProfiles();
    }
  }, [pageSize, currentPage, objSearch]);

  const handleClickRow = (row: SurveillanceProfileState) => {
    navigate(
      CustomRoutes.surveyProfile.subRoutes.detailSurveyProfile.path.replace(
        ':id',
        row.id?.toString() || '',
      ) + '?tab=completed',
    );
  };

  const handleDownloadAnalysis = async (profileId: number) => {
    console.log('🟡 Download button clicked for profile ID:', profileId);
    const result = await downloadReportProfile({ profile_id: profileId });

    if (result.success) {
      ToastTopHelper.success(
        result.message || t('Download request queued successfully'),
      );
    } else {
      ToastTopHelper.error(result.message || t('Failed to initiate download'));
    }
  };

  const { useFetchOptions, getOptionsByModel } = useCommonAPI();

  const purposeTypeConfig = useMemo(
    () => ({
      type: 'model' as const,
      params: { name_modal: 'MissionPurpose', search_field: 'name' },
      defaultLabel: t('Select'),
    }),
    [],
  );
  const purposeType = useFetchOptions(getOptionsByModel, purposeTypeConfig);

  const COLUMNS = [
    {
      Header: t(' '),
      accessor: 'action',
      cell: (row: { row: { original: { id: number } } }) => (
        <div
          className="special-label"
          onClick={(e) => {
            e.stopPropagation();
            setShowProfileDetailModal(true);
            fetchDetailSurveillanceProfile(row?.row?.original?.id);
          }}
        >
          <BsEye size={16} />
        </div>
      ),
      customStyle: ACTION_COLUMN_STYLE,
      enableSorting: false,
      enableColumnFilter: false,
    },
    {
      Header: 'Profile ID',
      accessor: 'id',
      customStyle: {
        width: '8rem',
      },
    },
    {
      Header: 'Profile Name',
      accessor: 'name',
      cell: (info: any) => {
        return info.getValue() ? (
          <Truncate
            content={info.getValue()}
            tooltipContent={info.getValue()}
          />
        ) : (
          '-'
        );
      },
    },
    {
      Header: 'Purpose',
      accessor: 'purpose__name',
      enableSorting: true,
      enableColumnFilter: true,
      filterVariant: 'select',
      filterOptions:
        purposeType.length > 0
          ? purposeType?.map((item: any) => ({
              label: item.label,
              value:
                item.label == 'Select' ||
                item.label == '선택' ||
                item.label == 'เลือก'
                  ? ''
                  : item.label,
            }))
          : [],
      cell: (info: any) => {
        return info.getValue() ? (
          <Truncate
            content={info.getValue()}
            tooltipContent={info.getValue()}
          />
        ) : (
          '-'
        );
      },
    },
    {
      Header: 'Created Date',
      accessor: 'created_on',
      filterVariant: 'datetime',
    },
    {
      Header: 'Start Date',
      accessor: 'start_time',
      filterVariant: 'datetime',
    },
    {
      Header: 'End Date',
      accessor: 'estimated_end_time',
      filterVariant: 'datetime',
    },
    {
      Header: 'Actual Start Date',
      accessor: 'actual_start_time',
      filterVariant: 'datetime',
    },
    {
      Header: 'Actual End Date',
      accessor: 'actual_end_time',
      filterVariant: 'datetime',
    },
    {
      Header: 'Total Distance',
      accessor: 'total_distance',
    },
    {
      Header: 'Total Time',
      accessor: 'total_flight_time',
    },
    {
      Header: 'Log',
      accessor: 'mission__log_collection',
      filterVariant: 'checkbox',
      filterOptions: ['True', 'False'],
      customStyle: {
        width: '7rem',
      },
      cell: (row: {
        row: { original: { mission__log_collection: boolean } };
      }) => {
        return formatEnabled(row?.row?.original?.mission__log_collection);
      },
    },
    {
      Header: 'Record',
      accessor: 'mission__video_recording',
      filterVariant: 'checkbox',
      filterOptions: ['True', 'False'],
      customStyle: {
        width: '7rem',
      },
      cell: (row: {
        row: { original: { mission__video_recording: boolean } };
      }) => {
        return formatEnabled(row?.row?.original?.mission__video_recording);
      },
    },
    {
      Header: 'Analysis',
      accessor: 'mission__video_analysis',
      filterVariant: 'checkbox',
      filterOptions: ['True', 'False'],
      customStyle: {
        width: '7rem',
      },
      cell: (row: {
        row: { original: { mission__video_analysis: boolean } };
      }) => {
        return formatEnabled(row?.row?.original?.mission__video_analysis);
      },
    },
    { Header: 'Operator', accessor: 'operator_full_name' },
    {
      Header: ' ',
      accessor: 'id',
      enableColumnFilter: false,
      enableSorting: false,
      notUseConfigTable: true,

      cell: (row: {
        row: { original: { id: string; has_video_analysis?: boolean } };
      }) => {
        const rowId = Number(row.row.original.id);
        const downloadAvailable = row.row.original?.has_video_analysis;

        return (
          <div
            style={{ width: '8rem' }}
            onClick={(e) => e.stopPropagation()}
          >
            <CustomBtn
              variant="outline"
              color="primary"
              type="button"
              icon={<BsDownload size={16} />}
              onClick={() => handleDownloadAnalysis(rowId)}
              disabled={!downloadAvailable}
            />
          </div>
        );
      },
    },
  ];

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

  return (
    <Box px="1rem">
      <CustomizableTable
        subTable
        stickyHeader
        notUseGroupColumn
        notShowSelectRow
        useSystemSetting
        availableHeight={spaceTableHeight}
        columns={COLUMNS}
        data={surveillanceProfiles}
        refreshTable={refreshTable}
        setRefreshTable={setRefreshTable}
        objSearch={objSearch}
        setObjSearch={setObjSearch}
        currentPage={currentPage}
        setCurrentPage={setCurrentPage}
        pageSize={pageSize}
        setPageSize={setPageSize}
        onClickRow={handleClickRow}
      />
      <ProfileDetailModal
        show={showProfileDetailModal}
        onHide={() => setShowProfileDetailModal(false)}
        detailData={
          detailSurveillanceProfile as SurveillanceProfileState | null
        }
        markerData={markerData}
        droneRoutes={droneRoutes}
        showActualStartTime
      />
    </Box>
  );
}
