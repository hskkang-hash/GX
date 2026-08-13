import { Slider } from 'antd';
import { ReactNode } from 'react';
import { Control, Controller } from 'react-hook-form';
import { useTheme } from 'rj-core';

import './CustomSlider.scss';

interface CustomSliderProps {
  name?: string;
  label?: string;
  control?: Control<Record<string, unknown>>;
  required?: boolean;
  value?: number;
  onChange?: (value: number) => void;
  placeholder?: string;
  min?: number;
  max?: number;
  step?: number;
  range?: boolean;
  isTooltip?: boolean;
  unit?: string;
}

const CustomSlider = ({
  name,
  label,
  control,
  required,
  value,
  onChange,
  min = 0,
  max = 100,
  step = 1,
  range = false,
  isTooltip = true,
  unit = '%',
}: CustomSliderProps) => {
  const [theme, _] = useTheme();

  const valuetext = (value?: number): ReactNode => {
    return value !== undefined ? `${value}${unit}` : '';
  };

  if (control && name) {
    return (
      <Controller
        name={name}
        control={control}
        render={({ field }) => (
          <div className={`custom-slider ${theme}`}>
            {label && (
              <label className="custom-slider__label">
                {label}{' '}
                {required && (
                  <span className="custom-slider__label--required">*</span>
                )}
              </label>
            )}
            <Slider
              className="custom-slider__slider"
              tooltip={{
                formatter: valuetext,
                open: isTooltip,
                getPopupContainer: (triggerNode: HTMLElement) =>
                  triggerNode.parentElement || document.body,

                placement: 'top',
              }}
              value={field.value as number}
              onChange={field.onChange}
              min={min}
              max={max}
              step={step}
              range={range}
              styles={{
                root: {
                  marginTop: '2rem',
                  marginBottom: '0',
                  height: '10px',
                },
                track: {
                  backgroundColor: theme === 'light' ? '#D3EFFF' : '#293438',
                },
                rail: {
                  backgroundColor: theme === 'light' ? '#F2F2F2' : '#2D2E30',
                },
              }}
            />
          </div>
        )}
      />
    );
  }

  // Direct mode without form control
  return (
    <div className="custom-slider">
      {label && (
        <label className="custom-slider__label">
          {label}{' '}
          {required && (
            <span className="custom-slider__label--required">*</span>
          )}
        </label>
      )}
      <Slider
        className="custom-slider__slider"
        tooltip={{ formatter: valuetext }}
        value={value}
        onChange={onChange}
        min={min}
        max={max}
        step={step}
      />
    </div>
  );
};

export default CustomSlider;
