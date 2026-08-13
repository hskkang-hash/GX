import { CaretDownOutlined, CaretUpOutlined } from '@ant-design/icons';
import { Button, ConfigProvider, Dropdown, MenuProps, Space } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

const ButtonStatus = ({
  color,
  backgroundColor,
  border,
  items,
  label,
}: {
  color?: string;
  backgroundColor?: string;
  border?: string;
  items: MenuProps['items'];
  label: string;
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [hover, setHover] = useState<boolean>(false);

  const handleMenuClick: MenuProps['onClick'] = (e) => {
    // Prevent row onClick when selecting a menu item
    e.domEvent.stopPropagation();
  };

  return (
    <ConfigProvider
      theme={{
        components: {
          Dropdown: {
            /* here is your component tokens */
            paddingBlock: 2,
          },
          Button: {
            paddingInline: 8,
            defaultBg: backgroundColor,
            defaultBorderColor: border,
            defaultColor: color,
            defaultHoverBg: backgroundColor,
            defaultHoverBorderColor: border,
            defaultHoverColor: color,
            fontWeight: 600,
            contentLineHeight: 1.2,
            contentFontSize: 12,
          },
        },
        token: {
          controlHeight: 25,
          colorBgElevated: theme === 'dark' ? '#1F1F20' : '#FFFFFF',
          controlItemBgHover: theme === 'dark' ? '#2D2E30' : '#ECECEF',
          colorText: theme === 'dark' ? '#FFFFFF' : '#000000',
          controlItemBgActive: theme === 'dark' ? '#2D2E30' : '#ECECEF',
          controlItemBgActiveHover: theme === 'dark' ? '#1F1F20' : '#FFFFFF',
        },
      }}
    >
      <Dropdown
        menu={{
          items: items,
          onClick: handleMenuClick,
        }}
        onOpenChange={(open) => {
          setHover(open);
        }}
        overlayStyle={{
          borderRadius: 8,
        }}
      >
        <Button
          onClick={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
          onPointerDown={(e) => e.stopPropagation()}
          style={{
            backgroundColor: backgroundColor,
            color: color,
            border: `1px solid ${border}`,
          }}
        >
          <Space>
            {t(label)}
            {hover ? <CaretUpOutlined /> : <CaretDownOutlined />}
          </Space>
        </Button>
      </Dropdown>
    </ConfigProvider>
  );
};

export default ButtonStatus;
