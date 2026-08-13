import { Checkbox, FormControl } from '@mui/material';
import { FormControlLabel } from '@mui/material';
import React from 'react';
import { Control, Controller } from 'react-hook-form';
import { useTheme } from 'rj-core';

import './CustomCheckBox.scss';

interface CustomCheckBoxProps {
  name: string;
  control: Control<any>;
  label?: string;
  disabled?: boolean;
  subLabel?: string;
  position?: 'start' | 'end' | 'bottom';
  minWidthStyle?: string;
  onChangeValue?: (value: boolean) => void;
}
const CustomCheckBox: React.FC<CustomCheckBoxProps> = ({
  name,
  control,
  label,
  subLabel,
  disabled = false,
  position = 'end',
  minWidthStyle,
  onChangeValue,
}) => {
  const [theme] = useTheme();
  return (
    <Controller
      name={name}
      control={control}
      defaultValue={false}
      render={({ field: { onChange, value } }) => (
        <FormControl
          component="fieldset"
          disabled={disabled}
        >
          {label && (
            <label className={`custom-checkbox-label ${theme}`}>{label}</label>
          )}
          <FormControlLabel
            sx={{
              minWidth: minWidthStyle || '120px',
              '&.Mui-disabled .MuiFormControlLabel-label': {
                color: 'gray !important',
                opacity: 0.6,
              },
            }}
            control={
              <Checkbox
                className={`custom-checkbox__checkbox ${theme}`}
                checked={value}
                onChange={(e) => {
                  onChange(e.target.checked);
                  onChangeValue && onChangeValue(e.target.checked);
                }}
                disabled={disabled}
              />
            }
            label={subLabel}
            labelPlacement={position}
          />
        </FormControl>
      )}
    />
  );
};

export default CustomCheckBox;
