import { formatIsProcessed } from '../../../utils/formatColumns';

export const COLUMNS_NOTICE_MANAGEMENT = [
  {
    Header: 'Created Date',
    accessor: 'created_time',
    filterVariant: 'datetime',
  },
  {
    Header: 'Content',
    accessor: 'content_text',
  },
  {
    Header: 'Creator',
    accessor: 'creator__full_name',
  },
  {
    Header: 'Editor',
    accessor: 'editor__full_name',
  },
  {
    Header: 'Updated Date',
    accessor: 'modified_on',
    filterVariant: 'datetime',
  },
  {
    Header: 'Comment',
    accessor: 'comment_count',
  },
];

export const COLUMNS_COMPLETED_NOTICE = [
  {
    Header: 'Created Date',
    accessor: 'created_time',
    filterVariant: 'datetime',
  },
  {
    Header: 'Status',
    accessor: 'status',
    filterVariant: 'select',
  },
  {
    Header: 'Content',
    accessor: 'content_text',
  },
  {
    Header: 'Creator',
    accessor: 'creator__full_name',
  },
  {
    Header: 'Editor',
    accessor: 'editor__full_name',
  },
  {
    Header: 'Updated Date',
    accessor: 'updated_time',
    filterVariant: 'datetime',
  },
  {
    Header: 'Comment',
    accessor: 'comment_count',
  },
];
