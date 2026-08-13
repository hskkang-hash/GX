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

import { formatLocalKoreanNumber } from '@/features/delivery/deliveryInquiry/utils/Setting';

import FlagKorea from '../../assets/images/korea-flag.png';
import Colors from '../../configs/Colors';
import './PhoneNumberInputV2.scss';

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
  value?: string | null;
};

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

const PhoneNumberInputV2 = <T extends FieldValues>({
  name,
  label,
  isRequired = false,
  disabled = false,
  registerOptions,
  placeholder = '010-1234-5678',
  unit,
  className = '',
  iconDivider,
  value,
  ...rest
}: Props<T>) => {
  const {
    formState: { errors },
    control,
    setValue,
  } = useFormContext();
  const error = errors[name];
  const { t } = useTranslation();
  const [theme] = useTheme();

  useEffect(() => {
    if (value !== undefined && value !== null) {
      setValue(name, value as any);
    }
  }, [value, name, setValue]);

  return (
    <Controller
      name={name}
      rules={{
        required: t('Phone number is required'),
        pattern: {
          value: /^[0-9]{10,11}$/,
          message: t('Invalid Korean phone number'),
        },
      }}
      render={({ field, fieldState }) => {
        const internalValue = field.value ?? '';
        const formattedDisplay = formatLocalKoreanNumber(internalValue);

        return (
          <div className={`phone-number-inputV2 ${theme}`}>
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

            <div
              className={`phone-number-inputV2__input ${fieldState.error?.message || error ? 'errorUnitInput' : ''}`}
            >
              <input
                {...field}
                className="phone-number-inputV2__input-input"
                style={{
                  borderRadius: '0.5rem',
                }}
                type="text"
                inputMode="numeric"
                value={formattedDisplay}
                placeholder={placeholder}
                disabled={disabled}
                onKeyDown={(e) => {
                  const allowedKeys = [
                    'Backspace',
                    'ArrowLeft',
                    'ArrowRight',
                    'Tab',
                    'Delete',
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
                }}
                onChange={(e) => {
                  const raw = e.target.value.replace(/\D/g, '').slice(0, 11);
                  let stored = raw;
                  if (raw.length > 0 && !raw.startsWith('0')) {
                    stored = '0' + raw;
                  }
                  field.onChange(stored);
                  setValue(name, stored as any, { shouldValidate: true });
                }}
              />
            </div>
            {(fieldState.error?.message || error) && (
              <div style={{ color: '#ff4d4f', fontSize: '0.875rem' }}>
                {typeof error === 'string'
                  ? error
                  : t(fieldState.error?.message || '')}
              </div>
            )}
          </div>
        );
      }}
    />
  );
};

export default PhoneNumberInputV2;
