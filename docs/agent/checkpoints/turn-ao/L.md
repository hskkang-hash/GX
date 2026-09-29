# 턴 AO · 차선 L (온보딩 갈래) — 체크포인트

WO-GX-20260930-18 · 세종 P-408. 시험 DB: `test_gx_lane_l`. 라이브 서버 측정은 하지 않았다
(V 몫) — 아래는 전부 소스 정독 + `turn_an_7.json`(일곱째 회차) 재해석이다.

## ① 바꾼/만든 파일

- `frontend/src/features/dsm/copy.ts` — `safeFreeText()` 신설(결정 번호·절 ID·백틱·
  마크다운 강조·상태 열거값만 지우는 서버 자유 문장 정화 함수).
- `frontend/src/features/dsm/pages/EventDetail.tsx` —
  ① 「판정 사유」(`e.reject_reason`) · 「실패 사유」(발송 이력 `failure_reason`) 두 칸을
     `safeFreeText()` 로 감쌈. ② `notify()` 의 세 갈래(0건·일부 실패·정상) 문구가 전부
     "발송을 요청했습니다"를 담도록 정정(U3#1 결과 문장 술어 대응 — `pred` 자체는 이
     문구로 안 바뀌는 것을 확인함, 아래 ⑤ 참조).
- `frontend/src/features/dsm/pages/AuditLog.tsx` — 「사유」 열(`dataIndex: 'reason'`)에
  `safeFreeText()` 적용.
- `frontend/src/features/dsm/pages/SystemSettings.tsx` — 재시작 요청 이력의 「사유」
  열에 `safeFreeText()` 적용.
- `backend/tests/test_ao_l_screen_language.py` (새 파일) — 위 넷을 소스 문자열로 대조.
- `docs/agent/onboarding_48.md` — 끝에 「★ 턴 AO 재갈래 표(P-408)」 절 추가(기존 내용
  줄이지 않음). (c) 16행을 c1/c2/c3/재검토로 재갈래 · U3#16 이 이미 초록이었다는 사실을
  정정(위 「턴 AN 일곱째 회차」 절 산문이 JSON 원본과 어긋났었다) · (a) 8행 일곱째 회차
  재점검 표.
- `docs/agent/checkpoints/turn-ao/L.md` (이 파일).
- 코드 변경 **없음**: `frontend/src/features/nav/roleNav.ts` — c2 인수 자산 셋
  (`/report-template`·`/roles`·`/device`) 을 대조만 했다. 앞 둘은 턴 AA(P-220)에 이미
  `NAV_ACQUIRED_HIDDEN` 으로 뗐고, `/device` 는 이미 "FWS 쪽 자산이라 안 뗀다"는 결정이
  코드 주석에 서 있었다 — 새로 뗄 것이 없었다.

## ② 시험

```
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e DB_TEST_NAME=test_gx_lane_l -w /app gx-shell \
  python -m pytest tests/test_ao_l_screen_language.py -q -p no:randomly --create-db
```
결과: **13 passed, 0 failed** (453.40s — 동시 여러 차선이 같은 gx-shell 을 쓰고 있어
`--create-db` 가 느렸다. 시험 자체는 소스 문자열 대조라 가볍다).

## ③ 닫은 절 · 못 닫은 절

이 턴은 P-356 별표 절 승격 대상이 아니다(§0.4 재갈래·화면 언어 작업) — 해당 없음.

## ④ 조율자에게 넘길 줄

- **세종 판정 청구 넷**(계측기·정본 결정 — 이 차선이 손댈 수 없는 자리):
  1. U2#6 `/report-template` · U5#2 `/roles` — 이미 우리 역할 메뉴에서 뗐다(턴 AA ·
     `roleNav.ts::NAV_ACQUIRED_HIDDEN`). 실제 고객 여정에서는 도달 불가능한 화면이니
     온보딩 48행 정본과 게이트 분모에서 **「해당 없음」**으로 빼 달라는 청구.
  2. U6#4 — `verify_click_completes.py`(Q 차선 소유)가 존재하지 않는 모델 이름
     (`WebhookOutbox` 등)을 찾는다. 실제 발송 표는 `stream_monitors.DeliveryRecord`.
     제품 결함이 아니라 판정기 결함.
  3. U3#1 — `/m/inbox` 의 `mine=true` 기본값은 턴 W·DA-04 의 의도된 설계다. "알림을
     보낸 사람이 자기 수신함에서 그 알림을 본다"는 이 온보딩 행의 술어 가정이 그
     설계와 안 맞을 수 있다 — 술어를 고치거나(발신자≠수신자를 인정) 설계를 바꾸거나
     결정해 달라는 청구.
  4. U4#8 — "조합 검색(사건번호·주소·유형 동시)" 상한에 결정 번호가 없다(`decisions.yaml`·
     `checkpoints/turn-aa/` 전수 grep 결과 없음). 번호를 달거나 실제로 지어 달라는 청구.
- `EVENT_ENTRY_SURFACE`(`test_f05_event_api.py`) — 해당 없음(새 `/api/dsm/` 라우트
  0건, 새 모델 0건).
- 라우트 대장 — 해당 없음.

## ⑤ 스스로 의심하는 점

- **safeFreeText 고침이 실제로 초록을 올리는지 확인 못 했다.** 라이브 서버를 안 두드려서
  (V 몫), U1#9·U2#3·U4#16·U5#14 의 실제 화면 텍스트에 그 넷 이외의 다른 위반 자리가
  더 있을 가능성을 배제 못 한다(예: `AuditLog.tsx` 의 「행위」 열 `dataIndex: 'action'`
  은 손대지 않았다 — `severity:set:4802` 같은 내부 API 이름이 절 ID 패턴과 우연히
  겹칠 가능성은 낮다고 판단했지만 검증은 안 했다).
- **U3#1 의 문구 정정은 `pred` 계산에 안 들어간다** — `rows_u3` 의 `pred` 는
  `post 200 and after > before and card` 셋뿐이고 `msg` 는 증거 문자열용이다.
  즉 이번 고침은 **증거 문장의 정확성만** 고쳤고 verdict 를 못 옮긴다. 진짜 블로커는
  `/m/inbox` 의 `mine` 필터이고, 그건 의도된 설계라 이 턴에서 손대지 않았다 — 다음
  손은 세종 청구 ③이다.
- **「재검토」 일곱 행(U1#8·U2#2·U2#16·U4#15·U6#4·U2#4·U4#8)을 c 밖으로 뺀 것이
  과도하게 관대한 해석일 수 있다.** 결정 번호가 없다는 사실만으로 뺐는데, 코드를
  다시 읽어 결함을 못 찾았다는 것이 "결함이 없다"의 증명은 아니다(턴 AN 도 같은 말을
  남겼다). 특히 U1#8·U2#2·U4#15 는 같은 DB(스냅샷 344598)를 두 회차 연속 쟀을 뿐이라
  진짜 표본 가설 검증(DB 를 리셋하고 다시 재는 것)은 아직 한 번도 안 됐다.
- **D-444 가 U1#2 를 직접 겨냥하는지에 자신도 한 갈래 의심이 남는다** — 결정문이 "U1#2"
  라는 행 이름을 쓰지 않고 "카메라 상태 칸은 월 모드가 냈으나 그것은 자리 화면이
  아니다"라고만 적는다. 이 문서 위쪽 「2026-09-05 턴 D 뒤 재측」 절의 U1#2 서술과
  글자 그대로 같은 사실이라 같은 결정으로 읽었지만, 그 결정문이 **이 온보딩 행을
  겨냥해 쓴 것이 아니라 다른 게이트(라우트 인벤토리) 보고문 안의 부수 서술**이다 —
  세종이 다르게 읽으면 U1#2 는 다시 「재검토」로 내려간다.
- U1#4 를 c1 로 판단한 근거(우리 메뉴 어디에도 안 걸림)는 소스 정독(`roleNav.ts` 전수
  grep)으로만 확인했다 — 실제 dj-core `Menu`/`RoleMenu` DB 행 존재 여부는 라이브
  조회가 필요해서(§0.4 · V 몫) 이 턴에서 확정하지 못했다.

## 재갈래 합계 (P-408)

**c1 = 1**(U1#4) · **c2 = 3**(U2#6·U5#2 이미 뗌 · U4#11 유지) · **c3 = 5**
(U1#2→D-444 · U1#11→D-399 · U3#7→D-399 · U3#14→D-306 · U4#9→D-306) ·
**재검토(세종 청구 후보) = 7**(U1#8·U2#2·U2#16·U4#15·U6#4·U2#4·U4#8).

`c_rows: U1#2, U1#4, U1#11, U3#7, U3#14, U4#9`(c1+c3 만 · Q 차선 두 수 산출기가 읽는다)

(a) 재점검: 8행 중 일곱째 회차 시점에 이미 초록 **3**(U1#3·U3#16·U5#5 — U3#16 은 위
「턴 AN 일곱째 회차」 절의 산문이 오기였을 뿐 JSON 원본은 처음부터 초록이었다).
이번 턴이 코드로 고친 것은 **4행 공통 원인**(U1#9·U2#3·U4#16·U5#14 — 서버 자유
문장 미가공 렌더) + U3#1 문구 절반(verdict 불변). 목표(5 이상)는 다음 회차 재측이
넷 중 둘만 옮겨도 채워진다 — 결과는 V 의 몫이라 이 턴은 보장하지 않는다.
