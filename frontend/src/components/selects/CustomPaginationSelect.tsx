import { theme as antdTheme, Checkbox, ConfigProvider } from 'antd';
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BsChevronDown, BsChevronUp } from 'react-icons/bs';
import { IoClose, IoSearchOutline } from 'react-icons/io5';
import { components } from 'react-select';
import { AsyncPaginate, LoadOptions } from 'react-select-async-paginate';
import { useTheme } from 'rj-core';

import Colors, { infoBg } from '@/configs/Colors';

import './CustomPaginationSelect.scss';

export interface OptionType {
  label: string;
  value: string;
  [key: string]: any;
}

interface PaginationMultiSelectProps {
  loadOptions: LoadOptions<
    OptionType,
    any,
    { page: number; page_size?: number }
  >;
  placeholder?: string;
  defaultValue?: OptionType[] | null;
  onChange?: (value: OptionType[] | null) => void;
  pageSize?: number;
  className?: string;
  [key: string]: any;
}

// Custom Option (checkbox style)
const CustomOption = (props: any) => {
  const { isSelected, label, innerProps, onChange } = props;
  const [theme] = useTheme();

  return (
    <components.Option {...props}>
      <div
        {...innerProps}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <ConfigProvider
          theme={{
            algorithm:
              theme === 'dark'
                ? antdTheme.darkAlgorithm
                : antdTheme.defaultAlgorithm,
          }}
        >
          <Checkbox
            checked={isSelected}
            onChange={(e) => {
              onChange?.(e.target.checked);
            }}
          >
            <label style={{ fontSize: 12 }}>{label}</label>
          </Checkbox>
        </ConfigProvider>
      </div>
    </components.Option>
  );
};

// Custom ValueContainer (only display "n selected")
const CustomValueContainer = (props: any) => {
  const { onChange } = props.selectProps;
  const { t } = useTranslation();
  const selected = props.getValue ? props.getValue() : [];
  const count = selected.length;
  const displayText =
    count > 0 ? `${count} ${t('selected')}` : props.selectProps.placeholder;
  const [theme] = useTheme();

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onChange) {
      onChange(null, { action: 'clear' });
    }
  };

  return (
    <components.ValueContainer {...props}>
      {count > 0 && (
        <div
          style={{
            padding: '2px 8px',
            color: theme === 'dark' ? Colors.Gray3 : Colors.PrimaryText,
            borderRadius: 20,
            backgroundColor: theme === 'dark' ? Colors.Gray6 : Colors.Gray2,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          {displayText}
          {count > 0 && (
            <IoClose
              onClick={handleClear}
              style={{
                marginLeft: 0,
                cursor: 'pointer',
                flexShrink: 0,
                fontSize: '18px',
              }}
            />
          )}
        </div>
      )}
    </components.ValueContainer>
  );
};

// Custom Menu with search input
const CustomMenu = (props: any) => {
  const { selectProps, children } = props;
  const { onInputChange, inputValue } = selectProps;
  const [searchValue, setSearchValue] = React.useState(inputValue || '');
  const { t } = useTranslation();
  // Sync inputValue from selectProps
  React.useEffect(() => {
    setSearchValue(inputValue || '');
  }, [inputValue]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setSearchValue(newValue);
    if (onInputChange) {
      onInputChange(newValue, { action: 'input-change' });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    // Prevent menu from closing when Escape key is pressed
    if (e.key === 'Escape') {
      e.stopPropagation();
    }
    // Prevent menu from scrolling when Arrow keys are pressed
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.stopPropagation();
    }
  };
  const [theme] = useTheme();

  return (
    <components.Menu {...props}>
      <div style={{ padding: '8px' }}>
        <div
          style={{
            position: 'relative',
            marginBottom: '8px',
          }}
        >
          <div
            style={{
              position: 'absolute',
              left: '12px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: '#999',
              pointerEvents: 'none',
              zIndex: 1,
            }}
          >
            <IoSearchOutline
              style={{
                fontSize: '16px',
                color: theme === 'dark' ? Colors.Gray4 : Colors.Gray5,
              }}
            />
          </div>
          <input
            type="text"
            value={searchValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={t('Search')}
            autoFocus
            style={{
              width: '100%',
              padding: '8px 8px 8px 36px',
              border: `1px solid ${theme === 'dark' ? Colors.Gray6 : Colors.Gray4}`,
              fontSize: '14px',
              outline: 'none',
              boxSizing: 'border-box',
              height: '2.75rem',
              borderRadius: '8px',
              backgroundColor: theme === 'dark' ? Colors.Gray7 : Colors.White,
              color: theme === 'dark' ? Colors.Gray3 : Colors.PrimaryText,
            }}
            onFocus={(e) => {
              e.stopPropagation();
              e.preventDefault();
            }}
            onClick={(e) => {
              e.stopPropagation();
            }}
            onMouseDown={(e) => {
              e.stopPropagation();
            }}
          />
        </div>
      </div>
      {children}
    </components.Menu>
  );
};

const CustomDropdownIndicator = (props: any) => {
  const isOpen = props.selectProps?.menuIsOpen || false;
  return (
    <components.DropdownIndicator {...props}>
      {isOpen ? (
        <BsChevronUp style={{ fontSize: '16px' }} />
      ) : (
        <BsChevronDown style={{ fontSize: '16px' }} />
      )}
    </components.DropdownIndicator>
  );
};

const PaginationMultiSelect: React.FC<PaginationMultiSelectProps> = ({
  loadOptions,
  // placeholder = 'Select option...',
  defaultValue = null,
  onChange,
  pageSize = 10,
  className,
  ...rest
}) => {
  const [value, setValue] = useState<OptionType[] | null>(defaultValue);
  const [menuIsOpen, setMenuIsOpen] = useState<boolean>(false);
  const selectRef = React.useRef<HTMLDivElement>(null);
  const { t } = useTranslation();
  const [theme] = useTheme();

  // Sync value with defaultValue when defaultValue changes
  useEffect(() => {
    if (defaultValue !== undefined && defaultValue !== null) {
      if (defaultValue.length > 0) {
        // Only set if current value is null/empty/undefined to avoid override when user has already selected
        if (!value || value.length === 0) {
          setValue(defaultValue);
        }
      } else {
        // Clear value when defaultValue becomes empty array
        setValue([]);
      }
    } else {
      // Clear value when defaultValue is null or undefined
      setValue(null);
    }
  }, [defaultValue]);

  // Handle click outside to close menu
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (!menuIsOpen) return;

      const target = event.target as Node;

      // Check if click is inside the select component
      if (selectRef.current?.contains(target)) {
        return;
      }

      // Check if click is inside any react-select menu (menu can be in portal)
      const menuElements = document.querySelectorAll(
        '[class*="menu"], [class*="Menu"], [id*="react-select"]',
      );
      let isInsideMenu = false;

      menuElements.forEach((menuElement) => {
        if (menuElement.contains(target)) {
          isInsideMenu = true;
        }
      });

      // Close menu if click is outside both select and menu
      if (!isInsideMenu) {
        setMenuIsOpen(false);
      }
    };

    if (menuIsOpen) {
      // Use setTimeout to avoid immediate close when opening menu
      setTimeout(() => {
        document.addEventListener('mousedown', handleClickOutside);
      }, 0);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [menuIsOpen]);

  const handleChange = (newValue: any) => {
    setValue(newValue);
    onChange?.(newValue);
  };

  const handleMenuOpen = () => {
    setMenuIsOpen(true);
  };

  const handleMenuClose = () => {
    setMenuIsOpen(false);
  };

  // remove isMulti from rest props to avoid conflict
  const { isMulti: _, ...restProps } = rest as any;

  return (
    <div
      className={className}
      ref={selectRef}
    >
      <AsyncPaginate<OptionType, any, { page: number; page_size?: number }>
        {...restProps}
        isMulti
        value={value}
        loadOptions={loadOptions}
        onChange={handleChange}
        onMenuOpen={handleMenuOpen}
        onMenuClose={handleMenuClose}
        menuIsOpen={menuIsOpen}
        additional={{ page: 1, page_size: pageSize }}
        loadingMessage={() => t('Loading...')}
        noOptionsMessage={() => t('No options')}
        closeMenuOnSelect={false}
        hideSelectedOptions={false}
        components={{
          Option: CustomOption,
          ValueContainer: CustomValueContainer,
          MultiValue: () => null, // hide all MultiValue to avoid duplicate
          Menu: CustomMenu, // add custom menu with search input
          ClearIndicator: () => null, // hide default clear button (second X button)
          DropdownIndicator: CustomDropdownIndicator,
        }}
        // placeholder={placeholder}
        debounceTimeout={300}
        styles={{
          menuPortal: (base) => ({ ...base, zIndex: 10 }),
          control: (base, state) => ({
            ...base,
            borderRadius: 8,
            borderColor: state.isFocused
              ? 'var(--ga-primary)'
              : theme === 'dark'
                ? Colors.Gray6
                : Colors.Gray4,
            minHeight: '1rem',
            boxShadow: state.isFocused ? '0 0 0 1px var(--ga-primary)' : 'none',
            backgroundColor: theme === 'dark' ? Colors.Gray7 : Colors.White,
            '&:hover': {
              borderColor: 'var(--ga-primary)',
            },
          }),
          option: (base, state) => ({
            ...base,
            backgroundColor: state.isFocused
              ? theme === 'dark'
                ? infoBg.dark
                : Colors.Gray1
              : state.isSelected
                ? theme === 'dark'
                  ? infoBg.dark
                  : Colors.White
                : theme === 'dark'
                  ? Colors.Gray7
                  : Colors.White,
            color: theme === 'dark' ? Colors.Gray3 : Colors.PrimaryText,
            ':hover': {
              backgroundColor: theme === 'dark' ? infoBg.dark : Colors.Gray1,
            },
            ':active': {
              backgroundColor: theme === 'dark' ? infoBg.dark : Colors.Gray2,
            },
          }),
          menu: (base) => ({
            ...base,
            zIndex: 20,
            borderRadius: '8px',
            backgroundColor: theme === 'dark' ? Colors.Gray7 : Colors.White,
            border: `1px solid ${theme === 'dark' ? Colors.Gray6 : Colors.Gray4}`,
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
          }),
          menuList: (base) => ({
            ...base,
            padding: 0,
          }),
          input: (base) => ({
            ...base,
            display: 'none',
            color: theme === 'dark' ? Colors.Gray3 : Colors.PrimaryText,
            backgroundColor: theme === 'dark' ? Colors.Gray7 : Colors.White,
          }),
        }}
      />
    </div>
  );
};

export default PaginationMultiSelect;
