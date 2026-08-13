import { styled, type TextFieldProps } from '@mui/material';
import { useEffect } from 'react';
import {
  Controller,
  type FieldValues,
  type Path,
  type RegisterOptions,
  useFormContext,
} from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../configs/Colors';
import './UnitInput.scss';

const StyledInput = styled('input')(({ theme }) => ({
  '&::-webkit-inner-spin-button, &::-webkit-outer-spin-button': {
    WebkitAppearance: 'none',
    margin: 0,
  },
  '&[type=number]': {
    MozAppearance: 'textfield',
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
  formError?: any;
  negative?: boolean;
  preventDecimal?: boolean;
};

const StyledLabel = styled('label')<{
  mode: 'light' | 'dark';
  error?: boolean;
}>(({ mode, error }) => ({
  fontWeight: 600,
  fontSize: '1rem',
  color: mode === 'dark' ? Colors.Gray3 : Colors.Gray7,
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',

  span: {
    color: error ? 'red' : 'inherit',
    marginLeft: '0.25rem',
  },
}));

const TextInput = <T extends FieldValues>({
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
  formError,
  negative = false,
  preventDecimal = false,
  onChange,
  ...rest
}: Props<T>) => {
  const formContext = useFormContext();
  const { t } = useTranslation();
  const [theme, _] = useTheme();

  // Handle standalone usage (without form context)
  if (!formContext) {
    return (
      <div className={`unit-input ${theme}`}>
        {label && (
          <StyledLabel
            mode={theme as 'light' | 'dark'}
            htmlFor={name}
          >
            {label} {isRequired && <span style={{ color: 'red' }}>*</span>}
          </StyledLabel>
        )}
        <div className={`unit-input__container`}>
          <StyledInput
            className={`unit-input__input`}
            type="number"
            min={negative ? undefined : 0}
            value={value ?? ''}
            onKeyDown={(e) => {
              const allowedKeys = [
                'Backspace',
                'ArrowLeft',
                'ArrowRight',
                'Tab',
                'Delete',
                ...(preventDecimal ? [] : ['.']),
                ...(negative ? ['-'] : []),
              ];
              const isNumberKey = /^[0-9]$/.test(e.key);
              const isCtrlCmd = e.ctrlKey || e.metaKey;

              if (!isNumberKey && !allowedKeys.includes(e.key) && !isCtrlCmd) {
                e.preventDefault();
              }
              if (e.key === '-' && (e.currentTarget.selectionStart ?? 0) > 0) {
                e.preventDefault();
              }
            }}
            disabled={disabled}
            placeholder={placeholder}
            onChange={(e) => {
              const inputValue =
                e.target.value === '' ? null : parseFloat(e.target.value);
              onChange?.(inputValue);
            }}
          />
          <div className={`unit-input__unit`}>{unit && t(unit)}</div>
          {iconDivider && (
            <div className="unit-input__divider">
              {typeof iconDivider === 'string' && iconDivider.includes('to')
                ? t(iconDivider)
                : iconDivider}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Handle form context usage
  const {
    formState: { errors },
    control,
    setValue,
  } = formContext;

  const error = errors[name] || formError;

  useEffect(() => {
    if (value !== undefined) {
      setValue(name, value);
    }
  }, [value, name, setValue]);

  return (
    <Controller
      name={name}
      rules={registerOptions}
      render={({ field, fieldState }) => {
        return (
          <div className={`unit-input ${theme}`}>
            {label && (
              <StyledLabel
                mode={theme as 'light' | 'dark'}
                htmlFor={name}
                error={!!error}
              >
                {label} {isRequired && <span style={{ color: 'red' }}>*</span>}
              </StyledLabel>
            )}
            <div className={`unit-input__container`}>
              <StyledInput
                {...field}
                step="any"
                className={`unit-input__input ${
                  fieldState.error?.message || error ? 'errorUnitInput' : ''
                }`}
                type="number"
                min={negative ? undefined : 0}
                value={
                  value !== undefined
                    ? value
                    : field.value !== null && field.value !== undefined
                      ? field.value
                      : ''
                }
                onKeyDown={(e) => {
                  const allowedKeys = [
                    'Backspace',
                    'ArrowLeft',
                    'ArrowRight',
                    'Tab',
                    'Delete',
                    ...(preventDecimal ? [] : ['.']),
                    ...(negative ? ['-'] : []),
                  ];
                  const isNumberKey = /^[0-9]$/.test(e.key);
                  const isCtrlCmd = e.ctrlKey || e.metaKey;

                  if (
                    !isNumberKey &&
                    !allowedKeys.includes(e.key) &&
                    !isCtrlCmd
                  ) {
                    e.preventDefault();
                  }
                  if (
                    e.key === '-' &&
                    (e.currentTarget.selectionStart ?? 0) > 0
                  ) {
                    e.preventDefault();
                  }
                }}
                disabled={disabled}
                placeholder={placeholder}
                onChange={(e) => {
                  const inputValue =
                    e.target.value === '' ? null : parseFloat(e.target.value);
                  field.onChange(inputValue);
                  onChange?.(inputValue);
                }}
              />
              <div className={`unit-input__unit`}>{unit && t(unit)}</div>
              {iconDivider && (
                <div className="unit-input__divider">
                  {typeof iconDivider === 'string' && iconDivider.includes('to')
                    ? t(iconDivider)
                    : iconDivider}
                </div>
              )}
            </div>
            {(fieldState.error?.message || error) && !hiddenErrorMessage && (
              <div
                style={{
                  color: '#ff4d4f',
                  fontSize: '0.875rem',
                }}
              >
                {error?.message || fieldState.error?.message || ''}
              </div>
            )}
          </div>
        );
      }}
    />
  );
};

export default TextInput;
