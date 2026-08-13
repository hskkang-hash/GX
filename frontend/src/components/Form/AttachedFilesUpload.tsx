import { Image } from 'antd';
import { useRef, useState } from 'react';
import { Control, Controller } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { IoClose } from 'react-icons/io5';
import { CustomBtn, CustomModal, useTheme } from 'rj-core';

import FileTypeFile from '../../assets/images/FileTypeFile';
import Colors from '../../configs/Colors';
import './AttachedFilesUpload.scss';

type Props = {
  name: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  control: Control<any>;
  label?: string;
  isRequired?: boolean;
  fileType?: string;
  onFileRemove?: (file: AttachedFile) => void;
  buttonLabel?: string;
  disabled?: boolean;
};

interface AttachedFile extends File {
  file_type?: string;
  file_url?: string;
  file_name?: string;
  id?: number;
}

export const AttachedFilesUpload = ({
  name,
  control,
  label,
  isRequired = false,
  fileType,
  onFileRemove,
  buttonLabel,
  disabled = false,
}: Props) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [theme] = useTheme();
  const { t } = useTranslation();
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewFile, setPreviewFile] = useState<AttachedFile | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string>('');
  const [iframeError, setIframeError] = useState(false);

  return (
    <Controller
      name={name}
      control={control}
      defaultValue={[]}
      render={({ field: { onChange, value } }) => {
        const fileList = (Array.isArray(value) ? value : []) as AttachedFile[];

        const handleFilesChange = (
          e: React.ChangeEvent<HTMLInputElement>,
        ): void => {
          const files = Array.from(e.target.files || []);
          if (fileType === 'image/*') {
            const imageFiles = files.filter((file) =>
              file.type.startsWith('image/'),
            );
            onChange([...fileList, ...imageFiles]);
          } else {
            onChange([...fileList, ...files]);
          }
          // Reset input để có thể chọn lại file giống nhau
          if (inputRef.current) {
            inputRef.current.value = '';
          }
        };

        const handleRemoveFile = (index: number): void => {
          const updated = [...fileList];
          const removedFile = updated[index];
          updated.splice(index, 1);
          onChange(updated);
          if (removedFile?.id && onFileRemove) {
            onFileRemove(removedFile);
          }
        };

        const getFileExtension = (fileName: string): string => {
          return fileName.split('.').pop()?.toLowerCase() || '';
        };

        const getFileType = (file: AttachedFile): string => {
          if (file.type) return file.type;
          if (file.file_type) return file.file_type;
          const fileName = file.name || file.file_name || '';
          const ext = getFileExtension(fileName);
          const mimeTypes: Record<string, string> = {
            pdf: 'application/pdf',
            doc: 'application/msword',
            docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            ppt: 'application/vnd.ms-powerpoint',
            pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            xls: 'application/vnd.ms-excel',
            xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          };
          return mimeTypes[ext] || '';
        };

        const handlePreview = (file: AttachedFile): void => {
          let url = '';

          if (file.type) {
            // File object từ input - tạo blob URL
            url = URL.createObjectURL(file);
          } else if (file.file_url) {
            // File từ server
            url = file.file_url;
          } else {
            // Không có URL để preview
            return;
          }

          // Reset iframe error và set preview file và URL
          setIframeError(false);
          setPreviewFile(file);
          setPreviewUrl(url);
          setPreviewOpen(true);
        };

        const handleClosePreview = (): void => {
          setPreviewOpen(false);
          // Cleanup object URL nếu là file local
          if (previewFile?.type && previewUrl.startsWith('blob:')) {
            URL.revokeObjectURL(previewUrl);
          }
          setPreviewFile(null);
          setPreviewUrl('');
          setIframeError(false);
        };

        const isImageFile = (file: AttachedFile): boolean => {
          const fileType = getFileType(file);
          return fileType.includes('image');
        };

        const isPdfFile = (file: AttachedFile): boolean => {
          const fileType = getFileType(file);
          return fileType === 'application/pdf';
        };

        const isOfficeFile = (file: AttachedFile): boolean => {
          const fileName = file.name || file.file_name || '';
          const ext = getFileExtension(fileName);
          return ['doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'].includes(ext);
        };

        const getOfficeViewerUrl = (fileUrl: string): string => {
          // Sử dụng Microsoft Office Online Viewer
          return `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(fileUrl)}`;
        };

        const handleDownload = async (): Promise<void> => {
          if (!previewFile || !previewUrl) return;

          const fileName =
            previewFile.name || previewFile.file_name || 'download';

          try {
            // Nếu là file từ server (không có type), fetch file và tạo blob để đảm bảo download
            if (!previewFile.type && previewFile.file_url) {
              const response = await fetch(previewUrl);
              const blob = await response.blob();
              const blobUrl = URL.createObjectURL(blob);

              const link = document.createElement('a');
              link.href = blobUrl;
              link.download = fileName;
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);

              // Cleanup blob URL sau khi download
              setTimeout(() => URL.revokeObjectURL(blobUrl), 100);
            } else {
              // File local - sử dụng blob URL trực tiếp
              const link = document.createElement('a');
              link.href = previewUrl;
              link.download = fileName;
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
            }
          } catch (error) {
            console.error('Error downloading file:', error);
            // Fallback: thử download trực tiếp
            const link = document.createElement('a');
            link.href = previewUrl;
            link.download = fileName;
            link.target = '_blank';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
          }
        };

        return (
          <div className="attached-files-upload">
            {label && (
              <label
                className="attached-files-upload__label"
                style={{
                  color: theme === 'dark' ? Colors.Gray3 : Colors.Gray7,
                  fontSize: '1rem',
                  fontWeight: 600,
                  marginBottom: '8px',
                  display: 'block',
                }}
              >
                {label} {isRequired && <span>*</span>}
              </label>
            )}
            <div className="attached-files-upload__container">
              <input
                ref={inputRef}
                type="file"
                className="attached-files-upload__input"
                multiple
                accept={fileType ? fileType : '*/*'}
                onChange={handleFilesChange}
              />
              <CustomBtn
                variant="outline"
                style={{
                  width: 'fit-content',
                }}
                type="button"
                color="primary"
                label={buttonLabel || t('Add File')}
                onClick={() => inputRef.current?.click()}
                disabled={disabled}
              />
            </div>
            {fileList.length > 0 && (
              <div className="attached-files-upload__files">
                {fileList.map((file: AttachedFile, index: number) => (
                  <div
                    key={index}
                    className="attached-files-upload__file-item"
                    onClick={() => handlePreview(file)}
                  >
                    <div className="attached-files-upload__file-content">
                      <span className="attached-files-upload__file-name">
                        {file.name || file.file_name}
                      </span>
                    </div>
                    <IoClose
                      className="attached-files-upload__trash-icon"
                      size={16}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveFile(index);
                      }}
                    />
                  </div>
                ))}
              </div>
            )}
            <CustomModal
              show={previewOpen}
              onHide={handleClosePreview}
              title={previewFile?.name || previewFile?.file_name || ''}
            >
              {previewFile && previewUrl && (
                <div className="attached-files-upload__preview">
                  {isImageFile(previewFile) ? (
                    <div
                      style={{
                        width: '80rem',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        backgroundColor:
                          theme === 'dark' ? '#1F1F20' : '#F2F2F2',
                        borderRadius: '8px',
                        padding: '1rem',
                      }}
                    >
                      <Image
                        src={previewUrl}
                        style={{
                          maxWidth: '92rem',
                          maxHeight: '70rem',
                          objectFit: 'contain',
                        }}
                        preview={false}
                      />
                      <a
                        href={previewUrl}
                        download={previewFile.name || previewFile.file_name}
                        onClick={(e) => {
                          e.preventDefault();
                          handleDownload();
                        }}
                        style={{
                          marginTop: '1rem',
                          color: Colors.Primary,
                          textDecoration: 'underline',
                          cursor: 'pointer',
                        }}
                      >
                        {t('Download File')}
                      </a>
                    </div>
                  ) : isPdfFile(previewFile) ? (
                    <div
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '1rem',
                      }}
                    >
                      {iframeError ? (
                        <div
                          style={{
                            width: '80rem',
                            height: 'calc(100vh - 200px)',
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            padding: '2rem',
                            backgroundColor:
                              theme === 'dark' ? '#1F1F20' : '#F2F2F2',
                            borderRadius: '8px',
                          }}
                        >
                          <FileTypeFile
                            color={
                              theme === 'dark' ? Colors.Gray1 : Colors.Gray7
                            }
                          />
                          <p
                            style={{
                              marginTop: '1rem',
                              color:
                                theme === 'dark' ? Colors.Gray1 : Colors.Gray7,
                            }}
                          >
                            {t(
                              'Unable to preview PDF. Please download to view.',
                            )}
                          </p>
                          <a
                            href={previewUrl}
                            download={previewFile.name || previewFile.file_name}
                            onClick={(e) => {
                              e.preventDefault();
                              handleDownload();
                            }}
                            style={{
                              marginTop: '1rem',
                              color: Colors.Primary,
                              textDecoration: 'underline',
                              cursor: 'pointer',
                            }}
                          >
                            {t('Download File')}
                          </a>
                        </div>
                      ) : (
                        <iframe
                          src={`${previewUrl}#toolbar=0`}
                          style={{
                            width: '80rem',
                            height: 'calc(100vh - 200px)',
                            border: 'none',
                            borderRadius: '8px',
                          }}
                          title="PDF Preview"
                          onError={() => setIframeError(true)}
                        />
                      )}
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'center',
                          padding: '0.5rem',
                        }}
                      >
                        <a
                          href={previewUrl}
                          download={previewFile.name || previewFile.file_name}
                          onClick={(e) => {
                            e.preventDefault();
                            handleDownload();
                          }}
                          style={{
                            color: Colors.Primary,
                            textDecoration: 'underline',
                            cursor: 'pointer',
                          }}
                        >
                          {t('Download File')}
                        </a>
                      </div>
                    </div>
                  ) : isOfficeFile(previewFile) ? (
                    previewFile.type ? (
                      // File local - không thể preview, chỉ có thể download
                      <div
                        style={{
                          width: '80rem',
                          height: 'calc(100vh - 150px)',
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          justifyContent: 'center',
                          padding: '2rem',
                          backgroundColor:
                            theme === 'dark' ? '#1F1F20' : '#F2F2F2',
                          borderRadius: '8px',
                        }}
                      >
                        <FileTypeFile
                          color={theme === 'dark' ? Colors.Gray1 : Colors.Gray7}
                        />
                        <p
                          style={{
                            marginTop: '1rem',
                            color:
                              theme === 'dark' ? Colors.Gray1 : Colors.Gray7,
                          }}
                        >
                          {t(
                            'Please upload the file first to preview Office documents',
                          )}
                        </p>
                        <a
                          href={previewUrl}
                          download={previewFile.name || previewFile.file_name}
                          onClick={(e) => {
                            if (!previewFile.type) {
                              // File từ server - cho phép download bình thường
                              return;
                            }
                            // File local - sử dụng handleDownload để đảm bảo hoạt động
                            e.preventDefault();
                            handleDownload();
                          }}
                          style={{
                            marginTop: '1rem',
                            color: Colors.Primary,
                            textDecoration: 'underline',
                            cursor: 'pointer',
                          }}
                        >
                          {t('Download File')}
                        </a>
                      </div>
                    ) : (
                      // File từ server - có thể preview bằng Office Viewer
                      <div
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '1rem',
                        }}
                      >
                        <iframe
                          src={getOfficeViewerUrl(previewUrl)}
                          style={{
                            width: '80rem',
                            height: 'calc(100vh - 200px)',
                            border: 'none',
                            borderRadius: '8px',
                          }}
                          title="Office Document Preview"
                        />
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'center',
                            padding: '0.5rem',
                          }}
                        >
                          <a
                            href={previewUrl}
                            download={previewFile.name || previewFile.file_name}
                            onClick={(e) => {
                              e.preventDefault();
                              handleDownload();
                            }}
                            style={{
                              color: Colors.Primary,
                              textDecoration: 'underline',
                              cursor: 'pointer',
                            }}
                          >
                            {t('Download File')}
                          </a>
                        </div>
                      </div>
                    )
                  ) : (
                    <div
                      style={{
                        width: '80rem',
                        height: 'calc(100vh - 150px)',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        padding: '2rem',
                        backgroundColor:
                          theme === 'dark' ? '#1F1F20' : '#F2F2F2',
                        borderRadius: '8px',
                      }}
                    >
                      <FileTypeFile
                        color={theme === 'dark' ? Colors.Gray1 : Colors.Gray7}
                      />
                      <p
                        style={{
                          marginTop: '1rem',
                          color: theme === 'dark' ? Colors.Gray1 : Colors.Gray7,
                        }}
                      >
                        {t('Preview not available for this file type')}
                      </p>
                      <a
                        href={previewUrl}
                        download={previewFile.name || previewFile.file_name}
                        onClick={(e) => {
                          e.preventDefault();
                          handleDownload();
                        }}
                        style={{
                          marginTop: '1rem',
                          color: Colors.Primary,
                          textDecoration: 'underline',
                          cursor: 'pointer',
                        }}
                      >
                        {t('Download File')}
                      </a>
                    </div>
                  )}
                </div>
              )}
            </CustomModal>
          </div>
        );
      }}
    />
  );
};
