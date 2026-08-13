import type { UploadFile } from 'antd';
import type { UploadFileStatus } from 'antd/es/upload/interface';

import {
  GXDownloadFile,
  useFileManagementStore,
  type GXFileType,
  type GXUploadFile,
} from '../store/FileManagement.store';

const generateUid = (): string =>
  `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

export const toSingleUploadFile = (
  input: UploadFile[] | File[] | FileList,
  id: number,
  type: GXFileType,
  userId?: number | string,
  onUploadSuccess?: (file: GXUploadFile) => void | Promise<void>,
  useOperationalDataEndpoint?: boolean,
): GXUploadFile | null => {
  if (Array.isArray(input)) {
    if (input.length === 0) return null;
    const lastItem = input[input.length - 1] as unknown;
    if (lastItem instanceof File) {
      const file = lastItem as File;
      return {
        uid: generateUid(),
        name: file.name,
        status: 'uploading',
        gxId: id,
        gxType: type,
        userId,
        onUploadSuccess,
        useOperationalDataEndpoint,
      };
    }
    const upload = lastItem as UploadFile;
    return {
      ...(upload as UploadFile),
      uid: upload.uid ?? generateUid(),
      status: 'uploading',
      gxId: id,
      gxType: type,
      userId,
      onUploadSuccess,
      useOperationalDataEndpoint,
    } as GXUploadFile;
  }
  const list = Array.from(input as FileList);
  if (list.length === 0) return null;
  const file = list[list.length - 1];
  return {
    uid: generateUid(),
    name: file.name,
    status: 'uploading',
    gxId: id,
    gxType: type,
    userId,
    onUploadSuccess,
    useOperationalDataEndpoint,
  };
};

export const toSingleDownloadFile = (
  id: string,
  name: string,
  type: GXFileType,
  userId?: number | string,
  useOperationalDataEndpoint?: boolean,
): GXDownloadFile | null => {
  return {
    uid: generateUid(),
    name: name,
    status: 'uploading',
    gxId: id,
    gxType: type,
    userId,
    useOperationalDataEndpoint,
  };
};

export const uploadFile = async (
  files: UploadFile[] | File[] | FileList,
  id: number,
  type: GXFileType,
  userId?: number | string,
  onUploadSuccess?: (file: GXUploadFile) => void | Promise<void>,
  useOperationalDataEndpoint?: boolean,
): Promise<void> => {
  const newFile = toSingleUploadFile(
    files,
    id,
    type,
    userId,
    onUploadSuccess,
    useOperationalDataEndpoint,
  );
  if (!newFile) return;

  useFileManagementStore.setState((state) => {
    const withoutSameKey = state.fileManagement.filter(
      (f) => !(f.gxId === id && f.gxType === type),
    );
    return {
      fileManagement: [...withoutSameKey, newFile],
      isVisible: true,
    };
  });
};

export const updateListFile = async ({
  id_file,
  status,
  type,
  progress,
}: {
  id_file: number;
  status: UploadFileStatus | string;
  type?: GXFileType;
  progress?: number;
}): Promise<void> => {
  const newStatus = status as UploadFileStatus;
  useFileManagementStore.setState((state) => {
    if (type) {
      return {
        fileManagement: state.fileManagement.map((file) =>
          file.gxId === id_file && file.gxType === type
            ? { ...file, status: newStatus, progress }
            : file,
        ),
      };
    }

    const candidates = state.fileManagement.filter((f) => f.gxId === id_file);
    if (candidates.length !== 1) {
      return { fileManagement: state.fileManagement };
    }
    const targetUid = candidates[0].uid;
    return {
      fileManagement: state.fileManagement.map((file) =>
        file.uid === targetUid ? { ...file, status: newStatus, progress } : file,
      ),
    };
  });
};

export const addListDownloadFile = async ({
  id_file,
  name,
  type,
  userId,
  useOperationalDataEndpoint,
}: {
  id_file: string;
  name: string;
  type: GXFileType;
  userId?: number | string;
  useOperationalDataEndpoint?: boolean;
}): Promise<void> => {
  const newFile = toSingleDownloadFile(
    id_file,
    name,
    type,
    userId,
    useOperationalDataEndpoint,
  );
  if (!newFile) return;
  useFileManagementStore.setState((state) => {
    const withoutSameKey = state.downloadFileManagement.filter(
      (f) => !(f.gxId === id_file && f.gxType === type),
    );
    return {
      downloadFileManagement: [...withoutSameKey, newFile],
      isVisible: true,
    };
  });
};

export const updateListDownloadFile = async ({
  id_file,
  status,
  type,
  progress,
}: {
  id_file: string;
  status: UploadFileStatus | string;
  type: GXFileType;
  progress?: number;
}): Promise<void> => {
  const newStatus = status as UploadFileStatus;

  useFileManagementStore.setState((state) => {
    return {
      downloadFileManagement: state.downloadFileManagement.map((file) => {
        return file.gxId === id_file && file.gxType === type
          ? { ...file, status: newStatus, progress }
          : file;
      }),
    };
  });
};

export const removeFile = async (
  id: number | string,
  type: GXFileType,
): Promise<void> => {
  useFileManagementStore.setState((state) => {
    if (
      type === 'downloadFileAll' ||
      type === 'downloadFileDrone' ||
      type === 'downloadFileRobot' ||
      type === 'downloadSurveillanceAnalysis'
    ) {
      return {
        downloadFileManagement: state.downloadFileManagement.filter(
          (file) => !(file.gxId === id && file.gxType === type),
        ),
      };
    }
    return {
      fileManagement: state.fileManagement.filter(
        (file) => !(file.gxId === id && file.gxType === type),
      ),
    };
  });
};

export const addTaskIdToFile = async (
  taskId: string,
  gxId: number | string,
  type: GXFileType,
  taskType: string | 'download' | 'upload',
): Promise<void> => {
  useFileManagementStore.setState((state) => {
    if (taskType === 'download') {
      return {
        downloadFileManagement: state.downloadFileManagement.map((file) =>
          file.gxId === gxId.toString() && file.gxType === type
            ? { ...file, taskId: taskId }
            : file,
        ),
      };
    } else {
      return {
        fileManagement: state.fileManagement.map((file) =>
          file.gxId === gxId && file.gxType === type
            ? { ...file, taskId: taskId }
            : file,
        ),
      };
    }
  });
};
