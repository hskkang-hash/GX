import { Tabs as MUITabs, Tab as MUITab, Box, IconButton } from '@mui/material';
import { styled } from '@mui/material/styles';
import React, { ReactNode, useEffect, useState } from 'react';
import { useTheme } from 'rj-core';

import Colors from '../../configs/Colors';

const StyledTabs = styled(MUITabs)(({ mode }) => ({
  minHeight: '2rem',
  '& .MuiTabs-indicator': {
    backgroundColor:
      mode === 'dark' ? 'var(--ga-primary-dark)' : 'var(--ga-primary)',
    height: '2px',
  },
  transition: 'all 600ms ease-in-out;',
}));

const StyledTab = styled(MUITab)(({ mode }) => ({
  textTransform: 'none',
  minHeight: '2rem',
  // width: $availableWidth ? `${$availableWidth / 2}px` : "auto",
  padding: '8px 16px',
  color: mode === 'dark' ? 'red' : Colors.Gray5,
  fontSize: '1.143rem',
  fontWeight: 600,
  transition: 'all 600ms ease-in-out;',

  '&.Mui-selected': {
    fontWeight: 700,
    color: mode === 'dark' ? 'var(--ga-primary-dark)' : 'var(--ga-primary)',
    outline: 'none',
  },
  '&:hover': {
    color: mode === 'dark' ? 'var(--ga-primary-dark)' : 'var(--ga-primary)',
  },
  '&:focus': {
    outline: 'none',
  },
}));

const TabLabel = styled('div')({
  display: 'flex',
  flexWrap: 'nowrap',
  alignItems: 'center',
  gap: '4px',
  fontSize: '1rem',
  letterSpacing: '0.01rem',
});

export interface TabItem {
  label: string;
  content: ReactNode;
  hasDropdown?: boolean;
  path?: string;
}

interface TabsProps {
  items: TabItem[];
  activeTab?: number;
  onTabChange?: (index: number) => void;
  availableWidth?: number;
  noNeedReRender?: boolean;
}

export function Tabs({
  items,
  activeTab,
  onTabChange,
  availableWidth,
  noNeedReRender = false,
  ...props
}: TabsProps) {
  const [internalValue, setInternalValue] = useState(0);

  // Use controlled value if provided, otherwise use internal state
  const value = activeTab ?? internalValue;

  const handleChange = (event: React.SyntheticEvent, newValue: number) => {
    if (onTabChange) {
      onTabChange(newValue); // Controlled mode
    } else {
      setInternalValue(newValue); // Uncontrolled mode (default)
    }
  };

  useEffect(() => {
    if (items.length === 1 && value !== 0) {
      if (onTabChange) {
        onTabChange(0); // Controlled mode
      } else {
        setInternalValue(0); // Uncontrolled mode
      }
    }
  }, [items, value, onTabChange]);

  const [theme, _] = useTheme();

  return (
    <Box
      sx={{
        flex: 1,
        zIndex: 1,
        // background: Colors.White,
        width: '100%',
        borderColor: 'divider',
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          // backgroundColor: Colors.White,
          borderBottom: `1px solid ${theme === 'dark' ? Colors.Gray6 : Colors.Gray4}`,
        }}
      >
        <StyledTabs
          mode={theme}
          value={value}
          variant={props.variant}
          onChange={handleChange}
          aria-label="custom tabs"
          sx={{
            button: {
              color: Colors.Gray5,
            },
          }}
        >
          {items.map((item, index) => (
            <StyledTab
              mode={theme}
              key={index}
              value={index}
              label={
                <TabLabel>
                  {item.label}
                  {/* {item.hasDropdown && <ChevronDown size={16} />} */}
                </TabLabel>
              }
              // $availableWidth={availableWidth}
            />
          ))}
        </StyledTabs>
      </Box>
      {items.map((item, index) => (
        <Box
          key={index}
          role="tabpanel"
          hidden={value !== index}
          id={`custom-tabpanel-${index}`}
          aria-labelledby={`custom-tab-${index}`}
          sx={{
            ...{
              marginTop: '16px',
              // backgroundColor: Colors.White,
            },
            ...(item.contentStyle ?? {}),
          }}
        >
          {noNeedReRender ? (
            <div style={{ display: value === index ? 'block' : 'none' }}>
              {item.content}
            </div>
          ) : (
            value === index && item.content
          )}
        </Box>
      ))}
    </Box>
  );
}
