import React, { useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { FormBlock } from 'rj-core';

import { remToPx } from '../../../utils/utils';
import { replaceQRParagraphWithDiv } from '../../waybillTemplate/hooks/convertFields';
import CustomNunjucksRerender from './CustomNunjucksRerender';

const PreviewTemplate = ({
  height,
  dataExample,
  templateContent,
}: {
  height: number;
  dataExample: Record<string, string | number | boolean | null | undefined>;
  templateContent: string;
}) => {
  const { t } = useTranslation();
  const innerTopRef = useRef<HTMLDivElement>(null);

  return (
    <FormBlock className="h-100">
      <h5 ref={innerTopRef}>{t('Preview')}</h5>
      <div
        tabIndex={-1}
        style={{
          height: `${height - remToPx(4.5)}px`,
          overflow: 'auto',
          marginTop: '1rem',
        }}
        onKeyDown={(e) => {
          if (e.key === 'Tab') {
            e.preventDefault();
          }
        }}
      >
        <CustomNunjucksRerender
          template={replaceQRParagraphWithDiv(templateContent)}
          data={dataExample}
        />
      </div>
    </FormBlock>
  );
};

export default React.memo(PreviewTemplate);
