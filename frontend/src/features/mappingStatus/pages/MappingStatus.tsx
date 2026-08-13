import { useMemo } from 'react';
import { useUserInfo } from 'rj-core';

import NonSuperuserMappingStatus from './NonSuperuserMappingStatus';
import SuperuserMappingStatus from './SuperuserMappingStatus';

const MappingStatus = () => {
  const userInfo = useUserInfo();
  const isSuperuser = useMemo(
    () => userInfo?.roles?.some((role: any) => role.code === 'superuser'),
    [userInfo],
  );

  if (isSuperuser) {
    return <SuperuserMappingStatus />;
  }

  return <NonSuperuserMappingStatus />;
};

export default MappingStatus;
