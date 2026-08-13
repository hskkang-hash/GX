import { Table, TableProps } from 'antd';
import React from 'react';

export const CustomTableAnalysis = <T extends Record<string, unknown>>({
  columns,
  data,
}: {
  columns: TableProps<T>['columns'];
  data: T[];
}) => {
  return (
    <Table<T>
      columns={columns}
      dataSource={data}
      pagination={false}
      size="small"
      bordered
    />
  );
};
