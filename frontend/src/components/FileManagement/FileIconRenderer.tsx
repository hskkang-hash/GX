import {
  LoadingOutlined,
  FileOutlined,
  PictureOutlined,
  VideoCameraOutlined,
} from '@ant-design/icons';
import { UploadFile } from 'antd';
import { JSX, memo } from 'react';

import { GXUploadFile } from '../../store/FileManagement.store';

interface FileIconRendererProps {
  file: UploadFile;
}

export const FileIconRenderer = memo<FileIconRendererProps>(
  ({ file }): JSX.Element => {
    if (file.status === 'uploading') {
      return <LoadingOutlined style={{ color: '#1677ff' }} />;
    }

    if (file.type && file.type.startsWith('image/')) {
      return <PictureOutlined style={{ color: '#1677ff' }} />;
    }

    const gxFile = file as unknown as GXUploadFile;
    return gxFile.gxType === 'uploadVideoDrone' ||
      gxFile.gxType === 'uploadVideoRobot' ? (
      <VideoCameraOutlined style={{ color: '#1677ff' }} />
    ) : (
      <FileOutlined style={{ color: '#1677ff' }} />
    );
  },
);
