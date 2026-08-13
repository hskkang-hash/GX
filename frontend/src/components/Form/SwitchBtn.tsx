import { Switch } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { useMenuData, useTheme, checkPermission } from 'rj-core';
import styled from 'styled-components';

import Colors from '@/configs/Colors';

const SwitchStyle = styled(Switch)`
  min-width: 41px !important;
  height: 18px !important;
  line-height: 18px !important;
  background-color: ${(props) =>
    props.theme == 'dark' ? '' : '#dddfe2'} !important;

  .ant-switch-handle {
    width: 14px;
    height: 14px;
  }

  &.ant-switch-checked {
    background-color: ${Colors.Primary} !important;
    .ant-switch-handle {
      left: calc(100% - 16px);
    }
  }

  .ant-switch-loading-icon {
    font-size: 10px !important;
    width: 10px !important;
    height: 10px !important;
    line-height: 10px !important;
    display: flex;
    align-items: center;
    justify-content: center;
    left: calc(100% - 12px);
  }
`;

const SwitchBtn = ({
  statusValue,
  onChange,
  label,
  loading,
  usePermission = true,
  actionType = null,
}: {
  statusValue: boolean;
  onChange?: () => void;
  label?: string;
  loading?: boolean;
  usePermission?: boolean;
  actionType?: string | null;
}) => {
  const [theme] = useTheme();
  const [value, setValue] = useState(statusValue);
  const [menuData] = useMenuData();
  const [notAvailable, setNotAvailable] = useState(false);
  const hasPermission = useMemo(() => {
    if (!usePermission) return true;
    if (!actionType || !menuData || menuData.length === 0) return true;
    return checkPermission(actionType, menuData);
  }, [usePermission, actionType, menuData]);

  useEffect(() => {
    if (!loading) {
      setValue(statusValue);
    }
  }, [statusValue, loading]);

  useEffect(() => {
    if (usePermission && !hasPermission) {
      setNotAvailable(true);
    }
  }, [usePermission, hasPermission]);

  const handleChange = (checked: boolean) => {
    if (!loading && !notAvailable) {
      setValue(checked);
      onChange?.();
    }
  };
  return (
    <div
      style={{ width: 'fit-content' }}
      onClick={(e) => {
        e.stopPropagation();
      }}
    >
      <SwitchStyle
        theme={theme}
        checked={value}
        onChange={handleChange}
        loading={loading}
        disabled={loading || notAvailable}
      />
    </div>
  );
};
export default SwitchBtn;
