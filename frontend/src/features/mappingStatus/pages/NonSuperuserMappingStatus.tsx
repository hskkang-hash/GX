import { useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Container, HeaderWithBtn, Main, useUserInfo } from 'rj-core';

import MappingStatusDetailView from '../components/MappingStatusDetailView';

const NonSuperuserMappingStatus = () => {
  const { t } = useTranslation();
  const headerPageRef = useRef<HTMLDivElement>(null);
  const userInfo = useUserInfo();

  const userGroupId = userInfo?.profile__group_id;
  const userGroupName = userInfo?.profile__group__name;

  if (!userGroupId) {
    return (
      <Container id="list-order-status">
        <HeaderWithBtn ref={headerPageRef} />
        <Main>
          <div style={{ padding: '2rem' }}>
            {t('No group assigned to your account')}
          </div>
        </Main>
      </Container>
    );
  }

  return (
    <Container id="list-order-status">
      <HeaderWithBtn ref={headerPageRef} />
      <Main>
        <MappingStatusDetailView
          groupId={userGroupId}
          groupName={userGroupName}
        />
      </Main>
    </Container>
  );
};

export default NonSuperuserMappingStatus;
