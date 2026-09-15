# P-124 — 턴 N 판정 P-111~117 **이월 원장 일곱 줄** [차선 P · 2026-09-10 턴 O]

- TARGET = `http://localhost:8500` (nginx → gunicorn · 진짜 MinIO 자격) · 저장소 작업본
- AS = `gxprobe_c`(차선 P 전용) · 익명 · gx-shell django ORM
- SOURCE = **오늘 내가 직접 두드린 응답**과 **내가 mtime 을 확인한 파일**. 남이 적어 준 줄은
  이 표에 **닫힘으로 올리지 않았다** — 규칙 하나: 내가 안 잰 것은 닫히지 않는다.

## 원장

| # | 판정 | 상태 | 사유 [실측] | 근거 경로 (내가 확인한 mtime) |
|---|---|---|---|---|
| 1 | **P-111** 정본 = 운영 프로필 서버 | **미착수** | 턴 N 이 「오늘 정본은 없다」를 냈고(8500 = `profile=dev` · `DEBUG=True` · DB 비번 5자), **오늘 아무도 다시 재지 않았다.** `verify_prod_settings.py` 는 09-07 20:50 이후 손댄 적이 없고 오늘 산출물이 없다. E 차선이 낸 것은 **신선도**(P-116)이지 프로필이 아니다 | `docs/agent/evidence/TURN-N/coordinator_20260908.md` (09-08 12:49) · `scripts/verify_prod_settings.py` (09-07 20:50) |
| 2 | **P-112** 74 계정 공유 비번 + 정책 5 | **미착수** | **오늘 내가 전수로 다시 셌다**: 전체 114 · 활성 113 · `Admin@123` 을 쓰는 계정 **74** — 턴 M 의 74 와 **같다**. 그중 **저장소 유일 superuser `phatlh` 포함**. 회전 산출물 0 · 정책 문서 0 | 내 실측(gx-shell django ORM · `check_password` 전수 · 09-10 17:38) · 대조본 `docs/agent/evidence/P-109/README.md` §③ (09-07 20:48) |
| 3 | **P-113** 익명 OTP 해제 | **닫힘** | **오늘 내가 익명으로 두드렸다**: `POST /api/v1/auth/otp/reset` → **401** `{"detail":"Unauthorized","reason":"authentication required"}`. 턴 N 의 **404 「사용자를 찾을 수 없습니다」**(= 익명이 이름의 존재를 캐낼 수 있는 자리)가 사라졌다 | 내 실측(TARGET=8500 · 익명 · 09-10 17:36) · 구현 `backend/common/otp_reset_guard.py` (09-10 17:23) · `backend/common/access_gate.py` (09-10 17:18) |
| 4 | **P-114** 익명 읽기 5 | **미착수** | **오늘 내가 익명으로 다섯을 다 두드렸다 — 다섯 다 200 이다**: `config-management/list-optimized` **16,436B** · `auth/timezones` **109,309B** · `auth/groups` **1,685B** · `auth/languages` 466B · `register-settings`(정확한 자리는 `/api/register-settings/`) 182B. 앞 셋의 바이트 수가 턴 M 기록과 **한 바이트도 안 다르다** — 아무것도 안 움직였다 | 내 실측(TARGET=8500 · 익명 · 09-10 17:36) · 대조본 `docs/agent/evidence/P-105/README.md` (09-07 20:49) |
| 5 | **P-115** 영역 ① 25 회색 절 · 절마다 쓰기 한 번 | **미착수** | 영역 게이트 `verify_feature_reach` 는 오늘도 **초록 4 · 빨강 3 · 잠김 7 · 회색 25 / 39** 를 낸다(비율 0.1026 → 영역 ① **10%**). 25 가 하나도 안 줄었고, 그 산출물은 **09-07 22:04 이후 다시 쓰인 적이 없다** | 내가 mtime·본문을 확인: `docs/agent/evidence/P-106/feature_reach.json` (09-07 22:04 · `{'n':39,'구현':4,'빨강':3,'미측정':25,'잠김':7}`) |
| 6 | **P-116** `gx-*` 프로세스 신선도 | **진행** | 게이트는 오늘 다섯 프로세스를 **다시 쟀다** — 그러나 **결과가 회색이다**(`worst_exit: 2`). **내가 본문을 열어 확인한 17:22:21 판**: `gx-nginx-e` 만 FRESH 이고 **`gx-gunicorn-e` · `gx-celery-e` · `gx-beat-e` · `gx-shell:runserver` 넷이 `LIVE_OLDER_THAN_SOURCE`** 다(작업본 `backend/apps/dsm/services.py` 가 기동 뒤에 또 바뀐다 — 지금 S 차선이 그 파일을 쓰고 있다). 그리고 판정의 **나머지 절반인 「재시작 정책 없는 컨테이너」는 오늘 아무도 다시 안 셌다.** 그래서 닫힘이 아니다 | 내가 mtime·본문 확인: `docs/agent/evidence/P-116/freshness_all_20260910.json` (09-10 **17:22:21** · `worst_exit 2`) · 나머지 절반 `docs/agent/evidence/TURN-N/coordinator_20260908.md` (09-08 12:49) |
| 7 | **P-117** 보고 첫 표 | **닫힘** | `scripts/verify_readiness_scores.py --report` 가 여덟 줄 + G1~G5 + 남은 턴 + RC-1 을 **찍는다**. 두 술어를 나란히 두고 **분모가 같은 자리(PR 15칸 · 온보딩 48행)에서만** 차를 뺀다. 자기시험 45건 통과(새 갈래 11) | `scripts/verify_readiness_scores.py` · `docs/agent/evidence/P-117/README.md` |

**닫힘 2(P-113 · P-117) · 진행 1(P-116) · 미착수 4(P-111 · P-112 · P-114 · P-115).**

> ⚠ **이 원장을 쓰는 동안 P-116 의 산출물이 내 눈앞에서 바뀌었다.** 17:13 판은 「다섯 다 FRESH」
> 였고 17:22 판은 「넷이 `LIVE_OLDER_THAN_SOURCE` · `worst_exit 2`」다. 남이 요약해 준 한 줄로
> 닫았다면 이 원장은 **거짓 초록**을 실었을 것이다. **이월 원장의 각 줄에는 내가 그 파일을 연
> 시각이 붙어야 한다** — 병렬 차선에서 산출물은 보고서보다 빨리 늙는다.

## 이 원장을 쓰며 걸린 것 하나 — **판정 번호에는 폴더가 없다**

`docs/agent/evidence/` 안에 **P-111 · P-112 · P-113 · P-114 · P-115 폴더가 없다.**
다섯 판정의 증거는 저마다 다른 자리(P-105 · P-106 · P-109 · TURN-N · 소스 주석)에 있다.
그래서 「이 판정의 증거를 보여 달라」가 **다섯 번 다 검색 작업**이 된다.
§3′-0 이 「판정 번호는 저장 경로가 아니다」를 적었는데, 그 반대편 값도 이번에 드러났다 —
**번호마다 한 줄짜리 이정표라도 있으면 이월 원장이 매 턴 재검색이 되지 않는다.**

## 그리고 P-113 에 붙는 단서 — **닫힘의 근거가 소스 주석뿐이었다**

401 을 적은 자리는 `access_gate.py` 의 주석이었고, `docs/agent/evidence/P-113/` 는 없다.
**고침을 담은 파일 안의 산문은 그 고침의 증거가 아니다.** 그래서 이 원장은 그 주석을
근거로 쓰지 않고 **오늘 내가 익명으로 직접 두드린 401** 을 근거로 닫았다.
