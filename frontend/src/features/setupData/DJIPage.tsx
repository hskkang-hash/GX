import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';
import { Container, CustomBtn, HeaderWithBtn, Main } from 'rj-core';

import API, { endpoint } from '../../services/API';

const DJIPage = () => {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const menuId = searchParams.get('menuId');
  const [djiUrl, setDjiUrl] = useState<string | null>(null);
  const headerPageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuId) return;
    const fetchDjiUrl = async () => {
      try {
        const response = await API.get(endpoint.getMenuUrl, {
          params: { menu_id: menuId },
        });
        if (response?.success) {
          window.open(response.text_value, '_blank');
          setDjiUrl(response.text_value);
        }
      } catch (error) {
        setDjiUrl(null);
      }
    };
    fetchDjiUrl();
  }, [menuId]);

  return (
    <Container>
      <HeaderWithBtn
        buttons={[]}
        ref={headerPageRef}
      />
      <Main>
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: `calc(100vh - ${headerPageRef.current?.clientHeight}px)`,
            width: '100%',
          }}
        >
          <CustomBtn
            label={t('Go to DJI Page')}
            size="lg"
            onClick={() => {
              if (djiUrl) {
                window.open(djiUrl, '_blank');
              }
            }}
          />
        </div>
      </Main>
    </Container>
  );
};

export default DJIPage;
