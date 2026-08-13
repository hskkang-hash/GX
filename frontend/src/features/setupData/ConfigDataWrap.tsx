import { useEffect } from 'react';
import { useRootRouterPath } from 'rj-core';

import { CustomRoutes } from '../../services/API';

const ConfigDataWrap = ({ children }: { children: React.ReactNode }) => {
  const [_, updateRootRouterPath] = useRootRouterPath();

  useEffect(() => {
    const formatRouterPath = Object.values(CustomRoutes)
      .filter((item) => typeof item === 'object' && item !== null)
      .map((item) => {
        return {
          label: item.title,
          value: item.path,
        };
      });

    updateRootRouterPath(formatRouterPath);
  }, []); // Empty dependency array means this effect runs once after initial render

  return <>{children}</>;
};

export default ConfigDataWrap;
