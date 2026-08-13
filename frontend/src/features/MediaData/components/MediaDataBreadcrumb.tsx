import React, { Fragment, forwardRef } from 'react';
import { Breadcrumb } from 'react-bootstrap';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import './MediaDataBreadcrumb.scss';

interface BreadcrumbItem {
  url?: string;
  text?: string;
  func?: () => void;
  fullObjectName?: string;
}

interface MediaDataBreadcrumbProps {
  items: BreadcrumbItem[];
  buttons?: React.ReactNode[];
}

export const MediaDataBreadcrumb = forwardRef<
  HTMLDivElement,
  MediaDataBreadcrumbProps
>(({ items, buttons = [] }, ref) => {
  const [theme] = useTheme();
  const { t } = useTranslation();

  return (
    <Fragment>
      <div
        className={`media-data-breadcrumb-area text-${
          theme === 'dark' ? 'white' : 'black'
        }`}
        data-bs-theme={theme === 'dark' ? 'dark' : 'light'}
        ref={ref}
      >
        <Breadcrumb>
          {items.map((item, index) => (
            <Breadcrumb.Item
              key={index}
              active={index === items.length - 1}
              className={`text-${theme === 'dark' ? 'white' : 'black'}`}
              onClick={item?.func}
              style={{
                cursor: item?.func ? 'pointer' : 'default',
              }}
            >
              {index === 0 && !item?.text
                ? t('All')
                : item?.text
                  ? t(item.text)
                  : ''}
            </Breadcrumb.Item>
          ))}
        </Breadcrumb>
        {buttons.length > 0 && (
          <div className="buttons-container">{buttons}</div>
        )}
      </div>
    </Fragment>
  );
});

MediaDataBreadcrumb.displayName = 'MediaDataBreadcrumb';
