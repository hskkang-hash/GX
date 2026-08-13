import { JSX, memo } from 'react';
import { BsFileEarmark } from 'react-icons/bs';
import { GoCheck, GoX } from 'react-icons/go';
import { useTheme } from 'rj-core';

import Colors from '../../configs/Colors';
import { GXUploadFile } from '../../store/FileManagement.store';
import { removeFile } from '../../utils/actionFileManagement';
import SpinPercent from './SpinPercent';

interface FileItemRendererProps {
  originNode: React.ReactNode;
  gxFile: GXUploadFile;
}

export const FileItemRenderer = memo<FileItemRendererProps>(
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  ({ originNode, gxFile }): JSX.Element => {
    const [theme] = useTheme();
    const handleRemoveFile = (): void => {
      removeFile(gxFile.gxId, gxFile.gxType);
    };

    return (
      <div
        className="d-flex align-items-center custom-item-render mx-2 py-2 px-3"
        style={{
          borderRadius: '0.5rem',
          minHeight: '3.5rem',
          border: `1px solid ${theme === 'dark' ? '#444646' : '#DDDFE2'}`,
          backgroundColor: theme === 'dark' ? '#2D2E30' : '#F2F2F2',
        }}
      >
        <BsFileEarmark size={20} />
        <p
          className="mb-0 ms-2 text-truncate"
          style={{
            maxWidth: '15rem',
          }}
        >
          {gxFile.name}
        </p>
        <div className="ms-auto d-flex align-items-center gap-2">
          {gxFile.status === 'uploading' && (
            <SpinPercent percent={gxFile.progress} />
          )}
          {gxFile.status === 'done' && (
            <GoCheck
              size={20}
              style={{ color: Colors.Green }}
            />
          )}
          {gxFile.status === 'error' && (
            <GoX
              size={20}
              className="cursor-pointer"
              onClick={handleRemoveFile}
              style={{ color: Colors.Red }}
            />
          )}
        </div>
      </div>
    );
  },
);
