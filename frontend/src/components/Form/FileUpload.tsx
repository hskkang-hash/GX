// components/CustomFileInput.tsx
import { Button, styled, TextField } from '@mui/material';
import { Image, UploadFile } from 'antd';
import { useRef, useState } from 'react';
import { Control, Controller } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { IoTrashOutline } from 'react-icons/io5';
import { useTheme } from 'rj-core';

import FileTypeFile from '../../assets/images/FileTypeFile';
import FileTypeImage from '../../assets/images/FileTypeImage';
import Colors from '../../configs/Colors';
import CustomBtn from '../buttons/CustomBtn';
import './FileUpload.scss';

type Props = {
  name: string;
  control: Control<any>;
  label?: string;
  isRequired?: boolean;
  fileType?: string;
  onFileRemove?: (file: CustomFile) => void;
};

interface CustomFile extends File {
  file_type?: string;
  file_url?: string;
  file_name?: string;
}

const StyledLabel = styled('label')<{
  error?: boolean;
  mode: 'light' | 'dark';
}>(({ mode, error }) => ({
  fontSize: '1rem',
  fontWeight: 600,
  color: mode === 'dark' ? Colors.Gray3 : Colors.Gray7,
  marginBottom: '8px',
}));

const StyledTextField = styled(TextField)(({ theme, disabled }) => ({
  '& .MuiOutlinedInput-root': {
    borderRadius: '8px',
    backgroundColor: disabled
      ? theme.palette.mode === 'dark'
        ? Colors.Gray7
        : Colors.Gray2
      : theme.palette.mode === 'dark'
        ? Colors.Black
        : Colors.White,
    '& fieldset': {
      borderColor: theme.palette.mode === 'dark' ? Colors.Gray7 : Colors.Gray4,
      borderWidth: '1px',
    },
    '&:hover fieldset': {
      borderColor: disabled
        ? theme.palette.mode === 'dark'
          ? Colors.Gray7
          : Colors.Gray4
        : theme.palette.primary.main,
    },
    '&.Mui-focused fieldset': {
      borderColor: theme.palette.primary.main,
      borderWidth: '1px',
    },
    '&.Mui-error fieldset': {
      borderColor: Colors.Red,
    },
    '&.Mui-error:hover fieldset': {
      borderColor: disabled
        ? theme.palette.mode === 'dark'
          ? Colors.Gray7
          : Colors.Gray2
        : Colors.Red,
    },
    '&.Mui-error.Mui-focused fieldset': {
      borderColor: Colors.Red,
    },
  },
  '& .MuiOutlinedInput-input': {
    padding: '12px 16px',
    fontSize: '0.875rem',
    color: theme.palette.mode === 'dark' ? Colors.Gray1 : Colors.PrimaryText,
    '&::placeholder': {
      color: theme.palette.mode === 'dark' ? Colors.Gray6 : Colors.Gray5,
      opacity: 1,
    },
  },
  '& .MuiFormHelperText-root': {
    margin: '4px 0 0',
    fontSize: '0.75rem',
    color: Colors.Red,
  },
}));

const StyledButton = styled(Button)(({ theme }) => ({
  height: '45px',
  marginLeft: '8px',
  borderRadius: '8px',
  textTransform: 'none',
  fontSize: '0.875rem',
  fontWeight: 400,
  padding: '12px 16px',
  backgroundColor: theme.palette.mode === 'dark' ? Colors.Black : Colors.White,
  borderColor: theme.palette.mode === 'dark' ? Colors.Gray7 : Colors.Gray4,
  color: theme.palette.mode === 'dark' ? Colors.Gray1 : Colors.PrimaryText,
  '&:hover': {
    borderColor: theme.palette.primary.main,
    backgroundColor:
      theme.palette.mode === 'dark' ? Colors.Black : Colors.White,
  },
}));

export default function FileUpload({
  name,
  control,
  label,
  isRequired = false,
  fileType,
  onFileRemove,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [theme] = useTheme();
  const { t } = useTranslation();
  return (
    <Controller
      name={name}
      control={control}
      defaultValue={null}
      render={({ field: { onChange, value }, fieldState: { error } }) => {
        const handleFilesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
          const files = Array.from(e.target.files || []);
          if (fileType === 'image/*') {
            const imageFiles = files.filter((file) =>
              file.type.startsWith('image/'),
            );
            onChange([...(value || []), ...imageFiles]);
          } else {
            onChange([...(value || []), ...files]);
          }
        };

        const handleRemoveFile = (index: number) => {
          const updated = [...value];
          const removedFile = updated[index];
          updated.splice(index, 1);
          onChange(updated);
          if (removedFile?.id && onFileRemove) {
            onFileRemove(removedFile);
          }
        };

        const [previewOpen, setPreviewOpen] = useState(false);
        const [previewImage, setPreviewImage] = useState('');

        const handlePreview = async (file: CustomFile) => {
          if (file.type) {
            if (!file.type.includes('image')) return null;
            const imageUrl = URL.createObjectURL(file);
            setPreviewImage(imageUrl);
            setPreviewOpen(true);
          } else if (file.file_type) {
            if (!file.file_type.includes('image')) return null;
            // console.log('file_file_url', file.file_url);
            // const transFileUrl = file.file_url?.includes("media") ? import.meta.env.VITE_API_URL + file.file_url.replace(/^\/+/, "") : import.meta.env.VITE_API_URL + file.file_url;
            setPreviewImage(file?.file_url || '');
            setPreviewOpen(true);
          }
        };
        return (
          <div className="file-upload">
            {label && (
              <StyledLabel
                mode={theme}
                error={!!error?.message}
              >
                {label} {isRequired && <span>*</span>}
              </StyledLabel>
            )}
            <div
              style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}
            >
              {value?.length > 0 && (
                <div
                  className={`file-upload__files ${value?.length > 0 ? 'file-upload__files--has-items' : ''}`}
                >
                  {value?.map((file: CustomFile, index: number) => (
                    <div
                      key={index}
                      onClick={() => handlePreview(file)}
                      className="file-upload__file-item"
                    >
                      <>
                        <span>
                          {(file.type && file.type.includes('image')) ||
                          (file.file_type &&
                            file.file_type.includes('image')) ? (
                            <FileTypeImage
                              color={
                                theme === 'dark' ? Colors.Gray1 : Colors.Gray7
                              }
                            />
                          ) : (
                            <FileTypeFile
                              color={
                                theme === 'dark' ? Colors.Gray1 : Colors.Gray7
                              }
                            />
                          )}
                        </span>
                        <span className="file-upload__file-name">
                          {file.name || file.file_name}
                        </span>
                      </>
                      <IoTrashOutline
                        className="file-upload__trash-icon"
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

              <input
                ref={inputRef}
                type="file"
                className="file-upload__input"
                multiple
                accept={fileType ? fileType : '*/*'}
                onChange={handleFilesChange}
              />
              <CustomBtn
                outlined
                label={t('Browse Files')}
                onClick={() => inputRef.current?.click()}
              />
            </div>
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
}
