# 차선 K — Kick 온보딩 카드 (턴 AB · WO-GX-20260921-04 §3 K 줄 · §4-4)

기계 시각: **2026-09-21** (호스트) · 2판 — 조율자가 도커를 되살린 뒤 **넘김 2 를 채웠다**
로그인 횟수: **3** (`gxseed_u1_operator` · `gxseed_u2_manager` · `gxseed_u4_official` · 전환 간격 61초)

---

## 1. 역할별 표 — 카드 3 · 닫는 서버 기록 · 재사용한 술어 / 새로 만든 술어

정본 문안은 WO-04 §4-4. 코드의 정본은 `backend/apps/dsm/onboarding.py::KICK_CARDS`.
「실제로 닫는 것」이 §4-4 의 「닫는 기록」과 다를 때는 **그 어긋남을 적었다** —
지시서도 입력이지 측정이 아니다.

| 역할 | 기둥 | 카드(문안 요약) | §4-4 가 적은 닫는 기록 | **실제로 닫는 서버 기록** | 술어 |
|---|---|---|---|---|---|
| **U1** 관제요원 | 골든타임 30 | 대응 시계가 도는 사건 하나를 접수 | 접수 기록 1 | `DetectionEvent.response_state ∈ {acknowledged,in_progress,closed}` → `event#N` | **재사용** `_closed_by_response` (카드 `u1.response` 그대로) |
| U1 | 정직 관제 | 이 사진은 시드입니다 — 판정 근거를 열어 보세요 | 판정 패널 열람 기록 1 | **없다 · BLOCKED** | — (사유 아래) |
| U1 | 훈련 모드 | 훈련 사건 하나를 만들어 종결까지 | drill 사건 생성·종결 1 | 훈련 창 안에서 `response_state=closed` 된 사건 → `event#N` | **신설** `_closed_by_drill_event_closed` |
| **U2** 관제팀장 | 골든타임 30 | 팀 대응 시계 p95 를 확인 | TeamStatus 열람 1 | **없다 · BLOCKED**(카드 `u2.by_reviewer` 의 사유 그대로) | — |
| U2 | 정직 관제 | 등급을 다시 매겨 보세요(기록이 남습니다) | 재판정 1 | **없다 · BLOCKED**(카드 `u2.regrade` 의 사유 그대로) | — |
| U2 | 훈련 모드 | 훈련 사건 보고서를 내 보세요 — 첫 줄에 「훈련」 | DOCX 1 | 훈련 창 안 사건을 대상으로 한 `DsmReportRun(kind=incident, status=succeeded)` → `report_run#N` | **신설** `_closed_by_drill_incident_report` |
| **U3** 현장요원 | 골든타임 30 | 내게 온 사건에 현장 도착을 눌러 보세요 | response 1 | 위 U1 ① 과 **같은 기록** → `event#N` | **재사용** `_closed_by_response` (카드 `u3.response` 그대로) |
| U3 | 정직 관제 | 알림이 사람에게 닿았는지 확인 | 도달 카드 열람 1 | **없다 · BLOCKED** | — |
| U3 | 훈련 모드 | 훈련 알림을 받아 보세요 | drill 수신 1 | 훈련 창 안 · `recipient=나` · `succeeded=True` 인 `DeliveryRecord` → `delivery#N` | **신설** `_closed_by_drill_delivery` |
| **U4** 지자체 담당 | 골든타임 30 | 이번 주 골든타임 한 장을 열어 보세요 | 월간 자동본 열람 1 | `DsmReportRun` 한 건 → `report_run#N` ⚠ **「열람」이 아니라 「실행 기록」이다**(§3 ③) | **재사용** `_closed_by_report_run` (카드 `u4.report` 그대로) |
| U4 | 정직 관제 | 사건 이력을 사건번호로 찾아 보세요 | 검색 1 | **없다 · BLOCKED**(카드 `u4.search` 의 사유 그대로) | — |
| U4 | 훈련 모드 | 훈련 사건 상황보고서(별지 1호)를 내려 보세요 | DOCX 1 | 훈련 창 안 사건의 `DsmReportRun(kind=upper, status=succeeded)` → `report_run#N` | **신설** `_closed_by_drill_upper_report` |
| **U5** 기관 관리자 | 골든타임 30 | 임계값을 우리 기관 값으로 바꿔 보세요 | 변경 기록 1 | `ThresholdChange(changed_by=나)` → `threshold_change#N` | **재사용** `_closed_by_threshold_change` (U2 카드 `u2.threshold` 와 **같은 함수**) |
| U5 | 정직 관제 | 알림 채널을 사람에게 닿는 것으로 바꿔 보세요 | 규칙 저장 1 | `k2_notify.resolve_recipients(severity=critical)` 의 규칙 → `notify_rule#N` | **재사용** `_closed_by_critical_recipients` (카드 `u5.recipients` 그대로) |
| U5 | 훈련 모드 | 훈련 구역 하나를 켜 보세요 | OPS-15 구역 1 | **없다 · BLOCKED** | — |
| **U6** 연계 담당 | 골든타임 30 | API 키로 사건 하나를 읽어 보세요 | 200 1 | **없다 · BLOCKED**(카드 `u6.events` 의 사유 그대로) | — |
| U6 | 정직 관제 | 웹훅 구독을 등록하고 서명 검증을 확인 | 구독 1 | `WebhookSubscription` 한 줄 → `webhook#N` | **재사용** `_closed_by_webhook_subscription` (카드 `u6.subscription` 그대로) |
| U6 | 훈련 모드 | 훈련 사건이 웹훅으로 오는지 보세요 | drill 수신 1 | 훈련 창 안 · `channel=webhook` · `succeeded=True` 인 `DeliveryRecord` → `delivery#N` | **신설** `_closed_by_drill_webhook_delivery` |

**술어 셈** — 재사용 **6**(`_closed_by_response`×2 · `_closed_by_report_run` ·
`_closed_by_threshold_change` · `_closed_by_critical_recipients` ·
`_closed_by_webhook_subscription`) · 신설 **5**(훈련 기둥 전부) · 못 잼 **7**.
신설 다섯도 **새 표·새 기록을 하나도 만들지 않았다** — `services.drill_report` 가 이미
감사에서 내주는 훈련 창을 읽고, 그 창 안의 사건 목록·발송 대장·보고서 실행 기록을 본다.

### 못 재는 카드 7 — 이름과 사유 (지우지 않았다 · D-301)

| 카드 | 왜 못 재나 |
|---|---|
| `u1.kick.honest` 판정 근거 열람 | `GET /events/{id}/snapshot` 은 워터마크를 찍어 바이트만 내보내고 **감사에 줄을 남기지 않는다**[실측 `services.event_snapshot` 본문에 `audit` 호출 0]. 「판정했다」(`_closed_by_my_review`)로 바꿔 닫지 않았다 — 이 카드가 묻는 것은 **누르기 전에 열어 봤는가**이고, 판정으로 닫으면 그 물음이 사라진다. |
| `u2.by_reviewer` TeamStatus 열람 | 집계를 본 사실이 서버에 안 남는다(기존 카드의 사유 그대로 · **사유를 다시 쓰지 않았다**). |
| `u2.regrade` 재판정 | 등급을 바꾼 기록을 **사건별로** 되짚는 자리가 없다. 실측: `review` 는 사건 행의 `verdict`·`reviewed_by` 를 덮어쓸 뿐 이력 표가 없고, 감사에 남는 `dsm.events.review` 한 줄은 **오탐 자동 종결** 경로의 것이며 행위자가 `_SystemActor` 다. |
| `u3.kick.honest` 도달 카드 열람 | 대장에는 「무엇이 언제 누구에게 갔나」가 있으나 **「누가 그것을 봤나」가 없다**. 도달(`DeliveryRecord`) 자체로 바꿔 닫지 않았다 — 알림이 닿은 것과 사람이 확인한 것은 다른 사실이고, 접으면 「정직 관제」 기둥이 묻는 것이 사라진다. |
| `u4.search` 검색 | 검색한 사실이 서버에 안 남는다(기존 카드 사유 그대로). |
| `u5.kick.drill` 훈련 구역 | **「훈련 구역」이 서버에 없다** — `Zone.Kind` 는 `camera_group`·`polygon` 둘뿐이고(D-299), 켠 구역이 훈련용인지 서버가 모른다. 아무 활성 구역으로 바꿔 닫으면 훈련과 무관한 구역 하나가 훈련 카드를 닫는다. |
| `u6.events` 키로 이벤트 조회 | 키로 읽은 사실을 남기는 자리가 없다 — 키 표는 §0.4(dj-core)라 마지막 사용 시각을 우리가 더할 수 없다(기존 카드 사유 그대로). |

---

## 2. 절 4 중 **닫힘 3 · 넘김 1**

| # | 닫는 조건 | 상태 | 증거 |
|---|---|---|---|
| ① | **카드 18 등재**(기존 표에 이어서) | **닫힘** | `backend/apps/dsm/onboarding.py::KICK_CARDS`·`KICK_PILLARS`·`KickCard`·`kick_integrity()`·`kick()` · `progress()` 응답의 `kick` 칸 |
| ② | **서버 기록 닫힘 시험 3 통과** | **닫힘** | `backend/tests/test_onboarding_progress.py::OnboardingKickCardsTest` **13 passed** · 파일 전체 **56 passed** (§3 ①) |
| ③ | **첫 진입 캡처 3**(U1·U2·U4) | **넘김 — PNG 0장 · 다만 첫 진입 응답은 3/3 잼** | §3 ② — 세 역할 **실계정 로그인 200 → `GET …/onboarding/progress` 200**. PNG 은 번들이 낡아 못 찍었다(§4) |
| ④ | **U0 운영자 카드 3 설계** | **닫힘** | §6 |

**캡처 3 은 내가 · 2 는 V 창으로 넘김** — 그 규약은 그대로다. 다만 이번 턴에 **내 몫 3 도
PNG 은 못 찍었다**: 3002 가 내주는 번들이 이 턴의 프런트 변경을 아직 안 싣는다(§4).
**U5·U6 둘과 함께 다섯 장 전부 V 창**이다.

---

## 3. 잰 것

### ① 서버 기록 닫힘 시험 — **13 passed** · 파일 전체 **56 passed** [실측 2026-09-21 · gx-shell]

```
docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
  python -m pytest tests/test_onboarding_progress.py::OnboardingKickCardsTest -q --nomigrations -p no:randomly
→ 13 passed in 20.31s   (rc=0)

docker exec … python -m pytest tests/test_onboarding_progress.py -q --nomigrations -p no:randomly
→ rc=0 · 56 passed in 68.44s
```

**닫힘 시험 3** — 전부 「기록 없을 때 안 닫힘 → 기록 생김 → 닫힘 + `source_ref` 대조」의
before/after 다. 「언제나 None」인 버그로는 뒤쪽 단언이 통과할 수 없다:

| 시험 | 무엇을 심어 무엇을 닫았나 |
|---|---|
| `test_closing_a_drill_event_closes_the_first_card` | 제품의 문으로 훈련 모드를 켜고(`services.set_drill_mode`) 커널 생성 경로로 사건을 만든 뒤 **미처리→접수→조치 중→종결** 을 밟는다 → `u1.kick.drill` 이 `event#N` 으로 닫힌다 |
| `test_receiving_a_drill_alert_closes_the_first_card` | 훈련 창 안에 **내게 온** 성공 발송 한 줄 → `u3.kick.drill` 이 `delivery#N` 으로 닫힌다 |
| `test_a_threshold_change_closes_the_sysops_first_card` | `ThresholdChange(changed_by=나)` → `u5.kick.golden30` 이 `threshold_change#N` 으로 닫히고, `closed_by` 가 **`predicate:_closed_by_threshold_change`** 인지까지 본다(U2 카드와 같은 함수인지 `assertIs` 로 대 본다) |

**음성 대조 1** — `test_someone_elses_drill_alert_does_not_close_my_card`: 같은 테넌트라도
**남에게** 간 훈련 알림은 내 카드를 못 닫는다.
**멱등 1** — `test_the_row_is_written_once_and_not_again`: 두 번 조회해도 행은 하나.
**나머지 8** — 짝지은 카드가 `CARDS` 의 그 카드 **하나로** 판정되는가(닫히기 전·후 둘 다) ·
못 재는 짝이 **같은 사유**를 쓰는가 · 18이 18인가 · 답에 언제나 3장인가 · 못 재는 카드가
이름·문안·사유를 갖는가 · 잴 수 있는 첫 카드가 0인 역할이 없는가 ·
**첫 카드가 `total`·`done` 을 흔들지 않는가**.

### ② 첫 진입 — 세 역할을 **제품의 문으로** 잼 [실측 2026-09-21 · gx-shell 안]

실계정 로그인(`POST /api/v1/auth/login` · `end_previous_session: true`) 뒤
`GET /api/dsm/onboarding/progress`. 자격은 저장소 밖 `.env.gates` 의
`GX_SEED_ROLE_PASSWORD`(sha256[:12] **de08e1f17eb3** · 길이 24) — **값은 argv 에도
셸 소싱에도 안 태웠다**(파일로 넣고 실행 뒤 지웠다). V 잠금은 없었다(`v_lock.is_locked() → False`).

| 역할 | 계정 | 로그인 | 진행률 응답 | 서버가 준 역할 | 첫 카드 | 닫힘 |
|---|---|---|---|---|---|---|
| U1 | `gxseed_u1_operator` | **200**(토큰 300자) | **200** | `U1` · `role_known=True` | 3장(재는 칸 2 · 회색 1) | **1** — `event#231073` (`CARDS:u1.response`) |
| U2 | `gxseed_u2_manager` | **200** | **200** | `U2` · `role_known=True` | 3장(재는 칸 1 · 회색 2) | 0 |
| U4 | `gxseed_u4_official` | **200** | **200** | `U4` · `role_known=True` | 3장(재는 칸 2 · 회색 1) | **1** — `report_run#1` (`CARDS:u4.report`) |

- **잰 역할 3/3.** 세 역할 모두 기둥이 **골든타임 30 · 정직 관제 · 훈련 모드** 로 왔고,
  카드가 **언제나 3장**(재는 칸 + 회색)이었다.
- 회색 카드는 **사유를 달고** 나왔다 — 예: U2 ②「등급을 바꾼 기록을 사건별로 되짚는
  자리가 아직 없습니다.」
- **진행률은 안 흔들렸다**: U1 `done=3/total=3 · blocked=4`, U2 `1/3 · blocked=4`,
  U4 `1/1 · blocked=6` — 전부 `CARDS` 만 센 수다.
- ⚠ 이것은 **화면이 아니다.** 「첫 진입에 그 사람이 서버에서 받는 것」이다.

### ③ 어긋남 하나를 적어 둔다 — U4 ① 「열람」

§4-4 는 U4 ① 의 닫는 기록을 **「월간 자동본 열람 1」**이라 적었다. 열람은 서버에 안 남는다.
그래서 이 카드는 **자동본의 실행 기록**(`DsmReportRun`)으로 닫힌다 — 「그 사람이 봤다」가
아니라 「그 보고서가 나왔다」다. 새 술어로 갈라 놓지 않고 같은 역할의 기존 카드
`u4.report` 를 **그대로 가리켰다**: 갈라 놓으면 같은 사실에 판정이 둘이 된다.
각 카드가 §4-4 의 약속을 `promised_record` 로 들고 있어 어긋남이 응답과 화면에 **보인다**.
위 ② 의 U4 줄이 그 실물이다 — 문안은 「열어 보세요」인데 닫은 기록은 `report_run#1` 이다.

### ④ 프런트 타입검사 — **내 파일 오류 4 → 0** [실측 · `gx-fe-build` 안]

`npx tsc --noEmit -p tsconfig.app.json` (총량으로 가른다 · 종료 코드가 아니다).

⚠ **첫 실행이 거짓 초록이었다 — 그 자리를 적어 둔다.** `npx tsc --noEmit` 만 부르면
`rc=0 · 총 오류 0` 이 나온다. 그런데 `/app/tsconfig.json` 은 **107바이트짜리 솔루션 파일**
(`"files": []` + `references` 둘)이라 **아무것도 검사하지 않는다.** 기준선이 수천인데
0 이 나오는 것이 신호였다 — 「빈 집합끼리 일치」다. `-p tsconfig.app.json` 을 줘야 실제로 돈다.

- 진짜 검사 1차: 총 **1651** · 그중 **내 파일 4건**(`'kick' is possibly 'undefined'` ×4 —
  `view` 로 이름을 바꾸다 머리글 넷을 놓쳤다). **고쳤다.**
- 진짜 검사 2차: 총 **1647**(정확히 −4) · **`Onboarding.tsx` 걸린 줄 0건**.
  줄어든 수가 내 파일에서 사라진 수와 **같다** — 다른 곳을 건드리지 않았다는 뜻이다.
- ⚠ 총량 1651 은 **기준선 3234 와 견줄 수 없다**: `gx-fe-build` 의 `/app/src` 는 다른 차선들의
  이 턴 변경이 안 실린 낡은 사본이고, 나는 **내 파일 하나만** 넣었다(공용 소스를 통째로
  덮으면 아홉 차선의 반쯤 된 코드를 함께 굽는다). 내가 말할 수 있는 것은 **내 파일의
  오류가 4 → 0** 이라는 것뿐이고, **총량 대조는 조율자의 병합 뒤 빌드 몫**이다.

---

## 4. PNG 캡처를 못 찍은 이유 — **번들이 이 턴의 프런트 변경을 안 싣는다** [실측]

```
grep -rl "오늘 먼저 세 가지" /app/_fe_dist   → (없음)
grep -rl "첫 근무일에 혼자 시작하기" /app/_fe_dist
                                          → /app/_fe_dist/assets/Onboarding-CisVBX2j.js
```

3002 가 내주는 번들에는 **옛 온보딩 화면만** 있다. 지금 `/start` 를 찍으면 **첫 카드 셋이
없는 화면**이 찍히고, 그 장을 「첫 진입 캡처」라고 부르면 **거짓 초록**이다.

번들을 다시 굽지 않았다. 굽는 일은 (ㄱ) `gx-fe-build` 의 `/app/src` 를 통째로 덮어
**아홉 차선의 반쯤 된 코드를 함께 굽고**, (ㄴ) 공용 `_fe_dist` 를 갈아 다른 차선의 캡처를
바꾼다. 둘 다 내 소유 밖이다. **그래서 회색이다 — 0 이 아니다.**
V 가 「첫 10분 화면 12」를 돌 때 **번들을 새로 구운 뒤** 다섯 장(U1·U2·U4·U5·U6)을 함께 찍으면 된다.

---

## 5. 조율자 요청 둘 — 반영했다

1. **`FirstCards` 를 `export`** 했다. `KickView`·`KickCardView` 타입도 함께 내보낸다.
2. **`kick` 을 선택 인자로 받는다** — 그리고 받으면 **아예 안 부른다**:
   `useDsmResource(..., { enabled: !kick })`. 「받아 놓고 버린다」가 아니라 **요청 자체가 없다** —
   홈 한 장이 같은 문을 두 번 두드리는 일이 구조로 사라진다.
   `/start` 는 인자가 없으므로 지금처럼 제가 부른다.
   ```tsx
   export function FirstCards({ chapter, kick }: { chapter?: string; kick?: KickView })
   ```
   `chapter` 도 선택 인자로 바꿨다(홈은 탭이 없다).

---

## 6. U0 운영자 카드 3 — **설계만** (구현 0 · 지시대로)

### 왜 표에 안 넣었나

`CARDS` 에 `"U0"` 을 더하면 **아무도 못 보는 버킷**이 하나 생긴다: `_role_buckets()` 는
K3 역할 넷만 가르고 `PERSONA_VIEWERS` 는 U3·U6 뿐이라, U0 표는 어떤 요청으로도 안 닿는다.
`test_every_card_table_is_reachable` 이 그 자리를 이미 빨강으로 잡고, 닿지 않는 표를 세어
「6/6」이라 적으면 그 수는 거짓이다(D-301). **운영자는 테넌트가 아니다.**

### 카드 3 (같은 세 기둥 · 문안 초안 · 닫는 기록 후보)

| 기둥 | 문안 초안 | 닫는 기록 후보 | 지금 있나 |
|---|---|---|---|
| 골든타임 30 | 「어제 30분을 넘긴 테넌트가 있는지 한 줄로 보세요」 | 운영자 콘솔의 p95 산출 실행 기록 1 | **없다** — 콘솔에 산출 기록 표가 없다. 서면 술어를 단다 |
| 정직 관제 | 「게이트가 심은 씨앗이 고객 수에 섞였는지 확인하세요」 | `billing_marks` 표식 산출 1 (차선 B 가 이번 턴에 세운다) | **이번 턴에 서는 중** — B 의 `backend/common/billing_marks.py` |
| 훈련 모드 | 「훈련 창에 실채널 발송이 0 인지 보세요」 | `drill_report.real_channel_sends` 산출 1 | **이미 있다** — `drill.py::drill_report` 가 모수와 함께 낸다 |

셋 다 **운영자 자신의 행위가 남기는 기록**으로 닫는다 — 사람 체크 0 규약은 운영자
콘솔에서도 같다. 그 표가 서는 턴에 `KickCard` **같은 모양**을 쓰면 판정 규약이 한 벌로 남는다.

---

## 7. 손댄 파일 (소유표 안 · 공용 0 · 삭제 0 · 커밋 0)

| 파일 | 무엇 |
|---|---|
| `backend/apps/dsm/onboarding.py` | `KICK_PILLARS` · `KickCard` · 훈련 술어 5 · `KICK_CARDS`(18) · `kick_integrity()` · `kick()` · `progress()` 응답에 `kick` 칸 |
| `backend/tests/test_onboarding_progress.py` | `OnboardingKickCardsTest` 13개 |
| `frontend/src/features/dsm/pages/Onboarding.tsx` | `FirstCards`(export · `kick` 선택 인자) · `KickView`·`KickCardView` export · `KICK_HEADLINE` · 탭을 제어 상태로 |
| `docs/agent/checkpoints/turn-ab/조율자.inbox/K.md` | 쪽지 |

**공용 파일 0건.** `api_f.py`·`App.tsx`·`routes.ts`·`services/API.ts`·`Home.tsx` 를 안 고쳤다 —
`api_f.py` 는 `progress()` 의 dict 를 스키마 없이 그대로 내보내므로 `kick` 칸이 라우트를
안 고치고 흘러간다[실측 `api_f.py:77` · 위 §3 ② 의 200 이 그 실물이다].

`--no-verify` 0 · 비밀 출력 0(지문 12자까지) · §0.4 금지구역 읽기만 · 커밋 0.

---

## 8. 남은 가정 하나

**`DsmReportRun.event` 가 있는 보고서만 「훈련 보고서」**라는 판정. 보고서 행에 훈련 칸이
없어서 **사건 쪽의 훈련 창**으로 갈랐다(훈련이란 이 저장소에서 「훈련 창 안에 발생한
것」이다 · `drill.is_drill_event_for_stream`). 월간 자동본처럼 사건이 없는 보고서는 이
카드를 못 닫는다 — 의도한 바다. U2 ③ · U4 ③ 두 카드가 이 판정 위에 선다.

(1판의 가정 ①「훈련 창 안의 사건·발송이 목록에서 안 빠진다」는 **시험 둘이 깨러 가서
통과했다** — 더는 가정이 아니다 · §3 ①.)
