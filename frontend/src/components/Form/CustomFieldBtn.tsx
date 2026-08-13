import { Box, Button } from '@mui/material';
import { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ToastTopHelper, useTheme } from 'rj-core';

import Colors from '@/configs/Colors';

import PlayVideoModal from '../modal/PlayVideoModal';

type actionType = 'download' | 'upload' | 'view';

const CustomFieldBtn = ({
  label,
  icon,
  onClick,
  action,
  downloadUrl,
  acceptFileType,
  videoUrl,
  isDisabled = false,
}: {
  label?: string;
  icon: React.ReactNode;
  onClick: (value?: FileList) => void;
  action?: actionType;
  downloadUrl?: string;
  videoUrl?: string;
  acceptFileType?: string[];
  isDisabled?: boolean;
}) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const { t } = useTranslation();
  const [isVideoModalOpen, setIsVideoModalOpen] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    console.log('acceptFileType', acceptFileType);
    const files = e.target.files;
    if (!files) return;
    for (const file of files) {
      const fileExtension = file.name.split('.').pop()?.toLowerCase();
      const formatAcceptFileType = acceptFileType?.map((item) =>
        item.replace('.', ''),
      );
      if (!fileExtension || !formatAcceptFileType?.includes(fileExtension)) {
        ToastTopHelper.error(
          t('Just accept file type:') + ' ' + acceptFileType?.join(', '),
        );
        e.target.value = '';
        return;
      }
    }
    onClick(files);
    // Reset the input so selecting the same file again triggers onChange
    e.target.value = '';
  };

  const handleDownload = async () => {
    try {
      if (!downloadUrl) return;
      const response = await fetch(downloadUrl);
      if (!response.ok) throw new Error('Cannot download file');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = downloadUrl.split('/').pop() || 'downloaded-file';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error download file:', error);
    }
  };

  const handleViewVideo = () => {
    if (!videoUrl) return;
    console.log('Click view video', videoUrl);
    setIsVideoModalOpen(true);
  };

  const handleCloseVideoModal = () => {
    setIsVideoModalOpen(false);
  };

  const [theme] = useTheme();

  return (
    <div>
      <input
        type="file"
        ref={inputRef}
        hidden
        accept={acceptFileType?.join(',')}
        // multiple
        onChange={handleFileChange}
      />
      <Button
        sx={{
          gap: '8px',
          display: 'flex',
          fontWeight: '600',
          borderRadius: '8px',
          fontSize: '0.75rem',
          width: 'fit-content',
          alignItems: 'center',
          textTransform: 'none',
          padding: '0.2rem 0.75rem',
          border: `1px solid ${isDisabled ? (theme === 'dark' ? Colors.Gray7 : Colors.Gray4) : 'var(--ga-primary)'}`,
          color: isDisabled ? Colors.Gray5 : 'var(--ga-light-theme-font-color)',
          backgroundColor: 'var(--ga-light-theme-background-color)',
          cursor: isDisabled ? 'not-allowed' : 'pointer',
          minWidth: 'fit-content',
        }}
        disabled={isDisabled}
        onClick={() => {
          if (action === 'upload') {
            // Ensure same-file selections trigger onChange by resetting value before opening dialog
            if (inputRef.current) inputRef.current.value = '';
            inputRef.current?.click();
          } else if (action === 'download') {
            handleDownload();
          } else if (action === 'view') {
            handleViewVideo();
          } else {
            onClick();
          }
        }}
      >
        <Box sx={{ color: isDisabled ? Colors.Gray5 : 'var(--ga-primary)' }}>
          {icon}
        </Box>
        {label && (
          <Box
            sx={{
              fontSize: '1rem',
              fontWeight: '600',
              color: isDisabled ? Colors.Gray5 : 'var(--ga-primary)',
              textWrap: 'nowrap',
            }}
          >
            {label}
          </Box>
        )}
      </Button>

      {videoUrl && (
        <PlayVideoModal
          videoUrl={videoUrl}
          open={isVideoModalOpen}
          onClose={handleCloseVideoModal}
        />
      )}
    </div>
  );
};

export default CustomFieldBtn;
