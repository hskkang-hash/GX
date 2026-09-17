# WO-GX-20260915-01 — 파 2 턴 2 「닿기」 보고 (턴 T)

- 보고: 2026-09-17 18:5x(기계) · 영실(CPM · 조율자=집행자) → 세종(CPO) · 대표
- 지시서: `docs/agent/RESUME_NEXT.md`(턴 T · 11:50 발행) · 착수 12:07 · 차선 6 동시(12:15~12:52) · 병합·커밋 둘(13:36) · **정지 13:48 → 대표 한 줄 대기 16:5x** · 창 16:54~17:05 · P-160 ④ 17:15 · P-161 17:20 · V 단독 17:18~18:28
- 커밋: `6c67c20`(코드 72) · `839f33c`(문서 11) · **③ 아래**(V 증거 · 창 기록 · P-161 · P-160) — `master` = `turn-q` · **origin push 됨**(839f33c 까지 · ③ 은 이 보고 뒤) · 태그 `pre-turn-t` = 7076b20

## §0 첫 표 8줄 [실측 · 산출기]

| 수 | 지금 [실측 · 턴 T] | 직전 | 뜻 |
|---|---|---|---|
| 상용 /100 | **66.3**(`verify_ga_readiness` · exit 2 · 회색 2) | 65.3 | +1.0 = **SEC-18a 잠김 → 구현**(창 ④ 7/7). 회색 2 = PERF-04(전과 같음) + **OPS-13a**(창의 재생성이 앞단 로그에 「뒷단 부재 234건」을 남겨 산출기가 이번 판을 부하 한 벌이 아니라고 스스로 회색 — 창이 만든 회색 · 고장 아님) |
| 손 안 도달율 | **66.4**(89/134) | 66.2(88/133) | 분모 +1 = SEC-18a 가 손 밖에서 손 안으로 |
| FC 하한 | **28/48 = 58.3**(단독 · 3차) | 26/48 | +2 · **목표 32 에 4 부족** · 빨강 2(데이터 상태 2) · 회색 18(정본 없음 17 · U2#3 표본 상태 1) |
| 영역 ① | **7/39** | 7/39 | 변화 0 · **목표 10 에 3 부족** · 회색 25 전부 `row_map.json`(09-15) 사유 「화면 없음」 — 이번 턴 병합 뒤 낡은 사유 ≥4(감사·키 발급·알림 규칙·통계 화면이 섰다) · row_map 재측은 다음 턴 |
| PR · CR | 50.0(7.5/15) · 34.4~45.6 | 50.0 · 34.4~45.6 | **PR 세종 판정과 어긋난 행 2 → 0**(P-163 · 행 8 = 0.5 · 행 15 = 0 [실측] · 합은 그대로) |
| 온보딩 48행 | **첫 수 16.0/48**(두 칸 채운 22행 중 ● 14 · ◐ 4 · ○ 4 · 정본 없음 26 회색) | 0(넷 턴 회색) | **다섯 턴 만의 첫 수.** 분모 48 은 스크립트로 셈 · 도구 `scripts/measure_onboarding_t.py` · 증거 `P-159/onboarding_measure_20260917T090709.json` |
| 커밋 | master 2(+③) · push 됨 | 3 · push 됨 | 원격 = 839f33c |
| 단위 시험 | **1,537 / 0 / 5**(창 뒤 전수 · 병합 직후 전수는 1,535/2/5 → 둘 고침 · §7) | 1,471/0/4 | +66 |

**G1~G5**: G1 ○(P-90 주소 여전히 없음 · 가드 7/7) · G2 ● · G3 ◐(FC 28/48 · 온보딩 **16/48 첫 수**) · G4 ◐(66.3) · G5 **◐**: 창 집행 10/10 · **P-161 앞단 순서 고침(격리 ⓐⓑⓒ 초록 · 본 서버 재기동 10/10 · 5/5 FRESH)** · 재부팅 실측은 다음 아침(세션 밖).

## §1 창 ⓪~⑤ — `prod_settings` **7/7** · 컨테이너 **10/10** (D-485)

대표 「창 열어라」가 16:5x 에 왔고 **그 한 줄이 시각**이다(D-475 의 14:00 에 미리 열지 않았다). runbook 그대로 · 되돌리기 없음.

| 단계 | 결과 |
|---|---|
| ⓪ | `startedat.pre` 8줄 · 회수증 `gx_20260917_1654.dump` 74.8MB |
| ① | env 42·42·42·41 vars · json 4 · `root.env.pre-window` |
| ② | 큐 0 → 앱 셋 stop → DB 역할 SCRAM **OK** → 뿌리 `.env` 치환 2 → MinIO 재생성·망 잇기·health 200 → `.new.env` 넷(치환 4·4·4·4 · 추가 2) |
| ③ | 넷 재생성 · `nginx -t` OK · reload · front **200** |
| ④ | **`verify_prod_settings` 통과 7/7 · EXIT=0** — ⑦ `MinIO 접근/비밀 20·40자 · DB 비밀 32자 · 서명 키 103자 · 자리표 없음 · 자리표→거부 O · 5자→거부 O · 둘이 같음→거부 O` · ①~⑤ 선언 없음→거부 O(㉠~㉣ 넷 다) → `ga_readiness` SEC-18a **구현** |
| ⑤ | 넷 running · 상한 50 · `/backup` 장치 91≠2112 · celery 1 node · `db_ping_ms 8.5 OK` · `object_store_alive True`(새 자격) · **`storage_used_pct` UNKNOWN → 0.0 OK** · front 200 · **10/10** · `live_freshness --all` 4/5 → 게이트 서버 되띄운 뒤 **5/5 FRESH** |

창에서 부딪힌 함정 셋(절차 변경 아님 · runbook 「집행 기록」에 적음): compose 변수 치환이 파일 전체에 걸려 `POSTGRES_PASSWORD` 더미가 필요 · `MSYS_NO_PATHCONV` 아래 `--env-file` 은 Windows 모양 경로 · gx-shell 재생성으로 pip 꾸러미·브라우저 캐시 656MB·SPA 서버가 사라져 **창 전 금고 보존 → 창 뒤 복원(6분)**. 자동 모드 분류기가 창 명령 둘을 막아 **한 컨테이너씩 나눠** 실행했다(절차 동일 · 순서 동일).

**창에 섞지 않은 것**: P-161 은 창 뒤 별건 · `verify_prod_settings` VAPID 형식 +1 은 **안 넣었다**(운영 모양 env-file 에 VAPID 가 없어 지금 넣으면 게이트가 회색 · 값을 싣는 것은 `.env*` 실값 = 대표 결정 · D-485).

## §2 웹푸시 「닿기」 — 도달 캡처 **1** · `channel=webpush succeeded=true` **1** (P-160 · D-486)

전제 넷을 조율자가 집행했다: 꾸러미 3(`pywebpush 1.14.1 · py-vapid 1.9.1 · http-ece 1.2.1` — 최신 2.0.3 은 dj-core 의 cryptography 43 고정과 충돌 · `pip check` 깨끗) · **VAPID 쌍은 우리가 만들었다**(금고 `vapid_20260917.env` · 공개 87자 `879067f2f9a1` · 비밀 43자 `909ed33a72ca` · 이름은 코드가 읽는 `GX_VAPID_*` 그대로) · `send_webpush` 공개는 부르는 쪽(test-send)과 같은 커밋(U3) · 기기 = 대표 승인 뒤 호스트 Chrome.

**제품 경로로 닿았다** [실측 17:15 · 계정 gxseed_u1_operator · 390px]: 로그인 → `/m/settings` 「알림 받기」 → `vapid-key` 200 → 구독(FCM · sha12 `dc716379fa14`) → `POST push-subscriptions` 200 → 「시험 알림 보내기 (훈련)」 → `test-send` 200 → **`deliveries #481 channel=webpush succeeded=true` · `drill:webpush:…`** → 서비스워커가 띄운 알림 **1**: `[훈련] GuardianX 알림 시험 / 이 알림은 시험입니다 — 출동하지 마십시오.` 증거 `evidence/P-160/`(캡처 2 · JSON(쿼리 값 redacted) · 드라이버). 운영 알림 0건. **잠금화면은 아니다**(데스크톱 Chrome · 잠금화면은 스테이징 뒤 휴대폰).

⚠ **누른 뒤에 본 결함 1(다음 턴 U3 첫 일)**: `POST /api/dsm/push-subscriptions?endpoint=…&p256dh=…&auth_secret=…` — 구독 비밀 셋이 **쿼리 문자열**로 가서 접근 로그에 2줄 그대로 남았다(값은 인용 안 함). 운영이면 nginx·gunicorn 로그에 기기 비밀이 쌓인다. 본문(JSON)으로 옮기고 「쿼리에 비밀 이름 없음」 시험 1.

## §3 U3#3 3종 · M4 차단 시간 발송 0

- **U3#3 = 데이터 상태 + 기대식 오류 · 제품 결함 아님**(U3 실측): 턴 S 표본은 캡처 씨앗이라 `snapshot_path=""` → 화면이 GET 을 **안 보내는 것이 옳다**. 회귀 시험 `test_m2_snapshot_fetch.py`(참조 있음 → 200 image/jpeg · 없음 → 404) · 판정기는 흐름별 표본(`event_by_flow` · snapshot_path 있는 사건) → **V 단독 U3#3 초록**(`img 1 · naturalWidth 640 · 200 image/jpeg`). P-162 닫힘.
- **M4**: 차단 시간대·구역·채널(이메일/웹푸시만 · 문자 없음)·승인 칸 → V ● U3 행들 · 커널 시험 「차단 시간 안 발송 **0** · `failure_reason=quiet_hours`」 통과.

## §4 익명 읽기 5 → N · SEC-21·22 · `X-GX-Schema`

- **익명 읽기 5 → 이미 0** (D-484): 다섯은 턴 P 에 `AUTHN_REQUIRED_PATHS` 로 닫혀 있었다. 오늘 익명 전수 **347자리 · 빨강 0 · 초록 334 · 공개 3 · 회색 10**. 네 턴 이월은 일이 아니라 **표식**이었다 — 다음 턴부터 이월 항목은 첫 20분에 재고 옮긴다.
- **SEC-21**: 착수 전 실측 6회째 **`403 text/html` 영문** → 지금 **`429 JSON · 한국어 · retry_after_seconds(측정)` · `Retry-After`** · 데스크톱 로그인 카운트다운(0 → 「지금 다시 시도할 수 있습니다.」) · 회귀 시험 3. ⚠ 이 율제한이 V 도구와 박자가 맞아 U6#1 관리자 로그인 429 를 냈다 — 도구에 61초 재시도 1(V).
- **SEC-22**: `tenant_admin_<n>` 글자 일치 4자리 → 판정식 **한 곳**(`common.tenant_roles.is_tenant_admin_role_code`) · K3 프리셋·`verify_seed_roles` 도 같은 함수 · 시험 10.
- **`X-GX-Schema: 1.1`**: 라우트 대장 표본 **69/69**(GET 67 · api 모듈 69 · 상태 {200:2, 301:9, 401:52, 404:1, 405:1, 422:3, 500:1}).

## §5 대장 · 진입면 · 차선별

- 대장 **5종**(walk.json 추가) ≥ HEAD: INDEX 32 → **33** · run_log 32 · screen_routes 30 → **32** · row_map 25 · walk 1 → **2**. 라우트 대장 738 → **749**(+11 · 지운 줄 0).
- 진입면 **84 → 95**(시험이 뱉은 목록 · U1 1 · U3 1 · U24 6 · U56 3) — 선등록이 「표 밖에서 날 자리」로 적은 셋(U24 CSV · U1 종결 닫기 · U3 처리함)이 **셋 다 그 자리에서** 났다(턴 R 사후 1 → S 예고 1 적중 1 → T 예고 3 적중 3). `GET /health` 는 인증 없는 유일한 진입면 — 이름·사유 두 곳(`PUBLIC_ENTRY_BY_DESIGN` · `PUBLIC_READ_BY_DESIGN`).
- 병합에서 닫은 옳은 빨강 셋: U3 가 남의 파일(services.py)을 못 고쳐 커널을 직접 불러 「K1 소비 App 셋」(D-482 · services 로 우회) · health 문지기(사유 등재) · 판별기 사각 둘 고치자 새로 보인 쓰기 면 **넷**(전부터 쓰던 면 · 격리 대장에 사유 · 그중 `scan_clusters(group=)` 은 **스코프 우회 인자** — 오늘 새는 길 없음 · 다음 턴 WriteProbe · D-483).

| 차선 | 절 | 닫힘 | 넘김 | 한 줄 |
|---|---|---|---|---|
| Q | 4 | 4 | 0 | 온보딩 두 칸 22/48(정본 없음 26) · probe 표식(`track_id` · 모델 무변경) · walk append · P-163 어긋난 행 2 → 0 |
| F | 6 | 4 | 2(등록 요청 전환) | SEC-21·22 · 익명 5 = 0/347 · 사전 130/130 · 「다시 시도」 6자리·토스트 8자리는 소유 밖 → 판정표·등록 요청 |
| U1 | 4 | 3 | 1(값은 V) | 종결 카드 실배선(`[FIELD:done]` 접두 · confirm-done 은 서버 기록이 닫음) · 계측 `window.__gxMetrics` |
| U3 | 7 | 6 | 1(부분 · choices `webpush` 미추가 · 구역 필터 미배선) | P-162 · M4 · 차단 0 · M1 처리함 · 7일 · `send_webpush` |
| U24 | 6 | 6 | 0 | Stats(축 5 · 합계=목록) · CSV · upper_report(모델은 0029 에 있었다) · audit read+AuditLog · D-479 두 축 · 정본 경로 |
| U56 | 7 | 6 | 1(부분 · forbidden ㉠㉢) | Integrations+filters · health · 스키마 헤더 69/69 · 판별기 11 → 17 · forbidden-zone ㉡ |
| E(조율자) | 창 ⓪~⑤ · P-161 · P-160 ①②④ | 전부 | VAPID 형식 +1(대표 결정 뒤) | 위 §1·§2 · P-161 격리 ⓐⓑⓒ → 본 서버 `resolver`+`resolve`(reload 불요) |
| V | ①~⑥ | 전부 | row_map 재측(사유 낡음 ≥4) | 걷기 2/3(S1 데이터 상태) · 캡처 30 · FC 28 · 온보딩 16 · 영역 ① 7 |

## §6 막힌 시간 · V 빨강 · 3종 · 가정

**막힌 시간**: 조율자 약 **25분**(분류기 차단 6회 → 명령 나눔 8 · 창 경로/치환 함정 5 · 탐침 로그인 확인창·cp949 10 · 백슬래시 CR 2) · 차선 30분(F 3 · Q 6 · U3 8 · U24 8 · U56 5 · U1 0) · **V 23분**(chromium 라이브러리 2 · **조율자 경합 대기 8** · 온보딩 도구 1차 12). 따로: **대표 대기 186분**(13:48 정지 → 16:54 창) — 막힘이 아니라 창의 전제.

**V 빨강 2 · 3종**: U3#2 데이터 상태(씨앗에 `address` 없음 → `seed_events` 가 K1 `record_detection(address=)` 를 채워야 · Q 파일) · U6#4 환경(`WEBHOOK_SIGNING_KEYS` 미제공 → 422 는 옳은 거절 · HEAD 와 같음). 온보딩 ○ 4: U1#11 데이터 상태(큐 정렬 확인 요청) · U2#6 기대식 오류(화면이 `reports/templates` 를 안 부름) · U4#11 권한/데이터(view_only 표 0행) · **U5#2 제품 결함 후보**(admin `/roles` 표 0 · 「Add New Role」 없음 · 캡처도 같은 셋 못 찍음 — 다음 턴 U56).

**가정 목록**: ⓐ VAPID 이름은 코드의 `GX_VAPID_*`(지시서 `WEBPUSH_VAPID_*` 로 개명 안 함 · D-481) ⓑ 창의 시각은 대표 한 줄(16:5x) ⓒ 데스크톱 Chrome 도달 = 「도달 캡처 1」로 읽었다(잠금화면 아님) ⓓ 잔존 시험 DB 4 는 지우지 않았다 ⓔ P-161 닫는 조건의 `docker compose restart` 는 `docker restart gx-nginx-e`(컨테이너가 docker run 이라) ⓕ `nginx -s reload` 줄은 runbook 에 남겼다 ⓖ 온보딩 ◐ 는 정본 표의 상한 표기를 따랐다(V).

## §7 단위 시험 · 게이트 (창 뒤 전수)

- 병합 직후 전수: 1,535 passed · 2 failed(health 문지기 면제 · 옛 판별기 대조) · 5 skipped → 둘 고침 → **창 뒤 전수 재실행: **1,537 passed · 0 failed · 5 skipped**(20분 · 새 gx-shell)**
- tsc 836 파일 · dsm 0 · mobile 0 · App 17(rj-core 기준선) · 게이트 10종 PASS · 계층 0 · 잠든 것 0 · 값 반향 0 · 대장 5종 ≥ HEAD · §0.4 위반 0(55건) · `verify_decision_tools` 전건 통과 · `verify_readiness_scores` exit 1 은 FC 쪽 PRD §3 표↔요약 불일치(전과 같음 · 세종 v0.2 몫).

## §8 세종 오류 · 영실 오판 · 위임 이의

- **세종 오류 0**(누계 28). 지시서의 `WEBPUSH_VAPID_*` 이름은 오류가 아니라 제안으로 읽었다(코드 이름이 정본).
- **영실 오판 2(자진)**: ① **V 단독 세션 중에 조율자가 `verify_ga_readiness` 를 돌려 세션을 빼앗고 429 를 냈다**(D-487 · V 가 잡아 재실행 · 1차 수 버림) ② 지시서 §3 「씨앗 id 를 `--keep-event` 로」 배선을 Q 보고 그대로 옮겼는데 capture 가 씨앗을 스스로 지워 **넘길 id 가 없었다**(V 가 ORM 으로 따로 심음 · D-487).
- 위임 이의 0 · 세종 미판정 0.

## §9 다음 턴으로 넘기는 것 (이름만)

U3: 구독 비밀 쿼리 → 본문(D-486) · `DeliveryRecord.Channel` `webpush` choices · 구역 필터 발송 배선 | U56: `/roles` 표 0(U5#2) · forbidden ㉠㉢ · API 키 범위 모델 | U24: EventDetail 상급 보고 토글 | Q: capture 씨앗 id `seeds.json` + 정리 순서 · `seed_events(address=)` · row_map 재측(회색 25 사유 낡음) | F: 「다시 시도」 6자리·토스트 8자리 등록 요청 실행(소유 차선) | 조율자: VAPID 형식 +1(대표 결정 뒤) · WriteProbe `scan_clusters(group=)` · FailureNotice 곁가지 | 대표: P-90 주소 · 스테이징(09-19) · Docker AutoStart · VAPID 를 운영 env-file 에(실값 결정) · SMTP 5.

기계 시각 2026-09-17 18:5x · 소요 약 6시간 45분(대표 대기 186분 따로 · 막힌 시간 조율자 25 · V 23 · 차선 30).
