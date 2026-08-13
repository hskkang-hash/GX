import { Form } from 'react-bootstrap';
import { Control, FieldValues, Path, useController } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  components,
  SingleValueProps,
  MultiValueGenericProps,
  OptionProps,
} from 'react-select';
import { AsyncPaginate, LoadOptions } from 'react-select-async-paginate';
import { useTheme } from 'rj-core';

import Colors from '@/configs/Colors';

interface SelectOption {
  value: string | number;
  label: string;
  isDefault?: boolean;
  [key: string]: any;
}

interface PaginationSelectProps<
  TFieldValues extends FieldValues = FieldValues,
> {
  label?: string;
  id?: string;
  error?: string | boolean;
  warning?: boolean;
  required?: boolean;
  description?: string;
  loadOptions: LoadOptions<
    SelectOption,
    any,
    { page?: number; page_size?: number }
  >;
  handleDroneChange?: (
    selectedOption: SelectOption | SelectOption[] | null,
  ) => void;
  value?: SelectOption | SelectOption[] | null;
  setValue?: (value: SelectOption | SelectOption[] | null) => void;
  placeholder?: string | null;
  name?: string;
  control?: Control<TFieldValues>;
  onChange?: (value: SelectOption | SelectOption[] | null) => void;
  maxValue?: number;
  controlHeight?: string;
  [key: string]: any;
}

const PaginationSelect = <TFieldValues extends FieldValues = FieldValues>({
  label,
  id,
  error,
  required,
  description,
  loadOptions,
  warning,
  value,
  setValue,
  placeholder = null,
  name,
  handleDroneChange,
  control,
  maxValue,
  menuPortalTarget = document.body,
  menuPlacement = 'auto',
  className,
  controlHeight,
  ...props
}: PaginationSelectProps<TFieldValues>) => {
  const { t } = useTranslation();
  const [theme] = useTheme();

  const controller =
    control && name
      ? useController({
          name: name as Path<TFieldValues>,
          control,
        })
      : null;

  const field = controller?.field;
  const fieldError = controller?.fieldState?.error;

  // Custom components với tooltip cho text bị cắt
  const SingleValue = (props: SingleValueProps<SelectOption>) => {
    return (
      <components.SingleValue {...props}>
        <span
          title={props.data?.label || ''}
          style={{ pointerEvents: 'auto' }}
        >
          {props.children}
        </span>
      </components.SingleValue>
    );
  };

  const MultiValueLabel = (props: MultiValueGenericProps<SelectOption>) => {
    return (
      <components.MultiValueLabel {...props}>
        <span
          title={props.data?.label || ''}
          style={{ pointerEvents: 'auto' }}
        >
          {props.children}
        </span>
      </components.MultiValueLabel>
    );
  };

  const Option = (props: OptionProps<SelectOption>) => {
    return (
      <components.Option {...props}>
        <span
          title={props.data?.label || ''}
          style={{ pointerEvents: 'auto' }}
        >
          {props.children}
        </span>
      </components.Option>
    );
  };

  const handleChange = (newValue: SelectOption | SelectOption[] | null) => {
    if (
      props.isMulti &&
      maxValue &&
      Array.isArray(newValue) &&
      newValue.length > maxValue
    ) {
      newValue = newValue.slice(0, maxValue);
    }

    field?.onChange?.(newValue);
    setValue?.(newValue);
    handleDroneChange?.(newValue);
    props.onChange?.(newValue);
  };

  return (
    <div className={`custom-select-section ${className || ''}`}>
      {label && (
        <Form.Label
          className={`text-${theme === 'dark' ? 'white' : 'black'} fs-6 fw-semibold`}
          htmlFor={id}
        >
          {label}
          {required && <span className="asterisk"> *</span>}
        </Form.Label>
      )}
      <AsyncPaginate<SelectOption, any, { page?: number; page_size?: number }>
        {...props}
        {...(field || {})}
        value={value ?? field?.value ?? null}
        loadOptions={loadOptions}
        menuPlacement={menuPlacement}
        menuPortalTarget={menuPortalTarget}
        additional={{
          page: 1,
          page_size: 10,
        }}
        onChange={handleChange}
        onBlur={field?.onBlur}
        isDisabled={props.disabled}
        debounceTimeout={300}
        loadingMessage={() => t('Loading...')}
        noOptionsMessage={() => t('No options')}
        placeholder={t(placeholder)}
        components={{
          ...props.components,
          SingleValue: props.components?.SingleValue || SingleValue,
          MultiValueLabel: props.components?.MultiValueLabel || MultiValueLabel,
          Option: props.components?.Option || Option,
        }}
        styles={{
          valueContainer: (base: any, state: any) => ({
            ...base,
            padding: '0.375rem 0.75rem',
            position: 'relative',
            fontSize: '0.875rem',
            cursor: state.isDisabled ? 'not-allowed' : 'text',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }),
          indicatorsContainer: (base: any) => ({
            ...base,
            position: 'relative',
          }),
          dropdownIndicator: (provided: any) => ({
            ...provided,
            svg: {
              width: '1.5rem',
              height: '1.5rem',
            },
          }),
          control: (baseStyles: any, state: any) => ({
            ...baseStyles,
            ':hover': {
              borderColor: state.isDisabled
                ? 'var(--ga-primary)'
                : 'var(--ga-primary)',
            },
            cursor: state.isDisabled ? 'not-allowed !important' : 'pointer',
            boxShadow: 'none',
            transition: 'none',
            backgroundColor:
              state.isDisabled && theme === 'dark'
                ? '#2D2E30'
                : state.isDisabled
                  ? '#f5f5f5'
                  : theme === 'light'
                    ? '#ffffff'
                    : 'transparent',
            borderRadius: '0.5rem',
            minHeight: '2.975em !important',
            // height: controlHeight ? controlHeight : '2.975em !important',
            borderColor:
              fieldError || error
                ? 'red'
                : warning
                  ? '#fce803'
                  : state.isFocused
                    ? 'var(--ga-primary-4)'
                    : theme === 'dark'
                      ? Colors.Gray6
                      : Colors.Gray4,
          }),
          indicatorSeparator: () => ({
            display: 'none',
          }),
          option: (provided: any, state: any) => {
            const isDisabled =
              props.isMulti &&
              maxValue &&
              Array.isArray(field.value) &&
              field.value.length >= maxValue &&
              !state.isSelected;
            return {
              ...provided,
              fontSize: '1rem',
              position: state?.data?.isDefault ? 'absolute' : 'relative',
              backgroundColor: state?.data?.isDefault
                ? 'transparent'
                : state.isSelected
                  ? theme === 'dark'
                    ? 'var(--ga-light-theme-font-color)'
                    : 'var(--ga-primary-3)'
                  : 'transparent',
              color: isDisabled
                ? theme === 'dark'
                  ? Colors.Gray6
                  : Colors.Gray5
                : state.isSelected
                  ? theme === 'dark'
                    ? 'var(--ga-primary-dark)'
                    : 'var(--ga-primary)'
                  : theme === 'dark'
                    ? '#DDDFE2'
                    : 'black',
              fontWeight: state.isSelected ? 600 : 'normal',
              cursor: isDisabled ? 'not-allowed' : 'pointer',
              // opacity: isDisabled ? 0.5 : 1,
              ':active': {
                backgroundColor: state?.data?.isDefault
                  ? 'transparent'
                  : state.isSelected
                    ? 'var(--ga-primary-3)'
                    : 'transparent',
                color: state.isSelected
                  ? theme === 'dark'
                    ? 'var(--ga-primary-dark)'
                    : 'var(--ga-primary)'
                  : theme === 'dark'
                    ? 'var(--ga-primary-dark)'
                    : 'var(--ga-primary)',
              },
              '&:hover': {
                backgroundColor: isDisabled
                  ? 'transparent'
                  : state?.data?.isDefault
                    ? 'transparent'
                    : theme === 'dark'
                      ? 'var(--ga-light-theme-font-color)'
                      : 'var(--ga-primary-3)',
                color: isDisabled
                  ? theme === 'dark'
                    ? Colors.Gray6
                    : Colors.Gray4
                  : theme === 'dark'
                    ? 'var(--ga-primary-dark)'
                    : 'var(--ga-primary)',
                fontWeight: isDisabled ? 'normal' : 600,
              },
            };
          },
          menu: (provided: any) => ({
            ...provided,
            overflow: 'hidden',
            backgroundColor: theme === 'dark' ? '#212529' : 'white',
            color: theme === 'dark' ? '#DDDFE2' : 'black',
            border: 'none',
          }),
          input: (baseStyles: any, state: any) => ({
            ...baseStyles,
            color: theme === 'dark' ? '#DDDFE2' : 'black',
            cursor: state.isDisabled ? 'not-allowed' : 'pointer',
          }),
          singleValue: (baseStyles: any) => ({
            ...baseStyles,
            color: theme === 'dark' ? '#DDDFE2' : 'black',
            fontSize: '1rem',
          }),
          menuPortal: (base: any) => ({ ...base, zIndex: 9999 }),
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
          placeholder: (base: any) => ({
            ...base,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            width: '100%',
          }),
        }}
      />
      {description && <div className="description">{description}</div>}
      {fieldError && (
        <div
          className="error"
          style={{ fontSize: '0.875rem' }}
        >
          {t(fieldError.message || fieldError?.value?.message || '')}
        </div>
      )}
    </div>
  );
};

export default PaginationSelect;
