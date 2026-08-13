import {
  FormControl,
  FormControlLabel,
  Radio,
  RadioGroup,
} from '@mui/material';
import React from 'react';
import { Control, Controller } from 'react-hook-form';
import { useTheme } from 'rj-core';

import Colors from '../../configs/Colors';
import './CustomRadio.scss';

interface RadioOption {
  value: string | number | boolean;
  label: string;
}

interface CustomRadioProps {
  name: string;
  control: Control<any>;
  label?: string;
  options: RadioOption[];
  disabled?: boolean;
  row?: boolean;
  required?: boolean;
  customOnChange?: (value: string | number | boolean) => void;
  onchange?: (value: string | number | boolean) => void;
  minWidthStyle?: string;
}

const CustomRadio: React.FC<CustomRadioProps> = ({
  name,
  control,
  label,
  required = false,
  options,
  disabled = false,
  row = false,
  minWidthStyle,
  onchange,
  customOnChange = () => {},
}) => {
  const [theme] = useTheme();
  return (
    <Controller
      name={name}
      control={control}
      defaultValue=""
      render={({ field: { onChange, value } }) => (
        <FormControl
          component="fieldset"
          disabled={disabled}
        >
          {label && (
            <label className={`custom-radio__label ${theme}`}>
              {label} {required && <span style={{ color: Colors.Red }}>*</span>}
            </label>
          )}
          <RadioGroup
            row={row}
            value={value}
            onChange={(e) => {
              if (disabled) return;
              onChange(e.target.value);
              if (customOnChange) {
                customOnChange(e.target.value);
              }
              if (onchange) {
                onChange(e.target.value);
              }
            }}
          >
            {options.map((option) => (
              <FormControlLabel
                className={`custom-radio__form-control ${theme}`}
                sx={{
                  width: minWidthStyle,
                }}
                key={String(option.value)}
                value={option.value}
                control={
                  <Radio
                    disabled={disabled}
                    className={`custom-radio__radio ${theme}`}
                  />
                }
                label={option.label}
              />
            ))}
          </RadioGroup>
        </FormControl>
      )}
    />
  );
};

export default CustomRadio;
