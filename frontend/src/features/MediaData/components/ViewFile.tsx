import { Close } from '@mui/icons-material';
import { Box, IconButton } from '@mui/material';
import { Modal } from 'antd';
import React from 'react';

import FileTypeFile from '@/assets/images/FileTypeFile';
import PlayVideoModal from '@/components/modal/PlayVideoModal';

interface ViewFileProps {
  link: string;
  type: 'video' | 'image' | 'pdf' | 'docx' | 'ppt' | 'pptx';
  isOpen: boolean;
  onClose: () => void;
}

export const ViewFile = ({
  link,
  type,
  isOpen,
  onClose,
}: ViewFileProps): React.JSX.Element | null => {
  if (!link || !isOpen) {
    return null;
  }

  if (type === 'video') {
    return (
      <PlayVideoModal
        videoUrl={link}
        open={isOpen}
        onClose={onClose}
      />
    );
  }

  if (type === 'image') {
    return (
      <Modal
        open={isOpen}
        onCancel={onClose}
        centered
        closable={false}
        width="90rem"
        footer={null}
        styles={{
          body: {
            border: 0,
            padding: 0,
          },
          content: {
            backgroundColor: 'transparent',
            padding: 0,
            boxShadow: 'none',
          },
        }}
      >
        <Box
          sx={{
            width: '100%',
            height: '100%',
            bgcolor: 'transparent',
            outline: 'none',
            padding: 0,
            position: 'relative',
          }}
        >
          <IconButton
            onClick={onClose}
            sx={{
              position: 'absolute',
              top: '-10%',
              right: '-100px',
              color: 'white',
              zIndex: 1,
            }}
          >
            <Close />
          </IconButton>
          <img
            src={link}
            alt="Preview"
            style={{
              width: '100%',
              height: 'auto',
              borderRadius: '8px',
              maxHeight: '80vh',
              objectFit: 'contain',
            }}
          />
        </Box>
      </Modal>
    );
  }

  if (type === 'pdf') {
    return (
      <Modal
        open={isOpen}
        onCancel={onClose}
        centered
        closable={false}
        width="90rem"
        footer={null}
        styles={{
          body: {
            border: 0,
            padding: 0,
            height: '80vh',
          },
          content: {
            backgroundColor: 'transparent',
            padding: 0,
            boxShadow: 'none',
          },
        }}
      >
        <Box
          sx={{
            width: '100%',
            height: '100%',
            bgcolor: 'transparent',
            outline: 'none',
            padding: 0,
            position: 'relative',
          }}
        >
          <IconButton
            onClick={onClose}
            sx={{
              position: 'absolute',
              top: '-10%',
              right: '-100px',
              color: 'white',
              zIndex: 1,
            }}
          >
            <Close />
          </IconButton>
          <iframe
            src={`${link}#toolbar=0`}
            style={{
              width: '100%',
              height: '100%',
              border: 'none',
              borderRadius: '8px',
            }}
            title="PDF Preview"
          />
        </Box>
      </Modal>
    );
  }

  if (type === 'docx' || type === 'ppt' || type === 'pptx') {
    return (
      <Modal
        open={isOpen}
        onCancel={onClose}
        centered
        closable={false}
        width="90rem"
        footer={null}
        styles={{
          body: {
            border: 0,
            padding: 0,
          },
          content: {
            backgroundColor: 'transparent',
            padding: 0,
            boxShadow: 'none',
          },
        }}
      >
        <Box
          sx={{
            width: '100%',
            height: '100%',
            bgcolor: 'transparent',
            outline: 'none',
            padding: 0,
            position: 'relative',
          }}
        >
          <IconButton
            onClick={onClose}
            sx={{
              position: 'absolute',
              top: '-10%',
              right: '-100px',
              color: 'white',
              zIndex: 1,
            }}
          >
            <Close />
          </IconButton>
          <Box
            sx={{
              width: '100%',
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '2rem',
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              borderRadius: '8px',
              color: 'white',
            }}
          >
            <FileTypeFile color="white" />
            <p style={{ marginTop: '1rem' }}>
              Document preview not available. Please download to view.
            </p>
            <a
              href={link}
              download
              style={{
                marginTop: '1rem',
                color: '#4a90e2',
                textDecoration: 'underline',
                cursor: 'pointer',
              }}
            >
              Download Document
            </a>
          </Box>
        </Box>
      </Modal>
    );
  }

  return null;
};
