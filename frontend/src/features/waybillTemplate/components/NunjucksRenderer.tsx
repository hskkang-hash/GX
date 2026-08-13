import nunjucks from 'nunjucks';
import { useTheme } from 'rj-core';

import { preprocessTemplate } from '../../../utils/templateUtils';

const NunjucksRenderer = ({
  template,
  data,
  printRef,
}: {
  template: string;
  data: Record<string, any>;
  printRef?: React.RefObject<HTMLDivElement>;
}) => {
  const [theme] = useTheme();
  let renderedHtml = '';

  try {
    nunjucks.configure({ autoescape: true });

    // Pre-process template for consistency
    const processedTemplate = preprocessTemplate(template);

    renderedHtml = nunjucks.renderString(processedTemplate, data);
  } catch (error) {
    console.error('Template render error:', error);
    renderedHtml = `<pre style="color: red;">Template render error! Please check the template again.</pre>`;
  }

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
      }}
      ref={printRef}
    >
      <div
        style={{
          pointerEvents: 'none',
          userSelect: 'none',
        }}
        dangerouslySetInnerHTML={{ __html: renderedHtml }}
      />
    </div>
  );
};

export default NunjucksRenderer;
