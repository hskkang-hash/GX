import {
  Radio,
  RadioGroup,
  FormControlLabel,
  FormControl,
  FormLabel,
} from '@mui/material';
import React from 'react';
import { Control, Controller } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import Colors from '../../configs/Colors';
import './CustomTableRadio.scss';

interface RadioOption {
  value: string | number | boolean;
  label: string;
}

interface TableRadioOption {
  name: string;
  value: string | number | boolean;
  label: string;
  option: RadioOption[];
}

interface CustomTableRadioProps {
  control: Control<any>;
  label?: string;
  disabled?: boolean;
  row?: boolean;
  required?: boolean;
  listItem: TableRadioOption[];
}

const CustomTableRadio: React.FC<CustomTableRadioProps> = ({
  control,
  label,
  required = false,
  disabled = false,
  listItem,
  row = false,
}) => {
  const [theme, _] = useTheme();
  const { t } = useTranslation();
  return (
    <table className={`custom-table-radio ${theme}`}>
      <thead>
        <tr>
          <th>{label ? label : ''}</th>
          <th>{t('Yes')}</th>
          <th>{t('No')}</th>
        </tr>
      </thead>
      <tbody>
        {listItem.map((item) => (
          <tr key={item.value}>
            <td>{item.label}</td>
            <td>
              <Controller
                name={item.name}
                control={control}
                defaultValue=""
                render={({ field: { onChange, value } }) => {
                  return (
                    <FormControlLabel
                      value={item.option[0].value}
                      control={
                        <Radio
                          checked={
                            (Boolean(value) || value) === item.option[0].value
                          }
                          onChange={(e) => onChange(item.option[0].value)}
                          className={`custom-radio ${theme}`}
                        />
                      }
                      label=""
                    />
                  );
                }}
              />
            </td>
            <td>
              <Controller
                name={item.name}
                control={control}
                defaultValue=""
                render={({ field: { onChange, value } }) => {
                  return (
                    <FormControlLabel
                      value={item.option[1].value}
                      control={
                        <Radio
                          checked={
                            (Boolean(value) || value) === item.option[1].value
                          }
                          onChange={(e) => onChange(item.option[1].value)}
                          className={`custom-radio ${theme}`}
                        />
                      }
                      label=""
                    />
                  );
                }}
              />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default CustomTableRadio;
