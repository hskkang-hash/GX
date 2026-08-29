# P-20 — 시드 구멍 둘을 메웠다 (알림 규칙 · 스냅샷) · 시스템 이벤트 둘

**실행 2026-09-22 · 차선 E2** · 도구 `manage.py seed_dsm_events` · 판정 `scripts/verify_seed_p20.py`
이름 넷: `DB_TEST_NAME=test_gx_e` · 포트 8500 · 접두 `e_` · 테넌트 `tenant_e`

---

## 0. 네 수 [실측 2026-09-22 · `verify_seed_p20.py` exit 0]

```
발송 기록        120행     (심각 10건 × 수신자 12명 · K2 가 만든 행이다)
스냅샷 객체       20장      (MinIO 실제 객체 · 합성 표식 프레임)
MinIO ↔ DB      일치      객체 20 · 참조 20 — **이름 하나하나로** 대조 · 고아 0 · 결번 0
시스템 이벤트      2건      camera_down 1 · storage_high 1
```

착수 전 같은 자리의 수 [실측 2026-09-22 · 같은 도구]:

```
알림 규칙 0 · 발송 기록 0 · 스냅샷 참조 0 · 시스템 이벤트 0 (기대 2)
```

---

## 1. 「반씩」이 우연이 아니다 — 규칙이 걸리는 자리를 등급으로 잡았다

지시서 P-20 ①: *"시드 이벤트 20건 중 **절반이 규칙에 걸려** 「발송 기록」이 생기게"*.

수를 맞추려고 10건을 골라 보내면 그 10은 **시드가 고른 10**이다. 그러면 「절반」은
배선의 성질이 아니라 시드의 성질이 된다. 대신 규칙을 `severity=critical` 하나로 세웠다:

```
fire 5 + flood 5 = critical 10          ← 규칙이 건다   (시드 이벤트의 정확히 절반)
intrusion 5(warning) + person 5(info)   ← 규칙이 없다   (안 가는 것이 맞다)
```

**시드는 「보내라」고 말하지 않는다.** 심은 이벤트를 전부 `k2_notify.send` 에 넘기고,
등급이 안 맞아 규칙이 없는 것은 K2 가 거른다. 절반은 그 결과로 나온다.

## 2. 시드는 규칙을 흉내 내지 않았다 (P-20 ④) — 그것을 어떻게 아는가

`DeliveryRecord` 행을 시드가 하나도 만들지 않았다. 세는 넷이 전부 K2 의 답이다:

```
발송 기록 120행 · 억제로 접힌 이벤트 0 · 수신자 0명 0 · 실패 행 0
```

★ **한 번 실측으로 확인됐다.** 시드를 지우지 않고 두 번 돌렸더니 두 번째 실행의 발송이
**전부 접혔다**(`억제로 접힌 이벤트 10 · 발송 기록 0행`). 5분 억제(K2 `suppress`)가
이전 실행의 성공한 발송을 보고 접은 것이다. 시드가 행을 직접 만들었다면 그 자리에
**120행이 또 생겼을 것이고**, 억제가 죽어 있어도 아무도 몰랐을 것이다.

## 3. 스냅샷 — **K1 경로로만 붙였다** (P-9 · `_base_manager` 직접 쓰기 0)

```
① 합성 표식 프레임을 만든다      (Pillow · 단색 + 글자)
② MinIO 에 올린다               stream_monitors.services.detection_snapshot.upload_snapshot
                               — 파이프라인이 쓰는 그 함수를 그대로 쓴다
③ 참조를 붙인다                 kernels.k1_event.record_detection(snapshot_path=…)
④ 같은 객체에 한 번 더 올린다     ← event_id 를 이미지에 적기 위해서
```

★ ④가 왜 필요한가. 그림에 `event_id` 를 적으려면 번호를 알아야 하는데, 번호는 K1 이
행을 만든 뒤에 생긴다. **행을 나중에 고치는 것은 직접 INSERT 와 같은 일**이므로(D-401),
대신 **같은 객체 이름에 덮어쓴다.** 객체 이름은 `(카메라, 시각)` 으로 정해지므로
같은 인자면 같은 이름이고, **객체 수는 늘지 않는다** — 위 「객체 20 · 참조 20」이 그 확인이다.
그림이 인자 말고 다른 것에 안 흔들린다는 것은 시험이 잰다
(`test_same_arguments_draw_the_same_picture`).

★ 이미지는 **실제 장면을 흉내 내지 않는다.** 단색 바탕에 다섯 줄:

```
SEED / 합성 표식 프레임
실제 CCTV 장면이 아닙니다
테넌트  ETRI-Group
event_id  4770
시각  2026-09-03 12:54:58
출처  data_source=seed
```

「사진이 아닌가」는 **가장 흔한 색 하나가 화면의 절반을 넘는가**로 잰다. 첫 판은
「색의 가짓수 < 3000」이었고 재어 보니 **3888**이었다(JPEG 가 글자 가장자리에 만드는 색).
그 수는 「사진인가」와 관계가 없어 **술어를 바꿨다** — 재고 나서 문턱만 올리는 것은
답을 고치는 일이다 (D-350).

## 4. 시스템 이벤트 — **지시서의 전제가 틀렸다** [실측]

지시서 §1 ③: *"이미 이벤트로 나오면(09-20 커밋) W1 프리셋 4 「시스템」
(event_type ∈ {camera_down, storage_high, …}) 으로 U5가 본다. **새 화면 없음.**"*

재어 보니 [실측 2026-09-22] `DetectionEvent.EventType` 에 그 둘이 **없었다.**
09-20 커밋이 만든 것은 `ops_monitor` 의 신호(`cameras_silent_24h` · `storage_used_pct`)이고,
그것은 크론이 읽는 자리이지 이벤트가 아니다. 「새 화면 없음」은 맞지만 **「새 열거값 없음」은
틀렸다.**

그래서 D-294 가 `flood` 를 더한 것과 **같은 규약**으로 열거를 늘렸다:

```
backend/stream_monitors/models.py                     EventType +2
backend/stream_monitors/migrations/0026_p20_system_event_types.py
backend/stream_monitors/services/detection_event_bridge.py   기본 등급 +2 (둘 다 warning)
docs/contracts/detection-event.md                     §열거값 + 사유
```

규약의 나머지 반쪽 — W2-3 색 규칙(`frontend/`) — 은 **이 차선이 건드리지 않았다**(C 의 자리).
다시 재어 보니 [실측 2026-09-22 · `frontend/src/features/dsm/severity.ts`] **차선 C 가 같은
턴에 이미 채워 놓았다**: `EVENT_TYPE_LABEL` 에 두 값 + `SYSTEM_EVENT_TYPES` 배열, 주석이
「마이그레이션 0026(P-20 · 차선 E2)」를 가리킨다. 두 차선이 **서로를 안 보고** 같은 열거를
같은 턴에 맞춘 셈이라 조율자에게 이 대조를 보고한다 — 맞았다는 것과 맞을 것을 알고 했다는
것은 다른 사실이다.

⚠ 이 둘은 **AI 라벨에서 오지 않는다.** `LABEL_TO_EVENT_TYPE` 에 넣지 않았다 — 넣으면
AI 가 「카메라가 죽었다」를 검출했다고 말할 수 있게 된다. 그리고 오탐률 분모가
`event_type` 별로 갈리므로(D-294), 전용 타입을 둔 것이 탐지 유형의 오탐률을 지킨다.

## 5. 규칙이 있다 ≠ 받을 사람이 있다 [실측 · D-301]

```
알림 규칙 4건   critical/fire_user · critical/operator · critical/fire_admin · critical/view_only_-_anyang
수신자   12명   역할별 {'operator': 12}
```

**넷 중 하나만 사람을 고른다.** 개발 DB 의 `ETRI-Group`(소속 4)에는 `operator` 12명이
있고 `fire_user`·`fire_admin`·`view_only_-_anyang` 은 **0명**이다.
그래서 U2(관제팀장)·U4(공무원)의 모바일 M1 은 여전히 빈 화면이다 — 그것은 규칙의
부재가 아니라 **계정의 부재**이고, 두 사실은 다르다.

규칙을 셋이 아니라 **넷** 세운 이유도 여기 있다. U1(관제요원)은 이 저장소에서 역할 코드가
둘(`fire_user` · `operator` — `config/k3_roles.py` 의 실측 매핑)이고, 하나만 세우면
「규칙은 섰는데 아무도 안 받는」 상태가 된다. 지시서의 「기본 3 [추정]」을 4로 읽었다.

## 6. 발송 이력의 `channel` 은 `log` 다 — **사람에게 갔다고 말하지 않는다**

발송 업체는 미정(D4-1)이고 이 환경의 메일 백엔드는 SMTP 를 가리킨다. 그대로 보내면
120행이 **전부 실패 행**이 되고, 그러면 M1 은 「알림이 있었다」와 「알림이 실패했다」를
가르는 화면이 아니라 실패만 보이는 화면이 된다 — 그것은 배선의 사실이 아니라 환경의 사실이다.

그래서 `LogChannel` 을 끼웠다. 도달한 곳은 **로그**이고, 그 사실은 지워지지 않는다:
발송 이력의 `channel` 칸에 `log` 가 남고, `channels.NON_HUMAN` 이 「이 채널은 사람에게
도달하지 않는다」를 판정식 복제 없이 답한다(D-212).

★ [실측] **시드 데이터로 F-10 은 초록이 될 수 없다.** 시드는 중복 억제(10초)를 피하려고
이벤트를 3분씩 과거로 밀어 심으므로 `occurred_at → sent_at` 이 언제나 30초를 넘는다.
시드 실행이 그 수(`F-10 만족 0행`)를 함께 찍는다 — 보고서가 시드의 지연을 제품의
지연으로 읽지 않게 하기 위해서다.

## 7. 새 쓰기 면 하나 — 탐침이 먼저다 (P-8)

`kernels.k2_notify.save_notification_rule` 을 열었다. 검사 넷을 지난다:

```
등급    계약 열거 밖이면 거절            (오탐 통계를 오염시키는 값이 안 들어온다)
역할    role.Role.code 로 실재 확인      (없는 역할을 가리키는 규칙은 영원히 0명을 고른다)
채널    등록 어댑터 또는 미구현 등재만    (오타 채널은 발송마다 실패 행만 남긴다)
소속    없으면 거절                     (소유 없는 규칙은 전 테넌트에 보인다)
```

`tests/test_tenant_isolation.WRITE_NO_PROBE` 의 선등재 줄을 **아직 못 지웠다** — 그 파일은
공용 등록부이고 조율자만 고친다. 그래서 같은 시나리오를 먼저 세웠다:
`backend/tests/test_e_p20_seed.py::SaveNotificationRuleIsolationTest`
(음성: A 가 B 의 규칙을 고치려 하면 거절 + **행이 안 바뀐다** · 양성: 제 규칙은 고친다).
옮길 조각은 보고서에 있다.

★ [실측 · 별건] `test_write_probe_registry_covers_kernel_writes` 가 훑는 패키지는
`kernels.k1_event` 와 `stream_monitors.services.zones` **둘뿐이다.** `kernels.k2_notify` 는
훑지 않는다 — 그래서 K2 의 쓰기 공개 면(`send` 도 포함)은 **대장이 안 보는 곳에서** 자란다.
D-301 의 이 파일 판이다. 조각을 보고했다.

## 8. 시험 [실측]

```
tests/test_e_p20_seed.py                                     14 passed · exit 0
tests/test_k2_notify_kernel.py 외 5종(계약·등급·DSM·FX-5·K4)   129 passed · exit 0
tests/test_tenant_isolation.py + no_drop + k1_kernel           58 passed · exit 0
tests/ (e2e 제외 · 커버리지 동시 측정)            590 passed · 2 failed · 1 skipped
```

2 failed 는 `tests/test_f05_event_api.py::EntrySurfaceIsLockedTest` 이고 **이 차선의 것이
아니다** — 진입면이 21 → 22 로 늘었고 새로 생긴 것은 `GET /api/dsm/events/summary` 다.
`backend/apps/dsm/api.py` 가 이번 턴 차선 C 의 자리다(파일 수정 시각으로 대조).
`EVENT_ENTRY_SURFACE` 등재는 그 면을 연 차선이 같은 커밋에서 늘려야 한다.

## 9. QA-07 — 커버리지 첫 수 [실측 2026-09-22]

```
설치   pytest-cov 6.0.0 · coverage 7.16.0        (lock: backend/requirements-dev.txt · --require-hashes 로 재설치 확인)
명령   pytest tests/ --ignore=tests/e2e --nomigrations -p no:randomly \
         --cov=kernels --cov=apps --cov=stream_monitors --cov=common
첫 수  TOTAL 12,356 stmts · 5,934 miss · **52%**
```

커널만 보면 다른 그림이다 — 회색 7절이 갈리는 자리가 여기다:

```
k1_event  92% · k2_notify 90% · k3_dashboard 88% · k4_report 90% · k5_trust 92~100%
apps/dsm  services 84% · api 45%
common    tenant_scope 94% · tenant_filters 82% · tenant_tripwire 70%
```

52% 를 끌어내리는 것은 `stream_monitors` 의 오래된 코드다. **첫 수가 빨강이어도 그것이
옳은 색이다** — 이제 회색 7이 수를 가진다.
