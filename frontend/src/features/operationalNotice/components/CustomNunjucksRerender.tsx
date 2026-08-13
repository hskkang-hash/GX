import nunjucks from 'nunjucks';
import React, { useEffect, useState } from 'react';
import { useTheme } from 'rj-core';

import { preprocessTemplate } from '../../../utils/templateUtils';
import { decodeCodeBlocks } from '../../reportTemplate/utils/decodeHTMLEntities';

const CustomNunjucksRerender = ({
  template,
  printRef,
}: {
  template: string;
  printRef?: React.RefObject<HTMLDivElement>;
}) => {
  const [theme] = useTheme();
  const [rendered, setRendered] = useState('');

  useEffect(() => {
    try {
      // Create a custom Nunjucks environment with the get filter
      const env = nunjucks.configure({
        autoescape: true,
        throwOnUndefined: false,
      });

      // Add custom filter to simulate Python's .get() method
      env.addFilter(
        'get',
        (
          obj: Record<string, unknown>,
          key: string,
          defaultValue?: unknown,
        ): unknown => {
          if (obj && typeof obj === 'object' && key in obj) {
            return obj[key];
          }
          return defaultValue !== undefined ? defaultValue : null;
        },
      );

      const processedTemplate = preprocessTemplate(template);

      const rendered = env.renderString(
        decodeCodeBlocks(processedTemplate),
        {},
      );

      setRendered(rendered);
    } catch (error) {
      console.error('Template render error:', error);
      setRendered(
        `<pre style="color: red;">Template render error! Please check the template again.</pre>`,
      );
    }
  }, [template]);

  // Disable focus on all child elements
  useEffect(() => {
    if (rendered && printRef?.current) {
      const focusableElements = printRef.current.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      focusableElements.forEach((element) => {
        element.setAttribute('tabindex', '-1');
        element.addEventListener('focus', (e) => {
          e.preventDefault();
          (e.target as HTMLElement).blur();
        });
      });
    }
  }, [rendered, printRef]);

  return (
    <div
      className="tiptap-preview-content"
      style={{
        border: `1px solid ${theme === 'dark' ? '#444646' : '#DDDFE2'}`,
        borderRadius: '8px',
        padding: '0.5rem',
        height: '100%',
        width: '100%',
        overflow: 'auto',
        position: 'relative',
        outline: 'none',
      }}
      onFocus={(e) => e.target.blur()}
      tabIndex={-1}
      onKeyDown={(e) => {
        if (e.key === 'Tab') {
          e.preventDefault();
        }
      }}
      ref={printRef}
    >
      <div
        tabIndex={-1}
        onKeyDown={(e) => {
          if (e.key === 'Tab') {
            e.preventDefault();
          }
        }}
        style={{
          pointerEvents: 'none',
          userSelect: 'none',
        }}
        className="no-focus"
        dangerouslySetInnerHTML={{ __html: rendered }}
        onFocus={(e) => {
          e.target.blur();
          e.preventDefault();
        }}
      />
    </div>
  );
};

export default React.memo(CustomNunjucksRerender);
