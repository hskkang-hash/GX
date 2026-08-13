import {
  StylesConfig,
  CSSObjectWithLabel,
  ControlProps,
  OptionProps,
  GroupBase,
} from 'react-select';

import Colors from '../../configs/Colors';

interface LangOption {
  value: string;
  label: string;
  flag: string;
}

export const selectStyles = (
  theme: string,
): StylesConfig<LangOption, false, GroupBase<LangOption>> => ({
  valueContainer: (base: CSSObjectWithLabel) => ({
    ...base,
    height: '2.975em',
    padding: '0',
    position: 'absolute',
    top: 0,
    left: 8,
    // right: 0,
  }),
  indicatorsContainer: (base: CSSObjectWithLabel) => ({
    ...base,
    height: '2.975em',
    position: 'absolute',
    top: 0,
    right: 0,
  }),
  dropdownIndicator: (provided: CSSObjectWithLabel) => ({
    ...provided,
    svg: {
      width: '1.2em',
      height: '1.2em',
    },
  }),
  control: (
    baseStyles: CSSObjectWithLabel,
    state: ControlProps<LangOption, false, GroupBase<LangOption>>,
  ) => ({
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
    minHeight: '2.975em',
    borderLeftWidth: '0.5px',
    height: '2.975em',
    width: '5.5em',
    borderRadius: '0.5em 0 0 0.5em',
    borderColor: state.isFocused
      ? 'var(--ga-primary-4)'
      : theme === 'dark'
        ? Colors.Gray6
        : Colors.Gray4,
  }),
  indicatorSeparator: () => ({
    display: 'none',
  }),
  option: (
    provided: CSSObjectWithLabel,
    state: OptionProps<LangOption, false, GroupBase<LangOption>>,
  ) => ({
    ...provided,
    backgroundColor: state.isDisabled
      ? 'transparent'
      : state.isSelected
        ? theme === 'dark'
          ? 'var(--ga-light-theme-font-color)'
          : 'var(--ga-primary-3)'
        : 'transparent',
    color: state.isDisabled
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
      backgroundColor: state.isDisabled
        ? 'transparent'
        : theme === 'dark'
          ? 'var(--ga-light-theme-font-color)'
          : 'var(--ga-primary-3)',
      color: state.isDisabled
        ? 'gray'
        : theme === 'dark'
          ? 'var(--ga-primary-dark)'
          : 'var(--ga-primary)',
      fontWeight: state.isDisabled ? 400 : 600,
    },
  }),
  menu: (provided: CSSObjectWithLabel) => ({
    ...provided,
    overflow: 'hidden',
    backgroundColor: theme === 'dark' ? '#212529' : 'white',
    color: theme === 'dark' ? '#DDDFE2' : 'black',
    border: 'none',
    zIndex: 999999,
  }),
  menuPortal: (base: CSSObjectWithLabel) => ({ ...base, zIndex: 9999 }),
  input: (baseStyles: CSSObjectWithLabel) => ({
    ...baseStyles,
    color: theme === 'dark' ? '#DDDFE2' : 'black',
  }),
  singleValue: (baseStyles: CSSObjectWithLabel) => ({
    ...baseStyles,
    color: theme === 'dark' ? '#DDDFE2' : 'black',
  }),
  multiValue: (baseStyles: CSSObjectWithLabel) => ({
    ...baseStyles,
    backgroundColor: theme === 'dark' ? '#2D2E30' : '#ECECEF',
    color: theme === 'dark' ? '#2D2E30' : '#444646',
    borderRadius: '1em',
  }),
  multiValueLabel: (baseStyles: CSSObjectWithLabel) => ({
    ...baseStyles,
    color: theme === 'dark' ? '#DDDFE2' : '#444646',
  }),
  multiValueRemove: (baseStyles: CSSObjectWithLabel) => ({
    ...baseStyles,
    color: theme === 'dark' ? '#DDDFE2' : '#444646',
    ':hover': {
      backgroundColor: theme === 'dark' ? '#2D2E30' : '#ECECEF',
      borderTopRightRadius: '1em',
      borderBottomRightRadius: '1em',
    },
  }),
});
