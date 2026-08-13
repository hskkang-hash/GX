import { styled } from '@mui/material';
import React from 'react';
import { Control, Controller } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '@/configs/Colors';

import './CustomTextarea.scss';

interface CustomTextareaProps {
  name: string;
  control: Control<any>;
  label?: string;
  isRequired?: boolean;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  rows?: number;
  customOnChange?: (value: string) => void;
  enableJsonFormat?: boolean;
}

const StyledLabel = styled('label')<{
  mode: 'light' | 'dark';
  error?: boolean;
}>(({ mode, error }) => ({
  fontWeight: 600,
  fontSize: '1rem',
  color: mode === 'dark' ? Colors.Gray3 : Colors.Gray7,
  span: {
    color: error ? 'red' : 'inherit',
    marginLeft: '0.25rem',
  },
}));

const CustomTextarea: React.FC<CustomTextareaProps> = ({
  name,
  control,
  label,
  isRequired = false,
  disabled = false,
  placeholder = 'Enter text here',
  className = '',
  rows = 4,
  customOnChange = () => {},
  enableJsonFormat = false,
}) => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  // Validate JSON function với kiểm tra null
  const validateJson = (value: string): string | true => {
    if (!enableJsonFormat) return true;
    if (!value || !value.trim()) return true; // Empty is valid (let required validation handle this)

    try {
      const parsed = JSON.parse(value);

      // Kiểm tra nếu parsed value là null
      if (parsed === null) {
        return 'JSON null is not allowed. Use {} for empty object';
      }

      return true;
    } catch (error) {
      return 'Invalid JSON format';
    }
  };

  const formatJson = (value: string): string => {
    try {
      if (!value.trim()) return value;
      const parsed = JSON.parse(value);

      // Không format nếu là null
      if (parsed === null) {
        return value; // Giữ nguyên để hiển thị error
      }

      const formatted = JSON.stringify(parsed, null, 2);
      return formatted;
    } catch (error) {
      // Không format nếu JSON không hợp lệ
      console.warn('Invalid JSON format - skipping auto format');
      return value;
    }
  };

  const formatAndUpdate = (
    value: string,
    onChange: (value: string) => void,
  ) => {
    const formatted = formatJson(value);
    if (formatted !== value) {
      onChange(formatted);
      customOnChange(formatted);
    }
  };

  // Kiểm tra và thay thế null bằng {} khi user gõ
  const handleInputChange = (
    newValue: string,
    onChange: (value: string) => void,
  ) => {
    // Kiểm tra nếu user vừa gõ "null"
    if (enableJsonFormat && newValue.trim() === 'null') {
      // Tự động thay thế bằng {} (object rỗng, không phải string)
      const replacedValue = JSON.stringify({}, null, 2); // Sẽ tạo ra "{}"
      onChange(replacedValue);
      customOnChange(replacedValue);
      return;
    }

    // Nếu không phải null thì xử lý bình thường
    onChange(newValue);
    customOnChange(newValue);
  };

  const handleBlur = (
    value: string,
    onChange: (value: string) => void,
    onBlur: () => void,
  ) => {
    // Auto format JSON khi blur nếu enableJsonFormat = true và không disabled
    if (enableJsonFormat && !disabled && value.trim()) {
      formatAndUpdate(value, onChange);
    }
    onBlur();
  };

  return (
    <Controller
      name={name}
      control={control}
      defaultValue=""
      rules={{
        validate: enableJsonFormat ? validateJson : undefined,
      }}
      render={({ field, fieldState: { error } }) => {
        // Auto format khi value thay đổi và field bị disabled
        React.useEffect(() => {
          if (
            enableJsonFormat &&
            disabled &&
            field.value &&
            field.value.trim()
          ) {
            const formatted = formatJson(field.value);
            if (formatted !== field.value) {
              field.onChange(formatted);
              customOnChange(formatted);
            }
          }
        }, [field.value, disabled, enableJsonFormat]);

        return (
          <div className={`unit-input ${theme} ${className}`}>
            {label && (
              <StyledLabel
                mode={theme as 'light' | 'dark'}
                htmlFor={name}
                error={!!error}
              >
                {label}{' '}
                {isRequired && <span style={{ color: Colors.Red }}>*</span>}
              </StyledLabel>
            )}

            <div className={`unit-input__container`}>
              <textarea
                id={name}
                className={`unit-input__input ${error?.message ? 'errorUnitInput' : ''}`}
                disabled={disabled}
                placeholder={
                  enableJsonFormat
                    ? t('Enter JSON (use {} for empty object)')
                    : placeholder
                }
                rows={rows}
                value={field.value}
                onChange={(e) => {
                  const newValue = e.target.value;
                  handleInputChange(newValue, field.onChange);
                }}
                onBlur={() =>
                  handleBlur(field.value, field.onChange, field.onBlur)
                }
                name={field.name}
                ref={field.ref}
                style={{
                  height: 'unset',
                  borderRadius: '0.5rem',
                  // fontFamily: enableJsonFormat
                  //   ? "Consolas, Monaco, 'Courier New', monospace"
                  //   : "inherit",
                  // fontSize: enableJsonFormat ? "0.875rem" : "inherit",
                  // lineHeight: enableJsonFormat ? "1.4" : "inherit",
                }}
              />
            </div>
            {error?.message && (
              <div
                style={{
                  color: Colors.Red,
                  fontSize: '0.875rem',
                }}
              >
                {t(error.message)}
              </div>
            )}
          </div>
        );
      }}
    />
  );
};

export default CustomTextarea;
