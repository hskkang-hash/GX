import { formatEnabled } from '../../../../../utils/formatColumns';

export const GENERAL_DATA = {
  name: {
    label: 'Name',
    code: 'string',
  },
  mission: {
    label: 'Mission',
    type: 'string',
  },
  start_time: {
    label: 'Start Time',
    type: 'string',
  },
  repeat: {
    label: 'Repeat',
    type: 'string',
  },
  operator: {
    label: 'Operator',
    type: 'string',
  },
  purpose: {
    label: 'Purpose',
    type: 'string',
  },
  // return: {
  //   label: 'Return',
  //   type: 'boolean',
  // },
  maximum_number_of_drones: {
    label: 'Maximum number of drones',
    type: 'unit',
  },
  total_distance: {
    label: 'Total Distance',
    type: 'unit',
  },
  total_estimated_time: {
    label: 'Total Estimated Time',
    type: 'string',
  },
  note: {
    label: 'Note',
    type: 'string',
  },
} as const;

export const INFORMATION_DATA = {
  name: {
    label: 'Name',
    code: 'string',
  },
  mission: {
    label: 'Mission',
    type: 'string',
  },
  start_time: {
    label: 'Start Time',
    type: 'string',
  },
  end_time: {
    label: 'End Time',
    type: 'string',
  },
  repeat: {
    label: 'Repeat',
    type: 'string',
  },
  operator: {
    label: 'Operator',
    type: 'string',
  },
  purpose: {
    label: 'Purpose',
    type: 'string',
  },
  // return: {
  //   label: 'Return',
  //   type: 'string',
  // },
  maximum_number_of_drones: {
    label: 'Maximum number of drones',
    type: 'unit',
  },
  total_distance: {
    label: 'Total Distance',
    type: 'unit',
  },
  total_estimated_time: {
    label: 'Total Time',
    type: 'string',
  },
  note: {
    label: 'Note',
    type: 'string',
  },
} as const;

export const COLUMNS_DRONE_LIST = [
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
  // {
  //   Header: 'Waiting Coordinates',
  //   accessor: 'waiting_coordinates',
  //   enableColumnFilter: false,
  //   enableSorting: false,
  //   cell: (row: {
  //     row: { original: { waiting_coordinates: [number, number] } };
  //   }) => {
  //     console.log('row', row);
  //     return row.row.original.waiting_coordinates
  //       ? `${row.row.original.waiting_coordinates[0].toFixed(7)}, ${row.row.original.waiting_coordinates[1].toFixed(7)}`
  //       : '-';
  //   },
  // },
  {
    Header: 'Log',
    accessor: 'log',
    enableColumnFilter: false,
    enableSorting: false,
    cell: (row: { row: { original: { log: boolean } } }) => {
      return formatEnabled(row.row.original.log);
    },
  },
  {
    Header: 'Record',
    accessor: 'record',
    enableColumnFilter: false,
    enableSorting: false,
    cell: (row: { row: { original: { record: boolean } } }) => {
      return formatEnabled(row.row.original.record);
    },
  },
  {
    Header: 'Analysis',
    accessor: 'analysis',
    enableColumnFilter: false,
    enableSorting: false,
    cell: (row: { row: { original: { analysis: boolean } } }) => {
      return formatEnabled(row.row.original.analysis);
    },
  },
];

export const COLUMNS_DRONE_LIST_GCS = [
  {
    Header: 'Drone',
    accessor: 'device__name',
    enableColumnFilter: false,
    enableSorting: false,
  },
  {
    Header: 'Actual Start Time',
    accessor: 'actual_start_time',
    enableColumnFilter: false,
    enableSorting: false,
    cell: (row: { row: { original: { actual_start_time: string } } }) => {
      console.log('row', row);
      return row.row.original.actual_start_time
        ? `${row.row.original.actual_start_time}`
        : '-';
    },
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
  // {
  //   Header: 'Waiting Coordinates',
  //   accessor: 'waiting_coordinates',
  //   enableColumnFilter: false,
  //   enableSorting: false,
  //   cell: (row: {
  //     row: { original: { waiting_coordinates: [number, number] } };
  //   }) => {
  //     console.log('row', row);
  //     return row.row.original.waiting_coordinates
  //       ? `${row.row.original.waiting_coordinates[0].toFixed(7)}, ${row.row.original.waiting_coordinates[1].toFixed(7)}`
  //       : '-';
  //   },
  // },
  {
    Header: 'Log',
    accessor: 'log',
    enableColumnFilter: false,
    enableSorting: false,
    cell: (row: { row: { original: { log: boolean } } }) => {
      return formatEnabled(row.row.original.log);
    },
  },
  {
    Header: 'Record',
    accessor: 'record',
    enableColumnFilter: false,
    enableSorting: false,
    cell: (row: { row: { original: { record: boolean } } }) => {
      return formatEnabled(row.row.original.record);
    },
  },
  {
    Header: 'Analysis',
    accessor: 'analysis',
    enableColumnFilter: false,
    enableSorting: false,
    cell: (row: { row: { original: { analysis: boolean } } }) => {
      return formatEnabled(row.row.original.analysis);
    },
  },
];
