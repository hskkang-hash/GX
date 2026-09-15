# WO-GX-20260915-01

GuardianX v1.1 멀티에이전트 초효율 기능구현 작업지시서 — 사용자축 차선 5 + 기반 1 + 검증자 1 · 4파 × 2턴

## 0. 헤더

| 항목 | 기입 |
| --- | --- |
| 지시서 번호 | WO-GX-20260915-01 (문서번호 GAION-GX-WO-2026-013) |
| 사업 / 리포 | GuardianX 재난안전 관제 v1.1 / `guardianx-source` · 기준 HEAD `6cf2c19` + 작업본 239파일(턴 P 커밋 셋 선행) · 차선 브랜치 `feat/v11-<차선>` |
| 발행 | 세종(CPO · Cowork) · 2026-09-15 · 대표 승인 **필수**(§9 결정 5) — 승인 전에는 파 1만 착수(결정 무관 절) |
| 수신 | 영실(CPM · Code 조율자) · 차선 에이전트 6 · 검증자 V |
| 실행 모델 | 조율자·기반 F·V: Opus · 사용자축 차선(U1·U3·U24·U56): Sonnet 기본 · §10 승격 조건 |
| 권한 모드 | 차선: acceptEdits(자기 소유 파일만) · 조율자: auto · 삭제·되돌리기·운영계·`.env` 실제 값: **대표** |
| 예산 상한 | 파당 차선 6 × 2턴 × 2시간 · 토큰 체감 상한: 차선 턴당 세션 1회 · 초과 시 중단·보고 |
| 관련 문서 | PRD GAION-GX-PRD-2026-011 §5·§7·§10 · 부속서 A GAION-GX-SPEC-2026-012 §1~§3 · `docs/agent/RESUME_NEXT.md`(턴 P) · `onboarding_48.md` · `GX-COPY_v1.md` · `ga_readiness.yaml`(D-346) · GC-600 · T-07 v0.91 |

## 1. 목표 (한 문장) + 완료 정의

**사용자 6종이 첫 근무일에 문서 0장으로 자기 일을 GuardianX 안에서 끝낸다** — 온보딩 48행 ≥ 90 · 120 Flow ≥ 85 · FC ≥ 85 · 편리성 8지표 ≥ 5배 · 상용 ≥ 95(손 안 100).

**DoD**: 부속서 A §1의 v1.1 열이 Code [실측]으로 덮였고(회색 0) · `verify_click_completes` 48/48 판정 · `verify_onboarding_walk` 6/6 진행률 100 · `walk_scenarios` S1~S6 초록(1440 + 390) · 게이트 16종 전부 초록 · 커밋은 파마다 셋(feat/화면/test-docs) · §7 보고서 파마다 1 · `docs/SCAN.md` 재생성. 「코드를 짰다」는 완료가 아니다 — **누른 뒤를 본 것만 초록**이다.

## 2. 배경·판단 요약

1. **왜 이 작업인가** — 대장 129절 중 106 구현·손 안 93.0%인데 「눌러서 끝나는가」로 재면 FC 22.9~72.9 · 온보딩 58~63 [실측 턴 P]. 계약 절은 섰고 사용자 여섯 중 넷이 하루를 못 끝낸다. 안양 검수(UX-05)·다음 계약(U4)·F-10 왕복(U3)이 전부 여기 걸린다.
2. **이미 내린 설계 결정 (재검토하지 않는다)** — 역할 홈 4종은 코드로 고정(P-131) · 응답 어댑터 한 곳(P-129) · 큐에서 판정+접수 한 트랜잭션 · U3는 반응형 웹 + 웹푸시(앱 없음) · 인수 화면은 숨기고 우리 층 화면 5장(§0.4 무수정) · 라우트는 차선별 `routes.ts`에서만 · 신규 테이블 7종 전부 `TenantModel` + `purpose_code` · 대표 결정 5는 대안과 동시 구현(PRD §10).
3. **버린 대안 (그 길로 가지 않는다)** — 네이티브 앱 · 인수 화면 개종 · 설정 주도 위젯 홈(v1.2) · PDF만(HWPX 대안 DOCX) · 온보딩 문서만.

## 3. 수용기준 — 파별 AC (각각 검증 방법)

| # | 수용기준 (Given–When–Then) | 검증 방법 |
| --- | --- | --- |
| AC-1 | Given 역할 계정 4(U1·U2·U4·U5) When 로그인 Then 첫 URL이 역할 홈 4/4이고 홈 띠의 수가 목록 수와 일치한다 | `walk_scenarios` 첫 URL 4/4 · `click_completes` U1#1·U2#1·U4#1·U5#14 |
| AC-2 | Given U1 큐 카드 When 키 1 Then `review`+`response` 호출 2 · 재조회 `verdict=confirmed`·`response_state=acknowledged` · 카드 상태 칸 「접수」 — 토스트 강제 비활성 상태에서도 | `click_completes` U1#11·#13 · 시험 `test_review_and_acknowledge.py` |
| AC-3 | Given U3(390px) M2 When 접수→도착→사진→「가 보니 아무것도 없음」 Then 각 단계 상태 칸 변화 · K6 행 1 · 종결 · 캡처 6장 | `walk_scenarios` S3 · `click_completes` U3 8행 |
| AC-4 | Given U2 When 재판정·요원별·오탐률→임계값 시험→저장 Then 등급 배지 변화 · 요원 ≥ 2행 · `thresholds` 재조회 변화 · 감사 3 | `click_completes` U2 8행 |
| AC-5 | Given U4 When 검색·통계·월간 자동본·HWPX(대안 DOCX)·감사 조회·열람청구 Then 사건 1건 ≤ 15초 · 합계 = 목록 수 · 파일 2 · 60초 도달 · 변경 메서드 403 전수 | `click_completes` U4 8행 · `verify_write_auth`(view_only) |
| AC-6 | Given U5 When 사람 6 추가·역할·비활성 · CSV 40 · 알림 받는 사람(심각 ≥ 1)·시험 발송 · 시스템 화면 · 재시작 요청 Then 각각 재조회 변화 · 비활성 401 · 주소 미입력 0 · 진행률 100 | `click_completes` U5 8행 · `verify_onboarding_walk` |
| AC-7 | Given U6 키 When health·필터 구독·상태 갱신·pulse·stats Then 200 · 대상 외 발송 0 · 스키마 버전 헤더 전 응답 · 익명 401 | 계약 라우트 도달 게이트 · `test_u6_contract.py` |
| AC-8 | 5상태 × 신규 화면 12장 캡처(역할 계정 · `data_source` 표기) · 한 화면 우리말 아닌 글자 0 · 기밀 0 · 콘솔 오류 0 | `verify_ui_copy` · `verify_ui_secrets` · `deploy.sh` · `docs/review/WO-GX-20260915-01/` |
| AC-9 | 신규 라우트 13종 전부 테넌트 선언 · 인증 관문 · 성능 예산 안 | `verify_route_inventory` · `verify_authn_paths` · `verify_perf_budget` |
| AC-10 | 온보딩 48행 셋째 술어 재측 ≥ 90 · 120행 표 v1.1 열 [실측] 회색 0 · 편리성 8지표 계측값 표 | `onboarding_48.md` 재측 절 · 부속서 A §1 갱신 · `walk_scenarios` 시간·클릭 출력 |

## 4. 작업 범위 — 차선 재편과 파일 소유권

### 4.1 차선 7 (조율자 1 + 기반 1 + 사용자축 4 + 검증자 1)

| 차선 | 모델 | 맡는 것 | 쓰기 면(파 1 첫 30분 선등록) |
| --- | --- | --- | --- |
| **조율자** | 영실(Opus) | 공용 등록부 · 병합 · 커밋 셋 · 보험 패치 · `ga_readiness.yaml` 등재 · `onboarding_48.md` · `authn_paths.md` · `decisions.yaml` | — |
| **F 기반** | Opus | 역할 홈 리다이렉트·홈 4장 껍데기 · 응답 어댑터(ADP-01) · 온보딩 진행률(UX-46) · SET-01 · SEC-20~22 잔여 · 게이트 신설 3 · 마이그레이션 7종 한 벌 | `onboarding/progress` · `me/notify-prefs`(스키마) |
| **U1** | Sonnet | UX-33 1클릭 · UX-23′ 격자 순회 · UX-34 인계 자동 초안 · UX-26 사진 · 사건 메모 · OPS-20 | `handover` · `events/{id}/note` · `review+response` 트랜잭션 |
| **U3 모바일** | Sonnet | UX-45 M2·M3 · UX-43-M4 · UX-48 · UX-49 · CH-03 웹푸시 · CH-01 문자 어댑터(결정 뒤 켬) | `field-photo` · `me/notify-prefs` · `me/notify-report` · `push-subscriptions` |
| **U24 팀장·공무원** | Sonnet | UX-35 · UX-36 · UX-37 · UX-47 · UX-38 · UX-39 · UX-40 · RPT-01(대안 DOCX) · UX-41 · LAW-07′ 배치 | `upper-report` · `thresholds/simulate` · `reports/{id}/send` · `report_run` |
| **U56 관리자·연계** | Sonnet | UX-42 · UX-42-me · UX-43 · UX-44 · OPS-21·22 · UX-01′ · API-01~04 · SEC-22 · S-21 | `people` · `notify-rules(+test)` · `system/restart-request` · `cameras/{id}/address` · `webhook filters` |
| **V 검증자** | Opus | 차선 코드를 읽지 않는다 — 색만 읽는다: 게이트 16 · `walk_scenarios` 6편 · 5상태 캡처 · 3종 분류 · 편리성 8지표 계측 | — |

**소유 파일 — 한 파일은 한 차선.** 이 목록 밖은 소유권이 없다. 겹치면 조율자가 갈라 준 뒤 띄운다.

- **조율자**: `docs/agent/**` · `services/API.ts`(메뉴 허용 목록만) · `App.tsx`(라우트 등록 줄만) · `ga_readiness.yaml` · `backend/apps/dsm/api.py`(공용부 · 차선 라우터 include)
- **F**: `frontend/src/features/dsm/home/**` · `features/dsm/adapter.ts` · `features/dsm/onboarding/**` · `backend/apps/dsm/onboarding.py` · `apps/dsm/migrations/00xx_v11_*.py` · `scripts/verify_onboarding_walk.py` · `scripts/verify_perf_budget.py` · `config/settings.py`(TIME_ZONE 한 줄)
- **U1**: `pages/FocusQueue.tsx` · `pages/CameraGrid.tsx` · `hooks/useFocusQueue.ts` · `hooks/useCameraGrid.ts` · `features/Handover/**` · `backend/apps/dsm/api_u1.py` · `apps/dsm/services.py::review_and_acknowledge` · `apps/dsm/handover.py` · `kernels/k1_event/notes.py`
- **U3**: `features/mobile/**` · `public/sw.js` · `backend/apps/dsm/api_u3.py` · `apps/dsm/field.py` · `apps/dsm/notify_prefs.py` · `kernels/k2_notify/channels.py`(webpush·sms 어댑터 추가만)
- **U24**: `pages/TeamStatus.tsx` · `CameraTuning.tsx` · `Stats.tsx` · `Reports.tsx` · `AuditLog.tsx` · `pages/EventList.tsx`(검색부) · `pages/EventDetail.tsx`(재판정·상급·보고서 버튼부) · `backend/apps/dsm/api_u24.py` · `apps/dsm/stats.py` · `monthly_report.py` · `hwpx_export.py` · `docx_export.py` · `audit.py::read`
- **U56**: `pages/People.tsx` · `Me.tsx` · `NotifySettings.tsx` · `SystemSettings.tsx` · `Integrations.tsx` · `CameraAddress.tsx` · `backend/apps/dsm/api_u56.py` · `apps/dsm/people.py` · `system.py` · `config/k3_roles.py`(8종 배선) · `kernels/k2_notify/services.py`(규칙 CRUD·test) · `webhook_outbox`(filters) · `docker-compose*.yml`(restart 정책 줄만)
- **V**: `docs/agent/evidence/WO-GX-20260915-01/**` · `scripts/walk_scenarios.py`(시나리오 추가만)

**금지**: `.env*` 실제 값(D-204) · `secrets/**` · §0.4 금지구역(dj-core · `backend/delivery/` 등 — 미들웨어 한 겹으로만) · `common/_base_manager` · 시험 고치기로 초록 만들기(D-327) · 라우트 삭제 · 데이터 삭제·되돌리기 · 계약 값(`severity`·`response_state`) 변경 · 무계정 링크 · 새 인증 경로 · 지시 없는 리팩터링.

**비범위**: 커널 재설계 · 드론·항공 자산 · 영상 추출(11조) · VLM(PERF-07) · 위험구역 그리기(v1.2) · 카메라 등록 요청 흐름(UX-50 · P2) · 당직 편성표.

### 4.2 공용 파일 규약 — 충돌은 라우팅 침묵으로 나타난다

`services/API.ts` · `App.tsx` · `api.py` 상단 공용부 · `routes.ts`는 **조율자만** 병합한다. 차선은 자기 `routes.<차선>.ts` 조각과 `api_<차선>.py` 라우터 모듈을 만들고 조율자에게 「등록 요청 한 줄」을 보낸다. `api.py`는 파 1 첫 30분에 조율자가 차선별 라우터 모듈로 쪼갠다(`api_u1.py` · `api_u3.py` · `api_u24.py` · `api_u56.py` · `api_base.py`) — 한 파일은 한 차선.

## 5. 기술 지시 (GC-100 전제 · 차이만)

| 항목 | 지시 |
| --- | --- |
| 재사용 | 큐 카드·대응 시계·전이 버튼(`allowed_next`)·오탐 사유·QA-12 `alarm_budget`·K6·K2 `resolve_recipients`·`ops_monitor` 11신호·`incident_report.py`·`privacy_request.py`·CAP 1.2 웹훅·`createObjectURL` 사진·`verify_ui_copy`·`click_completes` 술어 4 — **새로 만들지 말 것** |
| 트랜잭션 | `review_and_acknowledge`는 K1 안에서 한 트랜잭션 · 실패 시 둘 다 롤백 · 감사 1행(둘을 한 사건으로) |
| 데이터 | 신규 테이블 7(`dsm_handover` · `dsm_field_photo` · `dsm_notify_prefs` · `dsm_onboarding_progress` · `dsm_report_run` · `dsm_upper_report_flag` · `webhook_subscription.filters` 필드) — F 차선이 파 1에 마이그레이션 한 벌로 · 전부 `TenantModel` · `purpose_code` · ISO-03 선언 · 스키마 변경은 이 일곱뿐 |
| 멀티테넌트 | 새 라우트 13종 전부 테넌트 스코프 매니저 경유 · 시드는 `data_source=seed` |
| 언어 | 새 문구는 `GX-COPY_v1.md` §5에 먼저 넣고 `copy.ts`에 옮긴다 · 사전 v1.1 = 역할 홈·온보딩 카드·빈 상태 4문장 |
| 어댑터 | 프런트 응답 해석은 `features/dsm/adapter.ts::unwrap()` 한 곳 — 봉투 승격 전/후 모양 둘 다 · 성공 판정은 HTTP 상태 + `success` 둘 다(DA-03 §0-1) |
| 모바일 | 390×844 · 엄지 존 고정 버튼 ≤ 3 · 사진은 `createObjectURL` + 해제 · 3G에서 M2 ≤ 3초(사진 지연 로드) |
| 웹푸시 | VAPID 키는 `env:` 참조만 · 서비스워커 `public/sw.js` · 구독은 계정 귀속 · 훈련 모드에서 채널 `log` |
| HWPX | `hwpx_export.py`는 인터페이스만 고정(`render(report_run) -> bytes`) · 구현은 대표 결정 ⑤ 뒤 · 그 전에는 `docx_export.py`가 같은 인터페이스로 「HWP가 여는 DOCX」 |
| 성능 | 신규 라우트 p95 ≤ 800ms(집계 `stats`·`by-reviewer`·`false-positive`는 야간 배치 테이블 + 캐시 60초 · 상태·pulse는 캐시 금지 P-19) |
| 기본값 | 닫힌 쪽 · 실측 가능한 쪽 · 되돌릴 수 있는 쪽 · 반경 좁은 쪽 · 앱의 자격으로 · 운영 모양 서버에서 · 누른 뒤를 본 것만 초록 · 여섯이 같은 모양이면 뿌리 하나를 먼저 |

## 6. 실행 지도 — 4파 × 2턴(2시간) · 동시 5

한 턴 = 조율자 20분(등록·기동·계정 4/4 로그인 확인) → 동시 5 착수(착수 시각 기록) → 80분 → 병합 F→U1→U3→U24→U56, 각 뒤 V → 세 수 → 커밋 셋 → 보고. 못 닫은 절은 다음 턴으로 넘기고 지도는 안 바꾼다.

### 파 1 — 기반 + U1 (2026-09-16~17)

| 차선 | 턴 1 | 턴 2 | 첫 증거 |
| --- | --- | --- | --- |
| 조율자 | 턴 P 커밋 셋 완료 확인 · `api.py` 차선 모듈 분할 · 쓰기 면 13 선등록(격리 시험 전부 빨강 상태에서 띄움) · U2 계정 로그인 원인 ⓐⓑⓒ 닫기(P-130) | 병합 · `ga_readiness.yaml`에 v1.1 절 등재(산출기가 센다) · 커밋 셋 | 등록 13 · 로그인 4/4 · 커밋 해시 3 |
| F | 마이그레이션 7 · 역할 홈 리다이렉트 + 홈 4장 껍데기(띠·카드 자리) · `adapter.ts` + 대조표(P-129 여섯) · SET-01 격리 전/후 | UX-46 진행률(모델·라우트·카드 컴포넌트·자동 완료 훅) · `verify_onboarding_walk` · `verify_perf_budget` · `click_completes` 3종 분류 칸 | 첫 URL 4/4 · 여섯 → 0 · 진행률 라우트 200 |
| U1 | `review_and_acknowledge` 트랜잭션 + 시험 · 큐 카드 버튼 3 · 오탐 사유 3택 · 토스트 제거 | 격자 순회·N분할·검은 칸 · 인계 자동 초안(`/handover/draft`) + 본문 · 사건 메모 · 사진 실사건 1 | U1#11·#13 초록 · 격자 캡처 3 · 인계 본문 ≥ 4줄 |
| U3 | (파 1은 설계 확정만) M3 시트 설계 · 웹푸시 서비스워커 골격 · `notify_prefs` 스키마 F에 전달 | M2 사진 렌더·지도·전화 · `field-photo` 라우트 | M2 캡처 390 · img 1 |
| U24 | `stats.py` 집계(야간 배치 테이블) · `by-reviewer` · `false-positive` 라우트 + 시험 | `EventList` 검색 1칸·전체·기간 · `EventDetail` 재판정·상급 배지 | 라우트 3 도달 · 12.7초 검색 유지 |
| U56 | `people.py`(create-user 경유 · 비활성) · K3 8종 배선 · `system.py`(`ops_monitor` → 라우트) | `People.tsx` · `SystemSettings` 확장 · 재시작 정책 6/6 + compose | 생성 200 · 비활성 401 · 정책 6/6 |
| V | 게이트 14 + 신설 2 색 · 3종 분류 · U1 걷기 | 세 수 · 회색 목록 · 5상태 캡처 F·U1 | 색만 |

### 파 2 — U3 + U2 (2026-09-18~19)

| 차선 | 턴 3 | 턴 4 | 첫 증거 |
| --- | --- | --- | --- |
| F | 홈 4장 본문(띠 수 · 카드 · 인계 · 진행률) · UX-31′ 4문장 · 「다시 시도」 전수 | SEC-21·22 잔여 · 익명 읽기 5 → 401(P-133) · 사전 v1.1 등재 | 홈 수 = 목록 수 · 익명 자료 200 = 0 |
| U1 | UX-15 회귀 · 큐 「지원 요청」 배지 · 종결 확인 카드 | U1 8행 재측 지원 · 편리성 #1~#3 계측 | U1 8/8 |
| U3 | M3 시트(도착·사진·한 줄·오탐·지원·완료) · `field-reply` 확장 · 웹푸시 구독·발송 | M4(근무 외·구역·채널·미수신 신고) · M1 「처리함」 · 과거 사건 · 훈련 채널로 차단 실측 | S3 캡처 6 · 차단 시간 발송 0 |
| U24 | `TeamStatus` · `CameraTuning`(시뮬·저장·사유) · 재판정 버튼 | `Stats.tsx`(축 5 · CSV) · 상급 보고 체크 · 감사 `read` 라우트 | U2 8/8 · 합계 = 목록 |
| U56 | `NotifySettings`(규칙 CRUD · 심각 0 금지 · 시험 발송) · 채널 이메일/웹푸시 | `Me.tsx` · `Integrations.tsx`(키·구독) · webhook filters · `GET /health` · 스키마 버전 헤더 | 규칙 ≥ 1 · 시험 발송 1 · 헤더 전 응답 |
| V | S1·S3 걷기(1440 + 390) · 모바일 캡처 | S2 걷기 · U2·U3 5상태 | 색만 |

### 파 3 — U4 + U5·U6 (2026-09-22~23)

| 차선 | 턴 5 | 턴 6 | 첫 증거 |
| --- | --- | --- | --- |
| F | 온보딩 카드 40 자동 완료 훅 전수 배선 · `verify_onboarding_walk` 6/6 | 성능 예산 실측 · 회귀 감시 | 진행률 6/6 |
| U24 | `Reports.tsx`(서식 3 · 자동본 · 발송) · `monthly_report.py` 배치 · `docx_export.py` | `AuditLog.tsx`(필터·체인·CSV) · LAW-07′ 메뉴 배치 · HWPX(결정 시) | U4 8/8 · 자동본 1 · 파일 2 |
| U56 | `CameraAddress` 한 대 고치기 · 재시작 요청 라우트 · 백업 회수증 표시 · 저장 상한 선언 | API-03·04(키 범위 · pulse · stats) · 연계 명세 1장 · OpenAPI | U5 8/8 · U6 8/8 |
| U3 | CH-01 문자 어댑터(결정 시 켬 · 「1」 회신 파서) | 편리성 #5 계측 · 실카메라 스냅샷 1 | 도달 캡처 |
| U1 | 편리성 계측 보조 · 회귀 | — | — |
| V | S4·S5·S6 걷기 · U4·U5 5상태 | 게이트 16 전수 · 계약 라우트 도달 신규 13 | 색만 |

### 파 4 — 검수·온보딩 리허설·RC-1 (2026-09-24~25)

| 차선 | 턴 7 | 턴 8 | 첫 증거 |
| --- | --- | --- | --- |
| 조율자 | 온보딩 48행 셋째 술어 재측 · 부속서 A §1 v1.1 열 [실측] 덮기 · 120행 회색 0 | RC-1 커밋 · 대표 결정 반영분 교체(채널·HWPX·SMTP) · 스테이징 `walk_scenarios` | 48행 ≥ 90 · 세 수 |
| F | 빨강 3종 분류 → 제품 결함만 되돌림 | 재생성 창 runbook(P-134) 실행(창 열리면 30분) | 결함 0 |
| U1·U3·U24·U56 | 각 차선 빨강 닫기 · 캡처 재촬영(역할 계정) | 고객 온보딩 리허설(D-7~D+3 표를 시드 테넌트로 1회) | 리허설 진행률 6/6 |
| V | `walk_scenarios` 6편 · 편리성 8지표 표 · 콘솔 0 | 최종 게이트 16 · 5상태 × 27화면 캡처 색인 | 색만 |

## 7. 테스트·검증 지시

| 항목 | 지시 |
| --- | --- |
| 실행 | `pytest`(단위 ≥ 1,283 유지 + 신규 AC마다 ≥ 1) · `npm run build` exit 0 · `deploy.sh` exit 0 ×2 · 게이트 16: `live_freshness` · `prod_settings` · `route_inventory`(신선도 24h) · `authn_paths` · `write_auth` · `ui_copy` · `ui_secrets` · `error_body` · `feature_reach` · `contract_route_reach` · `ga_readiness` · `click_completes` · `onboarding_walk`(신설) · `perf_budget`(신설) · `walk_scenarios` · `front_line_502` |
| 순서 | 버그는 재현 시험 먼저 → 수정 · 새 라우트는 태어날 때 ISO-03·SEC-04·계약 도달 통과 · 시험은 캐시가 아니라 대상을 잰다(QA-05) |
| UI | 신규·보강 화면마다 5상태 캡처(역할 계정 · `data_source` 표기 · 1440/390) → `docs/review/WO-GX-20260915-01/<화면코드>/` · 판정 번호는 저장 경로가 아니다 |
| 계량 | `walk_scenarios`가 S1~S6마다 클릭 수·경과·콘솔 오류를 JSON으로 → 편리성 8지표 표(`evidence/WO-…/convenience.json`) |
| 게이트 계정 | 매 턴 첫 일: 역할 계정 4/4 로그인(회전 뒤 `.env.gates` 이름만 갱신 · 값은 저장소 밖) |

## 8. 보고 형식 — 파마다 `docs/workorders/WO-GX-20260915-01_report_wave<N>.md`

첫 표 8줄(산출기 출력 — 없으면 V 회색): 상용/100 · 손 안 · 온보딩 48 · FC 하한·상한 · PR · CR · 8영역 · 커밋 → G1~G5 한 줄씩 → 차선별 「절 N 중 닫힘 N · 넘김 N(사유)」 → `click_completes` N/48 + 3종 분류 수 → 120행 v1.1 열 갱신 수 → 편리성 8지표(잰 것만) → 신규 라우트 도달 N/13 → V 빨강 → **가정 목록**(지시서에 없어 스스로 정한 것 전부) → 세종 오류 N(누계 23+N) · 영실 오판 N · 위임 이의 N → 기계 시각 · 소요. 짧게 — 2시간 턴엔 보고도 짧다.

## 9. 진행 규칙 · 대표 결정 · 위임

- 질문은 불가역 작업(삭제·배포·외부 발송·스키마 변경 밖의 것)에만. 모호하면 §5 기본값으로 정하고 가정 목록에 적는다.
- 지시서와 코드 현실이 충돌하면(파일 없음·구조 상이) 중단·보고 — 임의 우회 금지.
- 커밋은 파마다 셋: ① `feat(v1.1-<차선>): …` ② `feat(화면): …` ③ `test/docs: …`. 메시지 `WO-GX-20260915-01: AC-n 요지`. 막는 게이트가 있으면 그 이름이 보고 첫 줄 — **사유 없는 커밋 보류는 없다.**
- 삭제·되돌리기·운영계 외부 행위·`.env` 실제 값은 대표. 그 밖의 선택은 세종 판정으로 집행(위임 규칙 · 이의는 보고 한 줄).

**대표 결정 5 (PRD §10) — 기한과 미결 시 차선 행동**

| # | 결정 | 기한 | 결정 전 차선이 하는 것 | 결정 후 |
| --- | --- | --- | --- | --- |
| ① | 알림 채널(문자/카톡/앱) | 09-19 | U3: 웹푸시로 왕복 완결 · 문자 어댑터 인터페이스만 | 어댑터 켬 + 「1」 회신 파서 1턴 |
| ② | 스테이징 1대(공개 URL) | 09-19 | V: 사내망 URL + 자체 서명으로 걷기 | 파 4에서 스테이징 걷기 |
| ③ | 재생성 창 1회 | 09-22 | F: runbook 1쪽 · vault 새 값 | 창 30분 · `prod_settings` 7/7 |
| ④ | SMTP · 수신 주소 | 09-19 | U56: mailpit + 시험 발송 · 초대 메일 골격 | 실수신 캡처 1 · OPS-10 닫힘 |
| ⑤ | HWPX · GPU | 09-26 | U24: DOCX 대안 · 인터페이스 고정 | HWPX 1턴 |

## 10. Escalation

| 조건 | 조치 |
| --- | --- |
| 같은 AC 2회 실패(Sonnet 차선) | 중단 → 실패 로그 첨부 → 세종 판정으로 해당 AC만 Opus 재시도 |
| 아키텍처 변경 필요 판단(커널·인증 경로·테넌시) | 구현 금지 · 변경안·영향·대안 2를 보고서로 → 세종·대표 |
| 보안·테넌트 격리·§0.4 경계 | 시작 전 명시 승인 확인 · 지시서에 없으면 하지 않는다 |
| 두 차선이 같은 게이트를 빨갛게 | 나중 것을 되돌린다 · 조율자가 파일 소유권 재배정 |
| 회색이 초록으로 둔갑할 위험(기대식 오류) | P-132 3종 분류 · 제품 결함만 빨강 · 정본 없음은 회색 유지 |

## 11. 스캔 팩 연동 (GC-600 §3 — 완료 조건)

파 종료 = §8 보고서 + `docs/SCAN.md` 재생성(`node scripts/scan.mjs`) + `docs/review/WO-…/` 캡처 색인 + `evidence/WO-…/` 게이트 출력. 세종은 코드 원본이 아니라 스캔 팩 5종(보고서 · diff --stat · 시험 로그 · 캡처 · SCAN.md)만으로 검증하고 차기 지시서를 쓴다. 실행은 `/gaion-wo WO-GX-20260915-01`.

## 12. 불변 제약 (전부 유지 + 이번 지시서 추가 셋)

여섯이 같은 모양이면 뿌리 하나를 먼저 · 기본값은 이전 고객의 것이다 · 게이트의 기대식은 정본 화면 문구에서 · 로그인 뒤 첫 화면은 역할 홈 · 사유 없는 커밋 보류는 없다 · 그려졌다 ≠ 동작한다 · 상태는 칸으로 · 읽기 전용은 쓰지 못한다 · 화면은 거짓말하지 않는다 · 한 화면에 우리말 아닌 글자 0 · 정본은 운영 모양 서버 · 게이트는 앱의 자격으로 · 역할 없는 계정은 아무것도 보지 않는다 · 자격의 기본값은 없다 · 빨강을 회색으로 바꾸지 않는다 · 「없다」도 실측 · 역할 있는 사람의 화면만 증거 · 분모는 손으로 적지 않는다 · 회수증 = 덤프 + 복원 · 운영계는 대표 한 마디 뒤 · 삭제·되돌리기는 대표 · **+ 한 파일은 한 차선 · + 온보딩 카드의 완료는 서버 기록이 닫는다(사람이 체크하지 않는다) · + 5배는 여덟이 전부 초록일 때만 말한다(회색은 초록이 아니다).**

## 13. Code 첫 프롬프트 (고정 문구)

```
docs/workorders/WO-GX-20260915-01.md 를 읽고 그대로 수행하라.
차선은 §4.1 소유 파일 밖을 만지지 말고, AC에 없는 것은 하지 말며, 모호하면 §5 기본값으로 정하고 가정 목록에 적어라.
매 턴 첫 일은 역할 계정 4/4 로그인 확인이다. 파가 끝나면 §8 보고서와 스캔 팩을 내라.
누른 뒤를 본 것만 초록이다.
```

## 14. 대표께

이 지시서는 코드로 닫을 수 있는 것 전부를 8턴(2시간 × 4파)에 넣었습니다. 차선을 영역이 아니라 **사람(U1·U3·U2/U4·U5/U6)** 으로 갈랐습니다 — 파일이 겹치지 않고, 한 차선이 닫으면 온보딩 표의 한 행이 통째로 초록이 되기 때문입니다. 대표 결정 다섯은 기한을 적었고, 결정이 늦어도 제품이 서도록 대안을 같은 차선이 함께 만듭니다 — 결정이 오면 1~2턴에 정본으로 바꿉니다. 승인이 필요한 것은 이 지시서 자체와 결정 다섯의 기한입니다.

## 15. 개정 이력

| 버전 | 일자 | 변경 | 작성 |
| --- | --- | --- | --- |
| v1.0 | 2026-09-15 | 최초 발행 — 사용자축 차선 재편 · 4파 8턴 · AC 10 · 게이트 16(신설 2) · 대표 결정 5 기한 | 세종(CPO) |
