import { DownOutlined } from '@ant-design/icons';
import {
  Collapse,
  CollapseProps,
  ConfigProvider,
  theme as antdTheme,
} from 'antd';

import '../assets/styles/CustomCollapse.scss';

const CustomCollapse = ({
  items,
  defaultActiveKey,
  activeKey,
  setActiveKey,
  showExpandAll = false,
  colorLight = '#ECECEF',
  colorDark = '#2D2E30',
  theme = 'light',
}: {
  items: CollapseProps['items'];
  defaultActiveKey?: number[] | string[];
  activeKey?: number[] | string[];
  setActiveKey?: (key: number[] | string[]) => void;
  showExpandAll?: boolean;
  colorLight?: string;
  colorDark?: string;
  theme?: 'light' | 'dark';
}) => {
  const { token } = antdTheme.useToken();

  const panelStyle: React.CSSProperties = {
    marginBottom: '1rem',
    border: 'none',
    background: theme === 'dark' ? colorDark : colorLight,
    borderRadius: token.borderRadiusLG,
  };

  const handleChangeActiveKey = (key: string[]) => {
    setActiveKey?.(key);
  };

  return (
    <ConfigProvider
      theme={{
        components: {
          Collapse: {
            headerBg: theme === 'dark' ? colorDark : colorLight,
          },
        },
        token: {
          colorText: theme === 'dark' ? colorLight : colorDark,
        },
      }}
    >
      <Collapse
        className={`custom-collapse-antd ${theme}`}
        items={items?.map((item) => ({ ...item, style: panelStyle })) || []}
        bordered={false}
        accordion={!showExpandAll}
        defaultActiveKey={defaultActiveKey}
        activeKey={activeKey}
        onChange={handleChangeActiveKey}
        expandIconPosition="end"
        expandIcon={({ isActive }) => (
          <DownOutlined rotate={isActive ? 0 : -180} />
        )}
      />
    </ConfigProvider>
  );
};

export default CustomCollapse;
