import { Image, Tooltip } from 'antd';
import React, { useEffect, useRef, useState } from 'react';
import { Control, Controller, useWatch } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { BsX } from 'react-icons/bs';
import { HiOutlineTrash } from 'react-icons/hi2';
import { IoEyeOutline } from 'react-icons/io5';
import { useTheme } from 'rj-core';

import ErrorImage from '@/assets/images/no-image-gray.png';

import './CustomFileInput.scss';

interface CustomFileInputProps {
  name: string;
  control: Control<Record<string, unknown>>;
  label?: string;
  onFileRemove?: (file: File | null) => void;
  fullWidthPreview?: boolean;
  showNoImage?: boolean;
  showFile?: boolean;
  typeAccept?: string;
  description?: string;
  multiple?: boolean;
}

const CustomFileInput: React.FC<CustomFileInputProps> = ({
  name,
  control,
  label,
  onFileRemove,
  typeAccept = 'image/*',
  fullWidthPreview = false,
  showNoImage = false,
  showFile = false,
  description,
  multiple = false,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [displayImage, setDisplayImage] = useState<string>('');
  const [inputValue, setInputValue] = useState<File | File[] | string>('');
  const [previewImage, setPreviewImage] = useState<string>('');
  const [previewOpen, setPreviewOpen] = useState<boolean>(false);
  const [theme] = useTheme();
  const { t } = useTranslation();

  const watchedValue = useWatch({
    control,
    name,
  });

  useEffect(() => {
    if (watchedValue !== undefined && watchedValue !== inputValue) {
      setInputValue(watchedValue as File | File[] | string);
    }
  }, [watchedValue, inputValue]);

  useEffect(() => {
    if (inputValue instanceof File) {
      const imageUrl = URL.createObjectURL(inputValue);
      setDisplayImage(imageUrl);
    } else if (Array.isArray(inputValue) && inputValue.length > 0) {
      // For multiple files, display file count
      const fileCount = inputValue.length;
      const fileText = fileCount === 1 ? t('file selected') : t('files selected');
      setDisplayImage(`${fileCount} ${fileText}`);
    } else if (typeof inputValue === 'string' && inputValue !== '') {
      // const transInputValue = inputValue.includes("media") ? import.meta.env.VITE_API_URL + inputValue.replace(/^\/+/, "") : import.meta.env.VITE_API_URL + inputValue;
      setDisplayImage(inputValue);
    } else {
      setDisplayImage('');
    }
  }, [inputValue, t]);

  const handleFileChange = (
    files: File | File[] | null,
    onChange: (value: File | File[] | null) => void,
  ) => {
    if (files) {
      onChange(files);
      setInputValue(files);
    }
  };

  const handleFileRemove = (
    onChange: (value: File | File[] | null) => void,
  ) => {
    if (onFileRemove) {
      onFileRemove(null);
    }
    setDisplayImage('');
    setInputValue('');
    onChange(null);
    // Reset the file input value so the same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <Controller
      name={name}
      control={control}
      defaultValue=""
      render={({ field: { onChange } }) => {
        return (
          <div className={`custom-file-input ${theme}`}>
            {label && (
              <label
                htmlFor="file-input"
                className="custom-file-input__label"
              >
                {label}
              </label>
            )}
            <div className="custom-file-input__input-container">
              <div
                className="custom-file-input__input-container-left cursor-pointer"
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  type="text"
                  className="custom-file-input__text-input cursor-pointer"
                  placeholder={t('Select')}
                  value={displayImage || ''}
                  readOnly
                />
              </div>
              <button
                type="button"
                className="custom-file-input__browse-button"
                onClick={() => fileInputRef.current?.click()}
              >
                {t('Browse File')}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept={typeAccept}
                multiple={multiple}
                className="custom-file-input__file-input"
                onChange={(e) => {
                  if (multiple) {
                    const files = e.target.files
                      ? Array.from(e.target.files)
                      : null;
                    handleFileChange(files, onChange);
                  } else {
                    const file = e.target.files?.[0] || null;
                    handleFileChange(file, onChange);
                  }
                }}
                hidden
              />
            </div>
            {description && (
              <p className="custom-file-input__description">{description}</p>
            )}

            {showNoImage && (
              <div
                className={`custom-file-input__preview ${
                  fullWidthPreview ? 'full-width-preview' : ''
                }`}
              >
                <img
                  src={displayImage || ErrorImage}
                  className="custom-file-input__preview-image"
                  // alt="preview"
                />
                {displayImage && (
                  <div className="custom-file-input__preview-overlay">
                    <div className="custom-file-input__preview-actions">
                      <IoEyeOutline
                        className="custom-file-input__preview-icon"
                        onClick={() => {
                          setPreviewImage(displayImage);
                          setPreviewOpen(true);
                        }}
                      />
                      <HiOutlineTrash
                        className="custom-file-input__preview-icon"
                        onClick={() => handleFileRemove(onChange)}
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            {displayImage && showFile && (
              <div
                className="mt-3"
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))',
                  gap: '0.75rem',
                }}
              >
                {Array.isArray(inputValue) ? (
                  inputValue.map((file, index) => (
                    <div
                      key={index}
                      className="d-flex align-items-center justify-content-between"
                      style={{
                        backgroundColor:
                          theme === 'dark' ? '#2D2E30' : '#F2F2F2',
                        borderRadius: '0.5rem',
                        padding: '0.75rem 1rem',
                      }}
                    >
                      <Tooltip
                        title={file.name}
                        placement="top"
                        zIndex={9999}
                      >
                        <p
                          className="mb-0"
                          style={{
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            fontSize: '0.875rem',
                            cursor: 'pointer',
                          }}
                        >
                          {file.name}
                        </p>
                      </Tooltip>
                      <BsX
                        size={24}
                        className="cursor-pointer"
                        style={{ flexShrink: 0, marginLeft: '0.5rem' }}
                        onClick={() => {
                          const newFiles = inputValue.filter(
                            (_, i) => i !== index,
                          );
                          if (newFiles.length === 0) {
                            handleFileRemove(onChange);
                          } else {
                            onChange(newFiles);
                            setInputValue(newFiles);
                          }
                        }}
                      />
                    </div>
                  ))
                ) : (
                  <div
                    className="d-flex align-items-center justify-content-between"
                    style={{
                      backgroundColor: theme === 'dark' ? '#1F1F20' : '#F2F2F2',
                      borderRadius: '0.5rem',
                      padding: '0.75rem 1rem',
                    }}
                  >
                    <Tooltip
                      title={inputValue && (inputValue as File).name}
                      placement="top"
                      zIndex={9999}
                    >
                      <p
                        className="mb-0"
                        style={{
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          fontSize: '0.875rem',
                        }}
                      >
                        {inputValue && (inputValue as File).name}
                      </p>
                    </Tooltip>
                    <BsX
                      size={24}
                      className="cursor-pointer"
                      style={{ flexShrink: 0, marginLeft: '0.5rem' }}
                      onClick={() => handleFileRemove(onChange)}
                    />
                  </div>
                )}
              </div>
            )}

            {previewImage && (
              <Image
                wrapperStyle={{ display: 'none' }}
                preview={{
                  visible: previewOpen,
                  onVisibleChange: (visible) => setPreviewOpen(visible),
                  afterOpenChange: (visible) => !visible && setPreviewImage(''),
                }}
                src={previewImage}
              />
            )}
          </div>
        );
      }}
    />
  );
};
export default CustomFileInput;
