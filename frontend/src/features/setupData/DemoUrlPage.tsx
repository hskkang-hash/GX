import { useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Container, useLoadingContext, useTheme } from 'rj-core';

import API, { endpoint } from '@/services/API';

// Đối tượng này sẽ lưu trữ tất cả các iframe đã được tạo
const iframeStore = {};
const DemoUrlPage = () => {
  const { showLoading, hideLoading } = useLoadingContext();
  const [theme] = useTheme();
  const [searchParams] = useSearchParams();
  const menuId = searchParams.get('menuId');
  // Sử dụng ref để theo dõi tất cả các iframe đã tạo
  const iframesContainerRef = useRef<HTMLDivElement>(null);
  const activeIframeRef = useRef<HTMLIFrameElement | null>(null);

  // Hàm này sẽ ẩn tất cả các iframe và chỉ hiển thị iframe cho menuId hiện tại
  const showActiveIframe = (id: string) => {
    if (!iframesContainerRef.current) return;

    // Ẩn tất cả các iframe
    const allIframes = iframesContainerRef.current.querySelectorAll('iframe');
    allIframes.forEach((iframe: { style: { display: string } }) => {
      iframe.style.display = 'none';
    });

    // Hiển thị iframe hiện tại
    const currentIframe = iframesContainerRef.current.querySelector(
      `#iframe-${id}`,
    );
    if (currentIframe) {
      currentIframe.style.display = 'block';
      activeIframeRef.current = currentIframe;
    }
  };

  useEffect(() => {
    if (!menuId) return;
    const fetchAndSetupIframe = async () => {
      showLoading();

      if (!iframesContainerRef.current) {
        return;
      }

      // Kiểm tra xem iframe cho menuId này đã tồn tại chưa
      const existingIframe = iframesContainerRef.current.querySelector(
        `#iframe-${menuId}`,
      ) as HTMLIFrameElement;

      // if (existingIframe) {
      //   // Nếu đã tồn tại, kiểm tra xem nó đã load xong chưa
      //   try {
      //     // Kiểm tra readyState có thể fail do CORS, nên wrap trong try-catch
      //     if (existingIframe.contentDocument?.readyState === 'complete') {
      //       showActiveIframe(menuId);
      //       return;
      //     }
      //   } catch (e) {
      //     // CORS error hoặc lỗi khác, tiếp tục với onload handler
      //   }

      //   // Nếu chưa load xong hoặc không thể kiểm tra, đợi nó load
      //   // Kiểm tra xem onload đã được set chưa để tránh set nhiều lần
      //   if (!existingIframe.onload) {
      //     existingIframe.onload = () => {
      //       showActiveIframe(menuId);
      //     };
      //   } else {
      //     // Nếu onload đã được set, có thể iframe đang load, chỉ cần show và hide loading
      //     showActiveIframe(menuId);
      //   }

      //   return;
      // }

      try {
        const response = await API.get(endpoint.getMenuUrl, {
          params: { menu_id: menuId },
        });

        if (response?.success) {
          const url = response.text_value;

          // Tạo iframe mới và thêm vào container
          const newIframe = document.createElement('iframe');
          newIframe.id = `iframe-${menuId}`;
          newIframe.style.width = '100%';
          newIframe.style.height = '100vh';
          newIframe.style.border = 'none';
          newIframe.style.display = 'none'; // Ẩn ban đầu

          // Xử lý khi iframe đã tải xong
          newIframe.onload = () => {
            console.log('IFRAME LOADED:', menuId, performance.now());
            showActiveIframe(menuId);
            // TODO: temporary fix, because iframe is not paint on screen immediately
            const timeout = setTimeout(() => {
              hideLoading();
              clearTimeout(timeout);
            }, 3300);
          };

          // Xử lý lỗi khi load iframe
          newIframe.onerror = () => {
            console.error('Error loading iframe:', url);
          };

          // Thêm iframe vào container trước khi set src
          iframesContainerRef.current.appendChild(newIframe);

          // Set src sau khi đã append và set handler
          newIframe.src = url;

          // Lưu URL vào store để tham khảo sau này nếu cần
          iframeStore[menuId] = { url };
        }
      } catch (error) {
        console.error('Error fetching iframe URL:', error);
      }
    };

    if (menuId) {
      fetchAndSetupIframe();
    }
  }, [menuId]);

  return (
    <Container
      id="home-page"
      className={`home-ads bg-${theme === 'dark' ? 'black' : 'light'}`}
    >
      <div className="home-page">
        {iframesContainerRef && (
          <div
            ref={iframesContainerRef}
            style={{ width: '100%', height: '100vh' }}
          />
        )}
      </div>
    </Container>
  );
};

export default DemoUrlPage;
