# P-371 증거 — 셋째 조건(그 사용자의 언어) 열 행의 원인과 조치 (2026-09-28 · 턴 AL · 차선 L)

턴 AK 다섯째 회차(`docs/agent/evidence/ONB-T/turn_ak_5.json` · 문서 `onboarding_48.md`
「★ 2026-09-27 턴 AK 다섯째 회차」절)가 셋째 조건을 처음 재면서 열 행을 초록→반·
빨강→반으로 내렸다. 이 절은 그 열 행 각각의 **정확한 위반 문자열 · 출처 파일 ·
고쳤는가**를 적는다. 재측(V·로그인 필요)은 이 차선이 못 한다 — 무엇이 뒤집힐지만
말한다.

판정기는 다시 만들지 않는다(D-479) — `scripts/measure_onboarding_t.py::
third_condition_violations` 는 `scripts/verify_ui_copy.scan_line` 을 그대로 부른다.
이 문서의 "출처"는 그 함수가 보는 **화면 전체 글자**(`body(page)`, Playwright
innerText)에서 실제로 걸리는 문자열을 손으로 되짚은 것이다.

## 표

| 행 | 위반 문자열 | 출처 | 상태 | 기대 효과 |
|---|---|---|---|---|
| U1#3 `/dsm/cameras/grid` | 결정 번호(`D-\d{3}`) | **미확정.** 이 화면은 카메라 이름(`row.name`)을 `CameraGrid.tsx:61-63`(`CameraTile`)에서 그대로 찍는다. 정적 소스에는 `D-\d{3}` 문자열이 없다(주석 제외 · 주석은 판정기가 안 본다) — 그래서 남는 가설은 **실제/시드 카메라 장비 이름 자체**가 `D-###` 꼴이라는 것이다. 그것이 맞다면 이것은 운영자가 붙인 자료이지 우리 문구가 아니다. | 고치지 않음(가설 미확정) | 다음 손: 실측 시점의 실제 화면 글자(스크린샷/HTML 덤프)를 V 가 남기면 이 자리가 코드인지 자료인지 한 번에 갈린다. |
| U1#9 `/dsm/events/:id` | 절 ID(`P-41`) · 마크다운 강조(`**…**`) · 채널 코드(`email`/`webpush`/`log`…) · 상태 코드 | ① 채널 코드 — `frontend/src/features/dsm/pages/EventDetail.tsx:858` 발송 이력 표 「채널」 칸이 렌더 함수 없이 `dataIndex: 'channel'` 원문을 그대로 찍고 있었다.<br>② 절 ID·마크다운 — `backend/kernels/k2_notify/channels.py` `EmailChannel.send_allowed()` 의 실패 사유 두 문장이 `"…**비어 있다**…(P-41)…"` / `"…**목록 밖**이다(P-41)…"` 였다. 이 문자열은 `services.py:810`(`row.failure_reason = (outcome.reason or "사유 없음")[:250]`)을 거쳐 같은 표의 「실패 사유」 칸(`dataIndex: 'failure_reason'`, 렌더 없음)에 원문 그대로 나간다. | **①·② 고침.** 상태 코드는 이 행에서 별도 출처를 못 찾았다(회수 이력 결과 칸은 이미 `OutcomeCell`이 번역해 그린다 · 감사·전이표는 이 화면에 안 뜬다). | 채널 코드 + 절 ID/마크다운 두 갈래는 사라진다. 상태 코드 원인이 남아 있으면 이 행은 그래도 ◐ 일 수 있다 — 다음 손: 이 행만 다시 실측해 남은 이름을 확인. |
| U2#3 `/dsm/events/:id` | 위와 동일 넷 | 위와 동일(같은 화면 · 같은 표) | 위와 동일 | 위와 동일 |
| U3#19 `/m/inbox` | 채널 코드(`email`/`log`…) | `frontend/src/features/mobile/pages/MobileInbox.tsx:664` 가 `channelDisplayLabel(d.channel)` 을 부르는데, 그 함수(`deliveryOutcome.tsx:154`)가 종전엔 `reachesAPerson(channel) ? channel : LOG_ONLY_CHANNEL_LABEL` — **사람에게 닿는 채널은 원문 그대로** 돌려주고 있었다. | **고침.** `channelDisplayLabel` 이 이제 `notifyChannelLabel(channel)` 을 돌린다(`deliveryOutcome.tsx:156`). | 이 행이 유일하게 꼽은 갈래(채널 코드)가 사라진다 — **초록으로 되돌아갈 후보.** |
| U4#16 `/dsm/audit` | 절 ID(`P-145 · SEC-16`) · 마크다운 강조 · 채널 코드 · 상태 코드 | 「행위」(`dataIndex: 'action'`) · 「사유」(`dataIndex: 'reason'`) 두 칸이 `AuditLog.tsx:449,483` 렌더 함수 없이 서버 `note`/`api_name` 원문을 그대로 찍는다. 감사 note 생성부 전부를 이번 턴에 못 훑었다(`apps/dsm/*.py` 스무 곳 가까이가 `audit.record*` 를 부른다) — 그중 확정한 한 곳: `backend/apps/dsm/webhook_key_service.py:93` `audit.record(..., reason="구독 등록과 함께 서명키 생성 (P-145 · SEC-16)")`. | **절 ID 한 자리만 고침.** 마크다운·채널 코드·상태 코드의 정확한 출처는 이번 턴에 못 찾았다 — 「채널」 칸 자체는 이미 `channelLabel`/`CHANNEL_NAME_UNKNOWN` 으로 옳게 번역돼 있어 그 칸이 원인은 아니다(다른 원인이 남는다는 뜻). | 부분 개선 — 이 행은 남은 세 갈래 때문에 여전히 ◐ 일 가능성이 높다. 다음 손: `grep -rn "reason=" backend/apps/dsm/*.py` 전수를 훑어 `\*\*`·절 ID·상태값 리터럴을 찾는 전담 회차 필요(이번 턴 예산 밖). |
| U5#2 `/roles` | 영문 메뉴(자기표지 `ADMIN_HEADER`) · 역할 코드 | **금지구역(rj-core).** `frontend/src/App.tsx:35,860-867` — `RoleManagement` 은 `import { … RoleManagement, … } from 'rj-core'` 다. 표 안의 영문 라벨·역할 코드는 그 인수 화면 안에 있다. 우리 쪽 코드(`components/InheritedScreen/InheritedScreen.tsx:37`)는 그 사실을 정직하게 알리는 한 줄(`관리자 전용 화면입니다. 아래 표기는 아직 영문입니다.`)만 얹는다 — 그런데 그 정직한 자기표지 문장 자체가 `measure_onboarding_t.py::ADMIN_HEADER` 상수와 같아서, 판정기가 그 문장의 **존재**를 "영문 메뉴가 있다"는 신호로 재사용한다. | **고치지 않음(§0.4).** | 재측해도 그대로 ◐(또는 빨강) — rj-core 를 고치기 전엔 못 오른다. 이 사실 자체를 대장(§0.4 등재 요청)으로 넘긴다. |
| U5#5 `/dsm/cameras/address` | 결정 번호(`D-\d{3}`) | **미확정.** U1#3 과 같은 모양 — `CameraAddress.tsx:255`(`dataIndex: 'name'`)가 카메라 이름을 그대로 찍는다. 이 화면의 다른 문자열(`row.reason`·`ACTION_LABEL`)은 전부 확인했고 깨끗하다(`bulk_register.py` 의 `row.reason` 값들 — "새로 만듭니다." "N개 칸이 바뀝니다." 등 — 에 D-코드 없음). | 고치지 않음(가설 미확정) | U1#3 과 같음 — 카메라 이름 자체가 원인이면 코드로 못 고친다(데이터). |
| U5#9 `/dsm/notify` | 마크다운 강조 · 채널 코드 | ① `backend/kernels/k2_notify/rule_admin.py:96` `CHANNEL_NOTE["log"]` 가 `"…**사람이 아니라 로그에 도달한다.**…"` — `NotifySettings.tsx` 「채널」 카드(`<Text type="secondary">{c.note}</Text>`)에 그대로 뜬다.<br>② 규칙 표 「채널」 열(`NotifySettings.tsx:438`, `cs.join(' · ')`) · 「켜짐」 토글 뒤 저장 알림(`saved.channels.join`) · 채널 카드 이름(`{c.channel}`) 이 전부 원문. | **고침.** ①의 `**`를 뗐다(`rule_admin.py:96`). ②는 새 사전 `notifyChannelLabel`(`copy.ts:766`)로 전부 감쌌다(`NotifySettings.tsx:198,199,327,359,381,391,440,581,593` — 9곳). | 두 갈래 다 사라진다 — **초록으로 되돌아갈 후보.** |
| U5#10 `/dsm/notify`(채널 열) | 마크다운 강조 · 채널 코드 | U5#9 와 같은 화면·같은 원인. | 고침(U5#9 와 같은 커밋) | 위와 동일. |
| U5#14 `/dsm/system` | 절 ID(`P-67`) · 마크다운 강조 | `backend/common/ops_tasks.py` 두 자리: ① `STORAGE_CAPACITY_NOTE`(1128행)가 `"상한은 **선언값**입니다…상한과 **같은 그릇을 재지 않습니다**…"` — 저장 용량 카드(`SystemSettings.tsx:432` `{storage.data.capacity_note}`)에 그대로 뜬다(선언 여부와 무관하게 **항상** 뜬다).<br>② `backup_declaration()`(1434행)의 미선언 사유 — `"…판단입니다 (P-67). …보존 일수(**선언 없음**)…"` — 백업 카드(`SystemSettings.tsx:348` `description={back.reason}`)에 뜬다(백업 미선언일 때만). | **고침.** ①·② 둘 다 절 ID·마크다운을 뗐다(뜻은 안 바꿈 — `test_u56_backup_declaration.py` 의 `assertIn("OPS_BACKUP_DIR", …)`·`assertIn("선언 없음", …)`·`assertIn("0 일로 선언됨", …)` 그대로 통과). | 두 갈래 다 사라진다 — **초록으로 되돌아갈 후보** (①은 상시 노출이라 확신이 높고, ②는 실측 순간 백업이 미선언이었어야 걸린다 — 미선언이었다면 이 행도 함께 오른다). |

## 재측 전 기대 — 다음 회차에 뒤집힐 자리

- **U3#19 · U5#9 · U5#10 · U5#14** — 이 턴에 찾은 각 행의 **모든** 위반 갈래를
  확인·수정했다. 다음 8500 회차에서 이 넷은 ◐ → ● 로 오를 것으로 기대한다(다만
  U5#14 의 백업 사유 절반은 그 순간 백업이 미선언 상태여야 실제로 걸렸던 자리라,
  선언 상태가 바뀌었다면 애초에 안 걸렸을 수도 있다 — 그래도 코드는 고쳐 잠갔다).
- **U1#9 · U2#3** — 넷 중 둘(채널 코드 · 절 ID/마크다운)을 고쳤다. 남은 갈래(상태
  코드, 그리고 나머지 절 ID/마크다운이 더 있을 가능성)를 못 찾았으므로 **이 둘은
  여전히 ◐ 로 남을 수 있다.**
- **U4#16** — 절 ID 한 자리만 고쳤다. 감사 note 생성부 전수를 못 훑어 **십중팔구
  ◐ 로 남는다.** 다음 손: 전담 회차로 `apps/dsm/*.py` 의 `audit.record*(reason=…)`
  리터럴을 전수 스캔.
- **U5#2** — §0.4 금지구역(rj-core) 이라 이번 턴으로는 못 뒤집는다. 대장 등재
  요청 대상.
- **U1#3 · U5#5** — 원인(카메라 이름 자체인지 코드인지)을 못 갈라 **손 안 댔다.**
  뒤집힐지 알 수 없다.

## 시험

`backend/tests/test_p371_screen_language.py`(시험 9개) — 이 턴에 고친 여덟 자리
(채널 사전 · deliveryOutcome · EventDetail 채널 칸 · NotifySettings 아홉 호출
자리 · `CHANNEL_NOTE` · `STORAGE_CAPACITY_NOTE` · `backup_declaration` ·
`EmailChannel.send_allowed` 실패 사유 둘 · 웹훅 감사 사유)가 **다시 그 모양으로
돌아오면 빨개진다.** 판정기 자체(`scan_line`)는 다시 만들지 않았다(D-479) —
이미 고친 리터럴이 남아 있는가만 소스/값으로 좁혀 본다.

관련 실행 — 전부 통과 확인(2026-09-28):

```
python scripts/verify_ui_copy.py              # 잔여 0건 · 새 위반 0건 (그대로)
python scripts/verify_ui_copy.py --self-test  # 통과
python scripts/measure_onboarding_t.py --check  # 문서·도구 48행 일치 (그대로 · 브라우저 없음)
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e DB_TEST_NAME=test_gx_lane_l -w /app gx-shell \
  python -m pytest tests/test_p371_screen_language.py tests/test_u56_backup_declaration.py \
  tests/test_e_ops10_alert_routing.py tests/test_k2_notify_kernel.py tests/test_u56_notify_rules.py \
  -q --create-db -p no:randomly
  # → 90 passed, 0 failed (196.68s) — 새 9개 + 기존 81개(이번 턴이 건드린
  #   channels.py·rule_admin.py·ops_tasks.py·webhook_key_service.py 를 재는
  #   기존 시험) 전부 초록. 그 뒤에 뜨는 "Logging error" 뭉치는 캐시 무효화
  #   백그라운드 스레드가 시험 프로세스 종료 뒤 닫힌 stdout 에 쓰려다 나는
  #   기존 소음이다(이 저장소의 알려진 결 · 이번 턴이 만든 것이 아니다) —
  #   종료 코드는 0.
```
