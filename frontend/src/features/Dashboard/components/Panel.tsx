import React from 'react';
import { useTheme } from 'rj-core';

import Colors, { cardBg } from '@/configs/Colors';

interface PanelProps {
  title?: string;
  children: React.ReactNode;
  fullHeight?: boolean;
  panelStyles?: React.CSSProperties;
  contentStyles?: React.CSSProperties;
  shouldHaveAspectRatio?: boolean;
}

const Panel: React.FC<PanelProps> = ({
  title,
  children,
  fullHeight,
  panelStyles,
  contentStyles,
  shouldHaveAspectRatio = true,
}) => {
  const [theme] = useTheme();

  const panelStyle: React.CSSProperties = {
    background: cardBg[theme === 'dark' ? 'dark' : 'light'],
    borderRadius: 10,
    // overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    position: 'relative',
    ...(shouldHaveAspectRatio && { aspectRatio: '69 / 50' }),
    ...(fullHeight && { height: '100%' }),
    ...panelStyles,
  };

  const contentStyle: React.CSSProperties = {
    padding: 'calc( (20 / 1920) * 100vw)',
    flex: 1,
    minHeight: 0,
    display: 'flex',
    flexDirection: 'column',
    // overflow: 'hidden',
    ...contentStyles,
  };

  return (
    <div
      className="panel"
      style={panelStyle}
    >
      {title && (
        <div
          className="panel-header"
          style={{
            padding: '10px 15px',
            fontSize: 18,
            color: theme === 'dark' ? Colors.Gray3 : '#333',
            flexShrink: 0,
            borderBottom: `1px solid ${theme === 'dark' ? '#232325' : '#e0e0e0'}`,
          }}
        >
          {title}
        </div>
      )}
      <div
        className="panel-content"
        style={contentStyle}
      >
        {children}
      </div>
    </div>
  );
};

export default Panel;
