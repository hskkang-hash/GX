import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Container } from 'rj-core';

import API, { endpoint } from '@/services/API';

const DemoPage = () => {
  const [menuHtml, setMenuHtml] = useState<string | null>(null);
  const [searchParams] = useSearchParams();
  const menuId = searchParams.get('menuId') || localStorage.getItem('menuId');
  useEffect(() => {
    if (menuId) {
      localStorage.setItem('menuId', menuId);
    }
  }, [menuId]);

  useEffect(() => {
    const fetchHTML = async () => {
      if (!menuId) {
        setMenuHtml(null);
        return;
      }

      try {
        const response = await API.get(endpoint.getMenuHtml, {
          params: { menu_id: menuId },
        });

        if (response) {
          setMenuHtml(response);
        } else {
          setMenuHtml(null);
        }
      } catch (error) {
        console.error('error', error);
        setMenuHtml(null);
      }
    };

    fetchHTML();
  }, [menuId]);

  return (
    <Container
      id="demo-page"
      className="home-page"
    >
      <div className="home-page">
        {menuHtml && (
          <iframe
            srcDoc={menuHtml}
            style={{
              width: '100%',
              height: '100vh',
              border: 'none',
            }}
          />
        )}
      </div>
    </Container>
  );
};

export default DemoPage;
