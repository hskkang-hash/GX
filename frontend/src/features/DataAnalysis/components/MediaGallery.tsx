import { Close } from '@mui/icons-material';
import { Box, IconButton } from '@mui/material';
import { Modal } from 'antd';
import React, { useState } from 'react';
import { BsPlayCircle } from 'react-icons/bs';

import FileTypeFile from '@/assets/images/FileTypeFile';
import PlayVideoModal from '@/components/modal/PlayVideoModal';
import Colors from '@/configs/Colors';

import '../assets/styles/MediaGallery.scss';

interface MediaItem {
  label: string;
  value: string;
  type?: 'video' | 'image' | 'document';
}

interface MediaGalleryProps {
  items: MediaItem[];
  theme?: 'light' | 'dark';
}

const MediaGallery: React.FC<MediaGalleryProps> = ({
  items,
  theme = 'light',
}) => {
  const [selectedVideo, setSelectedVideo] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<string | null>(null);

  const getFileType = (url: string): 'video' | 'image' | 'document' => {
    const urlLower = url.toLowerCase();
    const extension = url.split('.').pop()?.toLowerCase() || '';

    // Video types
    if (
      extension === 'mp4' ||
      extension === 'avi' ||
      extension === 'mov' ||
      extension === 'wmv' ||
      extension === 'flv' ||
      extension === 'webm' ||
      urlLower.includes('youtube') ||
      urlLower.includes('vimeo') ||
      urlLower.includes('video')
    ) {
      return 'video';
    }

    // Image types
    if (
      extension === 'jpg' ||
      extension === 'jpeg' ||
      extension === 'png' ||
      extension === 'gif' ||
      extension === 'bmp' ||
      extension === 'webp' ||
      extension === 'svg'
    ) {
      return 'image';
    }

    // Document types
    if (
      extension === 'pdf' ||
      extension === 'doc' ||
      extension === 'docx' ||
      extension === 'ppt' ||
      extension === 'pptx' ||
      extension === 'xls' ||
      extension === 'xlsx'
    ) {
      return 'document';
    }

    // Default to document if unknown
    return 'document';
  };

  const handleItemClick = (item: MediaItem) => {
    const fileType = item.type || getFileType(item.value);

    if (fileType === 'video') {
      setSelectedVideo(item.value);
    } else if (fileType === 'image') {
      setSelectedImage(item.value);
    } else if (fileType === 'document') {
      setSelectedDocument(item.value);
    }
  };

  const renderThumbnail = (item: MediaItem) => {
    const fileType = item.type || getFileType(item.value);

    if (fileType === 'video') {
      return (
        <div
          className="media-thumbnail media-thumbnail-video"
          onClick={() => handleItemClick(item)}
        >
          <div className="thumbnail-image">
            <video
              src={item.value}
              crossOrigin="anonymous"
              muted
              preload="metadata"
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
              }}
              onLoadedMetadata={(e) => {
                // Seek to first frame to show thumbnail
                const video = e.currentTarget;
                video.currentTime = 0.1;
              }}
              onError={(e) => {
                // Hide video if it fails to load
                (e.currentTarget as HTMLVideoElement).style.display = 'none';
              }}
            />
            <div className="play-overlay">
              <BsPlayCircle className="play-icon" />
            </div>
          </div>
        </div>
      );
    }

    if (fileType === 'image') {
      return (
        <div
          className="media-thumbnail media-thumbnail-image"
          onClick={() => handleItemClick(item)}
        >
          <div className="thumbnail-image">
            <img
              src={item.value}
              alt={item.label}
              crossOrigin="anonymous"
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
              }}
              onError={(e) => {
                // Fallback to a placeholder if image fails to load
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          </div>
        </div>
      );
    }

    // Document type
    return (
      <div
        className="media-thumbnail media-thumbnail-document"
        onClick={() => handleItemClick(item)}
      >
        <div className="thumbnail-image document-placeholder">
          <FileTypeFile
            color={theme === 'dark' ? Colors.Gray1 : Colors.Gray7}
          />
        </div>
      </div>
    );
  };

  return (
    <>
      <div
        className="media-gallery"
        data-theme={theme}
      >
        {items.map((item, index) => (
          <React.Fragment key={index}>{renderThumbnail(item)}</React.Fragment>
        ))}
      </div>

      {/* Video Modal */}
      {selectedVideo && (
        <PlayVideoModal
          videoUrl={selectedVideo}
          open={!!selectedVideo}
          onClose={() => setSelectedVideo(null)}
        />
      )}

      {/* Image Modal */}
      {selectedImage && (
        <Modal
          open={!!selectedImage}
          onCancel={() => setSelectedImage(null)}
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
              onClick={() => setSelectedImage(null)}
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
              src={selectedImage}
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
      )}

      {/* Document Modal */}
      {selectedDocument && (
        <Modal
          open={!!selectedDocument}
          onCancel={() => setSelectedDocument(null)}
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
              onClick={() => setSelectedDocument(null)}
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
            {selectedDocument.toLowerCase().endsWith('.pdf') ||
            selectedDocument.includes('pdf') ? (
              <iframe
                src={`${selectedDocument}#toolbar=0`}
                style={{
                  width: '100%',
                  height: '100%',
                  border: 'none',
                  borderRadius: '8px',
                }}
                title="Document Preview"
              />
            ) : (
              <div
                style={{
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
                  href={selectedDocument}
                  download
                  style={{
                    marginTop: '1rem',
                    color: '#4a90e2',
                    textDecoration: 'underline',
                  }}
                >
                  Download Document
                </a>
              </div>
            )}
          </Box>
        </Modal>
      )}
    </>
  );
};

export default MediaGallery;
