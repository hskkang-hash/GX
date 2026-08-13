import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  CustomBreadcrumb,
  CustomBtn,
  CustomizableTable,
  FormBlock,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useTheme,
} from 'rj-core';

import { Map } from '@/components/maps';
import Colors, { textLabel } from '@/configs/Colors';
import { CustomRoutes } from '@/services/API';
import { formatEnabled } from '@/utils/formatColumns';
import { formatWithUnit } from '@/utils/utils';

import Truncate from '../../../components/truncate/Truncate';
import useAPI from '../useAPI/useAPI';
import { convertEstimated } from '../utils/convertEstimated';
import './DetailRoute.scss';

// Define proper interfaces
interface RouteDetails {
  name?: string;
  total_stops?: string | number;
  total_distance?: string;
  estimated_time?: string;
  note?: string;
  [key: string]: string | number | boolean | undefined; // For any other properties
}

interface Stop {
  route_terminal_id?: number;
  terminal_id: number;
  order: number;
  terminal_name: string;
  terminal_type?: string;
  address?: string;
  stop?: boolean;
  note?: string;
  // For map functionality
  lat: number; // Required for map
  lng: number; // Required for map
  time_stops?: {
    value: number;
    unit: string;
  };
  for_robot?: boolean;
  [key: string]: string | number | boolean | undefined; // For any other properties
}

interface TableRow {
  getValue: () => string | number | null | undefined;
  row?: {
    original?: Stop;
  };
}

const GENERAL_DATA = {
  name: {
    label: 'Name',
    type: 'string',
  },
  total_stops: {
    label: 'Total Stops',
    type: 'number',
  },
  total_distance: {
    label: 'Total Distance',
    type: 'unit',
  },
  estimated_time: {
    label: 'Total Estimated Flight Time',
    type: 'unit',
  },
  estimated_arrival_time: {
    label: 'Estimated Arrival Time at Delivery Point',
    type: 'unit',
  },
  note: {
    label: 'Note',
    type: 'string',
  },
};

const DetailRoute = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [theme] = useTheme();
  const { id } = useParams();
  const [openOffcanvas, setOpenOffcanvas] = useState<boolean>(false);
  const [refreshTable, setRefreshTable] = useState<boolean>(false);
  const [pageSize, setPageSize] = useState<number>();
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [detailRoute, setDetailRoute] = useState<RouteDetails>({});
  const [stops, setStops] = useState<Stop[]>([]);

  const { getDetailRouteAPI } = useAPI();
  const [chartData, setChartData] = useState<any[]>([]);

  const HistoryBehaviorColumns = [
    {
      Header: 'Order',
      accessor: 'order',
      enableSorting: false,
      enableColumnFilter: false,
      customStyle: {
        width: '50px',
        flexWrap: 'wrap',
      },
    },
    {
      Header: 'Terminal Name',
      accessor: 'terminal_name',
      enableSorting: false,
      enableColumnFilter: false,
      customStyle: {
        width: '130px',
        flexWrap: 'wrap',
      },
      cell: (row: TableRow) =>
        row.getValue() ? (
          <Truncate
            content={row.getValue()}
            maxLengthContent={16}
            tooltipContent={row.getValue()}
          />
        ) : (
          '-'
        ),
    },
    {
      Header: 'Terminal Type',
      accessor: 'terminal_type',
      enableSorting: false,
      enableColumnFilter: false,
      customStyle: {
        width: '150px',
      },
      cell: (row: TableRow) => {
        return row.getValue() ? (
          <Truncate
            content={row.getValue()}
            maxLengthContent={20}
            tooltipContent={row.getValue()}
          />
        ) : (
          '-'
        );
      },
    },
    {
      Header: 'Address',
      accessor: 'address',
      enableSorting: false,
      enableColumnFilter: false,
      customStyle: {
        width: '200px',
        flexWrap: 'wrap',
      },
      cell: (row: TableRow) =>
        row.getValue() ? (
          <Truncate
            content={row.getValue()}
            maxLengthContent={20}
            tooltipContent={row.getValue()}
          />
        ) : (
          '-'
        ),
    },
    // {
    //   Header: 'For Robot?',
    //   accessor: 'for_robot',
    //   enableSorting: false,
    //   enableColumnFilter: false,
    //   customStyle: {
    //     width: '80px',
    //   },
    //   filterVariant: 'checkbox',
    //   filterOptions: ['true', 'false'],
    //   cell: (row: TableRow) => (row.getValue() ? formatEnabled(Boolean(row.getValue())) : '-'),
    // },
    {
      Header: 'Stop?',
      accessor: 'stop',
      enableSorting: false,
      enableColumnFilter: false,
      customStyle: {
        width: '50px',
      },
      filterVariant: 'checkbox',
      filterOptions: ['true', 'false'],
      cell: (row: TableRow) =>
        formatEnabled(
          Boolean(Number(row.row?.original?.time_stops) > 0 ? true : false),
        ),
    },
    {
      Header: 'Note',
      accessor: 'note',
      enableSorting: false,
      enableColumnFilter: false,
      customStyle: {
        width: '100px',
      },
    },
  ];

  const getDetailRoute = async (id: number) => {
    const { success, data, message } = await getDetailRouteAPI(id);
    if (!success) {
      ToastTopHelper.error(message);
      return;
    }
    const { estimatedArrivalTime } = convertEstimated(
      data.route_terminals || [],
      data.route.two_way,
    );
    setDetailRoute({
      ...data.route,
      estimated_arrival_time: estimatedArrivalTime,
    });
    setChartData(data.chart_data || []);
    if (data.route_terminals && Array.isArray(data.route_terminals)) {
      const formattedStops = data.route_terminals.map(
        (stop: Stop, index: number) => ({
          route_terminal_id: (stop as any).route_terminal_id,
          order: (stop as any).order || index + 1,
          terminal_id: stop.terminal_id,
          terminal_name: stop.name,
          terminal_type: stop.terminal_type__name,
          address: stop.address,
          stop: stop.stop,
          note: stop.note,
          lat: stop.latitude,
          lng: stop.longitude,
          time_stops: stop.time_stops,
          is_temp: stop.terminal_type__name === 'Temp',
          for_robot: stop.for_robot || false,
          cruise_speed: stop.cruise_speed,
          operating_altitude: stop.operating_altitude,
          command_line: stop.command_line,
          frame: stop.frame,
        }),
      );
      setStops(formattedStops);
    }
  };

  useEffect(() => {
    if (id) {
      getDetailRoute(Number(id));
    }
  }, [id]);

  const cumulativeDistances = chartData.map((item, index) => {
    let cumulativeDistance = 0;
    for (let i = 0; i <= index; i++) {
      cumulativeDistance += chartData[i].distance || 0;
    }
    return cumulativeDistance;
  });

  // add offsets to points have the same distance
  const chartDataForMap = chartData.map((item, index) => {
    const baseDistance = cumulativeDistances[index];

    console.log('baseDistance', baseDistance);

    // Count previous points have the same distance
    //offset to separate overlapping points
    const sameDistanceCount = cumulativeDistances
      .slice(0, index)
      .filter((d) => d === baseDistance).length;
    const offset = sameDistanceCount * 0.003;

    return {
      name: baseDistance + offset,
      uniqueKey: `point-${index}-${item.name}-${baseDistance}`,
      cruise_speed: item.cruise_speed || 0,
      operating_altitude: item.operating_altitude || 0,
      originalName: item.name,
      order: item.order || index + 1,
    };
  });

  const maxDistance =
    chartDataForMap.length > 0
      ? Math.max(...chartDataForMap.map((item) => item.name))
      : 0;
  const roundedMaxDistance = Math.ceil(maxDistance / 2) * 2;
  const ticks = [];
  for (let i = 0; i <= roundedMaxDistance; i += 2) {
    ticks.push(i);
  }

  return (
    <>
      <CustomBreadcrumb
        items={[
          { url: CustomRoutes.routes.path },
          { text: 'Detailed Information' },
        ]}
        buttons={[
          detailRoute.is_active && (
            <CustomBtn
              variant="outline"
              color="primary"
              label={t('Edit')}
              actionType={ROLE_PERMISSION.UPDATE}
              onClick={() =>
                navigate(
                  CustomRoutes.routes.subRoutes.editRoute.path.replace(
                    ':id',
                    id?.toString() || '',
                  ),
                  {
                    state: {
                      route: detailRoute,
                      stops: stops,
                    },
                  },
                )
              }
            />
          ),
        ]}
      />
      <Main>
        <div className="form-grid">
          <div className="form-container">
            <FormBlock>
              <div className={`detail-route__section ${theme}`}>
                <span className="detail-route__section-title">
                  {t('General')}
                </span>
                <ul className="detail-route__list">
                  {Object.keys(GENERAL_DATA).map(
                    (item, index) =>
                      detailRoute[item] !== undefined &&
                      detailRoute[item] !== null &&
                      detailRoute[item] !== '' && (
                        <li
                          key={index}
                          className={`detail-route__list-item ${theme}`}
                        >
                          <span className="detail-route__label">
                            {t(
                              GENERAL_DATA[item as keyof typeof GENERAL_DATA]
                                .label,
                            )}
                          </span>
                          <span className={`detail-route__value ${theme}`}>
                            {GENERAL_DATA[item as keyof typeof GENERAL_DATA]
                              .type === 'unit'
                              ? formatWithUnit(
                                  detailRoute[
                                    item as keyof typeof GENERAL_DATA
                                  ],
                                )
                              : detailRoute[item as keyof typeof GENERAL_DATA]}
                          </span>
                        </li>
                      ),
                  )}
                </ul>
              </div>
            </FormBlock>
            <FormBlock>
              <div
                className="detail-route__section-title"
                style={{ paddingBottom: '16px' }}
              >
                {t('Flight speed and altitude chart')}
              </div>
              <div
                style={{
                  flex: 1,
                  width: '100%',
                  height: '100%',
                  maxHeight: '320px',
                }}
              >
                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >
                  <LineChart
                    width={500}
                    height={300}
                    data={chartDataForMap}
                    margin={{
                      top: 5,
                      right: 30,
                      left: 20,
                      bottom: 5,
                    }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="name"
                      type="number"
                      domain={['dataMin', 'dataMax']}
                      tickFormatter={(value) => Math.round(value).toString()}
                      ticks={ticks}
                      stroke={textLabel[theme === 'dark' ? 'dark' : 'light']}
                    />
                    <YAxis
                      stroke={textLabel[theme === 'dark' ? 'dark' : 'light']}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor:
                          theme === 'dark' ? Colors.Secondary : Colors.White,
                        border:
                          theme === 'dark'
                            ? `1px solid ${Colors.Gray6}`
                            : `1px solid ${Colors.Gray4}`,
                        borderRadius: '8px',
                      }}
                      labelStyle={{
                        color: textLabel[theme === 'dark' ? 'dark' : 'light'],
                      }}
                      formatter={(value, name) => [value, name]}
                      labelFormatter={(label, payload) => {
                        if (payload && payload[0] && payload[0].payload) {
                          const dataPoint = chartDataForMap.find(
                            (item) =>
                              item.uniqueKey === payload[0].payload.uniqueKey,
                          );
                          return (
                            dataPoint?.originalName || `Distance: ${label} km`
                          );
                        }
                        const dataPoint = chartDataForMap.find(
                          (item) => item.name === label,
                        );
                        return (
                          dataPoint?.originalName || `Distance: ${label} km`
                        );
                      }}
                    />
                    <Legend />
                    <Line
                      type="linear"
                      dataKey="cruise_speed"
                      stroke="#7086FD"
                      activeDot={{ r: 8 }}
                      name={t('Cruise Speed (m/s)')}
                    />
                    <Line
                      type="linear"
                      dataKey="operating_altitude"
                      stroke="#6FD195"
                      activeDot={{ r: 8 }}
                      name={t('Altitude/Z')}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </FormBlock>
            <FormBlock>
              <div className="detail-route__section-title">
                {t('Stops List')}
              </div>
              <CustomizableTable
                subTable
                notUseGroupColumn
                notShowSelectRow
                useSystemSetting
                columns={HistoryBehaviorColumns}
                data={{
                  data: stops,
                }}
                hasPagination={false}
                refreshTable={refreshTable}
                setRefreshTable={setRefreshTable}
                currentPage={currentPage}
                setCurrentPage={setCurrentPage}
                pageSize={pageSize}
                setPageSize={setPageSize}
                offcanvas={openOffcanvas}
                setOpenOffcanvas={(boolean: boolean) => {
                  setOpenOffcanvas(boolean);
                }}
              />
            </FormBlock>
          </div>
          <div
            style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}
          >
            {/* <MapKakao
              operatingMarkers={stops.length > 0 ? stops : []}
              polylines={
                stops.length > 1
                  ? [
                      stops.map((stop) => ({
                        lat: stop.lat,
                        lng: stop.lng,
                        for_robot: stop.for_robot,
                      })),
                    ]
                  : []
              }
              style={{ height: 875 }}
            /> */}
            <Map
              operatingMarkers={stops.length > 0 ? stops : []}
              polylines={
                stops.length > 1
                  ? [
                      stops.map((stop) => ({
                        lat: stop.lat,
                        lng: stop.lng,
                        for_robot: stop.for_robot,
                      })),
                    ]
                  : []
              }
              style={{ height: 875 }}
            />
          </div>
        </div>
      </Main>
    </>
  );
};

export default DetailRoute;
