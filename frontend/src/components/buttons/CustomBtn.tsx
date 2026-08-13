import { ReactElement } from 'react';

import './CustomBtn.scss';

interface CustomBtnProps {
  label: string;
  isFlag?: boolean;
  icon?: ReactElement;
  outlined?: boolean;
  className?: string;
  contained?: boolean;
  isCancel?: boolean;
  type?: 'button' | 'submit' | 'reset';
}

const CustomBtn: React.FC<CustomBtnProps> = ({
  label,
  isFlag = false,
  icon,
  type = 'button',
  className,
  outlined,
  contained,
  isCancel,
  ...props
}) => {
  const buttonClasses = [
    'custom-btn',
    icon ? 'with-icon' : '',
    outlined
      ? 'outlined'
      : contained
        ? 'contained'
        : isCancel
          ? 'cancel'
          : 'transparent',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      type={type}
      {...props}
      className={buttonClasses}
    >
      {isFlag ? (
        <>
          {label} {icon}
        </>
      ) : (
        <>
          {icon} {label}
        </>
      )}
    </button>
  );
};

export default CustomBtn;
