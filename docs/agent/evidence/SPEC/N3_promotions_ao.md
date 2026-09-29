# N3 승격 제안 — 턴 AO (O-01·02·05~12 · 플랫폼 운영자 U0)
(턴 AO · WO-GX-20260930-18 · 차선 N3)

**조율자가 대장(`docs/agent/evidence/D-346/ga_readiness.yaml`)에 적용한다 — 이
문서는 제안·보고만 한다.** 이 차선은 `ga_readiness.yaml`을 손대지 않았다.

## 0. 일 요약

배정 10절(O-01·02·05·06·07·08·09·10·11·12, O-03·O-04 는 지시서가 이 차선의
일에서 뺐다 — P-413) 중 **여덟을 닫는다**: O-01·02·05·06·07·08·09·12. 새 DB
모델은 **0**개다 — dj-core `logger.AuditLogs`(기존 감사 표)에 계열별
`logger_name`(`guardianx.ops.*`)으로 스냅샷을 싣고, 현재 상태는 "같은 키의
가장 최근 행"으로 접어 읽는다(`stream_monitors/services/response_clock.py`
가 먼저 쓴 방식 그대로 — D-212, 판정 모양은 한 곳에서). dj-core 는 읽기·
호출만 했다(`UserGroup`·`CoreUser`·`UserProfileLink`·`Role` 는 사이트
패키지 `core`, 이 저장소 트리에 소스가 없다 — 수정할 파일 자체가 없다).

**둘은 못 닫는다** — 둘 다 완결조건이 AND 이고, 그중 한쪽 다리가 "라이브
서버 로그인" 또는 "실제 배포 되돌리기 집행"이라 이 차선(HTTP 라운드트립
시험)이 구조적으로 못 잰다: O-10(키·자격 회전 — 턴 AM 의 결론 유지) ·
O-11(릴리스·배포 — 이번 턴 새로 반쪽으로 드러남, 아래 §3).

## 1. 실측 함정 하나 — "완결 조건"과 "설명"은 다른 칸이다

착수 뒤 §7 표를 다시 읽다가 첫 시도(§0의 O-02·O-05·O-07·O-11 title_parts
초안)가 **"설명" 칸의 bullet 을 전부 title_parts 행으로 늘어놓고 있었다**는
것을 스스로 게이트(`judge_title_parts`, 아래 §4)에 걸려 알았다. §7 표는
"설명"과 "완결 조건" 을 **다른 칸**으로 나눠 적어 둔다:

| 절 | 설명(참고 — 전부 title_parts 로 안 옮긴다) | 완결 조건(★ 이것이 닫힘의 기준) |
|---|---|---|
| O-05 | 카메라 맥박·큐 지연·5xx·저장 %·백업 회수증·생존 알림·게이트 16 색 | **테넌트 수 = 보드 행 수 · 빨강 → 인시던트 자동 생성** |
| O-11 | 릴리스 트레인·테넌트별 단계 배포·되돌리기·배포 창 | **deploy.sh exit 0 · 걷기 초록 · 되돌리기 1회 시험** |

이 차이를 따라 O-05 는 (완결조건 두 항이 실제로 구현 가능해서) **닫혔고**,
O-11 은 (완결조건 세 항 중 "되돌리기 1회 시험"이 운영 집행이라 이 차선이
증명 못 해서) **반쪽으로 남았다.** 처음에 "설명" 칸을 title_parts 로 그대로
옮겼을 때는 O-02(유령 시드 정리)·O-07(다른 호스트 목적지)·O-11(되돌리기)
셋에 "없음" 행이 생겼는데, O-02·O-07 은 그 항목이 **완결조건에 없어서**
(설명 칸의 부가 기능일 뿐) 실제로 "measured — 범위 밖이지만 값은 실측"으로
정정해 닫혔고, O-11 만 완결조건 자체에 그 항목이 있어 정직하게 반쪽으로
남겼다. 이 표는 §4 게이트(`judge_title_parts`)의 자기시험이 "열린 행 1개도
안 놓친다"를 확인한다.

## 2. 닫은 여덟

| 절 | 라우트 | 완결조건 실측 | 시험 |
|---|---|---|---|
| O-01 | `POST/GET /api/dsm/ops/tenants` | UserGroup 발급 + 초기 관리자 1(`CoreUser`+`UserProfileLink`, role=admin) → **그 계정으로 실제 `POST /api/v1/auth/login` 200·access_token** | `O01_TenantIssuanceTest` |
| O-02 | `POST /api/dsm/ops/apps/install`·`/status` | `k_app_installation` 대체 행(감사 스냅샷) · 같은 버전 재설치 422(시드 대장 0 충돌) | `O02_AppInstallTest` |
| O-05 | `GET /api/dsm/ops/health` | 테넌트 수 = 보드 행 수 · 카메라 활성 0 인 테넌트 = red · red → `open_incident()` 자동 호출(재사용) · 재호출해도 중복 생성 0 | `O05_HealthBoardTest` |
| O-06 | `POST /api/dsm/ops/incidents(+/respond+/escalate+/close)` | 접수→1차대응→에스컬레이션→종결 4단 · SLA 시계(영업시간 4h·영업일 1일, 자체 구현) · 종결 보고서 1 | `O06_IncidentLifecycleTest` |
| O-07 | `GET /api/dsm/ops/backups` | `D-373/backup_last.json`·`restore_drill_last.json` 값을 **바이트 단위로 같게** 읽음(새 저장 0) | `O07_BackupBoardTest` |
| O-08 | `GET /api/dsm/ops/onboarding` | `ONB-T/turn_*.json`(최신) 읽어 역할별(U1~U6) 진행률·막힌 카드·테넌트별 D-day 계산(새 저장 0) | `O08_OnboardingBoardTest` |
| O-09 | `GET /api/dsm/ops/audit` · `POST .../access-requests(+/approve)` · `GET /api/dsm/ops/tenants/{code}/members` | 운영자 행위 전건(감사 total 증가) · 테넌트 구성원 열람 = 요청 전 403 · 요청 후(승인 전) 403 · 승인 후 200 | `O09_PlatformAuditTest` |
| O-12 | `POST /api/dsm/ops/seed/toggle` · `GET /api/dsm/ops/seed` | `data_source=seed` 표기 · plant→hide 최신 스냅샷 접힘(테넌트+시나리오 키) | `O12_SeedDataTest` |

증거: `docs/agent/evidence/SPEC/O-01.json` ~ `O-12.json`(닫은 여덟만).
`title_parts` 표는 각 파일 안에 있다 — 빈 칸 0.

## 3. 못 닫은 것 — 무엇이 없는가

- **O-10(키·자격 회전)** — 턴 AM 결론 유지. 이번 턴 콘솔 문 둘을 얹었다
  (`GET /api/dsm/ops/keys` 보드 · `POST /api/dsm/ops/keys/rotate` —
  `kernels.k5_trust.inbound_keys.rotate_key` **그대로 재사용**, 새로 안
  만듦). 그러나 완결조건의 AND 절반("회전 뒤 게이트 계정 로그인 4/4")은
  라이브 서버 로그인이 필요해 차선 공통 규칙이 막는다 — 결론 불변.
- **O-11(릴리스·배포)** — `GET /api/dsm/ops/releases` 는 실제로 서고
  `docs/agent/evidence/OPS-27/deploys.jsonl` 의 마지막 배포(commit)를
  바이트 단위로 그대로 읽는다(`O11_ReleaseBoardSmokeTest`, 승격은 안 함).
  완결조건 3항 중 앞 둘(exit 0·걷기 초록)은 실측 가능하지만, "되돌리기
  1회 시험"은 실제 배포 되돌리기(파일 스왑·컨테이너 재시작)가 필요해 HTTP
  라운드트립 시험 범위 밖이고, `deploys.jsonl` 에도 되돌리기 사례가 0건
  이라(grep 0) 장부를 읽는 방식으로도 못 채운다.
- **O-03(라이선스·계량·청구)·O-04(모델 레지스트리)** — 지시서가 이 차선의
  일에서 뺐다(P-413 「출시 뒤」 표 후보). 손 안 댐.
- **O-13·O-14(능력 요청·앱 카탈로그 / 지원 도구)** — 이번 지시서(WO-18)의
  N3 배정에 없다(O-01·02·05~12 만 배정). 손 안 댐 — 다음 배정 후보.

## 4. 게이트 — `scripts/verify_spec_ops.py` 확장

턴 AM 이 O-10·O-04 로 세운 파일을 이번 턴 확장했다(허가됨). 바꾼 것:

1. `CLOSED_CLAUSES = ("O-01","O-02","O-05","O-06","O-07","O-08","O-09","O-12")`.
2. 경로 접두어 판정을 `/api/ops/`(그날 아직 없던 앱을 가정한 자리) →
   **`/api/dsm/ops/`**(실재 라우트)로 고쳤다.
3. **새 판정 `judge_title_parts`** — 증거의 `title_parts` 표에 열린 행
   (`없음`·`부분`·`missing`·`[미확인]`·`대안`·`근사`·`대리` 로 시작하는
   `status`, `excluded_by`+`excluded_why` 없이)이 하나라도 있으면 그 절을
   FAIL 로 되돌린다 — "O 게이트가 빈 칸을 센다"(차선 공통 규약)를 코드로
   고정한다. `judge_evidence` 가 경로·상태 판정 뒤 이것도 통과해야 OK.
4. `run_gate_tests` 가 `test_p356_ops_spec_promotions.py`(AM) 와
   `test_ops_an.py`(N3) 를 **함께** 돈다.

```
python scripts/verify_spec_ops.py --self-test   # 22건(자기시험) 전부 통과
python scripts/verify_spec_ops.py --no-run       # 기본 — 지금 있는 evidence 만
  → 닫은 열 8/11 · PASS

MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e DB_TEST_NAME=test_gx_lane_n3 -w /app gx-shell \
  python -m pytest tests/test_ops_an.py tests/test_ops_an_gate_can_fail.py \
    tests/test_verify_spec_ops_gate_can_fail.py \
    tests/test_p356_ops_spec_promotions.py \
    -q --create-db -p no:randomly
```

자기시험 짝(P-319·P-323): `backend/tests/test_ops_an_gate_can_fail.py`
(이 턴 새로 — `judge_title_parts` 를 망가뜨려 1을 본다) +
`backend/tests/test_verify_spec_ops_gate_can_fail.py`(턴 AM 소유, 이 턴이
`CLOSED_CLAUSES`/`NOT_STARTED` 를 바꿨으므로 그 한 시험 메서드
`test_closed_clauses_is_honestly_empty_this_turn` 의 기대값만 새 진실에
맞게 고쳤다 — 그 파일 docstring 이 예고한 그대로("지우지 않고 값을
고친다")).

## 5. 조율자에게 넘길 줄

- 새 `/api/dsm/` 라우트 22개(아래 §6)를
  `backend/tests/test_f05_event_api.py::EVENT_ENTRY_SURFACE`(조율자 소유)
  에 올려 주십시오.
- `docs/agent/evidence/D-346/ga_readiness.yaml` — 위 여덟 절을 승격(대장
  이동)해 주십시오. 이 차선은 대장을 고치지 않았다.
- `test_verify_spec_ops_gate_can_fail.py`(턴 AM 소유 파일)의 값을 이번
  턴 진실에 맞춰 한 메서드만 고쳤습니다(§4) — 검토 부탁드립니다.
- frontend 빌드·타입체크는 이번 턴 안 돌렸습니다(화면 캡처 환경 셋업이
  이 차선의 시간 상자 밖) — `frontend/src/features/ops/{api.ts,copy.ts,
  pages/OpsHome.tsx}` 세 파일 타입체크를 조율자 창에서 확인 부탁드립니다.
- O-13·O-14 는 이번 지시서 배정에 없어 손 안 댔습니다 — 다음 배정 후보로
  올립니다.

## 6. 새 `/api/dsm/` 라우트 22개 (EVENT_ENTRY_SURFACE 후보 줄)

```
GET  /api/dsm/ops/tenants
POST /api/dsm/ops/tenants
GET  /api/dsm/ops/tenants/{tenant_code}/members
GET  /api/dsm/ops/apps
POST /api/dsm/ops/apps/install
POST /api/dsm/ops/apps/status
GET  /api/dsm/ops/health
GET  /api/dsm/ops/incidents
POST /api/dsm/ops/incidents
POST /api/dsm/ops/incidents/{incident_id}/respond
POST /api/dsm/ops/incidents/{incident_id}/escalate
POST /api/dsm/ops/incidents/{incident_id}/close
GET  /api/dsm/ops/backups
GET  /api/dsm/ops/onboarding
GET  /api/dsm/ops/audit
POST /api/dsm/ops/audit/access-requests
POST /api/dsm/ops/audit/access-requests/{request_id}/approve
GET  /api/dsm/ops/keys
POST /api/dsm/ops/keys/rotate
GET  /api/dsm/ops/releases
GET  /api/dsm/ops/seed
POST /api/dsm/ops/seed/toggle
```
(22줄 — 위 목록을 세어 조율자가 확인해 주십시오. 전부 `@tenant_scoped` +
`auth=JwtOrInboundKey()` — 익명 문 0.)
