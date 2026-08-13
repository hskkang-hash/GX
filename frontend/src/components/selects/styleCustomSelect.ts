import { GroupBase, StylesConfig } from 'react-select';

import Colors from '../../configs/Colors';

interface LangOption {
  value: string;
  label: string;
  flag: string;
}

export const styleCustomSelect = (
  theme: string,
  height: string = '2.975rem',
): StylesConfig<LangOption, false, GroupBase<LangOption>> => ({
  valueContainer: (base, state) => ({
    ...base,
    padding: '0.375rem',
    position: 'relative',
    fontSize: '0.875rem',
    cursor: state.isDisabled ? 'not-allowed' : 'text',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  }),
  indicatorsContainer: (base) => ({
    ...base,
    position: 'relative',
  }),
  dropdownIndicator: (provided) => ({
    ...provided,
    svg: {
      width: '1.5rem',
      height: '1.5rem',
    },
  }),
  control: (baseStyles, state) => ({
    ...baseStyles,
    ':hover': {
      borderColor: state.isDisabled ? 'var(--ga-primary)' : 'var(--ga-primary)',
    },
    transition: 'none',
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
    minHeight: `${height} !important`,
    width: '100%',
    borderColor: theme === 'dark' ? Colors.Gray6 : Colors.Gray4,
  }),
  indicatorSeparator: () => ({
    display: 'none',
  }),
  option: (provided, state) => {
    return {
      ...provided,
      fontSize: '1rem',
      position: 'relative',
      backgroundColor: state.isSelected
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
        backgroundColor: state.isSelected
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
        backgroundColor:
          theme === 'dark'
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
  singleValue: (baseStyles) => ({
    ...baseStyles,
    color: theme === 'dark' ? '#DDDFE2' : 'black',
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
});
