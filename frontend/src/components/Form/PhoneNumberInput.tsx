import { Skeleton } from 'antd';
import { useEffect, useState } from 'react';
import { Form, InputGroup } from 'react-bootstrap';
import { Search } from 'react-bootstrap-icons';
import {
  useFormContext,
  FieldValues,
  Path,
  Controller,
  useController,
} from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import Select from 'react-select';
import MaskedInput from 'react-text-mask';
import { useTheme } from 'rj-core';

import Colors from '@/configs/Colors';
import { checkPhoneMaskType, getPhoneMaskTypeByLanguage } from '@/utils/utils';

import './PhoneNumberInput.scss';

interface MaskOption {
  value: string;
  label: string;
  flag?: string;
  type?: string;
  pattern?: any;
  maskPipe?: any;
  maskPlaceholder?: string;
}

interface PhoneNumberInputProps<T extends FieldValues = FieldValues> {
  name: Path<T>;
  loading?: boolean;
  label?: string;
  id?: string;
  error?: string;
  initialValues?: string;
  initialMask?: string;
  required?: boolean;
  description?: string;
  prefixIcon?: boolean;
  suffixIcon?: boolean;
  maxLength?: number;
  customPlaceholder?: string;
  customRequired?: boolean;
  maskOptions?: MaskOption[];
  mask?: any;
  maskPlaceholder?: string;
  pipeMask?: any;
  inputStyle?: React.CSSProperties;
  placeholder?: string;
  type?: string;
  rules?: any;
  validatePhoneByMask?: (value: string, maskType: string) => string | boolean;
}

const PhoneNumberInput = <T extends FieldValues = FieldValues>({
  name,
  loading = false,
  label,
  id,
  initialValues,
  initialMask,
  required,
  description,
  prefixIcon,
  suffixIcon,
  maxLength = 255,
  customPlaceholder,
  customRequired,
  maskOptions,
  mask,
  maskPlaceholder = '\u0058',
  pipeMask,
  inputStyle,
  placeholder,
  type,
  rules,
  validatePhoneByMask,
  ...props
}: PhoneNumberInputProps<T>) => {
  const {
    formState: { errors },
    control,
    setValue,
    watch,
  } = useFormContext<T>();
  const { t, i18n } = useTranslation();
  const [theme] = useTheme();
  const [maskOption, setMaskOption] = useState(0);
  const [userSelectedMask, setUserSelectedMask] = useState(null); // Track user's manual selection
  const { field } = useController({ name, control });

  const formatOptionLabel = ({ value, label, flag, type }: MaskOption) => {
    return (
      <div style={{ display: 'flex', alignItems: 'center' }}>
        {type === 'img' ? (
          <img
            src={flag}
            style={{ margin: '0.5em', width: '1.5em', height: '1.5em' }}
            alt={label}
          />
        ) : (
          <label>{label}</label>
        )}
      </div>
    );
  };

  const onChangeMaskOption = (option: MaskOption | null) => {
    if (option) {
      setValue(name, '' as any);
      setMaskOption(
        maskOptions?.findIndex((item) => item.value === option.value) || 0,
      );
      setValue(
        `${name.replace('phone_number', 'phoneMask')}` as Path<T>,
        option.value as any,
      );
      setUserSelectedMask(option.value as any);
    }
  };

  useEffect(() => {
    if (maskOptions && maskOptions.length > 0) {
      //If user has manually selected a mask keep it
      if (userSelectedMask) {
        const userSelectedIndex = maskOptions.findIndex(
          (item) => item.value === userSelectedMask,
        );
        if (userSelectedIndex !== -1) {
          setMaskOption(userSelectedIndex);
          return;
        }
      }

      //If there's an existing phone number detect mask from it
      if (field.value && field.value.trim() !== '') {
        const detectedMask = checkPhoneMaskType(field.value);
        const detectedIndex = maskOptions.findIndex(
          (item) => item.value === detectedMask,
        );
        if (detectedIndex !== -1) {
          setMaskOption(detectedIndex);
          return;
        }
      }

      // If initialMask is provided for edit mode
      if (initialMask) {
        const initialIndex = maskOptions.findIndex(
          (item) => item.value === initialMask,
        );
        if (initialIndex !== -1) {
          setMaskOption(initialIndex);
          return;
        }
      }

      // Use current language as default for new entries
      const currentLanguageMask = getPhoneMaskTypeByLanguage(i18n.language);
      const defaultMaskIndex = maskOptions.findIndex(
        (item) => item.value === currentLanguageMask,
      );
      if (defaultMaskIndex !== -1) {
        setMaskOption(defaultMaskIndex);
      } else {
        setMaskOption(0);
      }
    }
  }, [maskOptions, initialMask, field.value, i18n.language, userSelectedMask]);

  const defaultRules = {
    ...(required && {
      required: t('This field is required'),
    }),
    ...(validatePhoneByMask && {
      validate: {
        phoneFormat: (value: string) => {
          if (!value || value.trim() === '') return true;
          const maskType =
            watch(`${name.replace('phone_number', 'phoneMask')}` as Path<T>) ||
            maskOptions?.[maskOption]?.value ||
            'Kr';
          return validatePhoneByMask(value, maskType);
        },
      },
    }),
    ...rules,
  };

  return (
    <div className="custom-input-section">
      <div className="d-flex justify-content-between align-items-center">
        {label && (
          <Form.Label htmlFor={id}>
            {label}
            {required && <span className="asterisk"> *</span>}
          </Form.Label>
        )}
      </div>
      {loading ? (
        <Skeleton.Input
          active
          size="small"
          className="w-100"
          style={{ height: '2.975rem' }}
        />
      ) : (
        <Controller
          name={name}
          control={control}
          rules={defaultRules}
          render={({ field, fieldState: { isTouched, error } }) => (
            <>
              <InputGroup className="custom-input">
                {prefixIcon && (
                  <InputGroup.Text style={styles.prefixIcon}>
                    <Search color={Colors.Secondary} />
                  </InputGroup.Text>
                )}
                {maskOptions ? (
                  <>
                    {maskOptions && maskOptions?.length > 1 && (
                      <Select
                        className="select-input"
                        options={maskOptions}
                        onChange={onChangeMaskOption}
                        defaultValue={maskOptions?.[0]}
                        value={maskOptions?.[maskOption]}
                        formatOptionLabel={formatOptionLabel}
                        styles={selectStyles(theme)}
                      />
                    )}
                    <MaskedInput
                      mask={maskOptions?.[maskOption]?.pattern ?? false}
                      pipe={maskOptions?.[maskOption]?.maskPipe ?? false}
                      guide={true}
                      placeholderChar={maskPlaceholder}
                      value={field.value || ''}
                      onChange={(e: any) => {
                        field.onChange(e.target.value);
                      }}
                      onBlur={field.onBlur}
                      render={(ref: any, maskedProps: any) => (
                        <Form.Control
                          ref={ref}
                          {...maskedProps}
                          {...props}
                          type={type}
                          data-bs-theme={theme === 'dark' ? 'dark' : 'light'}
                          className={`${error ? 'input-error' : ''}`}
                          id={id}
                          placeholder={
                            maskOptions?.[maskOption]?.maskPlaceholder ??
                            placeholder ??
                            ''
                          }
                          maxLength={maxLength}
                          style={inputStyle}
                          required={customRequired}
                          autoComplete={
                            maskOptions?.length > 1 ? 'new-password' : 'on'
                          }
                        />
                      )}
                    />
                  </>
                ) : (
                  <Form.Control
                    {...props}
                    {...field}
                    type={type}
                    data-bs-theme={theme === 'dark' ? 'dark' : 'light'}
                    className={`${isTouched && error ? 'input-error' : ''}`}
                    id={id}
                    maxLength={maxLength}
                    style={inputStyle}
                    required={customRequired}
                    value={field.value || ''}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                      field.onChange(e.target.value);
                    }}
                    onBlur={field.onBlur}
                  />
                )}
                {customPlaceholder && (
                  <div className="placeholder">
                    {customPlaceholder} <span className="asterisk"> *</span>
                  </div>
                )}
              </InputGroup>
              {error?.message && (
                <div className="error-message">
                  {t(String(error?.message || ''))}
                </div>
              )}
            </>
          )}
        />
      )}
      {/* {error && (
        <div className="error">{t(String(error?.message || ""))}</div>
      )} */}
      {description && <div className="description">{description}</div>}
    </div>
  );
};

export default PhoneNumberInput;

const styles = {
  prefixIcon: {
    background: 'unset',
    borderRightWidth: 0,
  },
};

const selectStyles = (theme: any) => ({
  valueContainer: (base: any) => ({
    ...base,
    height: '2.975rem',
    padding: '0',
    position: 'absolute',
    top: 0,
    left: 8,
  }),
  indicatorsContainer: (base: any) => ({
    ...base,
    height: '2.975rem',
    position: 'absolute',
    top: 0,
    right: 0,
  }),
  dropdownIndicator: (provided: any) => ({
    ...provided,
    svg: {
      width: '1.2em',
      height: '1.2em',
    },
  }),
  control: (baseStyles: any, state: any) => ({
    ...baseStyles,
    ':hover': {
      borderColor: 'var(--ga-primary)',
    },
    boxShadow: 'none',
    backgroundColor:
      state.isDisabled && theme === 'dark'
        ? '#2D2E30'
        : state.isDisabled
          ? '#E9ECEF'
          : 'transparent',
    minHeight: '2.975rem',
    borderLeftWidth: '0.5px',
    height: '2.975rem',
    width: '5.5em',
    borderRadius: '0.5em 0 0 0.5em',
    borderColor: state.isFocused
      ? 'var(--ga-primary)'
      : theme === 'dark'
        ? Colors.Gray6
        : Colors.Gray4,
  }),
  indicatorSeparator: () => ({
    display: 'none',
  }),
  option: (provided: any, state: any) => ({
    ...provided,
    backgroundColor: state?.data?.isDisabled
      ? 'transparent'
      : state.isSelected
        ? theme === 'dark'
          ? 'var(--ga-light-theme-font-color)'
          : 'var(--ga-primary-3)'
        : 'transparent',
    color: state?.data?.isDisabled
      ? 'gray'
      : state.isSelected
        ? theme === 'dark'
          ? 'var(--ga-primary-dark)'
          : 'var(--ga-primary)'
        : theme === 'dark'
          ? '#DDDFE2'
          : 'black',
    fontWeight: state.isSelected ? 600 : 'normal',
    ':active': {
      backgroundColor: state.isSelected ? 'var(--ga-primary-3)' : 'transparent',
      color: state.isSelected
        ? theme === 'dark'
          ? 'var(--ga-primary-dark)'
          : 'var(--ga-primary)'
        : theme === 'dark'
          ? 'var(--ga-primary-dark)'
          : 'var(--ga-primary)',
    },
    '&:hover': {
      backgroundColor: state?.data?.isDisabled
        ? 'transparent'
        : theme === 'dark'
          ? 'var(--ga-light-theme-font-color)'
          : 'var(--ga-primary-3)',
      color: state?.data?.isDisabled
        ? 'gray'
        : theme === 'dark'
          ? 'var(--ga-primary-dark)'
          : 'var(--ga-primary)',
      fontWeight: state?.data?.isDisabled ? 400 : 600,
    },
  }),
  menu: (provided: any) => ({
    ...provided,
    overflow: 'hidden',
    backgroundColor: theme === 'dark' ? '#212529' : 'white',
    color: theme === 'dark' ? '#DDDFE2' : 'black',
    border: 'none',
    zIndex: 999999,
  }),
  menuPortal: (base: any) => ({ ...base, zIndex: 9999 }),
  input: (baseStyles: any) => ({
    ...baseStyles,
    color: theme === 'dark' ? '#DDDFE2' : 'black',
  }),
  singleValue: (baseStyles: any) => ({
    ...baseStyles,
    color: theme === 'dark' ? '#DDDFE2' : 'black',
  }),
  singleValueLabel: (baseStyles: any) => ({
    ...baseStyles,
    color: theme === 'dark' ? '#DDDFE2' : '#444646',
  }),
  multiValue: (baseStyles: any) => ({
    ...baseStyles,
    backgroundColor: theme === 'dark' ? '#2D2E30' : '#ECECEF',
    color: theme === 'dark' ? '#2D2E30' : '#444646',
    borderRadius: '1em',
  }),
  multiValueLabel: (baseStyles: any) => ({
    ...baseStyles,
    color: theme === 'dark' ? '#DDDFE2' : '#444646',
  }),
  multiValueRemove: (baseStyles: any) => ({
    ...baseStyles,
    color: theme === 'dark' ? '#DDDFE2' : '#444646',
    ':hover': {
      backgroundColor: theme === 'dark' ? '#2D2E30' : '#ECECEF',
      borderTopRightRadius: '1em',
      borderBottomRightRadius: '1em',
    },
  }),
});
