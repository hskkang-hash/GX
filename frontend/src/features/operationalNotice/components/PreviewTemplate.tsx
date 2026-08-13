import React, { useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { FormBlock } from 'rj-core';

import { remToPx } from '../../../utils/utils';
import { replaceQRParagraphWithDiv } from '../../waybillTemplate/hooks/convertFields';
import { ContentSection } from '../types/operationalNotice.types';
import CustomNunjucksRerender from './CustomNunjucksRerender';

const PreviewTemplate = ({
  height,
  contentSections,
}: {
  height: number;
  contentSections?: ContentSection[];
}) => {
  const { t } = useTranslation();
  const innerTopRef = useRef<HTMLDivElement>(null);
  const invalidPatterns =
    ' padding: 4px;border-radius: 8px;"><p><br class="ProseMirror-trailingBreak"></p></div></div>';
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
        <div className="preview-sections">
          {contentSections?.map((section) => {
            if (!section.content) {
              return null;
            }
            if (section.content?.includes(invalidPatterns)) {
              return null;
            }
            return (
              <div
                key={section.id}
                className="preview-section mb-3"
              >
                <CustomNunjucksRerender
                  template={replaceQRParagraphWithDiv(section.content || '')}
                />
              </div>
            );
          })}
        </div>
      </div>
    </FormBlock>
  );
};

export default React.memo(PreviewTemplate);
