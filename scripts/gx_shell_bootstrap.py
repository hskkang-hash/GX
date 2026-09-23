#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""gx-shell 게이트 서버 자동 기동 — runserver 8000 + SPA 정적 서버 3002.

(P-263 · WO-GX-20260924-08 §5 E · 턴 AE 차선 E)

★ 왜 이 파일이 생겼나 — 재부팅 아침마다 손이 필요했다
------------------------------------------------------
전량 시험·판정기 다수가 `127.0.0.1:8000`(Django `runserver`)과 `127.0.0.1:3002`(SPA 정적
서버)를 gx-shell **안에서** 때린다. 이 둘은 여태 **컨테이너 자신의 기동 방법이 아니라**
`docker exec` 로 사람이 배경에 띄운 프로세스였다:

    python manage.py runserver 0.0.0.0:8000 --noreload   # docker exec 로 배경에 띄움
    python /tmp/gx_spa_server.py                          # docker exec 로 배경에 띄움

★ **`/tmp` 는 컨테이너가 다시 서면 빈다.** 그래서 SPA 서버의 소스 자체가 재부팅 때마다
  사라졌고, 재부팅 아침 준비도 「기계가 스스로 선다」(0/10 → 1/10) 뒤에도 **게이트 서버
  둘은 여전히 사람 손**이었다(P-263 실측). 이 파일은 그 뿌리 둘을 함께 없앤다:
    ① SPA 서버의 소스를 저장소 **안**(`scripts/gx_shell_bootstrap.py`)으로 옮긴다 —
       `/tmp` 가 아니라 `./scripts:/repo/scripts:ro` 로 컨테이너에 마운트되어 있으므로
       컨테이너가 다시 서도 사라지지 않는다.
    ② 이 파일 **자체가 gx-shell 의 entrypoint** 가 되면(`docker-compose.yml` 의 `shell`
       서비스), 컨테이너가 설 때 **이 파일이 스스로** 둘 다 띄운다 — 사람이 두 번
       `docker exec` 할 필요가 없다.

★★ ⚠ 이 턴에서는 **gx-shell 을 재생성하지 않는다** (WO-08 §5 E · 「gx-shell 컨테이너를
  재생성하지 마라」). 그래서 이 파일과 `docker-compose.yml` 의 배선은 **다음에 gx-shell 이
  다시 설 때**부터 효과가 있다 — 지금 도는 gx-shell(PID 35 `runserver` · PID 86
  `/tmp/gx_spa_server.py`)은 그대로 둔다. 「이렇게 하면 선다」는 조율자.inbox/E.md 에 적는다.

★ 자동 migrate 를 다시 열지 않는다 (D-283 · D-270)
---------------------------------------------------
gx-shell 이 `entrypoint: ["sleep"]` 로 이미지의 진짜 `/entrypoint.sh`(무조건
`manage.py migrate` 를 부른다)를 끊어 둔 이유가 있다 — 2026-08-27 사고. 이 파일은
**`migrate` 를 부르지 않는다.** `runserver` 와 SPA 정적 서버, 그 둘뿐이다.

무엇을 띄우나 — 둘
------------------
  ① `python manage.py runserver 0.0.0.0:8000 --noreload` — 게이트가 때리는 API 서버.
     자식 프로세스로 띄우고, 그 프로세스가 죽으면 **이 스크립트도 같이 끝난다** —
     "컨테이너는 떠 있는데 API 는 죽어 있다"는 착시를 만들지 않는다.
  ② SPA 정적 서버(3002) — **로직은 `/tmp/gx_spa_server.py` 와 한 글자도 다르지 않다**
     (턴 U · `deploy.sh` 짝 · V 가 찾은 「200 위장」 거짓 초록의 씨를 막는 `/api` 404 포함).
     옮겼을 뿐 고치지 않았다 — 옮기면서 뜻이 바뀌면 그것도 조용한 회귀다.

    (참고 — 이 컨테이너 밖에서 부르는 법, 사람이 재부팅 뒤 손으로 확인할 때):
        docker exec gx-shell sh -c "ps aux | grep -E 'runserver|gx_shell_bootstrap'"
        curl -sf http://127.0.0.1:8000/api/health/ -o /dev/null && echo API_OK
        curl -sf http://127.0.0.1:3002/ -o /dev/null && echo SPA_OK

되돌림: 이 파일은 **읽기만** 하고 새 프로세스 둘만 띄운다. DB·저장소·볼륨을 건드리지 않는다.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

#: SPA 정적 서버가 섬기는 자리. `/tmp/gx_spa_server.py` 와 같은 기본값 — 옮기면서
#: 바꾸면 그것도 조용한 변경이다.
SPA_ROOT = os.environ.get("GX_LIVE_DIR", "/app/_fe_dist")
SPA_PORT = int(os.environ.get("GX_SPA_PORT", "3002"))
API_HOST_PORT = os.environ.get("GX_RUNSERVER_BIND", "0.0.0.0:8000")
#: manage.py 가 사는 자리. `docker-compose.yml` 의 `shell` 서비스는 `./backend:/app` 이다.
APP_DIR = os.environ.get("GX_APP_DIR", "/app")


class _SpaHandler(SimpleHTTPRequestHandler):
    """SPA 정적 서버 — 알 수 없는 경로는 index.html 로 되돌린다(클라이언트 라우팅).

    ★ [턴 U · V 가 찾은 거짓 초록의 씨] **`/api/...` 에는 폴백하지 않는다.** 파일이
      없고 확장자가 없다고 무엇이든 `index.html` 을 200 으로 돌려주면, 상태코드로만
      「문이 살아 있다」를 세는 도구는 그 200 을 그대로 삼킨다. SPA 는 API 를 제 원점에
      두지 않는다(번들에 `VITE_API_URL` 이 박힌다) — 그러므로 이 서버에 오는 `/api/...`
      는 **잘못 온 것**이고, 잘못 온 것에는 404 가 옳다.
    ⚠ 이것은 제품이 아니라 **게이트용 정적 서버**다. 운영 앞단(nginx)은 `/api` 를
      뒷단으로 넘긴다 — 그 자리와 헷갈리지 마라.
    """

    def _is_api(self):
        path = (self.path or "").split("?", 1)[0]
        return path == "/api" or path.startswith("/api/")

    def translate_path(self, path):
        p = super().translate_path(path)
        if not os.path.exists(p) and "." not in os.path.basename(p) and not self._is_api():
            return os.path.join(SPA_ROOT, "index.html")
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
        super().__init__(*a, directory=SPA_ROOT, **k)


def _run_spa_server() -> None:
    ThreadingHTTPServer(("0.0.0.0", SPA_PORT), _SpaHandler).serve_forever()


def main() -> int:
    #: ① runserver — **migrate 는 안 부른다.** `--noreload` 는 기존 손 기동과 같다
    #:   (자동 리로드가 파일 변경 감시로 컨테이너 CPU 를 계속 문다 — 게이트용 서버에는
    #:   필요 없다).
    host, _, port = API_HOST_PORT.rpartition(":")
    runserver = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", "%s:%s" % (host or "0.0.0.0", port),
         "--noreload"],
        cwd=APP_DIR,
    )

    #: ② SPA 서버 — daemon 스레드로 띄운다. 메인 스레드는 ①을 기다린다.
    threading.Thread(target=_run_spa_server, daemon=True).start()

    #: runserver 가 죽으면(코드 오류 등) 이 프로세스도 같이 끝난다 — "컨테이너는
    #: 떠 있는데 API 는 죽어 있다" 는 착시를 만들지 않는다. `restart: unless-stopped`
    #: 가 걸려 있으면 컨테이너가 다시 서고, 그때 이 스크립트가 다시 둘을 띄운다.
    return runserver.wait()


if __name__ == "__main__":
    raise SystemExit(main())
