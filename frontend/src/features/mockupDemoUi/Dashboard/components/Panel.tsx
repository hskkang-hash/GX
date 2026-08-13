import React from 'react';
import { useTheme } from 'rj-core';

import Colors from '@/configs/Colors';

interface PanelProps {
  title?: string;
  children: React.ReactNode;
  fullHeight?: boolean;
}

const Panel: React.FC<PanelProps> = ({ title, children, fullHeight }) => {
  const [theme] = useTheme();
  const panelStyle = fullHeight
    ? {
        background: theme === 'dark' ? '#2D2E30' : '#fff',
        border: `1px solid ${theme === 'dark' ? '#232325' : '#e0e0e0'}`,
        borderRadius: 10,
        marginBottom: 20,
        overflow: 'hidden',
        boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
        height: '100%',
        display: 'flex',
        flexDirection: 'column' as const,
      }
    : {
        background: theme === 'dark' ? '#2D2E30' : '#fff',
        border: `1px solid ${theme === 'dark' ? '#232325' : '#e0e0e0'}`,
        borderRadius: 10,
        marginBottom: 20,
        overflow: 'hidden',
        boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
      };
  const contentStyle = fullHeight
    ? {
        padding: 15,
        minHeight: 0,
        flex: 1,
        display: 'flex',
        flexDirection: 'column' as const,
      }
    : {
        padding: 15,
        minHeight: 300,
      };
  return (
    <div
      className="panel"
      style={panelStyle}
    >
      <div
        className="panel-header"
        style={{
          padding: '10px 15px',
          // borderBottom: `1px solid ${theme === "dark" ? "#232325" : "#e0e0e0"}`,
          fontSize: 18,
          color: theme === 'dark' ? Colors.Gray3 : '#333',
          // background: theme === "dark" ? "#18191A" : "#f8f8f8",
        }}
      >
        {title}
      </div>
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
