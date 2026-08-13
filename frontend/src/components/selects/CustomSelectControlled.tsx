import { Form } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import Select, {
  ActionMeta,
  GroupBase,
  MenuPlacement,
  MultiValue,
  SingleValue,
  StylesConfig,
} from 'react-select';
import { useTheme } from 'rj-core';

import Colors from '@/configs/Colors';

export interface SelectOption {
  value: string | number;
  label: string;
  isDefault?: boolean;
  [key: string]: unknown;
}

interface CustomSelectControlledProps {
  label?: string;
  id?: string;
  required?: boolean;
  description?: string;
  options: SelectOption[];
  value?: SelectOption | null;
  setValue?: (value: SelectOption | null) => void;
  placeholder?: string;
  name?: string;
  isMulti?: boolean;
  isSearchable?: boolean;
  isClearable?: boolean;
  menuPlacement?: MenuPlacement;
  menuPortalTarget?: HTMLElement | null;
  disabled?: boolean;
}

const CustomSelectControlled = ({
  label,
  id,
  required,
  description,
  options,
  value,
  setValue,
  placeholder,
  isMulti = false,
  isSearchable = true,
  isClearable = false,
  menuPortalTarget = document.body,
  menuPlacement = 'auto',
  disabled,
  size = 'default',
  ...props
}: CustomSelectControlledProps) => {
  const [theme] = useTheme();
  const { t } = useTranslation();
  const customStyles: StylesConfig<
    SelectOption,
    boolean,
    GroupBase<SelectOption>
  > = {
    valueContainer: (base, state) => ({
      ...base,
      padding: size === 'sm' ? '0 0.75rem' : '0.375rem 0.75rem',
      position: 'relative',
      fontSize: '0.875rem',
      cursor: state.isDisabled ? 'not-allowed' : 'pointer',
      whiteSpace: 'nowrap',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
    }),
    indicatorsContainer: (baseStyles) => ({
      ...baseStyles,
      position: 'relative',
    }),
    dropdownIndicator: (provided) => ({
      ...provided,
      svg: {
        color: theme === 'dark' ? '#DDDFE2' : '#2D2E30',
        width: '1.5rem',
        height: '1.5rem',
      },
      padding: size === 'sm' ? '0 8px !important' : '0.5rem !important',
    }),
    control: (baseStyles, state) => ({
      ...baseStyles,
      ':hover': {
        borderColor: state.isDisabled
          ? 'var(--ga-primary)'
          : 'var(--ga-primary)',
      },
      cursor: state.isDisabled ? 'not-allowed !important' : 'pointer',
      boxShadow: 'none',
      backgroundColor:
        state.isDisabled && theme === 'dark'
          ? '#2D2E30'
          : state.isDisabled
            ? '#f5f5f5'
            : theme === 'light'
              ? '#ffffff'
              : 'transparent',
      borderRadius: '0.5rem',
      minHeight: size === 'sm' ? '2em !important' : '2.97em !important',
      height: size === 'sm' ? '2em !important' : '2.97em !important',
      borderColor: theme === 'dark' ? Colors.Gray6 : Colors.Gray4,
    }),
    indicatorSeparator: () => ({
      display: 'none',
    }),
    option: (provided, state) => {
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
        color: state.isSelected
          ? theme === 'dark'
            ? 'var(--ga-primary-dark)'
            : 'var(--ga-primary)'
          : theme === 'dark'
            ? '#DDDFE2'
            : 'black',
        fontWeight: state.isSelected ? 600 : 'normal',
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
          backgroundColor: state?.data?.isDefault
            ? 'transparent'
            : theme === 'dark'
              ? 'var(--ga-light-theme-font-color)'
              : 'var(--ga-primary-3)',
          color:
            theme === 'dark' ? 'var(--ga-primary-dark)' : 'var(--ga-primary)',
          fontWeight: 600,
        },
      };
    },
    menu: (provided) => ({
      ...provided,
      overflow: 'hidden',
      backgroundColor: theme === 'dark' ? '#212529' : 'white',
      color: theme === 'dark' ? '#DDDFE2' : 'black',
      border: 'none',
    }),
    input: (baseStyles, state) => ({
      ...baseStyles,
      color: theme === 'dark' ? '#DDDFE2' : 'black',
      cursor: state.isDisabled ? 'not-allowed' : 'pointer',
    }),
    singleValue: (baseStyles, state) => ({
      ...baseStyles,
      color: theme === 'dark' ? '#DDDFE2' : 'black',
      cursor: state.isDisabled ? 'not-allowed !important' : 'pointer',
      fontSize: '1rem',
    }),
    menuPortal: (base) => ({ ...base, zIndex: 9999 }),
    multiValue: (baseStyles) => ({
      ...baseStyles,
      backgroundColor: theme === 'dark' ? '#2D2E30' : '#ECECEF',
      color: theme === 'dark' ? '#2D2E30' : '#444646',
      borderRadius: '1em',
    }),
    multiValueLabel: (baseStyles) => ({
      ...baseStyles,
      color: theme === 'dark' ? '#DDDFE2' : '#444646',
    }),
    multiValueRemove: (baseStyles) => ({
      ...baseStyles,
      color: theme === 'dark' ? '#DDDFE2' : '#444646',
      ':hover': {
        backgroundColor: theme === 'dark' ? '#2D2E30' : '#ECECEF',
        borderTopRightRadius: '1em',
        borderBottomRightRadius: '1em',
      },
    }),
    placeholder: (base) => ({
      ...base,
      whiteSpace: 'nowrap',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      width: '100%',
    }),
  };

  return (
    <div className="custom-select-section">
      {label && (
        <Form.Label
          className={`text-${theme === 'dark' ? 'white' : 'black'}`}
          htmlFor={id}
        >
          {label}
          {required && <span className="asterisk"> *</span>}
        </Form.Label>
      )}
      <Select<SelectOption, boolean, GroupBase<SelectOption>>
        {...(props as Record<string, unknown>)}
        options={options.map((option) => ({
          ...option,
          label: t(option.label),
        }))}
        value={value}
        placeholder={placeholder}
        isMulti={isMulti}
        isSearchable={isSearchable}
        isClearable={isClearable}
        menuPlacement={menuPlacement}
        menuPortalTarget={menuPortalTarget}
        styles={customStyles}
        onChange={(
          newValue: MultiValue<SelectOption> | SingleValue<SelectOption>,
          // eslint-disable-next-line @typescript-eslint/no-unused-vars
          _actionMeta: ActionMeta<SelectOption>,
        ) => {
          if (setValue) {
            setValue(newValue as SelectOption | null);
          }
        }}
        isDisabled={disabled}
      />
      {description && <div className="description">{description}</div>}
    </div>
  );
};

export default CustomSelectControlled;
