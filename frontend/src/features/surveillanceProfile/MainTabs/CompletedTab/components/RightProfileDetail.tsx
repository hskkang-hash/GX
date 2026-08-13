import { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BsDownload } from 'react-icons/bs';
import { MdOutlineRemoveRedEye } from 'react-icons/md';
import { CustomizableTable, FormBlock } from 'rj-core';
import CustomFieldBtn from '../../../../../components/Form/CustomFieldBtn';
import { remToPx } from '../../../../../utils/utils';
import MapForRouteUnified from '../../../components/MapForRouteUnified';
import {
  WaypointDetails,
  WaypointDetailsProps,
} from '../../../components/WaypointDetails';
import { useSurveillanceProfile } from '../../../hooks/useSurveillanceProfile';
import { useDrawingModeStore } from '../../../stores/drawingModeStore';
import { DroneAssignment } from '../../../types';
import { useConvertDate, } from '@/features/Dashboard/utils/formatDateTime';

export const RightProfileDetail = ({
  markerData = [],
  droneRoutes = [],
  droneList = [],
}: {
  markerData?: { lat: number; lng: number; name?: string; color?: string }[];
  droneRoutes?: DroneAssignment[];
  droneList?: DroneAssignment[];
}) => {
  const { t } = useTranslation();
  const [waypointDetails, setWaypointDetails] =
    useState<WaypointDetailsProps | null>(null);

  const currentShape = useDrawingModeStore((state) => state.currentShape);
  const { downloadLogProfile, downloadAnalysisProfile } =
    useSurveillanceProfile();

  const isLineMode = useMemo(
    () => currentShape?.type === 'LINE',
    [currentShape],
  );

  const { converRawDateToTimeFormat } = useConvertDate();

  const formdata = useMemo(() => {
    return droneList.map((assignment) => {
      return {
        ...assignment,
        start_time: converRawDateToTimeFormat(assignment.start_time),
      };
    });
  }, [droneList, converRawDateToTimeFormat]);

  const handleMarkerClick = useCallback(
    (marker: {
      lat: number;
      lng: number;
      name?: string;
      command?: string;
      frame?: string;
      param_1?: number;
      param_2?: number;
      param_3?: number;
      param_4?: number;
      color?: string;
      altitude?: number;
      routeId?: string | number;
    }) => {

      const waypointDetails: WaypointDetailsProps = {
        command: marker.command ?? "WAYPOINT",
        frame: marker.frame ?? "FRAME",
        param_1: marker?.param_1 ?? 0,
        param_2: marker?.param_2 ?? 0,
        param_3: marker?.param_3 ?? 0,
        param_4: marker?.param_4 ?? 0,
        latitude: marker.lat.toString(),
        longitude: marker.lng.toString(),
        altitude: marker.altitude?.toString() || '10.0',
      };

      setWaypointDetails(waypointDetails);
    },
    [],
  );

  const COLUMNS_DRONE_LIST_RIGHT = [
    {
      Header: 'Drone',
      accessor: 'device__name',
      enableColumnFilter: false,
      enableSorting: false,
    },
    {
      Header: 'Start Time',
      accessor: 'start_time',
      enableColumnFilter: false,
      enableSorting: false,
    },
    {
      Header: 'Start Point',
      accessor: 'start_point',
      enableColumnFilter: false,
      enableSorting: false,
    },
    {
      Header: 'End Point',
      accessor: 'end_point',
      enableColumnFilter: false,
      enableSorting: false,
    },
    {
      Header: 'Log',
      accessor: 'log',
      enableColumnFilter: false,
      enableSorting: false,
      cell: (row: { row: { original: { log: boolean } } }) => {
        return (
          <>
            <CustomFieldBtn
              icon={<BsDownload size={16} />}
              isDisabled={!row.row.original.log_path}
              onClick={() => {
                downloadLogProfile({ profile_id: row.row.original.id });
              }}
            />
          </>
        );
      },
    },
    {
      Header: 'Record',
      accessor: 'record',
      enableColumnFilter: false,
      enableSorting: false,
      cell: (row: {
        row: { original: { record: boolean; video_path: string } };
      }) => {
        return (
          <>
            <CustomFieldBtn
              icon={<MdOutlineRemoveRedEye size={16} />}
              onClick={() => { }}
              action="view"
              videoUrl={row.row.original.video_path}
              isDisabled={!row.row.original.video_path}
            />
          </>
        );
      },
    },
    {
      Header: 'Analysis',
      accessor: 'analysis',
      enableColumnFilter: false,
      enableSorting: false,
      cell: (row: { row: { original: { analysis: boolean } } }) => {
        return (
          <>
            <CustomFieldBtn
              icon={<BsDownload size={16} />}
              isDisabled={!row.row.original.analysis_path}
              onClick={() => {
                downloadAnalysisProfile({ profile_id: row.row.original.id });
              }}
            />
          </>
        );
      },
    },
  ];


  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <MapForRouteUnified
        notUseActionButtons
        isLineMode={isLineMode}
        markerData={markerData.length > 0 ? markerData : []}
        droneRoutes={droneRoutes}
        style={{ height: '30rem' }}
        overlayContent={
          <WaypointDetails
            waypointDetails={waypointDetails}
            setWaypointDetails={setWaypointDetails}
          />
        }
        onMarkerClick={handleMarkerClick}
      />
      <FormBlock>
        <div
          style={{
            fontWeight: 600,
            fontSize: '1.2rem',
            marginBottom: '1rem',
          }}
        >
          {t('Drones List')}
        </div>
        <CustomizableTable
          availableHeight={remToPx(32.5)}
          stickyHeader
          columns={COLUMNS_DRONE_LIST_RIGHT}
          data={{
            data: formdata,
          }}
          hasPagination={false}
          notUseGroupColumn
          useSystemSetting
          subTable
          notShowSelectRow
        />
      </FormBlock>
    </div>
  );
};
