import { useMemo } from 'react';
import { useUserInfo } from 'rj-core';

export const CheckRoleAccount = (roleCheck: string) => {
  const userInfo = useUserInfo();
  const isRole = useMemo(
    () =>
      (userInfo as { roles: { code: string }[] })?.roles?.some(
        (role: { code: string }) => role.code === roleCheck,
      ),
    [userInfo, roleCheck],
  );
  return isRole;
};
