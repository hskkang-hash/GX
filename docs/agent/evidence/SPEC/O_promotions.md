# 차선 O 승격/판정 제안 — 턴 AM (P-376 「반쪽은 닫힘이 아니다」 · OPS O-10·O-04)

**대장(`docs/agent/evidence/D-346/ga_readiness.yaml`)은 손대지 않았다** — 아래는
조율자가 그대로 옮겨 붙일 수 있는 판정이다(P-356 ④ · lane_rules 규칙 3).

---

## §1. Goal 1 — P-376 반쪽 메움: DSM-U2-04 · DSM-U5-02

두 절은 턴 AK·AL(차선 N1)이 「구현」으로 이미 대장에 올렸으나, N1 자신의 메모가
각자 반쪽을 스스로 적어 뒀다(`N1_promotions.md` §AK 주석 · §AL 「부분 승격」 절).
P-376 은 「제목이 부르는 것 중 하나라도 없으면 승격하지 않는다」이므로, 이번 턴은
그 반쪽을 실제로 메워 **FULL**로 만들거나, 못 메우면 **REVERT**(annex 로 되돌림)를
제안한다.

### (a) DSM-U2-04 「임계값 도달 알림」

| 제목이 부르는 것 | 있는 것 (턴 AM 이전) | 있는 것 (턴 AM 이후) |
|---|---|---|
| 하천 **수위**가 통제 기준에 닿으면 도달 알림 | ✅ `waterlevel.baseline` 키(표 ①) + `POST /thresholds/observe`·`.../decide` | ✅ (안 건드림) |
| 하천 **강우량**이 통제 기준에 닿으면 도달 알림 | ❌ `rainfall.*` 키가 표 ①에 없음(N1 자신의 메모로 「강우량 키는 없이 수위만 실측」이라고 적어 둠) | ✅ `rainfall.baseline` 키 등록(`kernels/k5_trust/thresholds.py`) — 정의만(D-280, 지어낸 기본값 없음). 값은 여전히 운영이 카메라별로 심는다(`ThresholdNotSet` 그대로 지킴) |
| 도달 시각·결정 시각 둘 다 감사 | ✅ (수위 경로로 실측됨) | ✅ 강우량 경로로도 **같은 코드**·같은 감사 모양이 실측됨(코드 변경 0 — 표에 키 하나만 늘었다) |

**증거**: `docs/agent/evidence/SPEC/P376_DSM-U2-04-rainfall.json`(observe→182mm 관측
→reached=true→decide→강우량 키로 도달·결정 감사 왕복 실측) — 기존 `DSM-U2-04.json`
(수위 경로)은 그대로 둔다(N1 소유 시험이 씀, 손대지 않음).

**시험**: `backend/tests/test_p376_half_clauses.py::RainfallThresholdKeyTest`
(4건 — 표 등재·D-280 무결점 확인·강우량 관측→결정 왕복·미설정 지점 400 확인).
gx-shell 실측: 4건 전부 통과(아래 §3 재현 명령).

**코드 변경 반경**: `backend/kernels/k5_trust/thresholds.py` 에 `rainfall.baseline`
정의 한 항목 추가뿐 — `api_u24.py`(N1 소유)·`threshold_alert_service.py` 는
**한 줄도 안 고쳤다**(`ThresholdObserveIn.key: str` 이 이미 임의 키 문자열을 받고,
값 판정은 `resolve_threshold` 하나이므로 표에 키를 올리는 것만으로 같은 문이
새 키를 받는다 — N1 의 메모가 예견한 그대로).

**판정: FULL — 승격 유지.** 제목이 부르는 「수위·강우량」 둘 다 이제 실제 엔드포인트
+ 감사 + 증거로 갖춰졌다. 게이트(`scripts/verify_spec_dsm.py`)는 차선 N1 소유라
이번 턴에 행을 더하지 않았다 — 조율자가 그 파일에 `P376_DSM-U2-04-rainfall` 증거
참조를 원하면 옮겨 붙일 수 있다(이 차선은 그 파일을 고치지 않았다).

### (b) DSM-U5-02 「접근권한·접속기록」

| 제목이 부르는 것 | 있는 것 (턴 AM 이전) | 있는 것 (턴 AM 이후) |
|---|---|---|
| **접속기록** 조회·CSV(뒤 갈래) | ✅ `GET /access-log[/export.csv]`(`access_log_service.py`, N1) | ✅ (안 건드림 — `api_u24.py` 는 N1 소유라 손대지 않음) |
| **사람별 카메라·기능 권한**(앞 갈래) | ❌ 저장처·화면·엔드포인트 어디에도 없음(N1 자신의 grep 재확인 — `CameraPermission`·`권한관리` 0건) | ✅ `GET /access-log/permissions`(새 컨트롤러 `api_u5_perm.py`) — 사람마다 **카메라 목록**(그 사람의 그룹 소속 카메라 전체) + **기능 권한**(DA-03 §3-4 위젯 8종의 HIDDEN/VISIBLE/EDITABLE)을 낸다 |

**있는 것의 결(grain)을 숨기지 않는다**: 이 제품에 **사람별** 카메라 ACL 은 원래
없다 — 카메라 접근은 **테넌트(그룹) 단위**다(F-05 의 IDOR 차단도 이 단위). 그래서
새 문의 「카메라」 칸은 *그 사람이 속한 그룹의 카메라 전체*이고, 같은 그룹의 두
사람은 그 칸이 같다 — 시험(`test_sysop_sees_person_camera_and_feature_permissions`)
이 이 사실을 **일부러 확인**한다(다르게 보이면 그것이 거짓말이므로). 「기능」 칸은
사람마다 다르다(역할에 따라 위젯 매트릭스 값이 갈린다 — 실측: 팀장 role_bucket
`manager`, 시스템관리자 `sysop`, 8개 위젯 키 전부 응답에 실림).

**재사용(새 판정 0)**: 카메라 목록은 `stream_monitors.services.camera_pulse.
pulse_rows`(UX-23 이 이미 쓰는 그 함수) 그대로 부른다 — `StreamMonitor` 가
`BaseModelWithGroup`(M2M `groups`)이라 `.objects.filter(group=...)` 를 새로 짜면
필드 이름부터 틀린다는 것을 확인하고 기존 함수로 우회했다. 기능 권한은
`kernels.k3_dashboard.services.get_preset`·`widget_permission`(DA-03 §3-4 커널)을
사람마다 다시 부른다. 문지기는 `apps.dsm.audit.access_log_denial` **그대로
재사용**(접속기록과 같은 좁은 문 — 시스템관리자·테넌트관리자·전역관리자만).

**증거**: `docs/agent/evidence/SPEC/P376_DSM-U5-02-permissions.json`(시스템관리자로
실제로 두드려 팀장 A 의 행에 카메라 1대 + 위젯 8개 권한이 실려 나오는 것을 확인).

**시험**: `backend/tests/test_p376_half_clauses.py::AccessPermissionMatrixTest`
(4건 — 팀장 403·시스템관리자 200+내용 확인·타 테넌트 격리·조회 자체가 감사에
남음). gx-shell 실측: 4건 전부 통과.

**새 엔드포인트**: `GET /api/dsm/access-log/permissions`
(`backend/apps/dsm/api_u5_perm.py` — 새 컨트롤러 `DsmU5PermAPI`, `@tenant_scoped`
+ `JwtOrInboundKey()`, `api_u24.py` 는 한 줄도 안 고침). `EVENT_ENTRY_SURFACE`
(`backend/tests/test_f05_event_api.py`)와 `apps/dsm/urls.py`(컨트롤러 등록)에
각각 한 줄 추가 — 삼킴 없음 실측(`/access-log`·`/access-log/export.csv` 는 둘 다
완전한 리터럴, 변수 조각 없음).

**판정: FULL — 승격 유지.** 제목이 부르는 「접근권한(카메라·기능)·접속기록」 둘 다
이제 실제 엔드포인트 + 감사 + 증거로 갖춰졌다. 게이트는 N1 소유(`verify_spec_dsm.py`)
라 이번 턴에 행을 더하지 않았다 — 조율자가 원하면 `P376_DSM-U5-02-permissions`
증거 참조를 옮겨 붙일 수 있다.

---

## §2. Goal 2 — OPS annex O-10(키·자격 회전) · O-04(모델 레지스트리)

두 절 다 annex(`docs/agent/roadmap/기능명세_미포함표_20260925.md` Table A)에
「없음(annex · P-234 8영역 밖 · 신설 필요)」로 적혀 있고, U0(플랫폼 운영자) 몫이다
— DSM/FWS 테넌트 앱과는 다른 층(플랫폼 콘솔)이다. 조사 결과 **둘 다 P-356 넷을
갖추지 못한다** — 아래는 「무엇이 없는가」다(P-376 규율 그대로: 반쪽을 닫힌 것으로
올리지 않는다).

### O-10 「키·자격 회전」

완결 조건(`docs/design/GuardianX_플랫폼구조설계서_v1.0_…20260915.md` §7 표):
**「회전 뒤 게이트 계정 로그인 4/4 · 옛 키 401」**(AND 조건).

| 제목이 부르는 것 | 있는 것 | 없는 것 |
|---|---|---|
| API 키 회전 | ✅ `kernels.k5_trust.inbound_keys.rotate_key` + `POST /api/dsm/settings/api-keys/{id}/rotate`(F-05, 기존) — **옛 키 401** 은 이 door 로 Django test client 실측 가능 | 하나의 O-10 콘솔에 묶여 있지 않다(DSM 테넌트 설정 화면의 부속물) |
| 서명키 회전 | ✅ `kernels.k5_trust.webhook_signing_keys`(값 생성·`.env` 이름만 저장) | 재발급(회전) 경로는 있으나 **HTTP 로 여는 화면/엔드포인트가 없다** |
| DB/MinIO 자격 회전 | ◐ `scripts/rotate_shared_passwords.py`(P-112, 74계정 공유 비밀번호 회전) | **게이트 계정을 일부러 제외한다**(`NEVER_TOUCH` — `gxseed_*`·`gxprobe_*` 전원). 즉 이 스크립트를 아무리 돌려도 「게이트 계정이 새 값으로 로그인」은 애초에 관측 대상이 아니다. MinIO 쪽 자격 회전은 이 스크립트 안에 없다 |
| VAPID 회전 | ◐ `apps/dsm/notify_prefs.py` 가 **있는가/없는가**만 읽는다(값 회전 없음) | 회전 경로 자체가 없다. 표 ②(`credentials.py`)에도 없다 |
| 회전 주기 | ✅ `docs/agent/evidence/D-373/key_rotation_last.json`(90일 정책 · 초과 키 나이 추적, beat job) | API 키 한 갈래뿐 — 서명키·DB·VAPID 는 주기 추적이 없다 |
| 재생성 창 runbook | ◐ 각 스크립트 docstring 이 손 runbook(마른 실행→적용→원장) | **하나로 묶인 runbook 문서가 없다** — 넷이 각자 다른 파일에 흩어져 있다 |
| **완결 조건 앞 반**(게이트 계정 로그인 4/4, 회전 뒤) | ❌ | **이 환경에서 구조적으로 못 잰다** — 게이트 계정 자신의 자격을 실제로 바꾸고 실제 서버(8500/8000)에 로그인해 보는 행위가 필요한데, lane_rules 규칙 14(「Don't log in to live servers」)가 이 차선에 그 행위를 금지한다. 시간이 없어서가 아니라 **이 차선의 권한 밖**이다 |

**판정: 승격하지 않는다(REVERT 대상 아님 — 애초에 승격된 적이 없다. annex 에 그대로
둔다).** 이유를 한 줄로: *완결 조건이 AND 이고, 뒤 반(옛 키 401)은 이 턴에 기술적으로
증명 가능하다는 것을 확인했으나(재사용 가능한 door 실재), 앞 반(게이트 계정
로그인 4/4)은 이 차선이 라이브 서버에 로그인할 수 없다는 절차적 제약 때문에
**영구히**(이번 턴 한정이 아니라 이 실행 환경 자체가) 증명할 수 없다.* 승격
제안 대신 이 사실을 시험으로 고정했다(`backend/tests/test_p356_ops_spec_promotions.py::
KeyRotationCoverageTest`) — 다음 사람이 같은 조사를 반복하지 않게.

### O-04 「모델 레지스트리」

완결 조건: **「배포 → 테넌트 오탐률 추세 표시」**.

| 제목이 부르는 것 | 있는 것 | 없는 것 |
|---|---|---|
| 모델 버전 관리 | ❌ | `ModelVersion` 류 저장처 0건(전수 grep) |
| 앱 태그 | ❌ | 없음 |
| 테넌트 배포·롤백 | ❌ | 배포/롤백 상태기계 없음 |
| 카메라별 바인딩 현황 | ❌ | 카메라 ↔ AI 모델 버전을 잇는 표 없음 |
| 성능(오탐률) | ◐ `kernels.k6_feedback.false_positive_rate`(판정자·카메라별 오탐률은 있다) | **모델 버전과 안 엮인다** — 「배포 → 추세」를 이을 축이 없다(`false_positive_rate` 시그니처에 `model_version` 없음, 시험으로 고정) |

**판정: 승격하지 않는다(annex 에 그대로 둔다).** L~XL 규모(새 저장처 + 배포·롤백
상태기계 + 카메라 바인딩 + 추세 집계 넷을 다 새로 지어야 한다)라 이번 차선
시간 상자(2.5h, 이미 Goal 1 에 상당 시간을 썼다) 안에 정직하게 못 붙인다. 이
결론도 시험으로 고정했다(`ModelRegistryAbsenceTest`).

### 새 게이트 — `scripts/verify_spec_ops.py`

`verify_spec_fws.py` 구조를 그대로 베꼈다(D-212). `CLOSED_CLAUSES = ()`(닫은 열
0/2, 정직한 결론) · `NOT_STARTED` 에 O-10·O-04 각각의 「무엇이 없는가」. 자기시험
+ `TheSelfTestCanFail` 짝(`backend/tests/test_verify_spec_ops_gate_can_fail.py`)
+ `scripts/_gate_header.py::SELF_TEST_LINKS` 한 줄 — `verify_gate_header.py` 로
재확인: 「새 게이트 7개 중 짝 실재 7개」(내 것 포함, 기준선 빚에 안 들어감).

---

## §3. 시험·게이트 재현 (턴 AM · 차선 O)

```
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e DB_TEST_NAME=test_gx_lane_o -w /app gx-shell \
  python -m pytest tests/test_p376_half_clauses.py \
    tests/test_p356_ops_spec_promotions.py \
    tests/test_verify_spec_ops_gate_can_fail.py \
    tests/test_f05_event_api.py tests/test_dsm_app.py tests/test_k5_threshold_table.py \
    -q --create-db -p no:randomly

python scripts/verify_spec_ops.py --self-test   # 판정 규칙만(호스트 · docker 없음)
python scripts/verify_spec_ops.py               # 기본(닫은 열 0/2, PASS)
python scripts/verify_spec_ops.py --run          # 길목 시험을 다시 돌려 확인(손)
python scripts/verify_gate_header.py             # 새 게이트 머리글·짝 감사
```

## §4. 파일 변경 목록 (backend/frontend/shared)

**backend — 신규**
- `backend/kernels/k5_trust/thresholds.py` (편집 — `rainfall.baseline` 정의 추가)
- `backend/apps/dsm/access_permission_service.py` (신규)
- `backend/apps/dsm/api_u5_perm.py` (신규)
- `backend/tests/test_p376_half_clauses.py` (신규)
- `backend/tests/test_p356_ops_spec_promotions.py` (신규)
- `backend/tests/test_verify_spec_ops_gate_can_fail.py` (신규)

**shared — 최소 편집, 등재**
- `backend/apps/dsm/urls.py` (컨트롤러 등록 한 줄 — `api_u24.py` 는 안 건드림)
- `backend/tests/test_f05_event_api.py` (`EVENT_ENTRY_SURFACE` 한 줄)
- `scripts/_gate_header.py` (`SELF_TEST_LINKS` 한 줄)

**scripts — 신규**
- `scripts/verify_spec_ops.py` (신규 게이트)

**frontend** — 없음(이번 턴은 화면을 새로 만들지 않았다. 두 새 문 다 관리자류
좁은 문이고, N1 이 U4-06·U5-02 뒤 갈래를 닫을 때도 화면은 만들지 않았다 — 같은
판단, P-356 이 명시한 「화면은 선택」 그대로).

**docs — 증거**
- `docs/agent/evidence/SPEC/P376_DSM-U2-04-rainfall.json` (기계 작성)
- `docs/agent/evidence/SPEC/P376_DSM-U5-02-permissions.json` (기계 작성)
- `docs/agent/evidence/SPEC/O_promotions.md` (이 파일)
