import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { Accordion, AccordionDetails, AccordionSummary } from '@mui/material';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../configs/Colors';

interface ExpanDropDownProps {
  label: string;
  children: React.ReactNode;
  backgroundColor?: string;
  lableSize?: string;
  defaultExpanded?: boolean;
  expanded?: boolean;
  onChange?: (expanded: boolean) => void;
  sx?: any;
}

const ExpanDropDown = ({
  label,
  children,
  backgroundColor,
  lableSize,
  defaultExpanded = true,
  expanded,
  onChange,
  sx,
}: ExpanDropDownProps) => {
  const [theme] = useTheme('light');
  const [internalExpanded, setInternalExpanded] = useState(defaultExpanded);

  // Use either controlled or uncontrolled mode
  const isExpanded = expanded !== undefined ? expanded : internalExpanded;

  const handleChange = (_: React.SyntheticEvent, newExpanded: boolean) => {
    if (onChange) {
      onChange(newExpanded);
    } else {
      setInternalExpanded(newExpanded);
    }
  };

  const { t } = useTranslation();

  const labelTrans = label.includes('Option')
    ? label.replace('Option', t('Option'))
    : label;
  return (
    <Accordion
      expanded={isExpanded}
      onChange={handleChange}
      sx={{
        zIndex: 1000,
        backgroundColor:
          backgroundColor || (theme === 'dark' ? Colors.Secondary : 'white'),
        borderRadius: '10px !important',
        overflow: 'hidden',
        boxShadow: 'none',
        '.css-1lj39kh-MuiAccordionDetails-root': {
          padding: '0px 14px 14px 14px !important',
        },
        margin: '0 !important',
        ...sx,
      }}
    >
      <AccordionSummary
        sx={{
          borderRadius: '10px',
          minHeight: 'unset !important',
          '&.Mui-expanded': {
            borderRadius: '10px 10px 0 0',
            minHeight: '40px !important',
          },
          '& .css-yfrx4k-MuiAccordionSummary-content': {
            margin: '0.75rem 0 !important',
          },
        }}
        expandIcon={
          <ExpandMoreIcon
            sx={{ color: theme === 'dark' ? Colors.Gray3 : Colors.PrimaryText }}
          />
        }
        aria-controls="panel1-content"
        id="panel1-header"
      >
        <span
          style={{
            fontWeight: '600',
            fontSize: lableSize || '1.286rem',
            color: theme === 'dark' ? Colors.Gray3 : Colors.PrimaryText,
          }}
        >
          {labelTrans}
        </span>
      </AccordionSummary>
      <AccordionDetails>{children}</AccordionDetails>
    </Accordion>
  );
};

export default ExpanDropDown;
