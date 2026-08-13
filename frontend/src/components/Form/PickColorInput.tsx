import { Box, type TextFieldProps } from '@mui/material';
import { Input, ColorPicker, Typography, ConfigProvider } from 'antd';
import { useState } from 'react';
import {
  Controller,
  type FieldValues,
  type Path,
  type RegisterOptions,
  useFormContext,
} from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';
import styled, { createGlobalStyle } from 'styled-components';

import Colors from '@/configs/Colors';

const GlobalStyle = createGlobalStyle<{ theme: any }>`

.ant-select-dropdown .ant-select-item-option-selected:not(.ant-select-item-option-disabled) {
  color: #ffffff !important;
  background-color: #15325b !important; /* hoặc màu bạn muốn */
}

 .ant-color-picker-input .ant-color-picker-hex-input.ant-input-affix-wrapper .ant-input-prefix{
    color: #ffffff40 !important;
  }

  .ant-input-outlined:focus-within{
  border-color: ${Colors.Primary} !important;
    box-shadow: 0 0 0 2px #0591ff1a !important;
  }

  .ant-input-number-outlined:focus-within {
      border-color: ${Colors.Primary} !important;
    box-shadow: 0 0 0 2px #0591ff1a !important;
  }

     ${({ theme }) =>
    theme === 'dark' &&
    `
    .ant-input-number:hover .ant-input-number-handler-up-inner,
    .ant-input-number:hover .ant-input-number-handler-down-inner {
      color: #ffffff !important;
    }
  `}

    ${({ theme }) =>
    theme === 'dark' &&
    `
    /* Mũi tên ▼ trong ColorPicker Select */
    .ant-select-selector .ant-select-arrow svg {
      color: #ffffff !important;
      fill: #ffffff !important;
    }
  `}

  .ant-select .ant-select-arrow {
    color: #8c8c8c !important;
  }

`;

const ColorPickerWrapper = styled.div<{ theme: any; disabled?: boolean }>`
  .ant-color-picker-trigger {
    height: 2.975rem;
    display: flex;
    align-items: center;
    justify-content: flex-start;
    padding-left: 9px;
    border-radius: 6px;
    border: 1px solid
      ${({ theme }) => (theme === 'dark' ? Colors.Gray6 : '#d9d9d9')};
    transition: all 0.3s;
    background: ${({ theme, disabled }) =>
    disabled
      ? theme === 'dark'
        ? '#262626'
        : '#f5f5f5'
      : theme === 'dark'
        ? 'transparent'
        : 'white'};
  }

  .ant-color-picker-trigger:hover {
    border-color: ${Colors.Primary};
  }
  .ant-color-picker-trigger.ant-color-picker-trigger-active {
    border-color: ${Colors.Primary};
    box-shadow: 0 0 0 2px
      ${({ theme }) => (theme === 'dark' ? '#0591ff1a' : '#0591ff33')};
  }
`;
const darkTheme = {
  token: {
    colorBgContainer: '#1f1f1f',
    colorBorder: '#434343',
    colorText: '#ffffff',
    colorTextPlaceholder: '#8c8c8c',
    colorBgElevated: '#262626',
    colorPrimary: '#3aa0ff',
    colorError: '#ff7875',
    borderRadius: 6,
  },
  components: {
    ColorPicker: {
      colorBg: '#1f1f1f',
      colorBorder: '#434343',
      colorText: '#ffffff',
    },
    Input: {
      colorBgContainer: '#1f1f1f',
      colorText: '#ffffff',
      colorBorder: '#434343',
      colorPlaceholder: '#8c8c8c',
    },
    Select: {
      colorBgContainer: '#1f1f1f',
      colorBorder: '#434343',
      colorText: '#ffffff',
      optionSelectedBg: '#15325b',
    },
    Button: {
      colorBgContainer: '#3a3a3a',
      colorText: '#ffffff',
      colorPrimary: '#3aa0ff',
    },
  },
};

const StyledLabel = styled('label')<{
  mode: 'light' | 'dark';
  error?: boolean;
}>(({ mode, error }) => ({
  fontWeight: 600,
  fontSize: '1rem',
  color: mode === 'dark' ? Colors.Gray3 : Colors.Gray7,
  marginBottom: '0.4rem',
  span: {
    color: error ? 'red' : 'inherit',
    marginLeft: '0.25rem',
  },
}));
type Props<T> = TextFieldProps & {
  label?: string;
  name: Path<T>;
  isRequired?: boolean;
  registerOptions?: RegisterOptions<FieldValues>;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  unit?: string;
  iconDivider?: React.ReactNode;
  value?: number | null;
  onChange?: (value: number | null) => void;
  hiddenErrorMessage?: boolean;
};

const ColorInput = <T extends FieldValues>({
  name,
  label,
  isRequired = false,
  disabled = false,
  registerOptions,
  placeholder = 'Column Name',
  type,
  unit,
  hiddenErrorMessage = false,
  className = '',
  iconDivider,
  value,
  onChange,
  ...rest
}: Props<T>) => {
  const formContext = useFormContext();
  const { t } = useTranslation();
  const [theme, _] = useTheme();
  const {
    formState: { errors },
    control,
    setValue,
  } = formContext;

  const error = errors[name];

  return (
    <Controller
      name={name}
      rules={registerOptions}
      disabled={disabled}
      render={({ field, fieldState }) => {
        return (
          <div className={`unit - input ${theme} `}>
            <Box>
              {label && (
                <StyledLabel
                  mode={theme as 'light' | 'dark'}
                  htmlFor={name}
                >
                  {label}{' '}
                  {isRequired && <span style={{ color: 'red' }}>*</span>}
                </StyledLabel>
              )}
              <ConfigProvider theme={theme === 'dark' ? darkTheme : undefined}>
                <GlobalStyle theme={theme} />
                <ColorPickerWrapper
                  theme={theme}
                  disabled={disabled}
                >
                  <ColorPicker
                    {...field}
                    value={field.value || null}
                    onChange={(e) => field.onChange(e.toHexString())}
                  />
                </ColorPickerWrapper>
              </ConfigProvider>
            </Box>
            {(fieldState.error?.message || (error as any)?.message) &&
              !hiddenErrorMessage && (
                <div
                  style={{
                    color: '#ff4d4f',
                    fontSize: '0.875rem',
                  }}
                >
                  {(error as any)?.message || fieldState.error?.message || ''}
                </div>
              )}
          </div>
        );
      }}
    />
  );
};

export default ColorInput;
