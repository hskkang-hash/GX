# U온 (온보딩) → 조율자 — 턴 AF

열 계정: 턴 AF 시작 시각(§0 규약 그대로). 아래 각 절의 실측 시각을 그대로 적는다.

## 0. 요약 — 한 일 넷 중 셋을 끝까지, 하나는 진단만

1. **★★ 훈련 사건 하나** — 새 관리 명령 `seed_training_incident` 로 `event_id=446155`
   (group 4 · ETRI-Group)을 심었다. **청구 0 증가를 서버 기록으로 증명**했다(아래 ④).
2. **`api.ts` 합침** — 지난 턴 `EventDetail.tsx` 가 직접 적었던 URL 을 `api.ts` 끝에
   `dsmU2SeverityEndpoint` 로 옮기고 화면은 그 이름을 부르게 고쳤다.
3. **`U1#11` 「누른 뒤」 빨강** — **제품 결함이 아니다.** 실측으로 갈랐다: 이미 그
   값이라 안 바뀐 것이었다(아래 ③). 코드는 고치지 않았다 — 고칠 결함이 없었다.
4. 시간은 남았지만 U2#6·U2#16 은 **내가 브라우저로 못 재고**, ORM 실측이 지난 턴
   내 보고와 다른 사실을 냈다 — 정정하고 넘긴다(아래 ⑥).

---

## ① 실측 명령과 출력 그대로

### 1) 훈련 사건 — 청구 전/후 (신규 관리 명령 자체 실행)

```
docker exec -w /app gx-shell python manage.py seed_training_incident --user gxseed_u2_manager
```
출력(잡음 제거, `[TRAIN]` 줄만):
```
[TRAIN] [실측] 청구 셈(전, count_events, 소속 4) = 0 (⚠ 참고값 — 동시에 도는 다른 차선이 이 수를 함께 움직인다)
[TRAIN] [실측] record_detection(K1) 호출 → event_id=446155 · track_id='data_source=drill;run=p266open'
[TRAIN] [실측] mark_unbillable 완료 — record_detection 바로 다음 줄 (event_id=446155 · source=drill)
[TRAIN] [실측] 청구 셈(후, count_events, 소속 4) = 0 (전 0 → 후 0 · Δ=0 · ⚠ 여전히 참고값이다 — 아래 「격리 대조」가 판정이다)
[TRAIN] [실측] [판정] 이 행이 청구 쿼리(exclude_unbillable)에 남아있는가 = False (False 여야 훈련이다) · BillingMark 곁표에 있는가 = True
[TRAIN] [실측] 독립 재조회 · event_id=446155 · response_state='occurred' (occurred 여야 '열린' 사건) · severity=critical · stream_monitor_id=119 · track_id='data_source=drill;run=p266open' · is_drill_track=True
[TRAIN] [실측] services.event_data_source(상세 API 와 같은 호출) = 'drill' — 'drill' 이면 copy.ts dataSourceBadge.drill='훈련' 이 화면에 그려진다
EXITCODE=0
```

재실행(멱등 확인):
```
[TRAIN] 이미 있다(멱등) — 다시 만들지 않는다: event_id=446155
EXITCODE=0
```

**직접 대조** — 이 사건 하나가 DB 전체의 「미처리 비-probe」 분모를 0 → 1 로 옮겼다:
```python
DetectionEvent.objects.filter(response_state='occurred').exclude(track_id__startswith='data_source=probe').count()
# 이전 턴 실측: 0  →  이번: 1
qs4 = ...filter(stream_monitor__group_id=4)  # group4=1, [(446155, 'data_source=drill;run=p266open')]
```

### 2) U1#11 「누른 뒤」 진단 — 이미 그 값이라 안 바뀐 것

증거 원본(`docs/agent/evidence/P-118/click_completes.json:858-877`, 조율자/K+Q 소유
파일 — **읽기만 했다**):
```
"U1#11": {
  "control": {"found": true, "clicked": true, "name": "실제로 판정"},
  "calls": [
    {"method": "POST", "url": ".../events/342448/review?verdict=confirmed&reason=...", "status": null},
    {"method": "GET",  "url": ".../events/342448", "status": null}
  ],
  "state": {"kind": "server_change", "get": "/api/dsm/events/{event}",
            "field": "verdict", "before": "confirmed", "after": "confirmed"}
}
```
`text_after` 안의 「판정자 #110 · 13:13 · 17시간 전」— 이 사건은 클릭 **17시간 전에
이미** `confirmed` 로 판정돼 있었다. 즉 시험이 누른 것은 「지금 있는 값과 같은 값을
다시 요청」이었다.

**제품이 실제로 값을 바꾸는가 — 같은 사건·같은 함수로 뒤집어 봤다**(gx-shell ORM,
`kernels.k1_event.review_event` — API `/events/{id}/review` 가 그대로 부르는 그
함수):
```
BEFORE confirmed
AFTER rejected call rejected      ← 다른 값을 주면 실제로 바뀐다
AFTER confirmed call (revert) confirmed   ← 원래 값으로 되돌렸다(순변화 0)
```
**판정: 제품 결함이 아니다.** `review_event` 는 다른 값을 주면 정확히 바뀐다 —
빨강은 「같은 값을 다시 요청해 아무것도 안 바뀐」 시험 표본의 문제다(P-118 이 같은
드릴 사건 342448 을 반복해 재사용하고, 판정 사이에 값을 되돌리지 않기 때문). 되돌려
사건 342448 은 실측 전 상태(`verdict=confirmed`)로 **정확히 복귀**했다 — 순변화 없음.

### 3) 타입검사 (기준선과 경합 없이 단독 실행)
```
MSYS_NO_PATHCONV=1 docker exec -w /app gx-fe-build npx tsc -p tsconfig.app.json --noEmit
```
줄 수: **3234줄** — 기준선과 동일. `EventDetail.tsx`/`api.ts` 관련 오류 0건.

### 4) 문법 확인
```
docker exec -w /app gx-shell python -c "import py_compile; py_compile.compile('stream_monitors/management/commands/seed_training_incident.py', doraise=True)"
→ OK syntax
```

---

## ② 고친 파일:줄

- **신규** `backend/stream_monitors/management/commands/seed_training_incident.py`
  (전체 새 파일 — 소유표의 「훈련 사건 시드 스크립트 새로 1」). 씨앗 카메라
  (`GX-SEED-DSM` · group 4 · 이미 청구 밖)를 그대로 쓰고 새 카메라를 안 만든다.
  `mark_unbillable` 을 `record_detection` 바로 다음 줄에서 부른다(순서 실측 위 ①).
  `--report` 로 세기만 가능 · 지우는 길은 없다(대표 결정).
- `frontend/src/features/dsm/api.ts` — **끝에 추가**(1101행 이후, 기존 리터럴은 한
  줄도 안 건드림): `dsmU2SeverityEndpoint` 상수 묶음(`eventSeverity` 함수형 URL).
- `frontend/src/features/dsm/pages/EventDetail.tsx`
  - import 목록에 `dsmU2SeverityEndpoint` 추가.
  - `regrade()` 안의 `dsmPostQueryOnce(\`/api/dsm/events/${id}/severity\`, …)` 를
    `dsmPostQueryOnce(dsmU2SeverityEndpoint.eventSeverity(id), …)` 로 교체.

세 파일 다 U온 소유표 안(`frontend/src/features/dsm/**` · `api.ts` 이 턴 U온 소유 ·
훈련 사건 시드 스크립트 새로 1). `backend/apps/dsm/api_u24.py` 는 이번 턴 안 건드렸다
(고칠 필요가 없었다 — U2#3 문은 지난 턴에 이미 서 있다).

---

## ③ 안 한 것과 사유

1. **U2#6(상황보고서)·U2#16(알림 규칙)을 훈련 사건에 이어 붙이지 않았다.**
   조율자 지시문은 넷을 「전부 데이터 0건」으로 묶었지만, 이번 턴 ORM 실측이
   그 전제를 부분적으로 흔들었다 — ⑥에 정정해 적는다. 두 행을 직접 고치는 것은
   내 소유표(`frontend/src/features/dsm/**` · `api_u24.py` · 시드 스크립트 1) 밖의
   원인일 가능성이 있어 손대지 않았다.
2. **U2#2·U4#15 를 직접 브라우저로 재지 않았다** — §1 규약(차선은 브라우저를 안
   잰다)대로 ORM 대조까지만 하고 조율자에게 넘긴다(④).
3. **U4#11(`/device`)·U5#2(`/roles`) 등 다른 빨강은 손대지 않았다** — 지난 턴과
   같은 이유(소유표 밖 · `rj-core` 인접).
4. **U1#11 의 시험 표본 문제 자체(같은 드릴 사건을 반복 재사용)를 고치지 않았다** —
   그 판정기(`verify_click_completes.py`/`scripts/measure_onboarding_t.py`)는
   K+Q 소유다. 고칠 방향(사건 342448 을 매 실행 전에 되돌리거나, 판정마다 다른
   사건을 골라야 한다)만 여기 적어 넘긴다.
5. **전량 정본 시험은 안 돌렸다** — 이번 턴 백엔드 변경은 새 관리 명령 파일 1개뿐이고
   (기존 커널·앱 코드 무변경), ORM 진단은 전부 가역적으로 원복했다(342448 verdict
   원상 복귀 확인). 프런트 변경은 타입검사(③)로 갈음했다.

---

## ④ 훈련 사건 id 와 청구 전/후 표

| 항목 | 값 |
|---|---|
| event_id | **446155** |
| 소속(group) | 4 (ETRI-Group — `gxseed_u2_manager`·`gxseed_u4_official` 둘 다 이 소속) |
| 카메라 | `stream_monitor_id=119` (`GX-SEED-DSM`, 이미 `data_source=seed`) |
| track_id | `data_source=drill;run=p266open` |
| response_state | `occurred` (열려 있다 — 미처리) |
| verdict | `None`(미판정) — 건드리지 않았다 |
| 청구 셈(count_events, 소속4) | 전 0 → 후 0 · Δ=0 (⚠ 다른 차선과 공유하는 참고값) |
| **격리 대조(판정)** | `exclude_unbillable(qs.filter(pk=446155)).exists()` = **False** (청구 쿼리에서 빠짐) |
| BillingMark 곁표 | `event_id in marked_unbillable_ids(DetectionEvent)` = **True** |
| 화면 배지 | `services.event_data_source(view=...)` = `'drill'` → `copy.ts` `dataSourceBadge.drill='훈련'` |

**이 사건 id 로 계측기를 돌리면 넷 중 둘(U2#2·U4#15)이 잡힌다** — DB 전체의
「미처리 비-probe」 사건 수가 0 → 1 이 되었고, 그 1건이 `gxseed_u2_manager`·
`gxseed_u4_official` 둘 다의 소속(group 4)에 있다. U2#6·U2#16 은 이 사건 하나로
잡히는지 **불확실하다**(⑥ 참고 — ORM 이 이미 다른 사실을 냈다).

---

## ⑤ 조율자가 계측기·브라우저로 할 일

1. **재측**: `scripts/measure_onboarding_t.py` 를 다시 돌려 U2#2·U4#15(그리고
   가능하면 U2#6·U2#16)이 초록/◐ 로 바뀌는지 서버 기록으로 확인.
   - 계정: `gxseed_u2_manager`(U2 행) · `gxseed_u4_official`(U4 행)
   - 주소: `/dsm/events?preset=unhandled`(U2#2) · `/dsm/events`(U4#15, 「보고
     표시」 토글이 행마다 그려지는지) · 사건 상세 `/dsm/events/446155` 에서
     「훈련」 배지가 보이는지(사람 눈 대조 — 관제요원이 실사건으로 오인하지
     않는지가 이 일의 핵심 술어다).
2. **U2#6·U2#16 은 이 사건 하나로 안 잡힐 수 있다** — ⑥ 참고. 조율자가 재측한
   뒤에도 빨강이면, 시드가 아니라 **다른 원인**(화면이 그 문을 안 부른다 · 또는
   `/dsm/notify` 화면이 `fire_admin` 역할에서 다른 위젯을 그린다)일 가능성을
   K+Q/A 차선에 넘겨야 한다.
3. **U1#11 판정기 손질**: `scripts/measure_onboarding_t.py`(또는
   `verify_click_completes.py`)가 U1#11 을 잴 때 **같은 드릴 사건(342448)을
   반복 재사용**한다 — 그 사건이 이미 `confirmed` 인 채로 남아 있으면 다음 실행도
   계속 빨강이다. K+Q 에게 넘길 수정 방향: 판정 전에 사건을 되돌리거나(예:
   `rejected` 로 리셋한 뒤 재기), 매 실행마다 새 미판정 사건을 골라 누른다.
   이번 턴에 342448 은 진단 뒤 **원래 값(confirmed)으로 정확히 복귀**시켰다 —
   다음 실행이 이번과 같은 「이미 그 값」 빨강을 다시 낼 것이다(고치지 않았으므로).

---

## ⑥ 내가 틀렸던 것

1. **지난 턴 내 보고가 이번 턴 지시의 전제(「U2#6·U2#16 도 데이터 0건」)에 섞여
   들어갔는데, 이번 턴 ORM 실측이 그 전제를 부분적으로 깼다.** `NotificationRule`
   을 소속 4 기준으로 직접 세어 보니 **9건**이었다(0건이 아니다) —
   ```
   Rule._base_manager.filter(group_id=4).count() == 9
   ```
   즉 U2#16(알림 규칙 확인)의 빨강은 「규칙이 0건이라서」가 아닐 가능성이 있다.
   지난 턴 판정문의 「notify-rules/list 200=False」는 **호출 자체가 관측되지
   않았다**는 뜻이라(U2#6 의 「화면이 그 문을 안 부른다」와 같은 모양), 데이터
   문제가 아니라 **화면이 그 문을 안 부르는 문제**일 수 있다 — 추측으로 남긴다,
   §1 규약대로 **확실하지 않은 것을 초록으로 안 바꿨다.** 지시를 그대로 따라
   「전부 데이터 0건」으로 뭉뚱그려 보고했다면 이 지점에서 거짓 초록을 만들
   뻔했다 — 이번 턴에 갈라서 적는다.
2. **U1#11 의 「누른 뒤」 빨강을 처음엔 제품 결함일 수도 있다고 의심하고
   접근했다** — 지시문의 「요청은 나갔는데 값이 안 바뀐다」는 문장이 ㉡ 가족
   (실패 자국)을 가리키는 것처럼 읽혔기 때문이다. 증거 파일의 `text_after` 안
   「판정자 · 17시간 전」한 줄을 먼저 안 읽었으면 코드를 뒤졌을 것이다. 시각
   대조를 먼저 하고, 그 다음 같은 함수를 실측으로 뒤집어 봐서 가설을 기각했다 —
   추측이 아니라 A/B(다른 값→바뀜 · 같은 값→안 바뀜)로 가른 것이다.
3. `mark_unbillable` 을 사건 자신에게 걸 필요가 있는지 처음엔 불확실했다
   (`track_id` 표식만으로 이미 청구 쿼리에서 빠지기 때문 — `exclude_unbillable`
   첫 갈래). 조율자 지시가 명시적으로 그 경로를 가리켜서(K+Q 가 계측기에 배선한
   길) **덧댄 증거**로 걸었다 — 곁표 없이 track_id 표식만으로도 청구는 이미
   빠졌다는 것을 코드로 먼저 확인한 뒤에 결정했다(과잉이 아니라 이중 방어).
