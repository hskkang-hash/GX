# SPA 정적 서버 — 알 수 없는 경로는 index.html 로 되돌린다(클라이언트 라우팅) · deploy.sh 와 같은 본문
#
# ★ [2026-09-18 · 턴 U · V 가 찾은 거짓 초록의 씨] **`/api/...` 에는 폴백하지 않는다.**
#   종전 본문은 파일이 없고 확장자가 없으면 무엇이든 `index.html` 을 **200** 으로 돌려줬다.
#   그래서 이 서버로 `GET /api/dsm/무엇이든` 을 부르면 **200 + HTML** 이 온다 —
#   상태코드로 「문이 살아 있다」를 세는 도구는 그 200 을 그대로 먹는다(V 실측 · 턴 U).
#   SPA 는 API 를 제 원점에 두지 않는다(번들에 `VITE_API_URL` 이 박힌다) — 그러므로
#   이 서버에 오는 `/api/...` 는 **잘못 온 것**이고, 잘못 온 것에는 404 가 옳다.
#   ⚠ 이것은 제품이 아니라 **게이트용 정적 서버**다. 운영 앞단(nginx)은 `/api` 를 뒷단으로
#     넘긴다 — 그 자리와 헷갈리지 마라.
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.environ.get("GX_LIVE_DIR", "/app/_fe_dist")
PORT = int(os.environ.get("GX_SPA_PORT", "3002"))
NO_FALLBACK = ("/api/", "/api")


class H(SimpleHTTPRequestHandler):
    def _is_api(self):
        path = (self.path or "").split("?", 1)[0]
        return path == "/api" or path.startswith("/api/")

    def translate_path(self, path):
        p = super().translate_path(path)
        if not os.path.exists(p) and "." not in os.path.basename(p) and not self._is_api():
            return os.path.join(ROOT, "index.html")
        return p

    def send_head(self):
        if self._is_api():
            # 404 를 **본문 없이** 낸다 — 이 서버는 API 가 아니라는 사실만 말한다.
            self.send_error(404, "this is the SPA static server, not the API")
            return None
        return super().send_head()

    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)


ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
