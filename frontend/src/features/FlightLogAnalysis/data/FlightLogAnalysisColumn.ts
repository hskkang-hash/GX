import { t } from 'i18next';

export const FlightLogAnalysisColumn = [
  {
    Header: 'Drone Name',
    accessor: 'drone_name',
  },
  {
    Header: 'Service Name',
    accessor: 'service_name',
    filterVariant: 'select',
    filterOptions: [
      { label: t('Select'), value: '' },
      { label: t('Surveillance'), value: 'Surveillance' },
      { label: t('Delivery'), value: 'Delivery' },
    ],
  },
  {
    Header: 'Flight Start Time',
    accessor: 'start_time',
    filterVariant: 'datetime',
  },
  {
    Header: 'Flight End Time',
    accessor: 'end_time',
    filterVariant: 'datetime',
  },
  {
    Header: 'Total Distance',
    accessor: 'total_distance',
  },
  {
    Header: 'Start Point',
    accessor: 'start_point__name',
  },
  {
    Header: 'End Point',
    accessor: 'end_point__name',
  },
];
