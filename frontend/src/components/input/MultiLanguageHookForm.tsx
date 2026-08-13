/**
 * MultiLanguageHookForm - A multi-language input component for React Hook Form
 *
 * Usage example:
 * ```tsx
 * import { useForm } from 'react-hook-form';
 * import MultiLanguageHookForm from './MultiLanguageHookForm';
 *
 * interface FormData {
 *   title: { en?: string; ko?: string; };
 * }
 *
 * const MyForm = () => {
 *   const { control, handleSubmit } = useForm<FormData>();
 *
 *   return (
 *     <form onSubmit={handleSubmit(onSubmit)}>
 *       <MultiLanguageHookForm
 *         name="title"
 *         control={control}
 *         label="Title"
 *         placeholder="Enter title..."
 *         required
 *         rules={{ required: 'Title is required' }}
 *         onLanguageChange={(lang) => console.log('Language:', lang)}
 *       />
 *     </form>
 *   );
 * };
 * ```
 */
import 'flag-icons/css/flag-icons.min.css';
import { useState } from 'react';
import { Form, InputGroup } from 'react-bootstrap';
import { Control, Controller, FieldValues, Path } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import Select, { SingleValue } from 'react-select';
import { useTheme } from 'rj-core';

import EnFlag from '@/assets/images/english-flag.svg';
import KrFlag from '@/assets/images/korea-flag.svg';
import ThFlag from '@/assets/images/thai-flag.svg';

import './MultiLanguageHookForm.scss';
import { selectStyles } from './selectStyles';

interface LangOption {
  value: string;
  label: string;
  flag: string;
}

interface MultiLanguageValue {
  en?: string;
  ko?: string;
  th?: string;
}

interface MultiLanguageHookFormProps<T extends FieldValues> {
  name: Path<T>;
  control: Control<T>;
  label?: string;
  placeholder?: string;
  id?: string;
  required?: boolean;
  maxLength?: number;
  rules?: object;
  disabled?: boolean;
  onLanguageChange?: (lang: string) => void;
}

const LANG_OPTIONS: LangOption[] = [
  {
    value: 'en',
    label: 'English',
    flag: EnFlag,
  },
  {
    value: 'ko',
    label: '한국어',
    flag: KrFlag,
  },
  {
    value: 'th',
    label: 'ภาษาไทย',
    flag: ThFlag,
  },
];

const MultiLanguageHookForm = <T extends FieldValues>({
  name,
  control,
  label,
  placeholder,
  id,
  required = false,
  maxLength = 100,
  rules = {},
  disabled = false,
  onLanguageChange,
  ...props
}: MultiLanguageHookFormProps<T>): React.JSX.Element => {
  const { t, i18n } = useTranslation();
  const [theme] = useTheme();
  const [lang, setLang] = useState<string>(
    i18n?.language === 'ko' ? 'ko' : 'en',
  );

  const formatOptionLabel = ({
    label,
    flag,
  }: LangOption): React.JSX.Element => (
    <div style={{ display: 'flex', alignItems: 'center' }}>
      <img
        src={flag}
        style={{ margin: '0.5em', width: '1.5em', height: '1.5em' }}
        alt={label}
      />
    </div>
  );

  const handleLanguageChange = (
    selectedOption: SingleValue<LangOption>,
  ): void => {
    if (selectedOption) {
      setLang(selectedOption.value);
      onLanguageChange?.(selectedOption.value);
    }
  };

  const validationRules = {
    ...rules,
    ...(required && {
      validate: (value: MultiLanguageValue) => {
        const currentValue = value?.[lang as keyof MultiLanguageValue];
        return currentValue && currentValue.trim() !== ''
          ? true
          : t('Required');
      },
    }),
  };

  return (
    <Controller
      name={name}
      control={control}
      rules={validationRules}
      render={({
        field: { onChange, value, onBlur },
        fieldState: { error },
      }) => {
        const currentValue = (value as MultiLanguageValue) || {};

        const handleInputChange = (
          e: React.ChangeEvent<HTMLInputElement>,
        ): void => {
          const newValue = {
            ...currentValue,
            [lang]: e.target.value,
          };
          onChange(newValue);
        };

        return (
          <div
            className={`custom-select-section multi-language-input ${
              theme === 'dark' ? 'dropdown-dark' : 'dropdown-light'
            }`}
          >
            <Form.Label htmlFor={id}>
              {label}
              {required && <span className="asterisk"> *</span>}
            </Form.Label>
            <div
              className="d-flex"
              id="multi-language-select"
            >
              <Select
                className="select-input"
                options={LANG_OPTIONS}
                onChange={handleLanguageChange}
                value={LANG_OPTIONS.find((option) => option.value === lang)}
                formatOptionLabel={formatOptionLabel}
                styles={selectStyles(theme)}
                isDisabled={disabled}
              />

              <InputGroup className="custom-input">
                <Form.Control
                  {...props}
                  placeholder={placeholder}
                  data-bs-theme={`${theme === 'dark' ? 'dark' : 'light'}`}
                  id={id}
                  maxLength={maxLength}
                  value={currentValue[lang as keyof MultiLanguageValue] || ''}
                  onChange={handleInputChange}
                  onBlur={onBlur}
                  disabled={disabled}
                  style={{
                    borderTopLeftRadius: '0 !important',
                    borderBottomLeftRadius: '0 !important',
                  }}
                  className={`${error ? 'input-error' : ''}`}
                />
              </InputGroup>
            </div>
            {error && <div className="error">{error.message}</div>}
          </div>
        );
      }}
    />
  );
};

export default MultiLanguageHookForm;
