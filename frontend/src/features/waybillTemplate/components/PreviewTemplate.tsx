import { useRef } from 'react';
import { useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { FormBlock } from 'rj-core';

import { remToPx } from '@/utils/utils';

import { replaceQRParagraphWithDiv } from '../hooks/convertFields';
import NunjucksRenderer from './NunjucksRenderer';

const PreviewTemplate = ({
  height,
  dataExample,
}: {
  height: number;
  dataExample: Record<string, any>;
}) => {
  const { t } = useTranslation();
  const { watch } = useFormContext();
  const innerTopRef = useRef<HTMLDivElement>(null);
  const templateContent = watch('template');

  return (
    <FormBlock className="h-100">
      <h5 ref={innerTopRef}>{t('Preview')}</h5>
      <div
        style={{
          height: `${height - remToPx(4.5)}px`,
          overflow: 'auto',
          marginTop: '1rem',
        }}
      >
        <NunjucksRenderer
          template={replaceQRParagraphWithDiv(templateContent)}
          data={dataExample}
        />
      </div>
    </FormBlock>
  );
};

export default PreviewTemplate;
