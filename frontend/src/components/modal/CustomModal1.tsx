import React from 'react';
import Modal from 'react-bootstrap/Modal';
import { FormBlock, useTheme } from 'rj-core';

import './CustomModal1.scss';

const CustomModal1 = ({
  title,
  show,
  onHide,
  id,
  closeButton = true,
  children,
  isOpacity,
  ...props
}: {
  title: string;
  show: boolean;
  onHide: () => void;
  id: string;
  closeButton?: boolean;
  children: React.ReactNode;
  isOpacity: boolean;
}) => {
  const [theme] = useTheme();

  return (
    <Modal
      className={`${isOpacity && 'opacity-50'} custom-modal modal-${theme === 'dark' ? 'black' : 'light'}`}
      id={id}
      show={show}
      onHide={onHide}
      centered
      {...props}
    >
      <Modal.Header closeButton={closeButton}>
        <Modal.Title>{title}</Modal.Title>
      </Modal.Header>
      <FormBlock>{children}</FormBlock>
    </Modal>
  );
};

export default CustomModal1;
