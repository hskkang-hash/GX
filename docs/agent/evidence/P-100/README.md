# P-100 — 권한 거절이 500 + pydantic 역추적이던 자리 (2026-09-07 · 차선 Backend/DB)

> 이 문서의 수는 전부 **실측**이다. 잰 명령과 원문 파일을 같이 적었다.
> 잰 서버: `http://localhost:8000` (컨테이너 `gx-shell` · `runserver --noreload` · `config.settings`)
> 잰 계정: `gxseed_u4_official` (역할 `view_only_-_anyang`) · 로그인 `POST /api/v1/auth/login` + `end_previous_session:true`

## 1. 전 → 후 (그 라우트)

| | 전 [2026-09-07 09:39 UTC] | 후 [2026-09-07 10:15 UTC] |
|---|---|---|
| `GET /api/report-template/` | **HTTP 500** · text/plain 951바이트 | **HTTP 403** · JSON 328바이트 |
| `GET /api/report-template` (슬래시 없음) | (전에는 안 쟀다) | **HTTP 403** |
| `GET /api/report-template/1` | HTTP **200** + 봉투 `{"success":false,"status_code":403}` | **HTTP 403** |
| 본문 표지 | `Traceback` · `pydantic` · `File "` · `site-packages` · `/usr/local/lib` 다 있음 | **0개** |

원문: `before.json` · `after.json` · `after_nocache.json`

캐시 처리: **우회 + 대조**. 같은 순간에 헤더 없이 한 번(`after.json`), `X-No-Cache: true` 로
한 번(`after_nocache.json`) 때렸고 **네 자리 다 같은 수**였다 — 적중 본문이 답을 덮은 것이
아니다(D-341 착시 ⑦). 재기동도 확인했다: `scripts/verify_live_freshness.py --api http://localhost:8000`
→ `기동 2026-09-07 19:11:35 · 소스 최신 18:58:32` **초록**.

## 2. 같은 순간 3판 대조 — 무엇이 무엇을 고쳤나

같은 코드 · 같은 계정 · 같은 분에, **설정 두 지렛대만** 다르게 세 서버를 띄워서 쟀다.

| 판 | `API_CONTRACT_PROMOTE_PATHS` | `SAFE_ERROR_BODY` | 결과 | 표지 |
|---|---|---|---|---|
| :8020 | report-template **없음** | `false` | **500** · 951B | `Traceback` `pydantic` `File "` `site-packages` `/app/` `/usr/local/lib` |
| :8030 | report-template **없음** | `true`  | **500** · 170B | **0개** |
| :8000 | report-template **있음** | `true`  | **403** · 328B | **0개** |

원문: `control_8020_both_levers_reverted.json` · `control_8030_global_rule_only.json` ·
`control_8000_shipped.json`

읽는 법 — **두 반쪽이 서로를 안 덮는다**:
- 8020 이 고치기 전 그 판이다. 되돌리기가 실제로 되돌린다는 것도 이 줄이 증명한다(D-212).
- 8030 은 **전역 규칙만** 켠 판이다. 상태는 여전히 500 이지만 본문에 내부가 **없다** —
  즉 전역 절반은 라우트별 고침 없이도 혼자 성립한다.
- 8000 이 실제로 나가는 판이다.

## 3. 짝 게이트의 독립 측정 (차선 Q · `scripts/verify_error_body.py`)

`error_body_전후_20260907_TL.md` — 우리 수정과 **독립으로** 705 라우트 × 결 2 = 표본 1,410 을 뜬다.

| | 전 (재기동 전) | 후 (19:11:35 재기동 뒤) |
|---|---|---|
| 5xx | 709 | 709 (수는 그대로) |
| 그중 유출 | **709 (100%)** | **0** |
| 색 | 빨강(exit 1) | **초록(exit 0)** |
| 대표 본문 | `GET /api/v1/health` + `Bearer zzz` → 500 · **165,721바이트** 장고 디버그 전문 | 500 · **170바이트** JSON |

## 4. 반경 — 무엇을 어떻게 셌나

| 변경 | 반경 | 세는 법 |
|---|---|---|
| `/api/report-template/` 를 승격 접두에 추가 | **5 라우트** | `enumerate_operations()` × `path_in_scope()` · 승격권 **332 → 337** |
| ninja `Exception` 처리기 교체 | **705 오퍼레이션 / NinjaAPI 22개** | `_iter_ninja_apis()` · `enumerate_operations()` (정적 grep 아님) |
| `SafeErrorBodyMiddleware` 응답 그물 | **876 URL 패턴** (= 저장소의 모든 라우트) | `get_resolver().url_patterns` 재귀 계수 |

## 5. 왜 미들웨어 한 겹으로는 안 됐나

`ninja/errors.py:_default_exception` 은 `settings.DEBUG` 가 참이면 **예외를 뷰 밖으로 안 내보내고**
`traceback.format_exc()` 를 본문으로 돌려준다. 그래서 Django 의 `process_exception` 이 안 불리고,
`common/api_contract.py` 의 B 부류 승격이 **운영 서버에서만** 죽어 있었다 —
시험은 DEBUG=False 로 돌아 초록이었다(착시 ⑨). 그래서 고침이 두 겹이다: `common/error_body.py` 참조.

## 6. 남긴 것 — **닫히지 않은 것**

- **`verify_prod_settings.py` 는 여전히 「수 5」다.** 6번째 수(`SAFE_ERROR_BODY`)를 세려면
  그 파일의 `PROBE` 와 `judge()` 에 줄이 더 있어야 하고, `scripts/verify_*.py` 는 게이트 소유라
  이 차선이 안 건드린다. 설정 쪽 관측은 이미 서 있다 [실측]:
  `config.settings_prod` → `SAFE_ERROR_BODY=True` · 미들웨어 실림 `True` ·
  `config.settings` → `SAFE_ERROR_BODY=True` · 미들웨어 실림 `True`.
- **망가진 토큰에 705/705 가 여전히 500 이다** (차선 Q 측정). 본문은 이제 안 새지만
  상태는 401 이어야 한다. 인증 관문의 술어다 — P-100 의 술어가 아니다.
