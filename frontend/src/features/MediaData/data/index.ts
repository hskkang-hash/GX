export const MEDIA_DATA_COLUMNS = [
  {
    Header: 'Name',
    accessor: 'object_name',
  },
  {
    Header: 'Type',
    accessor: 'type',
    filterVariant: 'select',
    filterOptions: [
      { label: 'Select', value: '' },
      { label: 'video', value: 'video' },
      { label: 'image', value: 'image' },
      { label: 'Document', value: 'document' },
      { label: 'folder', value: 'folder' },
      { label: 'bucket', value: 'bucket' },
    ],
  },
  {
    Header: 'Size',
    accessor: 'size',
  },
  {
    Header: 'Last Modified',
    accessor: 'last_modified',
    filterVariant: 'datetime',
  },
];
