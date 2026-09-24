# P-343 증거 — 셋째 조건 배선 수 · U5#2(`/roles`) 0행의 원인 (2026-09-25 · 차선 Q)

## 배선 수

`scripts/measure_onboarding_t.py` 의 `result(` 호출부 **57/57** 이 이제
`screen_text=` 를 넘긴다(AST 로 호출 노드를 직접 세었다 — 문자열 흉내가 아니다).
정적 대조 시험: `backend/tests/test_p343_third_condition_wiring.py::
EveryResultCallSitePassesScreenTextTest::test_wiring_count_is_n_of_n`.

## U5#2 — `/roles` 표 0행의 원인: **seed 도 permission 도 proxy 도 아니다 — 화면(dj-core) 이다**

한 줄: 서버 질의는 비지 않았다(개발 DB 16행 · 테넌트로 안 좁힌다) — 남는 것은
**dj-core 화면 렌더링**이다(§0.4 금지구역 — 이 저장소가 못 고친다. 대장 등재 요청으로 넘긴다).

### 근거 — 새로 재지 않았다, 이미 있던 시험을 읽었다

이 물음은 턴 U · 차선 U56 이 이미 갈라 두었다 —
`backend/tests/test_u56_roles_table_probe.py` (읽기만 함, 손대지 않음):

- 화면이 실제로 두드리는 문은 `/api/dsm/roles` 가 아니라 **`GET /api/roles/`**
  (dj-core 라우트 — `backend/config/urls.py:65` 가 `core.urls` 를 맨 `/api/` 밑에
  붙인다 · `apps/dsm/urls.py` 에는 `roles` 경로 자체가 없다). `/api/dsm/` 접두는
  `config/urls.py:106` 로 따로 붙어 **겹치지 않는다** → **proxy/라우트 삼킴이 아니다.**
- `test_roles_queryset_is_not_tenant_scoped` (같은 파일 91–112행): `list_roles`
  의 질의는 `Role.objects.filter(deleted__isnull=True)` 이고 `Role.objects` 는
  **평범한 `Manager`** 다(테넌트로 좁히는 `CustomManagerGroup` 이 아니다) — 실측:
  개발 DB 비삭제 16행 · `group_id` 분포 `{None:6, 6:6, 5:3, 7:1}`. 소속이 달라
  안 보였다는 설명은 이 라우트에 **서지 않는다** → **seed(시드 소속 불일치)가 아니다.**
- `test_roles_door_refuses_an_account_without_menu_permission` (72–89행): 문
  앞에 메뉴 권한 문지기(`@path_permission("read", path_override="/roles")`)가
  하나 더 있어 **자격 없는 계정은 403**을 받는다 — 그런데 턴 T 가 잰 실측 그
  순간의 runserver 로그는 `GET /api/roles/?page_size=1&current_page=1 **200**`
  이었다(이 파일 6–8행 인용). 200 을 받았다는 것은 그 문지기를 **통과했다**는
  뜻이다 → 이번 0행의 원인이 **permission 도 아니다.**
- 남는 갈래(파일 자신의 결론, 100행): 「서버는 (비지 않은) 응답을 냈는데 화면이
  못 그렸다」— dj-core 인수 SPA 화면의 일이다. §0.4 금지구역이라 이 차선은
  고칠 수 없고, 사실만 적어 대장 등재 요청으로 넘긴다.

### 왜 세 갈래(seed·permission·proxy) 중 하나로 안 찍었나

셋 다 개별로 **기각**됐다(위 근거 셋) — 억지로 그중 하나를 고르면 다음 사람이
엉뚱한 자리를 판다(턴 Z 가 U6 자격 문제를 문 문제로 오판했던 것과 같은 모양).
회색은 초록이 아니듯, 안 맞는 상자에 억지로 넣은 답도 답이 아니다.

관련: `docs/agent/onboarding_48.md` 턴 AH 절(약 1395–1397행)이 이 물음을 다음
손에 넘겼다 — 그 손이 이 절이다.

## `onboarding_48.md` 의 "상한 표"(로드맵 줄) — 이번에는 안 건드렸다

문서에서 유일하게 그 이름에 맞는 자리는 turn AH 절의 로드맵 한 줄이다:

> 30.5(턴 AH) → AI ≥ 38 → AJ ≥ 43.2(문턱) → AK 46.0(상한)

이 줄은 **계측기가 자동으로 뽑아낸 표가 아니다** — 세종이 손으로 적은 로드맵
목표다. 이번 턴(P-343)은 배선만 했고 실측을 다시 돌리지 않았다(로그인 금지 ·
"누군가 measuring 중"이라는 지시 그대로) — 그래서 30.5 도, 이 로드맵 줄도
움직일 근거가 없다. 지시("그 문서에 계측기로부터 계산된 그런 표가 있을 때만")
에 따라 **onboarding_48.md 는 건드리지 않았다.**
