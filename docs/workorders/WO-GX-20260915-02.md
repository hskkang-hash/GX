# WO-GX-20260915-02

100% 상용서비스 · 역할 13종 온보딩을 위한 멀티에이전트 초효율 기능구현 작업지시서 — 재난안전관리 App 지침 보강 32 · 산불감시 App 90 · 플랫폼 능력 8 · 운영자 콘솔 12 · 5파 × 2턴

## 0. 헤더

| 항목 | 기입 |
| --- | --- |
| 지시서 번호 | WO-GX-20260915-02 (문서번호 GAION-GX-WO-2026-017) · 선행 WO-GX-20260915-01(RC-1) |
| 사업 / 리포 | GuardianX v1.1 RC-2 / `guardianx-source` · 기준 = RC-1 태그(WO-01 파 4 종료 커밋) · 차선 브랜치 `feat/v11r2-<차선>` |
| 발행 | 세종(CPO · Cowork) · 2026-09-15 · 대표 승인 **필수**(결정 ⑥⑦ 포함 · PRD §10) — 승인 전에는 파 5의 F 차선(플랫폼 경계·능력 인터페이스)만 착수 가능 |
| 수신 | 영실(CPM · Code 조율자) · 차선 에이전트 6 · 검증자 V |
| 실행 모델 | 조율자·F 플랫폼·V: Opus · DSM-지침·FWS-감시·FWS-대응·OPS: Sonnet 기본 · §10 승격 조건 |
| 권한 모드 | 차선 acceptEdits(자기 소유 파일만) · 조율자 auto · 삭제·되돌리기·운영계·`.env` 실제 값·외부 발송: **대표** |
| 예산 상한 | 5파 × 2턴 × 2시간 · 차선 6 동시 · 차선 턴당 세션 1회 · 초과 시 중단·보고 |
| 관련 문서 | PRD v1.1(GAION-GX-PRD-2026-011 §5.9~5.12 · §7.5 · §10 · §14) · 플랫폼 구조 설계서(GAION-GX-ARCH-2026-014) · 재난안전관리 App 명세서(GAION-GX-SPEC-2026-015) · 산불감시 App 명세서(GAION-GX-FWS-2026-016) · 부속서 A · WO-01 §4.2 공용 파일 규약 · `docs/agent/RESUME_NEXT.md` · GC-600 · T-07 |

## 1. 목표 (한 문장) + 완료 정의

**한 플랫폼 위에서 재난안전관리 App과 산불감시 App이 함께 돌고, 역할 13종(DSM 6 · FWS 6 · 플랫폼 운영자 1)이 첫 근무일을 문서 0장으로 끝내며, 운영자는 테넌트 화면에 들어가지 않고 발급·설치·배포·인시던트·온보딩 관제·청구를 끝낸다.**

**DoD**: `verify_app_boundary` exit 0(앱 간 import 0 · 커널 수정 0) · 플랫폼 능력 8 계약 시험 통과 · 지침 보강 32 「끝난다」 · FWS 기능 90 ≥ 85 「끝난다」 · `verify_onboarding_walk` 13/13 진행률 100 · 운영자 콘솔 P-01~12 AC 통과 · 시드 테넌트 2(DSM+FWS 동시 설치 1 · FWS 단독 1) 온보딩 리허설 완료 · 게이트 18 초록 · 파마다 커밋 셋 · §7 보고서 · `docs/SCAN.md`. **누른 뒤를 본 것만 초록**이다.

## 2. 배경·판단 요약

1. **왜 이 작업인가** — RC-1은 DSM 사용자 6종의 「끝난다」를 닫는다. 그러나 ① 재난안전과 공무원은 지침이 요구하는 별지 1호·재난문자·통제 4시각·영상 제공 대장 없이는 감사와 상급 보고를 GuardianX 밖에서 한다 ② 안양·의왕 같은 산 인접 지자체는 같은 카메라로 산불도 봐야 하고 2026.2 산림재난방지법 3단계 체계로 가을 조심기간(11.1)을 맞는다 ③ 두 번째 앱과 두 번째 테넌트가 생기는 순간 「플랫폼 운영자」가 없으면 에스비가 테넌트 화면으로 들어간다 — 채널 신뢰의 끝이다.
2. **이미 내린 설계 결정(재검토하지 않는다)** — 소유 축 4층·앱 개별 여섯(설계서 §1) · FWS는 P+R 아키타입 인스턴스이며 K1 「조치 중」 하위 상태 12 + 병행 축 2(대피·지휘) · 플랫폼 능력 8은 F 차선(플랫폼 팀)이 만들고 앱 차선은 인터페이스만 쓴다 · 재난문자·대피 명령은 제품이 발송·명령하지 않는다(초안·승인·기록까지) · 운영자 콘솔은 별도 도메인·별도 셸 · 라우트는 `features/<app>/routes.ts`에서만 · `api.py`는 WO-01에서 차선 모듈로 이미 분할됨 · 신규 테이블은 앱당 3 이하 + 지침 보강 5.
3. **버린 대안** — 산불을 DSM 사건 유형 하나로 넣기(단계·대피·지휘 축을 담을 수 없다) · 산림청 시스템 화면 재현(내보내기까지) · 운영자 기능을 테넌트 U5 화면에 슈퍼유저 플래그로(격리 붕괴) · 드론 수동 조종만(잔불 순회 자동이 값).

## 3. 수용기준 — AC 12 (각각 검증 방법)

| # | 수용기준 (Given–When–Then) | 검증 방법 |
| --- | --- | --- |
| AC-1 | Given 두 앱 설치 테넌트 When `gx-apps/fws`가 `kernels/**`·`common/**`·`gx-apps/dsm/**`를 import Then 빌드 실패 · 앱 테이블 접두·`TenantModel`·`purpose_code` 없으면 실패 | `verify_app_boundary`(신설) exit 1 시험 3 · exit 0 |
| AC-2 | Given 산 인접 카메라 1대 When DSM 화재 사건 생성 Then FWS가 같은 프레임 재추론 → 산불 후보 사건 1 · DSM 사건에 참조 ID · 반대로 `fws.fire.confirmed` → DSM 큐 시스템 카드 + 상황보고 초안 | 이벤트 버스 시험 5(PLT-03) · 걷기 |
| AC-3 | Given 플랫폼 능력 8 When 각 능력 계약 시험 Then PTZ 프리셋 호출 200 · 열화상 채널 스트림 1 · 주야 모델 전환 로그 · CBS 초안 90/157 검사 · WMS 레이어 1 · 이동체 위치 1 · 드론 임무 템플릿 3 · GPS 트랙·NFC·오프라인 큐 1 · K1 하위 상태 전이 · 시계 카운트다운 | `test_capability_*.py` 8 · 릴리스 트레인 등재 |
| AC-4 | Given U4 계정 When 심각 사건 확정 Then 별지 1호 제1보 초안 자동(13항목) · 「지체 없이」 타이머 · 승인(U2) → 발송 기록 · HWPX/DOCX · NDMS 내보내기 | `click_completes` DSM-U4-01·02 · 항목 대조 13/13 |
| AC-5 | Given U4 When 재난문자 초안 158자 Then 저장 불가 · 157자 저장 · 승인권자 결재 요청 · 발송 시각 입력 → 기록 · 21~06시 안전안내 경고 | `click_completes` DSM-U4-03 · 시험 글자 수 3 |
| AC-6 | Given 수위 관측값이 통제 기준 도달 When 도달 → U2 결정 → U3 실행 → 해제 Then 4시각 전부 감사 · 현황판 「도달 후 미결정 N분」 | `click_completes` DSM-U2-04·U3-02·U4-04 |
| AC-7 | Given F3 계정 · 훈련 모드 When AI 연기 후보 → 확인 요청 1클릭 → F1(390px) 「소각·오인」 회신 Then 종결 · K6 사유 · 10분 시계 · 반대 경로 「산불 맞음」 → 사건 `initial` · 신고 시각 = 30분 시계 시작 · 진화대 알림 | `walk_scenarios` F-1 · `click_completes` FWS-F1-06·F3-04~06 |
| AC-8 | Given `initial` 사건 When F3 입력 면적 12ha·풍속 4m/s·시설 없음 Then 「확산 1단계」 제안 · F4 확정 → 배지·감사 · 100ha/11m/s → 「확산 2단계 · 지휘 시·도지사」 제안 · 이양 시각·사유 기록 · 매시간 상황보고 초안 · 산림청 항목 내보내기 1 | `click_completes` FWS-F3-09·F4-02·F3-13 · 규칙 시험 별표 3 전수 |
| AC-9 | Given 확산예측 마을별 도달 예상 When 4h50m Then 「즉시 대피」 후보 · 초안(CBS 157자·방송·푸시) ≤ 10초 · F4 승인 → 기록 · **발송 버튼 없음** · 이행 % · 일몰 시각 표시 | `click_completes` FWS-F3-11·12·F4-05 · 정적 검사(발송 라우트 0) |
| AC-10 | Given 헬기 활동 중 플래그 When F5 정찰 임무 이륙 Then 차단 + 사유 · 해제 후 이륙 → 열점 3 → 지도 반영 · 잔불 순회 예약 1 | `click_completes` FWS-F5-01·02·04·06 |
| AC-11 | Given 운영자(2차) When 테넌트 생성 → 앱 2 설치 → 시드 → 카나리 배포 → 되돌리기 → 인시던트 자동(카메라 군집 두절) → 종결 → 청구서 초안 Then 각 단계 재조회 변화 · 테넌트 데이터 승인 없는 열람 0 · SLA 시계 | 운영자 콘솔 걷기 O-1 · `verify_ops_isolation`(신설) |
| AC-12 | Given 역할 13종 시드 계정 When 온보딩 카드 전부 수행 Then 진행률 13/13 100 · 5상태 캡처(신규 화면 32장 · 1440/390) · 우리말 아닌 글자 0 · 기밀 0 · 콘솔 0 · 신규 라우트 전수 테넌트 선언·관문·성능 예산 | `verify_onboarding_walk` 13 · `verify_ui_copy` · `verify_ui_secrets` · `verify_route_inventory` · `verify_perf_budget` |

## 4. 작업 범위 — 차선 7과 파일 소유권

### 4.1 차선

| 차선 | 모델 | 맡는 것 | 쓰기 면(파 5 첫 30분 선등록) |
| --- | --- | --- | --- |
| **조율자** | 영실(Opus) | 공용 등록부 · `routes.ts` 병합 · `ga_readiness.yaml` 등재(DSM 지침·FWS·PLT·OPS-C) · `onboarding_48.md` FWS·U0 표 신설 · `authn_paths.md`(F1~F6·U0 행) · 병합 · 커밋 셋 · 보험 패치 · 시드 테넌트 2 | — |
| **F 플랫폼** | Opus | PLT-01~04(`verify_app_boundary` · `app_code` 마이그레이션 · 이벤트 버스 5 · 앱 레일·홈 띠 슬롯·큐 병합) · **플랫폼 능력 8**(PLT-05~12 · 인터페이스 먼저 → 구현) · PLT-13 · K1 하위 상태·병행 축 · 대응 시계 설정화 · `k_event_contract` 버전 | `event_contract` · `capability.*` · `k1.substate` |
| **DSM-지침** | Sonnet | DSM-U1-01~06 · U2-01~05 · U3-01~04 · U4-01~09 · U5-01~05 · U6-01~03 · 화면 S-11b·11c·23·24·25·04′ | `situation-reports` · `cbs-drafts` · `controls` · `agency-notify` · `situation-meetings` · `shifts` · `privacy 제3자 제공` · `audit/export` |
| **FWS-감시** | Sonnet | FWS-F1-01~15 · F3-01~08·16~20 · U5-01~05 · 화면 FW-01·02·03·09·10 · FM1·FM2 · 오탐 필터 모델 바인딩 · 확인 요청·회신·신고 접수 | `fws/patrol/*` · `fws/verifications` · `fws/reports(신고)` · `fws/incidents(create)` · `fws/settings/*` · `fws/coverage-gaps` |
| **FWS-대응** | Sonnet | FWS-F2-01~15 · F3-09~15 · F4-01~15 · F5-01~10 · F6-01~10 · 화면 FW-04~08 · FM3·FM4 · 시계 8 · 단계 규칙(별표 3) · 대피 초안 · 매시간 보고 · 산림청 내보내기 · 드론 임무·차단 | `fws/missions` · `fws/incidents/{id}/*`(stage·spread·command-post·aircraft·agency·meetings·lines·mopup·ember) · `fws/evacuations` · `fws/drone/*` · `fws/investigations` · `fws/export` |
| **OPS 콘솔** | Sonnet | OPS-C-01~05 · P-01~P-12 · `ops.` 셸·도메인 · 1차/2차 권한 · SLA 시계 · 인시던트 자동 · 온보딩 관제 집계 · 청구서 초안 · 지원 대행 동의 토큰 · `verify_ops_isolation` | `ops/tenants` · `ops/apps` · `ops/releases` · `ops/models` · `ops/billing` · `ops/incidents` · `ops/onboarding` · `ops/secrets` · `ops/assist` |
| **V 검증자** | Opus | 차선 코드를 읽지 않는다 — 색만: 게이트 18 · `walk_scenarios` S1~S6 + F-1~F-4 + O-1 · 5상태 캡처 32장 · 3종 분류 · 온보딩 13 · 편리성(DSM 8 + FWS 4) | — |

### 4.2 소유 파일 — 한 파일은 한 차선

- **조율자**: `docs/agent/**` · `services/API.ts`(허용 목록) · `App.tsx`(라우트 등록 줄) · `ga_readiness.yaml` · `backend/apps/dsm/api.py`(include) · `backend/apps/fws/api.py`(include) · `backend/apps/ops/api.py`(include) · `docker-compose*.yml`(ops 서비스 1줄)
- **F 플랫폼**: `backend/kernels/**`(k1 substate · k2 channels cbs/broadcast · k3 슬롯 · k4 clock) · `backend/common/event_bus/**` · `backend/common/capabilities/**` · `backend/stream_monitors/`(PTZ·열화상 · **미들웨어·어댑터 한 겹만, §0.4 파일 무수정**) · `gx-link/{cbs_draft,broadcast,drone_missions}/**` · `frontend/src/features/shell/**`(앱 레일·홈 띠 슬롯·큐 병합) · `frontend/src/features/map/layers/**` · `frontend/src/features/mobile/core/**`(GPS·NFC·오프라인 큐) · `scripts/verify_app_boundary.py` · `apps/*/migrations/00xx_app_code_*.py`
- **DSM-지침**: `frontend/src/features/dsm/pages/{SituationReport,DailyReport,CbsDraft,Controls,Logbook}.tsx` · `EventDetail.tsx`(행동 카드·통보·상황판단 카드부) · `backend/apps/dsm/{situation_report,cbs_draft,controls,agency_notify,logbook,shifts,audit_export}.py` · `apps/dsm/api_law.py` · `templates/report/{form1,daily,logbook}/` · `seeds/playbooks.yaml`(유형별 행동 카드)
- **FWS-감시**: `frontend/src/features/fws/{routes.ts,pages/{Dashboard,CameraGrid,VerifyQueue,Stats,Settings}.tsx,copy.ts}` · `features/mobile/fws/{Patrol,Verify}.tsx` · `backend/apps/fws/{__init__,models_patrol,patrol,verifications,intake,settings,stats}.py` · `apps/fws/api_watch.py` · `gx-apps/fws/{manifest,archetype,screens,metering}.yaml` · `seeds/{ai_models,menus,terms}.yaml`
- **FWS-대응**: `features/fws/pages/{Command,Resources,Evacuations,Drone,Reports}.tsx` · `features/mobile/fws/{Mission,Evac}.tsx` · `backend/apps/fws/{models_incident,incidents,stage_rules,missions,resources,evacuations,spread,drone,reports,export,investigations}.py` · `apps/fws/api_respond.py` · `gx-apps/fws/{events.yaml,seeds/{grade_rules,playbooks}.yaml,templates/report/**}`
- **OPS 콘솔**: `frontend/src/ops/**`(별도 엔트리) · `backend/apps/ops/**` · `scripts/verify_ops_isolation.py` · `nginx/ops.conf`
- **V**: `docs/agent/evidence/WO-GX-20260915-02/**` · `scripts/walk_scenarios.py`(F-1~F-4 · O-1 추가만)

**금지**: `.env*` 실제 값 · `secrets/**` · §0.4 금지구역(dj-core · `backend/delivery/` · `stream_monitors` 원파일 — 미들웨어·어댑터 한 겹만) · 시험 고치기로 초록 · 라우트·데이터 삭제 · 계약 값 변경(`severity`·`response_state`는 그대로 · FWS 하위 상태는 **별도 필드**) · 무계정 링크 · 새 인증 경로 · 재난문자·대피 **발송·명령 라우트 생성 금지** · 드론 이륙은 차단 규칙 없이 열지 않는다 · 앱 차선이 `kernels/**` 수정 금지(F 차선에 능력 요청 한 줄).

**비범위**: 산림청 시스템 대체 · 헬기 지휘 · 확산예측 자체 모델 · 광역 통합 상황판 · 산사태·병해충 · 위험구역 그리기 · VLM · 카카오 알림톡(P2) · 운영자 콘솔 P&L 자동 산출(표만).

## 5. 기술 지시 (GC-100 전제 · 차이만)

| 항목 | 지시 |
| --- | --- |
| 재사용 | K1~K6 · 대응 시계 · 큐 카드 · 전이 버튼(`allowed_next`) · 오탐 사유 · QA-12 · 훈련 모드 · 인계 · 온보딩 진행률 · `incident_report.py` · `privacy_request.py` · CAP 웹훅 · `createObjectURL` · `ops_monitor` 11신호 · `click_completes` 술어 4 — **새로 만들지 말 것** |
| 능력 8 | 파 5 턴 9에 **인터페이스(추상 클래스·라우트 시그니처·시험 골격)** 먼저 → 앱 차선은 인터페이스에 코딩 → 파 6~7에 구현. 인터페이스 변경은 조율자 승인 · 앱 차선이 능력 구현을 대신 짓지 않는다 |
| 사건 모델 | FWS 사건 = K1 사건 + `fws_incident`(하위 상태 · 단계 · 지휘 · 면적·풍속·시설 · 시계 8) 1:1 · 대피 축 `fws_evacuation` · 지휘 축은 `fws_incident.command` 이력 · 전이 규칙은 `stage_rules.py` 한 곳(별표 3 값은 `grade_rules.yaml`) |
| 두 앱 한 카메라 | `streammonitoraimodel.app_code` · 사건은 앱마다 · 참조 ID만 · 조회는 이벤트 버스 페이로드로 |
| 지침 서식 | 별지 1호 13항목·일일보고·관제일지·산불 상황보고·진화완료·산림청 항목 = K4 서식 파일 · 항목 대조표를 `templates/report/<name>/fields.yaml`로 두고 시험이 읽는다(손으로 적지 않는다) |
| 재난문자·대피 | `cbs_draft`·`evacuation`에 **send/notify 라우트 없음** · 상태 = 초안 → 승인 → 「발송 시각 입력(사람)」 · 글자 수·야간 검사는 서버 |
| 운영자 콘솔 | 별도 도메인 `ops.` · 별도 JWT 오디언스 · 테넌트 데이터 접근은 「요청·승인」 또는 동의 토큰 경유만 · 전건 감사 · 시험 `verify_ops_isolation`: 운영자 토큰으로 테넌트 라우트 전수 → 401/403 |
| 모바일 | 390×844 · F1·F2 버튼 ≤ 3 · 오프라인 큐(서비스워커 + IndexedDB) · 산지 3G에서 FM2 ≤ 3초 |
| 드론 | `gx_dji` `BaseDroneConnector` 10메서드 위에 임무 템플릿 3 · 비행 제한 규칙은 커넥터 앞 미들웨어(헬기 플래그 · 고도) · 시험 mock_server |
| 성능 | 신규 라우트 p95 ≤ 800ms · 집계는 야간 배치 + 60초 캐시 · 시계·맥박·건강 보드는 캐시 금지(P-19) |
| 언어 | 새 문구는 `GX-COPY_v1.md` §5 → `copy.ts` · 산불 용어 사전 `gx-apps/fws/seeds/terms.yaml` · 운영자 콘솔도 우리말 · 기밀 0 |
| 기본값 | 닫힌 쪽 · 실측 가능한 쪽 · 되돌릴 수 있는 쪽 · 반경 좁은 쪽 · 앱의 자격으로 · 운영 모양 서버에서 · 누른 뒤를 본 것만 초록 · 여섯이 같은 모양이면 뿌리 하나를 먼저 |

## 6. 실행 지도 — 5파 × 2턴(2시간) · 동시 6

한 턴 = 조율자 20분(등록·기동·역할 계정 13 로그인 확인) → 동시 6 착수 → 80분 → 병합 F → DSM-지침 → FWS-감시 → FWS-대응 → OPS, 각 뒤 V → 세 수 → 커밋 셋 → 보고. 못 닫은 절은 다음 턴으로 넘기고 지도는 안 바꾼다.

### 파 5 — 플랫폼 경계 · 능력 인터페이스 · DSM 지침 Ⅰ (2026-09-28~30)

| 차선 | 턴 9 | 턴 10 | 첫 증거 |
| --- | --- | --- | --- |
| 조율자 | RC-1 태그 확인 · `apps/fws`·`apps/ops` 골격 · 쓰기 면 선등록(격리 시험 빨강 상태) · 시드 테넌트 2 · 역할 계정 13(시드 · `data_source=seed`) | `ga_readiness.yaml` 절 등재(PLT·DSM-U·FWS·OPS-C) · `onboarding_48.md` FWS·U0 표 · 커밋 셋 | 계정 13/13 로그인 · 등재 N |
| F 플랫폼 | `verify_app_boundary` · `app_code` 마이그레이션 · K1 하위 상태·병행 축 · 시계 설정화 · **능력 8 인터페이스 + 시험 골격** | 이벤트 버스 5(계약 등록·발행·구독) · 앱 레일·홈 띠 슬롯·큐 병합 · 능력 ①②(PTZ·열화상 어댑터) 구현 | 게이트 exit 1→0 · 버스 시험 5 · 인터페이스 8 |
| DSM-지침 | `situation_report.py`(별지 1호 · 채번 · 타이머) · S-11b · 행동 카드 `playbooks.yaml` · S-04′ 카드부 | `controls.py` 4시각 · S-24 · 임계값 도달 시스템 사건 · 112/119 통보 기록 · 상황판단 카드 | 제1보 초안 자동 · 4시각 |
| FWS-감시 | `models_patrol` · `manifest/archetype/screens.yaml` · `terms.yaml` · `routes.ts` · FW-10 설정(조심기간·초소·마을·대피소·오탐 필터) | `patrol.py`(체크인·트랙·계도) · FM1 · `intake.py`(신고 접수 5항목) | 설정 저장 · 체크인 1 |
| FWS-대응 | `models_incident`(하위 상태·시계 8) · `stage_rules.py` + 별표 3 시험 전수 · `grade_rules.yaml` | `incidents.py`(create·stage·command-post·aircraft·agency) · FW-04 골격(지도·시계·단계) | 규칙 시험 초록 · FW-04 캡처 |
| OPS 콘솔 | `ops/` 셸·도메인·JWT 오디언스 · `verify_ops_isolation` · P-01 건강 보드(테넌트 × 11신호) | P-02 테넌트 발급·앱 설치(registry) · P-06 인시던트(자동 생성·SLA 시계) | 격리 게이트 초록 · 보드 행 = 테넌트 |
| V | 게이트 16 + 신설 2 · 3종 분류 | 5상태 캡처 F·DSM-지침 · 세 수 | 색만 |

### 파 6 — DSM 지침 Ⅱ · FWS 감시 왕복 · 능력 구현 (2026-10-01~02)

| 차선 | 턴 11 | 턴 12 | 첫 증거 |
| --- | --- | --- | --- |
| F 플랫폼 | 능력 ③④(주야 모델·앱 태그 · CBS 초안·방송 어댑터) · ⑤(WMS·이동체 레이어) | 능력 ⑥⑦⑧(드론 임무 템플릿·비행 제한 · GPS·NFC·오프라인 큐 · 시계 카운트다운) · PLT-13 | 능력 시험 8/8 |
| DSM-지침 | `cbs_draft.py`(글자 수·야간·승인·발송 기록) · S-23 · S-11c 일일보고 배치 · 위기경보·비상 단계 접수 입력 | `logbook.py`·S-25(관제일지·제3자 제공 대장) · `audit_export.py` ZIP · 접근권한·접속기록 · 연계 설정·임계값 소스 · 교대 CSV · 역할별 M2 문안·통제 실행 회신 | 158자 저장 불가 · 대장 100% · ZIP |
| FWS-감시 | `verifications.py`(확인 요청·회신·10분 시계·대상 자동 제안) · FW-03 큐 · FM2 회신 · 오탐 필터 바인딩 | FW-01 상황판(띠 6수) · FW-02 격자(PTZ·열화상 · 능력 ①② 사용) · `stats.py` · FW-09 · 오프라인 큐·사각 신고·근무 종료 인계 | 확인 왕복 1 · 띠 6수 |
| FWS-대응 | `missions.py`·`resources.py` · FW-05 배치판 · FM3 임무(출동·도착·보고·지원) · 30분 시계 | `spread.py`(확산예측 등록·마을별 도달) · `evacuations.py`(8h/5h · 초안 3종 · 승인 · **발송 라우트 없음**) · FW-06 | 임무 도달 · 대피 초안 ≤ 10초 |
| OPS 콘솔 | P-09 온보딩 관제(13 역할 집계) · P-03 릴리스(카나리→전체·되돌리기) | P-07 게이트 보드 · P-08 플랫폼 감사 · P-12 지원 대행(동의 토큰·30분) | 되돌리기 시험 1 · 대행 감사 |
| V | F-1 걷기(탐지→확인, 390) · DSM-지침 5상태 | O-1 걷기 초반 · 세 수 | 색만 |

### 파 7 — FWS 대응·대피·드론 · 운영자 Ⅰ 마감 (2026-10-06~08)

| 차선 | 턴 13 | 턴 14 | 첫 증거 |
| --- | --- | --- | --- |
| F 플랫폼 | 이벤트 버스 시나리오 5 실걷기(DSM↔FWS) · 큐 병합 정렬 · 성능 예산 실측 | 회귀·릴리스 트레인 등재 · 능력 문서 8 | AC-2 · 예산 초록 |
| DSM-지침 | U6 연계(스마트시티 CAP 프로파일 · NDMS 내보내기 API · 실종 요청) · 지역안전지수 분류 | 빨강 닫기 · 지침 32 재측 | DSM 32 「끝난다」 |
| FWS-감시 | 훈련 시나리오(산불) · 온보딩 카드 F1·F3 · `verify_onboarding_walk` 배선 | 빨강 닫기 · 실카메라 연기 프레임 1 실측 | 카드 자동 완료 |
| FWS-대응 | FW-04 완성(지휘 이양·통합지휘본부·헬기·협조·회의·야간 전환·우선순위) · F2 주불·잔불·뒷불·철수 · `drone.py`·FW-07(임무·열점·순회·**차단**) · FM4 대피 안내 | `reports.py`(매시간·진화완료·사후 1쪽) · `export.py`(산림청 항목 `fields.yaml`) · `investigations.py` · FW-08 | 이양 기록 · 차단 시험 · 내보내기 1 |
| OPS 콘솔 | P-04 모델 레지스트리(그림자 배포·전환·롤백) · P-05 계량·청구서 초안 | P-10 키·자격 회전 runbook 연동 · P-11 카탈로그·능력 요청 · 온보딩 카드 U0 | 청구서 1 · 회전 4/4 |
| V | F-2·F-3 걷기(초기대응·확산·대피) · FWS 5상태 | F-4 걷기(잔불·드론·보고) · O-1 걷기 | 색만 |

### 파 8 — 통합 · 온보딩 리허설 준비 (2026-10-13~15)

| 차선 | 턴 15 | 턴 16 | 첫 증거 |
| --- | --- | --- | --- |
| 조율자 | 시드 테넌트 2에 두 앱 실걷기 · `onboarding_48` FWS 표 셋째 술어 첫 재측 | 부속서·명세서 §1 표 v1.1 열 [실측] 덮기(DSM 32 · FWS 90) | 재측 N/N |
| F·DSM·FWS 차선 | 빨강 3종 분류 → 제품 결함만 되돌림 · 캡처 재촬영(역할 계정 13) | 편리성 계측(DSM 8 + FWS 4) · 문구 사전 v1.2 | 회색 0 |
| OPS 콘솔 | OF-1 테넌트 온보딩 절차를 콘솔로 1회 완주(시드 테넌트) | OF-2 인시던트 1회(카메라 군집 두절 → 종결 보고서) | 완주 기록 |
| V | 게이트 18 전수 · 5상태 캡처 색인 32장 | `walk_scenarios` 11편(S1~6 · F1~4 · O1) 초록 | 색만 |

### 파 9 — 온보딩 리허설(역할 13) · RC-2 (2026-10-20~22)

| 차선 | 턴 17 | 턴 18 | 첫 증거 |
| --- | --- | --- | --- |
| 조율자 | 고객 온보딩 리허설 D-14~D+3(FWS) · D-7~D+3(DSM) 시드 테넌트로 · 운영자 P-09에서 관제 | RC-2 커밋 · 대표 결정 ⑥⑦ 반영분 교체 · 스테이징 걷기 | 진행률 13/13 |
| 전 차선 | 리허설 빨강 닫기 | 산불 훈련 1회(FF-8) 왕복 · 종료 보고서 | 보고서 1 |
| V | `verify_onboarding_walk` 13 · 편리성 12지표 표 | 최종 게이트 18 · 세 수 | 색만 |

## 7. 테스트·검증 지시

| 항목 | 지시 |
| --- | --- |
| 실행 | `pytest`(단위 ≥ 1,283 + 신규 AC마다 ≥ 1 · 별표 3 규칙 전수 · 능력 8 · 버스 5 · 격리) · `npm run build` exit 0(테넌트·ops 두 번들) · `deploy.sh` exit 0 ×2 · 게이트 18: WO-01의 16 + `verify_app_boundary` + `verify_ops_isolation` |
| 순서 | 능력 인터페이스 → 시험 골격 → 앱 코딩 → 능력 구현 → 통합 · 새 라우트는 태어날 때 ISO-03·SEC-04·계약 도달 통과 · 시험은 대상을 잰다(QA-05) |
| UI | 신규·보강 화면 32장(DSM 6 · FWS 14 · OPS 12) 5상태 캡처(역할 계정 · `data_source` · 1440/390) → `docs/review/WO-GX-20260915-02/<화면코드>/` |
| 걷기 | `walk_scenarios` 11편 — S1~S6(WO-01) + **F-1 탐지→확인(390) · F-2 초기대응 30분 · F-3 확산·대피 · F-4 잔불·드론·보고 · O-1 운영자 발급→설치→배포→인시던트→청구** · 클릭·경과·콘솔 JSON |
| 계량 | 편리성 DSM 8 + FWS 4(확인 요청 1클릭 · 회신 ≤ 10분 · 대피 초안 ≤ 10초 · 상황보고 수작업 0) → `evidence/WO-…/convenience.json` |
| 게이트 계정 | 매 턴 첫 일: 역할 계정 13 로그인(DSM 6 · FWS 6 · U0 1) · 회전 뒤 `.env.gates` 이름만 갱신 |

## 8. 보고 형식 — 파마다 `docs/workorders/WO-GX-20260915-02_report_wave<N>.md`

첫 표 8줄(산출기 출력 — 없으면 V 회색) → G1~G5 → 앱별 세 수(DSM · FWS) → 차선별 「절 N 중 닫힘 N · 넘김 N(사유)」 → `click_completes` DSM 48 + 지침 32 + FWS 90 · 3종 분류 → 능력 8 상태 → 온보딩 13 진행률 → 편리성 12(잰 것만) → 신규 라우트 도달 N/N → V 빨강 → **가정 목록** → 세종 오류 N · 영실 오판 N · 위임 이의 N → 기계 시각 · 소요. 짧게.

## 9. 진행 규칙 · 대표 결정 · 위임

- 질문은 불가역 작업에만 · 모호하면 §5 기본값 + 가정 목록 · 지시서와 코드 현실 충돌 시 중단·보고 · 커밋은 파마다 셋(`feat(v11r2-<차선>)` · `feat(화면)` · `test/docs`) · 막는 게이트 이름이 첫 줄 · 사유 없는 커밋 보류는 없다.
- 삭제·되돌리기·운영계 외부 행위·`.env` 실제 값·**외부 발송(재난문자·대피·산림청 전송)** 은 대표. 그 밖의 선택은 세종 판정으로 집행.

| # | 대표 결정 (PRD §10) | 기한 | 결정 전 차선 행동 | 결정 후 |
| --- | --- | --- | --- | --- |
| ①~⑤ | WO-01과 동일(채널·스테이징·재생성 창·SMTP·HWPX/GPU) | 09-19~26 | WO-01 대안 유지 | 교체 1~2턴 |
| **⑥** | 산림청 시스템 연계 조건(입력 규격 · 위험예보·확산예측 API · 산림재난 앱 푸시) | 10-10 | FWS-대응: 항목 `fields.yaml` + CSV/JSON 내보내기 · 수동 입력·업로드 이중 경로 | 어댑터 1턴 |
| **⑦** | 산불 1호 고객·자산 범위 · 에스비 1차 운영 범위 | 10-05 | 시드 테넌트로 리허설 · 권한 기본값 설계서 §7 | 실테넌트 발급 |

## 10. Escalation

| 조건 | 조치 |
| --- | --- |
| 같은 AC 2회 실패(Sonnet 차선) | 중단 → 로그 첨부 → 세종 판정으로 해당 AC만 Opus |
| 앱 차선이 커널·능력 수정이 필요하다고 판단 | 구현 금지 · F 차선에 「능력 요청 한 줄」 · 조율자가 인터페이스 변경 승인 |
| 아키텍처 변경(인증·테넌시·이벤트 계약 버전) | 변경안·영향·대안 2 보고 → 세종·대표 |
| 운영자 콘솔이 테넌트 데이터에 닿는 경로 발견 | 즉시 빨강 · 격리 게이트 재실행 · 해당 라우트 닫기 전 병합 금지 |
| 두 차선이 같은 게이트를 빨갛게 | 나중 것을 되돌린다 · 소유권 재배정 |
| 기대식 오류 vs 제품 결함 | P-132 3종 분류 · 정본 없음은 회색 유지 |

## 11. 스캔 팩 연동 · 불변

파 종료 = §8 보고서 + `docs/SCAN.md` 재생성 + 캡처 색인 + 게이트 출력. 실행은 `/gaion-wo WO-GX-20260915-02`. **불변**: WO-01 §12 전부 + 한 파일은 한 차선 + 온보딩 카드의 완료는 서버 기록이 닫는다 + 5배는 전부 초록일 때만 + **앱은 커널을 만지지 않는다 — 능력 요청 한 줄로** + **제품은 재난문자를 보내지 않고 대피를 명령하지 않는다 — 초안·승인·기록까지** + **운영자는 테넌트 화면에 들어가지 않는다** + **헬기가 뜨면 드론은 뜨지 않는다**.

## 12. Code 첫 프롬프트 (고정 문구)

```
docs/workorders/WO-GX-20260915-02.md 를 읽고 그대로 수행하라.
차선은 §4.2 소유 파일 밖을 만지지 말고, 앱 차선은 kernels/** 를 수정하지 말며 필요하면 F 차선에 능력 요청 한 줄을 보내라.
AC에 없는 것은 하지 말고, 모호하면 §5 기본값으로 정하고 가정 목록에 적어라.
매 턴 첫 일은 역할 계정 13 로그인 확인이다. 재난문자·대피·산림청 전송 라우트는 만들지 않는다.
파가 끝나면 §8 보고서와 스캔 팩을 내라. 누른 뒤를 본 것만 초록이다.
```

## 13. 대표께

이 지시서는 RC-1 뒤 5파 10턴으로 세 가지를 한 번에 닫습니다 — 재난안전과 공무원이 지침대로 보고·문자·통제 기록을 GuardianX 안에서 끝내는 것, 같은 플랫폼 위에 산불감시 앱이 가을 조심기간 전에 서는 것, 그리고 에스비와 가이온이 테넌트 화면에 들어가지 않고 운영하는 콘솔입니다. 앱 차선이 커널을 만지지 못하게 게이트로 막았고, 산불 앱이 요구하는 능력 여덟은 플랫폼 팀이 만들어 세 번째 앱이 공짜로 얻게 했습니다. 승인이 필요한 것은 이 지시서와 결정 ⑥(산림청 연계 조건 · 10-10) ⑦(산불 1호 고객 · 10-05)입니다.

## 14. 개정 이력

| 버전 | 일자 | 변경 | 작성 |
| --- | --- | --- | --- |
| v1.0 | 2026-09-15 | 최초 발행 — 차선 7(플랫폼·DSM-지침·FWS-감시·FWS-대응·OPS·V) · 5파 10턴 · AC 12 · 게이트 18(신설 2) · 대표 결정 ⑥⑦ | 세종(CPO) |
