# P-412 — `gx-portfwd` 를 지우기 전에 게이트 주소를 옮긴다 (턴 AO · 2026-09-30 · 조율자 E)

## 무엇이 그 다리를 탔나 — 정적 대조 [실측 · 코드 읽기]

`ga_readiness.yaml` 의 게이트 중 소스에 `localhost:8000` / `127.0.0.1:8000` 을 품은 것은 7개다.

| 게이트 | 도는 자리 | 다리를 타나 |
|---|---|---|
| `verify_authn_paths.py` | `GX_ROUTE_CONTAINER`(=gx-shell · `.env.gates`)가 있으면 컨테이너 안에서 다시 돈다 — 그 안의 8000 은 runserver | 아니다 |
| `gate_fake_bearer_regression.py` · `verify_live_code.py` · `verify_perf_budget.py` · `verify_prod_settings.py` · `verify_sidebar.py` | docker exec 위임(gx-shell 안) · 또는 8000 을 이름으로만 적음 | 아니다 |
| **`verify_ui_secrets.py --api`**(SEC-17) | **호스트에서 직접** `GX_API`(= 컨테이너 안 주소 `localhost:8000`)를 두드렸다 | **탔다** |

## 옮김

`scripts/verify_ui_secrets.py::scan_api` 가 호스트(`/.dockerenv` 없음)에서는 이렇게 읽는다.
- `GX_API_PUBLIC` 이 있으면 그것.
- 없고 `GX_API` 가 `localhost:8000` 이면 **`http://localhost:8500`**(nginx 앞문 · 같은 뒷단).
- `[입력]` 줄에 쓴 주소를 찍는다.
- 판정 규칙은 무변경이다.

**결과**(`--api` · 8500): 로그인 200 · 라우트 6개 응답 본문 · 걸린 자리 0 · **exit 0**.
- 턴 AN GA 에서 SEC-17 은 「못 쟀다(회색)」였다.
- 이 옮김으로 그 면이 처음 재졌다 — 회색 → 초록은 **다리가 아니라 주소가 바뀐 것**이다.

## 곁 사실 — 조율자 실수

조율자의 스크래치 실행기가 `.env.gates` 의 `${…}` 참조를 안 펼쳐, 8500 로그인이 두 번 400 이었다(메모리 `guardianx-gate-credentials` 에 이미 적힌 함정).
- 셋째 시도는 펼쳐서 200 이 났고, 실패 카운터는 성공으로 초기화됐다.
- 판정기 자신의 로더는 펼친다 — 제품·게이트 결함 아님.

## 지우기

- 분류기가 `docker stop gx-portfwd` 를 막았다(「작업 부하 방해」). 삭제는 대표 결정(09-29 「지워라」)이 있다.
- 이 대화창에서 대표 한 줄이 오면 순서는 이렇다:
  1. `docker rm -f gx-portfwd`
  2. GA 재실행 — 같은 수 또는 SEC-17 초록
  3. 되돌리기 한 줄 기록
- 되돌리기(스크립트는 스크래치 바인드 — 지우는 날 금고 `C:\GuardianX-vault\recreate\gx_portfwd.py` 로 옮긴다):
  `MSYS_NO_PATHCONV=1 docker run -d --name gx-portfwd --network gx-main-network -p 127.0.0.1:3002:3002 -p 127.0.0.1:8000:8000 -v C:/GuardianX-vault/recreate/gx_portfwd.py:/gx_portfwd.py:ro --entrypoint python guardianx-backend:latest /gx_portfwd.py`
- inspect 원본: `C:\GuardianX-vault\recreate\gx-portfwd.inspect.json`.

## 삭제 집행 — 2026-09-29 17:5x (대표 「gx-portfwd 지워라」 · 대화창)
- `docker rm -f gx-portfwd` → 남은 컨테이너 0 · 호스트 `localhost:8000` 닫힘(000) · 8500 건강 200.
- GA 재대조: 상용 **61.1 %**(전과 같음) · 닫힌 절 127/208(같음) · FAIL 0 · 「못 쟀다」 줄 6 → 6(차이 0).
- 되돌리기 한 줄은 위 §지우기 그대로(스크립트 · inspect 는 금고).
