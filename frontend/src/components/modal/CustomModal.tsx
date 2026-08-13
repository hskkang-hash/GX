import { Close } from '@mui/icons-material';
import {
  Box,
  Dialog,
  DialogActions,
  DialogContent,
  type DialogProps,
  DialogTitle,
  Grid,
  IconButton,
} from '@mui/material';
import { forwardRef, useCallback, useImperativeHandle, useState } from 'react';
import { CustomButton } from 'rj-core';

import Colors from '../../configs/Colors';

type Props = {
  title: string;
  btnVariant?: 'outlined' | 'contained';
  content?: string | React.ReactNode;
  maxWidth?: DialogProps['maxWidth'];
  fullWidth?: boolean;
  width?: string;
  widthLimit?: number;
  confirmFn?: () => void;
  cancelFn?: () => void;
  onClose?: () => void;
  confirmText?: string;
  cancelText?: string;
  disableConfirm?: boolean;
};

export interface ModalRef {
  open: () => void;
  close: () => void;
}

const CustomModal = forwardRef<ModalRef, Props>(
  (
    {
      onClose,
      cancelFn,
      confirmFn,
      title,
      content,
      width,
      maxWidth,
      fullWidth,
      widthLimit,
      confirmText,
      cancelText,
      btnVariant = 'contained',
      disableConfirm = false,
    },
    ref,
  ) => {
    const [isOpen, setIsOpen] = useState(false);

    const handleClose = useCallback(() => {
      if (cancelFn) {
        cancelFn();
      }
      if (onClose) {
        onClose();
      }

      setIsOpen(false);
    }, [cancelFn, onClose]);

    const handleConfirm = useCallback(() => {
      if (confirmFn) {
        confirmFn();
      }

      setIsOpen(false);
    }, [confirmFn]);

    useImperativeHandle(ref, () => ({
      open: () => setIsOpen(true),
      close: () => setIsOpen(false),
    }));

    return (
      <Dialog
        sx={{
          '.MuiDialog-container': {
            // maxWidth: maxWidth,
          },
          '.MuiDialog-paper': {
            width: width,
            maxWidth: widthLimit,
            borderRadius: '0.8rem',
            padding: '1rem 1rem',
          },
        }}
        open={isOpen}
        onClose={handleClose}
      >
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <DialogTitle sx={{ p: 0, fontWeight: 600 }}>{title}</DialogTitle>
          <IconButton
            aria-label="close"
            onClick={handleClose}
            disableRipple
            sx={{
              // position: "absolute",
              // right: 8,
              // top: 8,
              color: (theme) => theme.palette.grey[500],
              '&:hover': {
                backgroundColor: 'transparent',
              },
              '&:focus': {
                backgroundColor: 'transparent',
                outline: 'none',
                border: 'none',
              },
            }}
          >
            <Close />
          </IconButton>
        </Box>
        <DialogContent sx={{ p: 0, mt: '1rem' }}>{content}</DialogContent>
        <DialogActions sx={{ p: 0, mt: '1.5rem' }}>
          <Grid
            className="w-full"
            container
            justifyContent="center"
            spacing={2}
          >
            <Grid size={6}>
              <CustomButton
                onClick={handleConfirm}
                buttonVariant={btnVariant}
                disabled={disableConfirm}
                text={confirmText ?? 'Yes'}
              />
            </Grid>
            <Grid size={6}>
              <CustomButton
                onClick={handleClose}
                buttonVariant="outlined"
                color={Colors.Red}
                text={cancelText ?? 'No'}
              />
            </Grid>
          </Grid>
        </DialogActions>
      </Dialog>
    );
  },
);
export default CustomModal;
