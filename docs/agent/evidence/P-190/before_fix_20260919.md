# P-190 — **두 도구가 같은 행에 다른 정본을 든다** · 고치기 **전** 빨강 (2026-09-19 · 턴 W · 차선 Q)

조율자 요구: 「당신이 세우는 판정이 진짜라면, **고치기 전에** U5#15 에서 빨강이 떠야 한다.
빨강을 못 본 채 고치면 그 판정이 실제로 무엇을 잡는지 아무도 모른다.」 — 그 빨강이 아래다.

## 어떻게 다시 만들 수 있나 (재현 절차)

이 목록은 **지금 판정 규칙**(`verify_click_completes.canon_disagreements`)을
**턴 W 착수 시점의 두 정본**에 먹여 얻은 것이다:

```
git show HEAD:scripts/verify_click_completes.py   > /tmp/old_vcc.py     # HEAD = 4479648 (턴 V)
git show HEAD:docs/agent/onboarding_48.md         > /tmp/old_canon.md
# old_vcc.FLOWS 의 note × verify_click_completes.canon_cells(old_canon.md) 의 마지막 칸
```

판정 자리: `scripts/verify_click_completes.py` **자기시험 ⑧**. 따로 게이트를 만들지 않았다 —
`click-completes` 게이트가 이미 그 자기시험을 부르고, 깨지면 `--measure` 도 멈춘다.

술어(양쪽이 **적극적으로** 말할 때만 다툼이다 · 한쪽의 침묵은 주장이 아니다):
- ㉠ 이 파일이 그 행을 **「정본 없음」**이라 적었는데 온보딩 정본에는 잴 것이 적혀 있다 → 빨강
- ㉡ 이 파일이 **기대 호출을 못 박았는데** 온보딩 정본이 **「정본 없음」**이라 적었다 → 빨강
- 「이 도구가 그 자리를 안 누른다」는 **빨강이 아니다** — 도구의 한계이지 사실 다툼이 아니다
- 정본 문서를 못 읽으면 **회색** — 문서가 없다고 두 정본이 갈렸다고 말하지 않는다

## 빨강 **11행** (고치기 전)

| 행 | `verify_click_completes.py` 가 말하는 것 | `onboarding_48.md` 가 말하는 것 |
|---|---|---|
| **U2#9** | 「정본 없음」 — 정본: 집계 면 없다 — 사람별로 세는 자리가 없다 | 잴 것이 적혀 있다 — [API 호출] `GET /api/dsm/stats/by-reviewer` 200 + [화면 상태] 제목 `요원별 현황` 1 · 표 행 ≥ 1 (`요원` 열) — 표가 0행이면 「없다」가 떠야 하고 빈 표는 빨강 |
| **U2#16** | 「정본 없음」 — 정본: 조회 라우트·화면 없다 · 규칙 0건 | 잴 것이 적혀 있다 — [API 호출] `GET /api/dsm/settings/notify-rules/list` 200 + [화면 상태] 제목 1 · 규칙 표 행 ≥ 1 (규칙 0건이면 「없다」가 떠야 하고 빈 표는 빨강) |
| **U3#16** | 「정본 없음」 — 정본: 없음 — 알림 채널 결정 대기 | 잴 것이 적혀 있다 — [실측 2026-09-18 · 조율자 병합] M4 **실자료가 섰다** — `MobileSettings.tsx` 에 `pushOutcome`(구독 상태 칸 · 145행) · `saveOutcome`(저장 · 145행) · `testOutcome`(시험 발송 · 206행 |
| **U4#1** | 「정본 없음」 — 정본: 라우트는 hours=168 을 받지만 **누를 자리가 없다** | 잴 것이 적혀 있다 — [API 호출] `GET /api/dsm/events?since=…` 200(누른 뒤 창이 지금부터 7일 전까지) — ⚠ 서버 요약 문 `summary?hours=168` 을 이 프리셋이 부르지 않는다(부르는 것은 목록 문이다) · 턴 T 착시 ⑨는 「누를 데가 없다」 |
| **U4#15** | 「정본 없음」 — 정본: 없음 — 상급기관 서식 T4 | 잴 것이 적혀 있다 — [서버 기록] `POST /api/dsm/events/{id}/upper-report` 200 → 재조회에서 그 행의 표시가 **서버 값으로** `보고함` + [화면 상태] 두 말이 같은 화면에 동시에 있지 않을 것 |
| **U5#1** | 「정본 없음」 — 정본 없음 — 단추는 있으나(App.tsx:728 「사용자 추가」) 그것은 서식 화면으로 가는 링크다. 계정 생성은 다음 화면의 서식을 채워야 끝난다 · 그 문은 프리플라이트 401 로 끊겨 있다(P-125 A절 · 보안 차선) | 잴 것이 적혀 있다 — [서버 기록] `POST /api/dsm/settings/people/create` 200 → 사용자 수 +1 — ⚠ 문 경로는 `/settings/people` 이 아니라 `/settings/people/create` 다(`/settings/{domain}` 이 삼켜 |
| **U5#4** | 「정본 없음」 — 정본 없음 — 자리는 /dsm/cameras/import(routes.ts:23 · roleNav.ts:132)이나 「표 먼저, 그 다음 적용」이 세 걸음이고 매번 새 시험 자료가 필요하다. 한 번 누름으로 재는 정본이 없다 | 잴 것이 적혀 있다 — [서버 기록] `POST /api/dsm/cameras/import` 200 (dry-run 뒤 실행) → 카메라 수 +N |
| **U5#5** | 「정본 없음」 — 정본 없음 — 단추는 「표 먼저 보기」·「채우기」(CameraAddress.tsx:177·185)이고 둘 다 입력 전에는 잠겨 있다. 「표 먼저, 그 다음 채움」이 두 걸음이다 | 잴 것이 적혀 있다 — [서버 기록] `POST /api/dsm/cameras/{id}/address` 200(`api_u56.py:506`) → `GET /api/dsm/cameras/address-gap` 재조회에서 `without_address` **-1**. ⚠ [턴 U 이전] 위 U |
| **U5#10** | 「정본 없음」 — 정본: 없음 — 알림 채널 결정 대기(대표) | 잴 것이 적혀 있다 — [서버 기록] 규칙 저장 200 → `channel` 값 `email`/`webpush` 가 `…/list` 에 남음 + [화면 상태] 제목 1 |
| **U5#15** | 「정본 없음」 — 정본: 신호는 ops_monitor 안에만 있다 — 읽는 라우트가 없다 | 잴 것이 적혀 있다 — [API 호출] `GET /api/dsm/system/storage` 200(`api_u56.py:647` · `common/ops_tasks.py:1126` `storage_declaration()` 하나가 판정) + [화면 상태] 상한 미선언이면 `used_pct: |
| **U6#14** | 「정본 없음」 — 정본: 없음 — 스키마 버전 | 잴 것이 적혀 있다 — [API 호출] 아무 응답이나 헤더 `X-GX-Schema` 1 · `backend/tests/test_u56_schema_header.py` 가 잠근다 |

★ **`U5#15` 가 그 안에 있다** — 조율자가 지목한 그 행이다. 차선 U56 이 이 턴에
`GET /api/dsm/ops/backup/declaration` 을 세우고 **눌러서 200 을 봤으므로**,
이 파일의 「읽는 라우트가 없다」 쪽이 거짓이었다.

## 고친 뒤

- `verify_click_completes.py` 주석 11개(U2#9·U2#16·U3#16·U4#1·U4#15·U5#1·U5#4·U5#5·U5#10·U5#15·U6#14)
  — 「정본 없음」 주장을 지우고 **정본이 든 문·문구를 적은 뒤, 이 도구가 안 누르는 사유**를 남겼다.
- `onboarding_48.md:1101` — U4#15 를 **U24 문안 글자 그대로**(U4 로 ●가 될 수 없다 · U2 축에서 잰다).
- `onboarding_48.md:881·882` — U1#1·U1#2 기대식을 **화면이 실제로 부르는 것**으로.
- `onboarding_48.md:595` — 턴 T 촬영 기록은 **지우지 않고** 턴 W 정정을 덧붙였다.

⚠ **고친 사람이 잰 수는 여기 없다.** 이 파일은 「갈린 행이 있었다」와 「무엇을 고쳤다」만 적는다.
FC 와 온보딩의 수는 **차선 V** 가 낸다 (「정본은 고치는 사람과 재는 사람이 다르다」).
