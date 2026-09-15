# P-125 / UX-30 — 상황 보고서가 택배 운송장이었다 (before → after)

- 잰 사람: 차선 B (Backend/DB) · 턴 O · 2026-09-10
- **TARGET** = `http://localhost:8500` (`gx-nginx-e` → `gx-gunicorn-e` · 운영 *공정* 모양,
  `profile=dev` · `DEBUG=True`. 운영 보안 프로필로 도는 서버는 이 기계에 **없다**)
- **AS** = `gxprobe_s` (role=`user` · group=`ETRI-Group`) · 자격은 `.env.gates` 의
  `GX_PROBE_PASSWORD`, sha256 앞 12자 `b6ae237c2c7b`. ⚠ `gxseed_u4_official`·`gxseed_u2_manager` 로 재려 했으나
  **동시 접속 1개** 제약 때문에 다른 차선의 로그인에 두 번 밀렸다(`session_evicted`).
  같은 자격으로 잰 수만 이 문서에 남긴다.
- **SOURCE** = 이 저장소 작업본 (HEAD `6cf2c19` + 이 턴의 미커밋 변경) ·
  `gx-gunicorn-e` 를 변경 뒤 재기동하고 잰 수다.

---

## 1. before — 무엇이 나왔나

| 요청 | 상태 | 크기 | 쪽수 | md5 앞 12자 |
|---|---|---|---|---|
| `GET /api/dsm/reports/7.pdf` | 200 | 14,848 bytes | **3쪽** | `1f4cd5de7caf` |
| `GET /api/dsm/reports/7.pdf?event_id=4802` | 200 | 14,851 bytes | 3쪽 | `82ebee8f58c9` |

**본문에서 찾은 칸 이름** (PDF 스트림을 풀어 ToUnicode 로 되돌려 읽었다):

```
배송 완료 보고서 · Operation ID · Order Information · Order Code · Order ID ·
Created Date · Order Status · Sender Name · Sender Phone · Sender Address ·
Recipient Name · Recipient Phone · Recipient Address · Note ·
Pickup Location Terminal · Delivery Terminal · Delivery Operation Details ·
Current Status · Route Information · Route ID · Route Name ·
Financial Information · Subtotal · Delivery Fee · Tax Amount ·
Discount Amount · Total Amount · Additional Information · ETRI Receipt ID
```

그리고 **치환되지 않은 자리표시자 36개** — `{{ order__sender_name }}` ·
`{{ order__delivery_fee__value }}` · `{{ another_info__etri__receipt_id }}` …

`?event_id=4802` 를 붙인 종이의 **본문에 `4802` 라는 글자가 없다**(`"4802" in 본문 → False`),
자리표시자 수도 36개로 **같다**. 두 번을 같은 초에 부르면 md5 까지 같고, 몇 분 뒤에
부르면 3바이트(생성 시각) 만 다르다 — 즉 **사건 id 는 종이에 아무 영향이 없었다.**

### 왜 그랬나 — 원인 셋 (렌더러가 아니다)

1. `/api/dsm/reports/{template_id}.pdf` 의 경로 숫자는 **템플릿 id** 다 (사건 id 가 아니다).
   `backend/apps/dsm/api.py` `report_pdf`.
2. `report_template` 표의 **19행이 전부 택배 운송장**이다 — 사건 보고서 서식은 그 표에
   한 행도 없다. (7번은 `name='Template'`, group 4, 9,231자 · 실측)
3. K4 의 치환은 `{{ events }}`·`{{ actions }}`·`{{ captures }}`·`{{ since }}`·`{{ until }}`·
   `{{ sources_failed }}`·`{{ manual_fields }}` **일곱 이름만** 바꾼다
   (`backend/kernels/k4_report/services.py::_fill`). 운송장 서식에는 그 일곱이 **하나도
   없어서** 꽂을 자리가 없었다.

→ **「렌더러가 event 를 안 읽는다」가 아니라, 읽은 값을 꽂을 자리가 서식에 없었다.**
   고칠 자리는 렌더러가 아니라 **서식**이다.

---

## 2. after — 무엇이 나오나

**화면이 부를 주소 (프런트 차선에 넘기는 값):**

```
GET /api/dsm/events/{event_id}/report.pdf
Authorization: Bearer <access_token>
→ 200 application/pdf
  Content-Disposition: attachment; filename="guardianx-incident-{event_id}.pdf"
  Cache-Control: no-store, no-cache, must-revalidate, private
```

| 요청 | 상태 | 크기 | 쪽수 |
|---|---|---|---|
| `GET /api/dsm/events/4802/report.pdf` | 200 | 53,660 bytes | **1쪽** |
| `GET /api/dsm/events/4801/report.pdf` | 200 | 52,555 bytes | 1쪽 |
| `GET /api/dsm/events/4805/report.pdf` | 200 | 52,524 bytes | 1쪽 |
| `GET /api/dsm/events/999999/report.pdf` | **404** | — | — |
| `GET /api/dsm/events/4802/report.pdf` (토큰 없음) | **401** | — | — |

세 종이의 md5 가 **전부 다르다**(같은 순간 세 번 부른 값 · 저장한 두 파일의 앞 12자는 `e4f3c2ee59b6` · `f7f6dd36df81`) —
사건 id 가 종이를 바꾼다. 크기가 큰 것은 내용이 아니라 **한글 글꼴 임베딩**이다(1쪽).

**본문에서 찾은 칸 이름** (같은 방법으로 읽었다):

```
ETRI-Group · 사건 보고서 · 사건번호 · 발행 · 발행자
① 사건 개요   사건번호 · 발생 시각 · 등급 · 유형 · 카메라 · 설치 주소
② 대응 경과   발생 · 접수 · 조치 시작 · 종결 · 발생→접수 · 발생→조치 시작 ·
              발생→종결 · 현재 상태 · 종결 방식(자동 종결이면) · 재개 횟수(있으면)
③ 판정       판정 · 판정 시각 · 판정자 · 판정 사유
④ 조치 이력   채널 · 대상 · 발송 시각 · 결과
꼬리말        출처 문장 · 시각 고지
```

**택배 낱말 0개** — `order__` · `Sender` · `Recipient` · `Pickup Location` ·
`Delivery Fee` · `Tax Amount` · `ETRI Receipt` · `배송` · `택배` 전부 없다.
치환되지 않은 자리표시자 **0개**.

### 사건 4802 의 실제 본문 (그대로 옮김)

```
ETRI-Group  사 건 보 고 서
사건번호 4802 · 발행 2026-09-10 15:40:21 · 발행자 Probe SGX (gxprobe_s)
① 사건 개요  사건번호 4802 | 발생 시각 2026-09-03 20:02:31 |
             등급 심각 | 유형 화재 | 카메라 시드 카메라 (검수용) |
             설치 주소 경기도 안양시 만안구 안양천서로 100 (시드 카메라)
② 대응 경과  발생 2026-09-03 20:02:31 | 접수 기록 없음 | 조치 시작 기록 없음 |
             종결 2026-09-03 20:17:32 | 발생→종결 15분 1초 | 현재 상태 종결 |
             종결 방식 오탐 판정에 따른 자동 종결 — 사람이 닫은 것이 아닙니다.
③ 판정       판정 기각 (오탐) | 판정 시각 2026-09-03 20:17:32 |
             판정자 gxprobe_e2e (계정명 · 실명 미등록) |
             판정 사유 시드 — 화재 — 하천 둔치 소각
④ 조치 이력  log / gxseed_u4_official@seed.invalid / 2026-09-06 20:29:50 / 성공  (외 5줄)
             이 쪽에는 6건만 실었습니다 — 전체 42건은 알림 이력 화면에서 확인하십시오.
꼬리말       … 기록이 없는 칸은 「기록 없음」으로 적습니다(0으로 적지 않습니다).
             모든 시각은 서버 표준시 Asia/Ho_Chi_Minh (UTC+07:00) 기준입니다.
```

---

## 3. 판정자 · 판정 사유 — 지금 어떻게 찍히나

- **판정자**: `#105` 를 **찍지 않는다.** 실명이 있으면 `홍길동 (계정명)`,
  실명이 없으면 `gxprobe_e2e (계정명 · 실명 미등록)`, 계정이 사라졌으면
  `확인 불가 (계정 정보 없음)`, 아무도 판정 안 했으면 `미판정 (판정자 없음)`.
  이름 규칙은 `common/role_request._display_name` **한 곳**에서 온다(D-212).
- **판정 사유**: `DetectionEvent.reject_reason` 원문을 그대로 적는다. 사건 4802 의 DB 값은
  `시드 — 화재 — 하천 둔치 소각` 이었다(지시서에 적힌 `lane-C probe` 는 이 사건의 값이
  아니다 — 22건 전부를 확인했고 사유는 전부 `시드 — <유형> — <상황>` 꼴이다).
  값이 비어 있으면 `기재된 사유 없음` 이라고 적는다.
- ⚠ **남은 사실 하나**: 이 테넌트의 판정 22건이 **전부 `gxprobe_e2e`(내부 탐침 계정)**로
  되어 있다. 종이는 이제 그것을 「계정명 · 실명 미등록」이라고 **정직하게** 말하지만,
  감사에게 나갈 종이에 사람 이름이 실리려면 **판정을 사람 계정으로 다시 쌓아야 한다.**
  코드로 고칠 수 있는 자리가 아니다 — 시드 데이터의 문제다.

## 4. 함께 드러난 것 — **시각이 두 시간 이르다**

`config/settings.py:799` 의 `TIME_ZONE` 기본값이 **`Asia/Ho_Chi_Minh`(UTC+07:00)** 이다.
그래서 사건 4802 의 발생 시각이 종이에 `2026-09-03 20:02:31` 로 찍히는데 한국 시각으로는
`22:02:31` 이다. **여기서 서울 시각을 강제하지 않았다** — 강제하면 화면과 종이가 다른
시계를 쓰고, 두 수가 다른 것보다 나쁜 것은 왜 다른지 아무도 모르는 것이다.
대신 종이가 **자기가 어느 시계로 적혔는지 말한다**(꼬리말 마지막 줄). 설정을 바꾸면 그
줄도 함께 바뀐다(`tests/test_incident_report.ThePaperSaysWhichClockItUsedTest` 가 잰다).

→ **대표 결정 후보**: 배포 환경변수 `TIME_ZONE=Asia/Seoul` 한 줄. 값은 운영의 것이다.

## 5. 시험

★ **전 시험이 먼저 멈춰 세웠다** — `tests/test_f05_event_api.EntrySurfaceIsLockedTest` 가
`56 != 57` 로 빨개졌다. F-05 진입면은 **이름으로 잠근 계약**이고, 새 라우트를 손으로
등재하는 일이 곧 「진입면을 넓힌다」는 선언이다(D-327 · 게이트가 지시보다 위다).
등재하고 사유를 적었다: `backend/tests/test_f05_event_api.py`
`("GET", "/api/dsm/events/{int:event_id}/report.pdf")`.

`backend/tests/test_incident_report.py` — 17건 전부 초록
(`pytest tests/test_incident_report.py -q --nomigrations -p no:randomly`).
그중 셋이 이 사고를 직접 겨눈다:

- `NoCourierFieldOnThePageTest` — 완성된 HTML 에 택배 낱말이 하나라도 있으면 빨강
- `TheEventIdChangesThePaperTest` — 서로 다른 두 사건이 같은 종이를 내면 빨강
- `TheReviewerIsAPersonNotAnIdTest` — 판정자 칸에 내부 id 가 찍히면 빨강


## 6. 함께 저장한 파일 (같은 폴더)

| 파일 | 무엇 |
|---|---|
| `before_reports-7.pdf` | `GET /api/dsm/reports/7.pdf` — 배송 완료 보고서 3쪽 |
| `before_reports-7_event_id-4802.pdf` | 같은 주소 + `?event_id=4802` — 본문 동일 |
| `after_events-4802-report.pdf` | `GET /api/dsm/events/4802/report.pdf` — 사건 보고서 1쪽 |
| `after_events-4801-report.pdf` | 같은 라우트, 다른 사건 — 종이가 다르다 |
