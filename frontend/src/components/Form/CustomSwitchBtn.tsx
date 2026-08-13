import { Switch, ConfigProvider } from 'antd';
import { Controller, Control, FieldValues, Path } from 'react-hook-form';
import { useTheme } from 'rj-core';

import Colors from '../../configs/Colors';
import './CustomSwitchBtn.scss';

interface CustomSwitchBtnProps<T extends FieldValues> {
  name: Path<T>;
  control: Control<T>;
  label?: string;
  required?: boolean;
  disabled?: boolean;
  onChange?: (checked: boolean) => void;
  style?: React.CSSProperties;
  className?: string;
  isHorizontal?: boolean;
  height?: number;
}

export const CustomSwitchBtn = <T extends FieldValues>({
  name,
  control,
  label,
  required = false,
  disabled = false,
  onChange: customOnChange,
  style,
  className,
  isHorizontal = false,
}: CustomSwitchBtnProps<T>): React.JSX.Element => {
  const [theme] = useTheme();

  return (
    <div
      className={`custom-switch-btn ${isHorizontal ? 'custom-switch-btn--horizontal' : ''}`}
    >
      {label && (
        <label className={`custom-switch-btn__label ${theme}`}>
          {label} {required && <span style={{ color: Colors.Red }}>*</span>}
        </label>
      )}
      <ConfigProvider
        theme={{
          components: {
            Switch: {
              colorPrimary: Colors.Primary,
              trackPadding: 4,
              handleSize: 12,
              trackHeight: 20,
            },
          },
        }}
      >
        <Controller
          name={name}
          control={control}
          render={({ field }) => (
            <Switch
              {...field}
              checked={field.value}
              disabled={disabled}
              onChange={(checked) => {
                field.onChange(checked);
                customOnChange?.(checked);
              }}
              style={{
                ...style,
                marginLeft: '8px',
                marginRight: '27px',
              }}
              className={`custom-switch-disabled ${theme} ${className}`}
            />
          )}
        />
      </ConfigProvider>
    </div>
  );
};
