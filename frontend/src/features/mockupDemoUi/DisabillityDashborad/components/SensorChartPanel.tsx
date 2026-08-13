import React from 'react';
import { Col } from 'react-bootstrap';
import { useTheme } from 'rj-core';

import Colors from '../../../../configs/Colors';

interface AxisData {
  label: string;
  icon: string;
  value: string;
}

interface SensorChartPanelProps {
  title: string;
  chartData: number[];
  axisData: AxisData[];
}

const SensorChartPanel: React.FC<SensorChartPanelProps> = ({
  title,
  chartData,
  axisData,
}) => {
  const [theme] = useTheme();

  return (
    <div
      style={{
        background: theme === 'dark' ? Colors.Black : '#fff',
        borderRadius: 5,
        border: '1px solid #e0e0e0',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        marginBottom: 5,
      }}
    >
      <h4
        style={{
          margin: '10px 0',
          fontSize: 16,
          color: theme === 'dark' ? Colors.Gray3 : '#333',
          textAlign: 'left',
        }}
      >
        <span
          style={{
            display: 'inline-block',
            width: 24,
            height: 24,
            background: theme === 'dark' ? '#2D2E30' : '#f8f8f8',
            borderRadius: '50%',
            marginRight: 5,
            verticalAlign: 'middle',
            position: 'relative',
          }}
        >
          <span
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%,-50%)',
              width: 12,
              height: 12,
              background: '#1D9BE2',
              borderRadius: '50%',
            }}
          />
        </span>
        {title}
      </h4>
      <div
        style={{
          width: '100%',
          height: 80,
          background: theme === 'dark' ? '#2D2E30' : '#f8f8f8',
          border: '1px solid #e0e0e0',
          borderRadius: 3,
          position: 'relative',
          marginTop: 10,
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'flex-end',
        }}
      >
        {chartData.map((h, i) => (
          <div
            key={i}
            style={{
              flex: 1,
              background: '#1D9BE2',
              margin: '0 1px',
              height: `${h}%`,
              boxShadow: '0 0 5px rgba(29,155,226,0.5)',
            }}
          />
        ))}
      </div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 10,
          margin: '10px 0',
        }}
      >
        {axisData.map((item) => (
          <div
            key={item.label}
            style={{
              background: theme === 'dark' ? '#2D2E30' : '#f8f8f8',
              border: '1px solid #e0e0e0',
              borderRadius: 3,
              padding: 20,
              position: 'relative',
              textAlign: 'center',
            }}
          >
            <div
              style={{
                position: 'absolute',
                left: 10,
                top: '50%',
                transform: 'translateY(-50%)',
                width: 30,
                height: 30,
                border: '2px solid #1D9BE2',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <span
                style={{
                  color: '#1D9BE2',
                  fontWeight: 'bold',
                  fontSize: 14,
                }}
              >
                {item.icon}
              </span>
            </div>
            <span
              style={{
                fontWeight: 'bold',
                fontSize: 16,
                color: theme === 'dark' ? Colors.Gray3 : '#333',
              }}
            >
              {item.label}
            </span>
            <br />
            <span
              style={{
                color: '#1D9BE2',
                fontSize: 16,
                marginTop: 5,
                display: 'inline-block',
              }}
            >
              {item.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SensorChartPanel;
