import React from 'react';
import { IconType } from 'react-icons';
import {
  FaTools,
  FaTasks,
  FaRoute,
  FaChartLine,
  FaShippingFast,
} from 'react-icons/fa';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

interface StatBoxProps {
  icon: IconType;
  title: string;
  value: React.ReactNode;
  unit?: string;
}

const StatBox: React.FC<StatBoxProps> = ({
  icon: Icon,
  title,
  value,
  unit,
}) => {
  const [theme] = useTheme();

  return (
    <div
      className="stat-box"
      style={{
        flex: 1,
        background: theme === 'dark' ? Colors.Black : '#fff',
        border: `1px solid ${theme === 'dark' ? Colors.Gray7 : '#e0e0e0'}`,
        borderRadius: 5,
        padding: 15,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
      }}
    >
      <div
        className="stat-icon"
        style={{
          width: 70,
          height: 70,
          borderRadius: '50%',
          background: theme === 'dark' ? Colors.Gray7 : '#f0f0f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: `1px solid ${theme === 'dark' ? Colors.Gray6 : '#e0e0e0'}`,
          fontSize: 30,
          color: '#4169e1',
        }}
      >
        <Icon />
      </div>
      <div
        className="stat-info"
        style={{ textAlign: 'right' }}
      >
        <div
          className="stat-title"
          style={{
            fontSize: 16,
            marginBottom: 5,
            color: theme === 'dark' ? Colors.Gray3 : '#666',
          }}
        >
          {title}
        </div>
        <div
          className="stat-value"
          style={{ fontSize: 32, fontWeight: 'bold', color: '#4169e1' }}
        >
          {value}
        </div>
        {unit && (
          <div
            className="stat-unit"
            style={{
              fontSize: 14,
              color: theme === 'dark' ? Colors.Gray3 : '#666',
            }}
          >
            {unit}
          </div>
        )}
      </div>
    </div>
  );
};

export default StatBox;
