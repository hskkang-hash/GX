import { CustomBtn } from 'rj-core';

import { SurveyMissionState } from '../types/surveyMission.types';

export const columns = (
  handleApproveMission: () => void,
  handleRejectMission: () => void,
) => {
  return [
    {
      Header: 'ID',
      accessor: 'id',
    },
    {
      Header: 'Name',
      accessor: 'name',
    },
    {
      Header: 'Status',
      accessor: 'status',
    },
    {
      Header: 'Active',
      accessor: 'active',
    },
    {
      Header: 'Created By',
      accessor: 'created_by',
    },
    {
      Header: 'Created At',
      accessor: 'created_at',
    },
    {
      Header: 'Start Point',
      accessor: 'start_point',
    },
    {
      Header: 'End Point',
      accessor: 'end_point',
    },
    {
      Header: 'Total Distance (km)',
      accessor: 'total_distance',
    },
    {
      Header: 'Estimated Time (min)',
      accessor: 'estimated_time',
    },
    {
      Header: 'Note',
      accessor: 'note',
    },
    {
      Header: 'Group Name',
      accessor: 'group__name',
    },
    {
      Header: 'Group ID',
      accessor: 'group__id',
    },
    {
      Header: ' ',
      accessor: 'id',
      enableColumnFilter: false,
      enableSorting: false,
      notUseConfigTable: true,
      customStyle: {
        width: '170px',
        justifyItems: 'center',
      },
      cell: () => {
        return (
          <div className="d-flex gap-2">
            <CustomBtn
              label="Approve"
              type="button"
              variant="outline"
              color="primary"
              size="sm"
              onClick={handleApproveMission}
            />
            <CustomBtn
              label="Reject"
              type="button"
              variant="outline"
              color="primary"
              size="sm"
              onClick={handleRejectMission}
            />
          </div>
        );
      },
    },
  ];
};

export const exampleSurveyMissions: SurveyMissionState[] = [
  {
    id: 'SM001',
    name: 'Urban Traffic Survey - Downtown',
    status: 'active',
    active: true,
    created_by: 'John Smith',
    created_at: '2024-01-15T08:30:00Z',
    start_point: 'Central Station',
    end_point: 'City Hall',
    total_distance: 5.2,
    estimated_time: 45,
    note: 'Rush hour traffic analysis for downtown area',
    group__name: 'Traffic Analysis Team',
    group__id: 1,
  },
  {
    id: 'SM002',
    name: 'Highway Safety Inspection',
    status: 'completed',
    active: false,
    created_by: 'Sarah Johnson',
    created_at: '2024-01-10T14:15:00Z',
    start_point: 'Highway 101 North',
    end_point: 'Highway 101 South',
    total_distance: 25.8,
    estimated_time: 120,
    note: 'Comprehensive safety inspection of main highway',
    group__name: 'Safety Inspection Unit',
    group__id: 2,
  },
  {
    id: 'SM003',
    name: 'Pedestrian Walkway Assessment',
    status: 'pending',
    active: true,
    created_by: 'Mike Chen',
    created_at: '2024-01-20T09:45:00Z',
    start_point: 'University Campus',
    end_point: 'Shopping District',
    total_distance: 3.1,
    estimated_time: 30,
    note: 'Evaluate pedestrian safety and accessibility',
    group__name: 'Urban Planning Team',
    group__id: 3,
  },
  {
    id: 'SM004',
    name: 'Industrial Zone Survey',
    status: 'active',
    active: true,
    created_by: 'Lisa Wang',
    created_at: '2024-01-18T11:20:00Z',
    start_point: 'Industrial Park Gate',
    end_point: 'Warehouse District',
    total_distance: 8.7,
    estimated_time: 65,
    note: 'Environmental impact assessment for industrial area',
    group__name: 'Environmental Team',
    group__id: 4,
  },
  {
    id: 'SM005',
    name: 'Residential Area Traffic Flow',
    status: 'completed',
    active: false,
    created_by: 'David Brown',
    created_at: '2024-01-12T16:00:00Z',
    start_point: 'Oak Street',
    end_point: 'Maple Avenue',
    total_distance: 4.3,
    estimated_time: 35,
    note: 'Study traffic patterns in residential neighborhoods',
    group__name: 'Traffic Analysis Team',
    group__id: 1,
  },
  {
    id: 'SM006',
    name: 'Bridge Infrastructure Check',
    status: 'active',
    active: true,
    created_by: 'Anna Garcia',
    created_at: '2024-01-22T07:30:00Z',
    start_point: 'Bridge Approach North',
    end_point: 'Bridge Approach South',
    total_distance: 1.2,
    estimated_time: 90,
    note: 'Structural integrity assessment of main bridge',
    group__name: 'Infrastructure Team',
    group__id: 5,
  },
  {
    id: 'SM007',
    name: 'Public Transport Route Analysis',
    status: 'pending',
    active: true,
    created_by: 'Tom Wilson',
    created_at: '2024-01-25T10:15:00Z',
    start_point: 'Bus Terminal',
    end_point: 'Train Station',
    total_distance: 6.8,
    estimated_time: 50,
    note: 'Evaluate efficiency of public transport connections',
    group__name: 'Public Transport Team',
    group__id: 6,
  },
  {
    id: 'SM008',
    name: 'Emergency Route Planning',
    status: 'active',
    active: true,
    created_by: 'Emma Davis',
    created_at: '2024-01-28T13:45:00Z',
    start_point: 'Emergency Services HQ',
    end_point: 'Hospital District',
    total_distance: 7.5,
    estimated_time: 40,
    note: 'Critical emergency response route optimization',
    group__name: 'Emergency Planning Team',
    group__id: 7,
  },
  {
    id: 'SM009',
    name: 'Cycling Path Assessment',
    status: 'completed',
    active: false,
    created_by: 'James Miller',
    created_at: '2024-01-14T15:30:00Z',
    start_point: 'Park Entrance',
    end_point: 'City Center',
    total_distance: 9.2,
    estimated_time: 55,
    note: 'Evaluate cycling infrastructure and safety',
    group__name: 'Sustainable Transport Team',
    group__id: 8,
  },
  {
    id: 'SM010',
    name: 'Night Time Traffic Study',
    status: 'active',
    active: true,
    created_by: 'Rachel Taylor',
    created_at: '2024-01-30T20:00:00Z',
    start_point: 'Entertainment District',
    end_point: 'Residential Area',
    total_distance: 5.6,
    estimated_time: 75,
    note: 'Analyze night time traffic patterns and safety concerns',
    group__name: 'Traffic Analysis Team',
    group__id: 1,
  },
];

export const exampleSurveyMissionData = {
  data: exampleSurveyMissions,
  totalItem: exampleSurveyMissions.length,
  totalPage: 1,
};
