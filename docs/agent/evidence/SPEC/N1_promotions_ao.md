# N1 승격 제안/소급 — 턴 AO (P-406 결정 제외 · P-407 옛 승격 40 소급 · 반쪽 잔여 셋)
(턴 AO · WO-GX-20260930-18 · 차선 N1)

**조율자가 대장(`docs/agent/evidence/D-346/ga_readiness.yaml`)에 적용한다 — 이
문서는 제안·보고만 한다.** 이 차선은 `ga_readiness.yaml` 을 손대지 않았다.

## 0. 일 셋 요약

① **P-406** — `scripts/verify_spec_title_parts.py` 에 두 규칙 추가: 결정 제외
(`excluded_by: P-###|D-###` + `excluded_why`)는 status 앞머리와 무관하게 닫힘 ·
대리 지표(`근사`·`대리`·`proxy` 앞머리)는 언제나 열린 행. `--self-test` 31건
통과(짝 표본 셋 포함).

② **P-407** — 게이트가 「옛 승격·표 없음」으로 세던 **39건**(WO 문서의 "40"과
실측이 다르다 — 아래 §2 참고) 전부에 `title_parts` 표를 소급했다. **채워 넣지
않았다** — 명세 제목 ↔ 실제 코드/시험을 대조해 닫힌 부분은 닫힘, 못 채운 부분은
정직하게 열어 뒀다. 결과: 옛 승격(표 없음) **0** · 표 있고 깨끗함(초록) **4** ·
표 있고 반쪽(빨강) **35**.

③ **반쪽 잔여 셋** — FWS-F6-07(산림청 앱 실제 푸시 행에 `excluded_by: P-392` →
닫힘) · DSM-U4-07(연간 통계 신설 → 닫힘) · DSM-U5-05(인계 메모 근무자 자동 연결
→ 그 행은 닫힘, 그러나 관제일지 부재로 절 전체는 여전히 반쪽).

## 1. P-406 — 게이트 규칙 (scripts/verify_spec_title_parts.py)

```python
EXCLUDED_BY_RE = re.compile(r"^(?:P|D)-\d{3}$")
PROXY_PREFIXES = ("근사", "대리", "proxy")

def _is_excluded_closed(row):
    by, why = row.get("excluded_by"), row.get("excluded_why")
    return (isinstance(by, str) and EXCLUDED_BY_RE.match(by.strip())
            and isinstance(why, str) and bool(why.strip()))

def _is_proxy(status):
    ...  # 근사/대리/proxy 앞머리(대소문자 무시)

# judge_title_parts 행 판정:
closed = _is_excluded_closed(row) or (_is_closed(status) and not _is_proxy(status))
```

`--self-test` 에 짝 셋을 추가했다: 번호 있는 결정 제외(`P-392`+사유) → 닫힘 ·
번호 없는 「없음」(`excluded_by` 없음) → 여전히 열림 · 대리 지표(`대리`/`근사`/
`proxy` 앞머리) → 열림. `CLOSED_PREFIXES`·`PROXY_PREFIXES` 겹침 없음도 자기시험이
확인한다. 31건 전부 통과.

## 2. P-407 — 소급 결과

게이트 실측(`python scripts/verify_spec_title_parts.py --list`, 2026-09-30):
영역 7 승격 **59건** 중 「옛 승격·표 없음」이던 것은 **39건**이었다(WO-18 §4 의
목록이 「40」이라 적었지만 실측은 39 — 이 문서는 실측을 정본으로 삼는다,
WO-18 §4 「판정기 출력 정본」). 소급 뒤:

| 구분 | 건수 |
|---|---|
| 옛 승격·표 없음(그레이) | **0**(전부 표를 얻었다) |
| 표 있고 깨끗함(빈 칸 0·열린 행 0) | **4** |
| 표 있고 반쪽(열린 행 ≥ 1 — 빨강) | **35** |

### 2-1. 완전히 닫힌 넷 (조율자가 그대로 초록으로 유지해도 되는 후보)

| id | 표 행 수 | 무엇을 대조했나(사람 확인 1줄, evidence json `retro` 에도 있음) |
|---|---|---|
| DSM-U3-04 | 4 | 상황실 번호·PS-LTE 그룹통화 저장/조회 + `MobileEventDetail.tsx` 758~777행의 실제 `tel:` 1탭 버튼까지 확인 — evidence의 `what` 은 저장 왕복만 쟀다 적었지만 프런트까지 이미 있었다 |
| FWS-F6-08 | 3 | 교통통제·입산통제 협조 기록 + 사건별 조회 — 완결조건(「기록」)이 연동을 요구하지 않아 3행 모두 닫힘. `mountain_entry_control` 은 `traffic_control` 과 코드 분기 없이 같은 경로임을 확인 |
| FWS-F2-14 | 3 | 장비 점검(둥짐펌프·진화차) — `equipment_type` 이 의도적 자유 텍스트(코드 주석 확인)라 한 번의 실측이 두 예시를 함께 덮는다. 완결조건(「점검 1」) 직접 실측 |
| FWS-F1-08 | 3 | 비상연락망 값·익명 차단·PatrolHome.tsx:138-143 실제 `tel:` 프런트 배선까지 확인 — 이 39건 중 유일하게 서버·화면 전부 실측됨 |

### 2-2. 반쪽(빨강) 35건 — 「내릴 절 후보」(조율자 판단 · 대장은 이 차선이 안 고친다)

아래는 각 id 의 **열린 행 요약**(전체 표는 `docs/agent/evidence/SPEC/<id>.json`
의 `title_parts`·`retro` 칸). 닫힌 부분이 더 많아도 **하나라도 열려 있으면
반쪽**이다(P-392·이 턴 규약).

**DSM**
- DSM-U2-03(회의 4칸 기록) — 화면 0 · 「결정→테넌트 상태축 변경」 완결조건 미구현(감사 줄만)
- DSM-U2-04(통제기준 도달) — 도달/결정 이원 감사는 닫힘, **팀장·U4 실제 알림 발송**·UI 없음
- DSM-U2-05(인계 합동 확인) — ack+감사는 닫힘, 08~09시 시간창 강제 없음·홈카드 UI 없음
- DSM-U3-03(현장사진→보고서 ⑨ 첨부) — 건수 자동 반영은 닫힘, 원본 사진 자체는 계약상 의도적 미첨부(법적 근거 있음)
- DSM-U4-06(경계 단계 접수) — 입력 4칸·감사·상태 read-back 닫힘, 상단바 띠·홈카드 UI 는 개발 당시부터 범위 밖 선언
- DSM-U5-02(접속기록·권한) — 조회·CSV·권한표는 닫힘, **보관기간 선언(730일)≠심긴값(365일) 불일치** · 「60초 이내」 성능 게이트 없음

**FWS-F1**(F1-08 만 닫힘, 나머지 9는 반쪽)
- F1-01 체크인 — 서버 GPS/NFC 는 닫힘, 화면이 좌표를 하드코딩(`navigator.geolocation` 미호출)
- F1-02 순찰 경로 — 트랙/체크포인트 카운트는 닫힘, 체크포인트 레지스트리 없음·프런트 호출 0건
- F1-03 산불경보 수신 — 응답 계약은 닫힘, `mountain_entry_banned` 영구 False(죽은 필드)·`fire_alert` 는 건기달력 **대리 지표**
- F1-05 확인요청 상세 — GET·좌표는 닫힘, 「거리」 필드 없음·F1 화면에서 호출 0건
- F1-06 확인회신 — 확정/오인은 닫힘, `cannot_access` 실측 0 · 스펙이 요구한 「사진 1」 첨부 파라미터 없음
- F1-10 안전경보 — 배달/수신확인은 닫힘, **풍향 급변 트리거 코드 자체가 없음**
- F1-11 내 순찰 이력 — 집계는 닫힘, 프런트 호출 0건(화면 미연결)
- F1-12 근무외 알림설정 — 저장/조회는 닫힘, **저장값을 실제로 읽어 차단하는 코드가 없다**(K2 는 DSM 전용 표를 읽는다 — 배선 안 됨)
- F1-13 오프라인 큐 — 체크인 재생은 닫힘, 트랙 큐잉은 죽은 코드·자동시험 0 · 명세의 "서비스워커" 대신 단순 online 이벤트(**대리**)

**FWS-F2**(F2-14 만 닫힘, 나머지 9는 반쪽)
- F2-01 대기상태 — 주/야간·위치는 닫힘, 자원배치판 표시는 F3 화면(범위 밖)
- F2-02 임무 수신 — 좌표·심각도는 닫힘, `access_route`·`wind_direction`·`muster_point`·`commander` 는 **영구 None**(K1 스키마에 칸 자체가 없음 — 구조적 한계)
- F2-03 이동·도착 회신 — 도착·GPS·30분 시계는 닫힘, 「이동중」 별도 상태 자체가 없음(도착만 실재)
- F2-05 지원요청 — 4종 요청은 닫힘, 지휘화면 배지는 DSM 화면(범위 밖)
- F2-07 안전경보 — 배달/수신확인은 닫힘, **풍향 급변·헬기 투하구역 이탈 경보 규칙이 `kernels/k2_notify` 어디에도 없다**(가장 중요한 결손)
- F2-11 철수·복귀 — 기록·순서·다중 크루는 닫힘, 복귀→자원배치판 해제 자동 연결 없음
- F2-12 임무이력·투입시간 — 목록·시간 합계는 닫힘, 명세가 부르는 CSV 내보내기 없음
- F2-13 훈련임무 배지 — 배지·0건 실발송은 닫힘, 실제 모의 임무에 태그돼 도착하는 경로가 없음(깃발만)
- F2-15 근무외 차단·담당구역 — 저장/조회는 닫힘, **F1-12 와 같은 결손** — 저장값이 실제 억제 로직에 안 읽힌다

**FWS-F5**
- F5-01 정찰임무 — 요청·상태전이는 닫힘, 발화 좌표가 응답에 안 실림·열화상 데이터 경로 자체 없음(드론 0대·설계상)
- F5-02 열점/화선 표시 — 좌표 제출·재조회는 닫힘, 열화상 프레임→좌표 추출·지도 렌더 없음
- F5-03 확인결과 — 회신·확정/오인·사진참조 필수화는 닫힘, 「사진」과 「열화상」 증빙 구분 필드가 하나뿐
- F5-08 비행기록 — 배터리·기체·재조회는 닫힘, **실제 DJI 등 커넥터 연동 0건**(전부 수동 입력)
- F5-10 비행시간 계량 — 합계/건수는 닫힘, 월 필터 미검증·S-20 커널 계량 미연계(**대리**: 드론 전용 로컬 카운터)·월 표 화면 없음

**FWS-F6**(F6-08 만 닫힘, 나머지 6은 반쪽)
- F6-01 KFS 내보내기 — JSON/CSV/1:1표/P-386 단계는 닫힘, 산불상황관제·산림재난정보 **두 상대 시스템** 각각의 실제 스키마 대조는 없음
- F6-02 웹훅 4종 — 카탈로그·CAP1.2 발송·200 수신은 닫힘, 제목이 괄호로 명시한 **종류별 필터**가 없음(K1 event_type 기준일 뿐)
- F6-03 위험지수 예보 — 수동입력·P-386 띠·재조회는 닫힘, 산림청 API 실시간 연동 없음·지자체 전체 통합 없음(본인 값만)
- F6-05 헬기요청 — 등록·좌표값·조회는 닫힘, 산림항공본부 실시간 연동 없음
- F6-06 소방연계 — 119 기록·DSM 카드 전달은 닫힘, 국가 재난안전통신망 자체 연동은 없음(제목 해석에 따라 논쟁 여지 있음)
- F6-10 관할이첩 — 국립공원/국유림 기록·조회는 닫힘, 상대 기관 시스템으로 실제 이관·수신확인은 없음

**소급 방법**: 절마다 ① `docs/agent/roadmap/기능명세_미포함표_20260925.md` +
명세 원문(`docs/design/DSM_재난안전관리App_명세서_v1.1_*.md` ·
`FWS_산불감시App_명세서_v1.0_*.md`)에서 제목·완결조건을 「부르는 것」 목록으로
쪼개고 ② 기존 evidence json(request/response/what) ③ 구현 서비스 파일(대개
머리말에 ★ 표로 미비를 스스로 적어 둠) ④ 시험 코드를 대조했다. 다섯 개
읽기전용 조사(각 그룹 DSM·F1·F2·F5·F6)를 병렬로 돌리고 이 차선이 전건 병합·
검산(빈 칸 0 확인)했다. 각 id 의 `retro` 칸에 사람 확인 1줄이 있다.

## 3. 반쪽 잔여 셋

### 3-1. FWS-F6-07 — 닫힘

`backend/tests/test_an_n1_f6_07_webpush.py::_merge_title_parts` 호출의 「산림청
스마트산림재난 앱 실제 푸시 발송」 행에 `excluded_by: "P-392"` + `excluded_why`
(세종 판정 · 산림청 앱은 연동 계약이 없는 제3자 앱)를 기계로 찍게 고쳤다 — 웹푸시
훈련 채널 행이 이 절의 실제 「앱 푸시 연계」다. 게이트(`verify_spec_title_parts.py`)
가 이제 이 행을 닫힘으로 센다(P-406 규칙 자기시험 표본이 정확히 이 사례를 본뜬다).

### 3-2. DSM-U4-07 「연간 통계」 — 닫힘

`video_access_ledger_service.annual_stats()` 신설(새 표 0 — 기존 감사 이력
`LOGGER_NAME` 을 연도로 걸러 요청·승인·제공 건수·월별 요청 건수를 낸다. 감사
모델에 저장 시각 칸이 없어 `create_request`/`approve_request`/`provide` 가 이미
문장에 적어 둔 `접수=`·`시각=` 스탬프를 되읽는다). 라우트
`GET /api/dsm/video-access-requests/annual-stats?year=`(`api_u4.py`, U4-07 절 안).
새 시험 `backend/tests/test_ao_n1_dsm_u4_07_annual_stats.py`(4건 — 이번 해
집계·다른 해 0·잘못된 연도 400·테넌트 격리) 전부 통과. `DSM-U4-07.json`
title_parts 의 「연간 통계(출력)」 행을 `있음(신규)` 로 갱신.

### 3-3. DSM-U5-05 「일지 근무자」 — 행 하나는 닫힘, 절 전체는 여전히 반쪽

`handover_service.build_draft()` 가 `shift_roster_service.current_workers()`
를 불러 그 날짜의 조별 근무자를 인계 초안 **본문 5번째 줄**과 `on_duty` 구조
칸에 싣는다(새 표 0 — `DsmHandover` 에 칸을 더하지 않았다, 텍스트에만 실린다).
「인계 메모 근무자 자동」 행은 닫혔다. 새 시험
`backend/tests/test_ao_n1_dsm_u5_05_handover_roster.py`(4건 — 근무표 있음/없음·
저장 왕복·테넌트 격리) 전부 통과.

**그러나** 관제일지(DSM-U1-04) 자체가 이 저장소 어디에도 없다 — 이 턴도
만들지 않았다(지시된 「새 표 0」과 일치). 그래서 「일지 근무자 자동」·완결조건
「일지 근무자 = 편성표」 두 행은 정직하게 **열린 채로 남긴다**. **DSM-U5-05 는
이 턴에도 반쪽이다** — 조율자에게: 인계 메모가 사실상의 일지 역할을 대신하는
것으로 완결조건을 재해석할지, 아니면 DSM-U1-04 를 별도 절로 남겨 둘지 판단
부탁드린다(N4 가 턴 AM 부터 반복해 온 같은 질문).

## 4. 게이트·시험 재현

```
python scripts/verify_spec_title_parts.py --self-test   # 31건 통과
python scripts/verify_spec_title_parts.py --list        # 옛 승격 0 · 반쪽(빨강) 35 · 깨끗함 4

python scripts/verify_spec_dsm_u4.py --self-test          # 0건 실패
python scripts/verify_spec_dsm_u4.py --no-run              # 닫은 열 4/4 · PASS

MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e DB_TEST_NAME=test_gx_lane_n1 -w /app gx-shell \
  python -m pytest tests/test_p356_u4_rest_spec_promotions.py \
    tests/test_ao_n1_dsm_u4_07_annual_stats.py \
    tests/test_ao_n1_dsm_u5_05_handover_roster.py \
    tests/test_an_n1_f6_07_webpush.py -q --create-db -p no:randomly
```

## 5. 조율자에게 넘길 줄

- `docs/agent/evidence/D-346/ga_readiness.yaml` — §2-2 의 **35건 반쪽 후보**를
  내릴지(closed_partial → half/open) 판단 부탁드린다. 이 차선은 대장을 고치지
  않았다.
- 새 `/api/dsm/` 라우트 `video-access-requests/annual-stats` —
  `backend/tests/test_f05_event_api.py::EVENT_ENTRY_SURFACE`(조율자 소유)에
  올려 주십시오.
- DSM-U5-05 완결조건 재해석 여부(§3-3) — N4(턴 AM)·N1(턴 AN·AO)이 세 번째로
  같은 질문을 남긴다.
- FWS-F2-07·F1-10 의 「풍향 급변」 경보 규칙 부재는 이 39건 중 가장 눈에 띄는
  결손이다(코드 어디에도 트리거가 없다) — 다음 배정 후보로 추천.
