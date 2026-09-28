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

## §AM 증거 — 남은 네 자리 (2026-09-28 · 턴 AM · 차선 L)

턴 AL 이 못 갈랐던 자리 넷을 이 턴이 잇는다. 여기도 판정기(`scan_line`)는 다시
만들지 않는다(D-479) — 아래는 소스·값을 손으로 되짚은 것이다.

### 1. U1#9 · U2#3 — 남은 「상태 코드」를 찾았다

턴 AL 은 채널 코드·절 ID/마크다운 둘을 고치고 「상태 코드」 원인을 못 찾은
채로 남겼다. 이번 턴에 찾았다:

`frontend/src/features/dsm/pages/EventDetail.tsx` 「대응 시계」 카드의 **전이
한 줄**(옛 674~683행)이 `timeline.data.transitions` 의 `t.from`·`t.to` 를
사전 없이 그대로 찍고 있었다 — `${t.from}→${t.to}`. 이 값은
`backend/kernels/k1_event/response_flow.py` 의 `frm`/`to_state`(계약 값
`occurred`·`acknowledged`·`in_progress`·`closed`)를 그대로 옮긴 것이라,
「전이 3건 — 09:10 occurred→acknowledged (규칙) · …」처럼 영문 상태값이
한글 문장 속에 그대로 섰다. 바로 위 줄(710행, 처리 단계 한 줄)은 이미
`labelOf(RESPONSE_STATE_LABEL, e.response_state)` 를 쓰는데, 같은 값을
문장으로 푸는 이 줄만 사전을 건너뛰고 있었다.

**고쳤다** — `labelOf(RESPONSE_STATE_LABEL, t.from)`·`labelOf(RESPONSE_STATE_LABEL, t.to)`
로 감쌌다. 값(계약 스키마)은 안 바꾼다 — `RESPONSE_STATE_LABEL` 은 이미 U1#9
화면이 쓰던 그 사전이다(두 벌을 안 만든다).

| 제목이 부르는 것 | 있는 것 |
|---|---|
| U1#9·U2#3 「상태 코드」 갈래 | `EventDetail.tsx` 전이 한 줄의 `t.from`/`t.to` — 고쳤다 |

### 2. U4#16 — 감사 「사유」 전수 스캔

`backend/apps/**`·`backend/kernels/**`·`backend/common/**` 의
`audit.record(...)`·`audit_writer.write(...)` 호출부에서 `reason=` 문자열을
전수 훑었다(`grep -rn "reason="`, 42개 파일 우선 목록 + 수동 대조). **주의**:
`@tenant_scoped(reason=...)`(라우트 스코프 선언문)와 `TenantScope.system(reason=...)`
(시스템 스코프 등재 사유)는 **다른 `reason`**이다 — 감사 행의 `reason` 칸으로
가지 않는다(개발자용 자기 증명 문구다). 이 둘은 스캔에서 제외했다 — 빼지
않으면 `UX-14`·`LAW-02` 같은 수십 건이 오탐으로 잡힌다.

실제 감사 사유(`/dsm/audit` 「사유」 칸에 원문 그대로 뜨는 자리)에서 **다섯
곳**을 찾아 고쳤다:

| 파일 | 종전 | 문제 | 고침 |
|---|---|---|---|
| `kernels/k1_event/response_flow.py::advance_response` | `reason=reason.strip() or f"대응 진행 {frm} → {to_state}"` | 사유 없이 진행하면(보통 경로) `frm`/`to_state` 원문(`occurred`·`acknowledged`·`in_progress`)이 그대로 감사에 남는다 | `_STATE_KOREAN` 사전 + `_state_ko()` 를 새로 두고 `_state_ko(frm)`·`_state_ko(to_state)` 로 감쌌다 |
| `kernels/k1_event/response_flow.py::close_as_false_positive` | `f"오탐 판정에 따른 자동 종결 (판정자 {by} · P-16)"` | 절 ID(P-16)가 사유에 그대로 | `· P-16` 제거(뜻은 그대로) |
| `kernels/k2_notify/rule_admin.py::save_rule` | `"S-16 규칙 저장 — …채널 %s…" % (…, ",".join(view.channels), …)` | 절 번호(S-16) + 채널 코드 나열(`email,log`…) 원문 | "S-16 " 제거 · 채널 나열은 자유문에서 뺐다(이미 `after.channels` 에 구조화돼 있다) |
| `kernels/k2_notify/rule_admin.py::send_test_notification` | `"S-16 시험 발송 — … 훈련 채널(%s)로 …" % (…, channel, …)` | 절 번호(S-16) + 채널 코드(`log`) 원문 | "S-16 " 제거 · `채널(%s)` → 「훈련 채널로」(값은 `after.channel` 에 남는다) |
| `apps/dsm/webhook_key_service.py::set_subscription_filters` | `reason="구독 필터 저장 (WS-17)"` | 절 ID(WS-17) — `SECTION_ID` 정규식 접두(UX·SEC·OPS·…) 밖이라 기존 시험이 못 잡았다 | `(WS-17)` 제거 |
| `common/ops_tasks.py::video_retention_sweep` (호출부) | `reason="주기 집행 — 선언한 보존 일수대로 지운다 (P-57 파기)"` | 절 ID(P-57) — `apps/dsm/retention.py::purge_all_declared` 를 거쳐 `audit_writer.write(reason=...)` 로 그대로 들어간다 | `(P-57 파기)` 제거 |

**훑고 고치지 않은 것** — 정직하게 적는다:
- `role_request.py::notify_admin` 의 `reason=f"역할 부여 요청 — 수신 {to} (경로 {admin.get('source')})"` —
  `admin.get('source')` 가 `"none"`/`"global_admin"` 같은 내부 코드를 실을 수
  있다. 다만 지금 가능한 값들은 현재의 `HANGUL_ONLY_PATTERNS` 세 무리(역할·채널·
  상태 코드) 중 어느 것과도 맞지 않는다(`admin` 단어는 `global_admin` 처럼
  붙어 있으면 `\b` 경계가 안 선다) — 판정기가 못 잡는 자리라 이번 턴 예산 안에서
  **우선순위를 낮췄다.** 다음 손 후보.
- `kernels/k5_trust/services.py::credential_fact`/`secret_for` 의
  `reason=f"조회 — 상태 {observed}"` — `observed` 는 자격증명 상태 코드
  (`typed`/`absent`/…)다. 이 감사 로거(`logger_name`)가 `/dsm/audit` 에
  실제로 노출되는지 이번 턴에 확인하지 못했다(§0.4 밖이지만 시간 밖) —
  다음 손 후보.
- `kernels/k2_notify/renotify.py` 의 `skipped_reason`(백틱 + `**무응답**` 포함) —
  **화면이 없다.** `renotify`/`skipped_reason` 을 부르는 프런트 자리를
  `frontend/src` 전수에서 찾지 못했다(0건) — 이 값을 그리는 화면이 아직
  없으므로 셋째 조건의 대상이 아니다. 화면이 생기면 그때 고친다.
- `apps/**` 의 `audit.record`/`audit_writer.write` 호출부 전부를 한 줄 한
  줄 열지는 못했다(파일 40여 개) — 위 다섯 자리는 **grep 전수 + 결정
  ID·마크다운·백틱·원문 채널/상태 코드 패턴 대조**로 찾은 것이고, 나머지는
  1차 grep 에서 `reason=` 값이 이미 한국어 서술문이었거나(예:
  `access_log_service.py`) 사용자가 스스로 적은 자유 텍스트(`reason=reason`
  형태 — `alert_level_service.py`·`k5_trust/grade_rules.py` 등, 우리가 짓는
  문장이 아니라 고칠 대상이 아니다)였다.

또한 확인 요청 받은 **action/channel 칸**:
- 「채널」 칸(`AuditLog.tsx:485`)은 이미 `channelLabel`/`CHANNEL_NAME_UNKNOWN`
  사전을 거친다(턴 AL 이전부터) — 원인이 아니다.
- 「행위」 칸(`AuditLog.tsx:449`, `dataIndex: 'action'`)은 **렌더 함수가
  없다.** `action=f"response.{frm}->{to_state}"` 처럼 상태값이 action 문자열
  에도 들어간다 — 다만 `action` 은 원래 기계 식별자(`notify.save_rule`,
  `law02a:retention_sweep_preview` 등 수십 종)이고, 전부를 사전화하는 일은
  이번 턴 예산 밖이다. **고치지 않음 — 다음 손으로 남긴다.**
- 「HTTP」 칸(`status_http`)은 숫자를 그대로 찍지만, 판정기의 「상태 코드
  숫자」 눈금은 그 숫자 앞뒤에 특정 한국어 어휘(「오류」·「응답」·「서버가」 등)가
  붙어야 걸린다 — 칸 이름이 이미 "HTTP" 뿐이라 이번 실측 표본으로는 안 걸릴
  가능성이 높다. 손대지 않았다(추측으로 고치지 않는다).

| 제목이 부르는 것 | 있는 것 |
|---|---|
| U4#16 「절 ID·마크다운·채널 코드·상태 코드」 네 갈래 | 다섯 자리 고침(위 표) · 「행위」 칸·역할 요청 사유·자격 상태 사유는 **못 고쳤다**(다음 손) |

### 3. U1#3 · U5#5 — 「결정 번호」 가설을 갈랐다

턴 AL 은 「카메라 이름이 `D-###` 꼴이라면 그것은 자료이지 코드가 아니다」는
가설만 남기고 못 갈랐다. 이번 턴에 개발 DB 를 읽기 전용으로 확인했다:

```
MSYS_NO_PATHCONV=1 docker exec -w /app -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
  python manage.py shell -c "
import re
from stream_monitors.models import StreamMonitor
pat = re.compile(r'(?<![A-Za-z0-9])D-\d{3}(?![0-9])')   # 진짜 절 ID 모양(앞뒤 경계)
names = list(StreamMonitor._base_manager.values_list('id','name').order_by('id'))
matches = [(i,n) for i,n in names if n and pat.search(n)]
print('MATCHCOUNT', len(matches)); print('ALLCOUNT', len(names))
"
# → MATCHCOUNT 0 · ALLCOUNT 60
```

**결정 번호(진짜 `D-\d{3}` 절 ID) 모양의 카메라 이름은 0건이다.** 그런데
게이트가 쓰는 실제 정규식(`scripts/verify_ui_copy.py:60`)은
`r"D-\d{3}(?!\d)"` — **앞쪽 경계가 없다.** 그래서 느슨한 첫 조회(경계 없이
잰 조회)에서 `id=14 name='GD-150Q'` 가 걸렸다 — 이것은 절 ID 가 아니라
**드론/카메라 장비 모델명**("GD-150Q")의 부분 문자열이 우연히 `D-150` 모양과
겹친 것이다(뒤에 `Q` 가 더 붙어 있어 진짜 절 ID 라면 `(?!\d)` 는 통과하지만
앞에 `G` 가 붙어 있는 것을 그 정규식이 못 본다). 표본 60행 중
`GD-150Q`·`Q02-0002`·`H40-0001`·`NBP-DR-P2`·`Anyang - DJI1`·`Gaion - DJI1`
등은 전부 **실제 드론/카메라 장비 이름**이다.

`grep -rn "GD-150Q\|Anyang - DJI\|H40-0001\|NBP-DR-P2\|Q02-000" backend/` →
**0건.** 이 이름들은 이 저장소의 어떤 시드·픽스처 명령도 만들지 않는다
(`seed_dsm_events.py` 는 `"시드 카메라 (검수용)"` 만 만든다 ·
`create_stream_monitors.py` 는 `"Stream Monitor Alpha/Beta/…"` 만 만든다).
즉 이 60행은 **이 턴 이전부터 개발 DB 에 있던 자료**다 — 과제 지시대로
**기존 DB 행은 손대지 않았다.**

**고치지 않음.** 시드 이름에 문제가 없으므로 시드 코드를 고칠 것이 없다.
진짜 원인은 게이트 정규식(`scripts/verify_ui_copy.py:60`)에 앞쪽 경계가
없다는 것인데, 그 파일은 이 턴의 편집 대상이 아니다(대장급 스캐너를 이
한 자리 때문에 고치는 것은 이 턴의 몫이 아니라고 판단했다 — 다른 화면
수십 곳이 그 정규식에 기대고 있다). **대장에 등재 요청**: 「결정 번호」
정규식에 `(?<![A-Za-z0-9])` 왼쪽 경계를 더하면 장비 모델명 오탐이
사라진다 — 다음 손.

| 제목이 부르는 것 | 있는 것 |
|---|---|
| U1#3·U5#5 「결정 번호」 | **가설 기각** — 카메라 이름 중 진짜 절 ID 모양은 0건. 오탐의 원인은 게이트 정규식의 경계 누락(장비 모델명 `GD-150Q` 등과 우연히 겹침) — 시드 변경 없음·게이트 정규식은 이 턴에서 안 고침(대장 등재 요청) |

### 4. 술어 없음(`gray_kind=nopred`) 여덟 행 — 무슨 술어가 있어야 하는가

`docs/agent/evidence/ONB-T/turn_ak_5.json` 의 U6 그룹 여덟 행 전부가
`gray_kind: "nopred"` 다 — 전부 **화면이 없는 기계 호출**(API·헤더·익명
호출)이라 셋째 조건(화면이 사용자 언어를 쓰는가)이 원천적으로 안 걸린다.
`scripts/measure_onboarding_t.py` 는 이 턴에 건드리지 않는다(대장 소관) —
아래는 **무슨 술어가 있어야 이 행들이 회색을 벗는가**를 손으로 짚은 표다.

| 행 | 걸음 | 왜 회색인가 | 필요한 술어(가상) |
|---|---|---|---|
| U6#1 | `POST /settings/api-keys` | 응답이 `{key, key_id, …}` 뿐 — 사람이 읽는 문장이 없다. 이 발급 자체를 보여 주는 화면(`/dsm/system` API 키 카드)은 **다른 행**이 이미 사람 화면으로 잰다 | 이 API 걸음 자체에는 필요 없다 — 화면 쪽 등가 행(예: U5 계열 API 키 발급 화면)이 따로 서면 그 행이 셋째 조건을 진다. 이 행은 계약(200/401)만 재는 것이 옳다 |
| U6#2 | `GET /api/dsm/events` | 성공 응답(`{events, total}`)에 문장이 없다 — 실패 시에만 `detail` 문자열이 생긴다 | **실패 갈래 술어**: 이 라우트가 4xx/5xx 를 낼 때 `detail` 문자열이 `verify_ui_copy` 사전(결정 번호·마크다운·raw enum 없음)을 통과하는가. 지금은 그 갈래를 이 걸음이 두드리지 않는다 |
| U6#3 | `GET /api/dsm/events/{id}` (JWT vs 키) | 200/401/403 상태 코드만 대조한다 — 몸통 문장은 안 본다 | 위와 같음: **키 거절 응답의 `detail` 문장**이 사용자 언어인가(절 ID·raw 코드 없음)를 재는 술어 |
| U6#4 | `POST /webhook-subscriptions` (422) | 422 은 Django Ninja/Pydantic 이 만드는 **필드별 영문 검증 오류**(`loc`/`msg`/`type`)다 — 이 형은 원래 기계용이라 사람 화면이 그 몸통을 직접 그리면 안 된다 | **화면이 이 422 몸통을 직접 그리지 않는가**를 재는 술어 — 프런트가 `detail` 배열을 그대로 토스트로 찍으면(있다면) 그 자리가 빨강이어야 한다. 지금은 「직접 안 그린다」는 것 자체를 재는 술어가 없다 |
| U6#9 | `POST /events/{id}/response` (없는 id → 404) | 404 의 `detail` 문장 하나만 있고, 그 문장이 사용자 언어인지는 안 잰다 | **404 `detail` 술어**: 「그런 이벤트가 없습니다.」류의 한국어 서술인가 — `HttpError(404, "…")` 문자열이 실제로 이 사전을 통과하는지 대조 |
| U6#12 | 익명 5개 라우트 → 전부 401 | Django Ninja 기본 401 은 흔히 `{"detail": "Unauthorized"}` 류의 **영문**이다 — 지금은 상태 코드(401=참)만 잰다 | **401 몸통 술어**: 이 401 응답의 `detail` 이 영문 원문이면, 그것을 그대로 찍는 화면이 있는가(로그인 만료 인터셉터 등)를 함께 재야 한다 — 화면이 그 원문을 찍으면 셋째 조건 위반이다 |
| U6#14 | `X-GX-Schema` 헤더 | HTTP 헤더는 **애초에 화면 글자가 아니다** — 브라우저 개발자 도구가 아니면 사람이 안 본다 | 없음(영구) — 헤더는 셋째 조건의 대상이 될 수 없다. 회색이 맞는 자리다 |
| U6#15 | `GET /api/dsm/health` | `{"db":…, "cache":…, "queue":…}` 값만 대조한다 — 이 이름·값이 화면에 뜨는지 안 본다 | **화면 노출 술어**: 이 헬스체크 이름·값을 그리는 운영 화면(`/dsm/system` 계열)이 생기면, 그 화면이 `db`/`cache`/`queue` 를 한국어로(예: 「데이터베이스」·「캐시」·「대기열」) 그리는지 재는 사전 대조가 필요하다. 지금은 그런 화면이 없다(확인: `frontend/src` 에 `"db"` 를 그대로 라벨로 쓰는 화면 없음) |

**요약**: U6#14 는 **영구 회색**(헤더는 화면이 아니다)이고, U6#1 은 등가
화면 행이 따로 있어 **회색이어도 무해**하다. 나머지 다섯(U6#2·3·4·9·12·15)은
전부 **실패/오류 몸통(`detail`)의 언어**를 재는 술어가 없어서 회색이다 —
공통 패턴: 지금 이 측정기는 **성공 계약(상태 코드)만** 재고, 실패 응답의
**문장**은 한 번도 안 잰다. 이것이 이 여덟 행을 가르는 하나의 원인이다.

## 시험 (§AM 추가분)

`backend/tests/test_p371_screen_language.py` 에 시험 아홉 개를 더했다
(`ResponseFlowAuditReasonTests`·`NotifyRuleAdminAuditReasonTests`·
`RetentionSweepAuditReasonTests`·`EventDetailTransitionRawStateTests`·
`WebhookAuditReasonTests.test_filter_save_reason_has_no_section_id`) —
이 턴에 고친 다섯 자리(대응 전이 기본 사유·오탐 자동 종결 사유·규칙 저장
사유·시험 발송 사유·구독 필터 저장 사유)와 프런트 한 자리(전이 한 줄)가
**다시 그 모양으로 돌아오면 빨개진다.**

캐시 처리: 해당 없음 — 새로 더한 시험도 전부 정적 소스 읽기 + 파이썬 모듈
임포트뿐이다(HTTP 를 때리지 않는다).

