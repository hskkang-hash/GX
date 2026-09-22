# B → 조율자 (턴 AD · 2026-09-22 저녁)

**이것 하나만 · 끝까지 — 끝났다.** 발급 순간 배선. 다섯 자리를 실측했더니 **다섯이
아니었다** — 실제로 태어나는 자리·태어나지 않는 자리를 갈랐고, 태어나는 자리에만
배선했다(③·⑦ 참고). 회귀 시험 둘(5개 테스트 메서드) 전부 초록. 시간이 남아 V 잔여
표식(마이그레이션 둘)도 했다 — **삭제 0**.

**추가(조율자가 중간에 넘긴 `verify_seed_p20.py` 실측 — ⑩ 참고): 처리했다.**
씨앗 **사건**(`GX-SEED-DSM` 위 23건 중 22건)이 `exclude_unbillable` 의 옛 세 갈래
어디에도 안 걸려 청구로 새고 있던 것을 고쳤다. `verify_seed_p20.py` **rc 1 →
rc 0**(「유출 22건」→「남은 것 0건」), A/B 회귀 시험 신설, 고객 사건 안 줄어듦도
같이 잰다. 전체 시험 **31 passed, 0 failed**(233초 실행분 24+5 신설, 181초
재실행분 29+2 P-251 신설 — 누적 31).

## ① 실측 (명령 + 결과)

```
# mark_unbillable 기존 호출부 — 발급 순간 배선 0/5 라는 전제 확인
grep -rln "mark_unbillable" --include="*.py" .
→ backend/common/billing_marks.py (정의) · backend/tests/test_b_billing_marks.py (시험) 뿐.
  프로덕션 호출 0건 — 전제 맞음.

# ① 게이트 탐침 카메라 — StreamMonitor 생성 지점 7곳(6파일) 실측
grep -n "\.create(\|\.get_or_create(" scripts/probe_event_rate_limit.py scripts/probe_video_backup.py \
  scripts/verify_camera_pulse.py scripts/verify_alarm_budget.py scripts/verify_purge.py scripts/capture_screens.py
→ probe_event_rate_limit.py:262 / verify_camera_pulse.py:308 / verify_alarm_budget.py:269 /
  verify_purge.py:499,502  →  전부 `transaction.atomic()` 안에서 `raise _Rollback` 로 되돌린다
  (직접 코드로 확인: 각 파일에서 `raise _Rollback` 뒤 `except _Rollback: pass`) — **DB에 안 남는다.**
  probe_video_backup.py:129 / capture_screens.py:661  →  `get_or_create` · 롤백 없음 · **실제로 남는다.**

# ② 온보딩 계측기 — 출생 표본 위치 확인
grep -n "U5#1\|U5#4" scripts/measure_onboarding_t.py
→ 1893(U5#4 카메라 일괄등록 POST /api/dsm/cameras/import) · 1988(U5#1 계정 생성
  POST /api/dsm/settings/people/create). 파일 머리에 `import django` 없음 —
  **Django ORM 접근 자체가 없다**(순수 Playwright). 두 자리 다 **실제 고객이 쓰는
  것과 같은 프로덕션 HTTP 문**을 두드린다(`backend/apps/dsm/api_u56.py:298` →
  `people.py:94 create_person()` — 이 함수의 유일한 다른 부르는 자리가 실제 관리
  화면 API 다). 이 파일은 **Q 소유**(규약 §1).

# ③ 훈련 창 — drill.py 가 무엇을 만드는지 실측
grep -n "\.objects\.create\|\.save(\|_base_manager" backend/stream_monitors/services/drill.py
→ `_base_manager.filter(...)` 세 곳뿐 — **create/save 0건.** 파일 머리말 그대로
  "새 표를 만들지 않는다(D-333)·새 쓰는 손을 만들지 않는다(D-325)". 태어나는 자리가
  없다 — 배선할 곳이 없다.

# ④ 씨앗 계정 — seed_role_users.py 실측
sed -n '455,545p' backend/stream_monitors/management/commands/seed_role_users.py
→ management command(Django ORM 접근 있음) · `_readback()` 이 이미 ORM 으로 user
  객체를 되읽는다 — 그 자리가 배선 지점.

# ⑤ 탐침 계정 — 반복 생성 코드 존재 여부 실측
grep -rn "gxprobe_e2e" 전체
→ `scripts/capture_screens.py:45`: "이 저장소의 개발 환경에는 gxprobe_e2e 를 **손으로
  만들어 두었고**" — 한 번 수동 생성된 고정 픽스처. 반복되는 "태어나는 자리"가 없다.
  이미 `common/migrations/0003_p224_seed_account_marks.py:66-67`(pk=105)로 소급됨.

# 회귀 시험
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings -w /app \
  gx-shell python -m pytest tests/test_b_billing_marks.py -q -p no:randomly
→ 29 passed, 0 failed, 233.78s (기존 24 + 신설 5)

# V 잔여 — 재서 대 봄 (지시서의 "계정 226 · 카메라 16" 전제 확인)
docker exec ORM 조회 → gxprobe_onb_* 계정 **다섯**(118·119·224·225·226) 전부 표식
없음(226 만 is_active=True). 카메라는 `GX-ONB-V-*` 계열 중 **pk=6144**
(`GX-ONB-V-20260921T145138` — 226 과 같은 타임스탬프) 만 data_source=live, 나머지
여섯은 0031 이 이미 probe 로 소급해 뒀다.

# ⑩ 조율자가 넘긴 verify_seed_p20.py — 고치기 전 (조율자 원 실측 그대로)
docker exec ... gx-shell python /repo/scripts/verify_seed_p20.py
→ rc 1 · "씨앗 23건 중 청구 셈에 남은 것 22건 — GX-SEED-DSM 은 track_id 표식도
  없고 StreamMonitor.data_source 도 상속 경로가 없어 exclude_unbillable 의
  ㉠㉡㉢ 중 아무것도 안 걸린다"

# 원인 실측 — 카메라 자체는 이미 표식돼 있었다(오해 정정)
docker exec ORM: Stream.objects.get(code="GX-SEED-DSM").data_source
→ 'seed' (마이그레이션 0031 이 pk=119 를 이미 소급해 둠). **문제는 카메라가 아니라
  사건이었다** — DetectionEvent 에는 `data_source` 칸이 없고(U1 의 의도적 설계 —
  칸을 만들면 「빈 과거」 문제), track_id 표식도 없다(seed_dsm_events.py 가 K1
  정식 경로로 심어서 고정값을 안 남긴다). exclude_unbillable 이 카메라→사건
  상속을 아예 모른다 — 그래서 셋째 갈래(곁표)도 못 걸었다.

# 배선 뒤 재실측
docker exec ... gx-shell python /repo/scripts/verify_seed_p20.py
→ rc 0 · "P-251 씨앗은 청구·KPI 0건    씨앗 23건 중 청구 셈에 남은 것 0건" ·
  "통과 — P-20 네 수가 전부 섰다"
```

## ② 고친 파일 : 줄

- `scripts/probe_video_backup.py:135-140` — `get_or_create` 뒤 `mark_unbillable(monitor,
  "probe", reason=...)` 추가
- `scripts/capture_screens.py:678-684` — 주소 갱신 뒤 `mark_unbillable(monitor, "probe",
  reason=...)` 추가
- `backend/stream_monitors/management/commands/seed_role_users.py:527-538` — 되읽기
  루프 안에서 `user is not None` 일 때 `mark_unbillable(user, SEED_SOURCE, reason=...)`
  추가(새로 만든 것·이미 있던 것 둘 다 — `update_or_create` 라 안전)
- `backend/tests/test_b_billing_marks.py:353-445 부근` — 신설 클래스 둘
  (`TheNewSeedIsBornAlreadyMarkedTest` · `TheRealCustomerBillNeverShrinksTest`, 5 시험)
- `backend/common/billing_marks.py` — **P-251 추가 배선**(⑩): `CAMERA_RELATION_FIELD =
  "stream_monitor"` 상수 신설(105줄 부근) · `exclude_unbillable` 에 넷째 갈래(㉣)
  `elif CAMERA_RELATION_FIELD in names:` 추가(213-217줄 부근) — 제 칸이 없는 표가
  카메라로 이어지면 카메라의 `data_source` 를 상속해서 뺀다. 소급판·발급판이 같은
  함수(`mark_unbillable`)로 되는지 확인만 했던 것과 달리 **이 함수(exclude_unbillable)
  는 실제로 고쳤다** — 계정·카메라와 달리 사건은 발급 순간에 달 칸 자체가 없어서
  (U1 의 의도적 설계) "발급 순간 배선"이 아니라 "셈이 상속을 볼 줄 알게" 고치는
  쪽이 맞는 고침이었다.
- `backend/stream_monitors/management/commands/seed_dsm_events.py:220-249` —
  `_camera()` 의 `get_or_create` defaults 에 `data_source=SEED_SOURCE` 추가 +
  기존 행 보정 줄(발급 순간 배선 — 이 카메라가 재생성될 미래를 방어) 추가
- `backend/tests/test_b_billing_marks.py:493-526 부근` — 신설 클래스
  `TheSeedEventInheritsTheCamerasSourceTest`(2 시험 — 씨앗 사건 0 증가 · 고객 사건
  그대로)
- `backend/common/migrations/0004_p224_seed_account_marks_v_residual.py` — 신설(V 잔여
  계정 5)
- `backend/stream_monitors/migrations/0032_p224_camera_data_source_v_residual.py` —
  신설(V 잔여 카메라 1)
- `backend/common/billing_marks.py` — **변경 없음.** 소급판·발급판이 **같은 함수**
  (`mark_unbillable`)로 되는지 읽어 확인만 했다 — 곁표(`common.BillingMark`) 경로라
  모델에 `data_source` 칸이 있든 없든 동일하게 동작한다(§0.4 U1 소유 `data_source`
  낱말 밭은 **읽기만** 했다 — 칸 자체는 안 건드리고 곁표만 썼다).

## ③ 배선 N/5 — **다섯 중 셋만 태어나는 자리가 있었다**

| 자리 | 태어나는가 | 배선 | 파일:줄 |
|---|---|---|---|
| ① 게이트 탐침 카메라 | **부분** — 7곳 중 2곳만 DB에 남는다(5곳은 시험 트랜잭션이 자체 롤백) | ✅ 남는 2곳 배선 | `probe_video_backup.py:139-140` · `capture_screens.py:682-683` |
| ② 온보딩 계측기 | 그렇다(U5#1·U5#4) — 그러나 **Q 소유 파일**이고 **Django ORM 없음**(Playwright) · 실제 고객과 **같은 프로덕션 API**를 씀 | ❌ 못 함(⑦ 참고) | `scripts/measure_onboarding_t.py:1893,1988`(못 고침) |
| ③ 훈련 창 | **아니다** — create/save 0건, read-only 창 판정 | 배선 대상 없음 | `backend/stream_monitors/services/drill.py`(해당 없음) |
| ④ 씨앗 계정 | 그렇다 | ✅ 배선 | `seed_role_users.py:527-538` |
| ⑤ 탐침 계정 | **아니다** — 손으로 한 번 만든 고정 픽스처, 이미 소급됨(pk=105) | 배선 대상 없음 | `common/migrations/0003_p224_seed_account_marks.py:66-67`(이미 됨) |

**결론**: 실제로 배선한 곳은 **3자리(①의 2곳 + ④)**. ②는 소유·도구 제약으로 오늘
못 했다(파일 소유 Q + Django 접근 없음 + 실고객과 endpoint 공유라 서버 쪽에 걸면
고객까지 걸린다). ③·⑤는 애초에 배선할 "태어나는 자리"가 없다 — 지시서의 "다섯"은
입력이었고 실측은 셋이었다.

## ④ 「새 씨앗 계정 1 을 만들면 청구 수가 0 증가」 시험 결과

**초록.** `TheNewSeedIsBornAlreadyMarkedTest` (3 메서드) —
`test_a_freshly_born_seed_account_adds_zero_to_the_bill` ·
`test_a_freshly_born_probe_camera_adds_zero_to_the_bill` ·
`test_born_together_still_adds_zero`(계정+카메라 같은 회에 함께 태어나는 V 회차
모양) — 전부 통과. `seed_role_users.py`·`probe_video_backup.py`·`capture_screens.py`
가 지금 하는 일(만들고 그 자리에서 `mark_unbillable` 호출)을 그대로 흉내 냈다.

## ⑤ 「진짜 고객 것의 청구는 한 톨도 안 준다」 시험 결과

**초록.** `TheRealCustomerBillNeverShrinksTest` (2 메서드) —
`test_customer_rows_created_alongside_seeds_are_not_touched`(고객 카메라·계정 5개를
만들고 **같은 회에** 씨앗·탐침도 섞어 만들어도 고객 몫 청구 수는 정확히 5 그대로) ·
`test_the_seed_username_convention_does_not_catch_a_real_customer`(이름이 우리 접두
`gxseed_` 와 우연히 겹쳐도 **표식을 안 달면** 청구는 그대로 — 세는 코드가 이름을
안 본다는 사실을 이름이 겹치는 상황에서 확인, D-280과 짝) — 전부 통과.

## ⑥ 출생 표본 (D-310)

이 배선을 만들게 한 실례: **턴 AB V 회차가 만든 계정 1(`gxprobe_onb_20260921T145138`
· pk=226) · 카메라 1(카메라 수 15→16 · pk=6144 `GX-ONB-V-20260921T145138`)이 표식
없이 태어나 그대로 청구에 들었다**(`docs/agent/checkpoints/turn-ab/V.md:190-198`).
시험 파일 `backend/tests/test_b_billing_marks.py`의 신설 두 클래스 머리말·주석에
「출생 표본」 문구를 그대로 넣었다(`verify_tool_selftest.py` 의 `BIRTH_MARKERS` 요건
대비).

## ⑦ 못 한 것과 왜

- **② 온보딩 계측기(measure_onboarding_t.py)는 오늘 못 배선했다.** 이유 셋:
  ⓐ 그 파일은 **Q 소유**(규약 §1 소유표) — 내가 고치면 소유표를 어긴다.
  ⓑ 그 스크립트는 **Django import 가 아예 없는 순수 Playwright** — `mark_unbillable`
  (ORM 함수)을 부를 방법이 그 파일 안에 없다.
  ⓒ U5#1·U5#4 가 두드리는 문(`/api/dsm/settings/people/create` →
  `people.create_person()` · `/api/dsm/cameras/import`)은 **실제 고객이 쓰는 것과
  같은 프로덕션 API**다(`api_u56.py:298` 가 유일한 다른 부르는 자리). 서버 쪽에
  "이건 우리 측정이다"를 구분할 신호가 없다 — 억지로 걸면 실고객이 걸릴 위험이
  지시서가 명시적으로 경계한 바로 그것이다("배선을 넣어도 고객 수가 줄면 그것은
  청구 근거를 바꾼 것"). 그래서 **안전하게 걸 방법이 없어서 안 걸었다.**
  대안은 다음 턴 제안: Q 가 U5#1/U5#4 응답에서 얻는 새 id 를 캡처해 자기 쪽에서
  (혹은 내가 제공하는 별도 헬퍼를 불러) 측정 종료 뒤 별도로 `mark_unbillable` 을
  거는 것 — 오늘은 넓히지 않았다.
- 회색 게이트(verify_camera_pulse.py 등 5곳의 카메라 생성 지점)에는 **배선하지
  않았다** — 실측으로 확인 결과 전부 `transaction.atomic()` + `raise _Rollback` 로
  자체 롤백돼 DB에 안 남는다(청구 위험 0). 배선해도 틀리진 않지만 "넓히지 마십시오"
  규약과 시간 제약상 실제 위험이 있는 2곳(persist 하는 곳)만 했다. 롤백이 나중에
  제거되면 이 5곳도 위험해진다는 점은 코드 주석으로 남기지 않았다 — 이 쪽지가 그
  기록이다.

## ⑧ 틀린 전제

- 지시서 "다섯 자리"는 **입력이지 측정이 아니었다**(지시서 본문이 스스로 경고한
  대로). 실측 결과: **③ 훈련 창은 태어나는 자리 자체가 없고, ⑤ 탐침 계정도 반복
  생성되지 않는 고정 픽스처**라 배선 대상이 아니다. ①도 "카메라"라는 단수 개념이
  실제로는 7개 호출 지점(6파일)으로 흩어져 있었고, 그중 5곳은 자체 롤백이라 청구
  위험이 없었다 — "게이트 탐침 카메라"를 하나의 자리로 뭉뚱그리면 위험 없는 5곳에
  괜히 배선하고 진짜 위험한 2곳을 놓칠 수 있었다.
- "V 잔여(계정 226 · 카메라 16)"도 다시 재보니 **단수가 아니었다** — 계정은 226
  하나가 아니라 **같은 계열 다섯(118·119·224·225·226)**이 전부 미표식이었다(카메라
  쪽은 6개 중 5개가 이미 0031 로 소급돼 있었는데 계정 쪽은 **단 한 번도** 소급된
  적이 없었다). 카메라는 정확히 "16번째"가 아니라 **pk=6144 한 대**(전체 카메라
  수와 무관하게 마지막 GX-ONB-V-* 한 줄)였다.

## ⑩ 조율자가 중간에 넘긴 것 — `verify_seed_p20.py` (P-251)

조율자가 직접 실측해 넘겼다: 씨앗 **사건**(`GX-SEED-DSM` 위) 23건 중 22건이
`count_events` 의 `exclude_unbillable` 을 그대로 통과해 청구·KPI 로 샜다(rc 1).

**원인**: 카메라(pk=119)는 이미 `data_source=seed` 로 맞았다(마이그레이션 0031).
문제는 **사건 쪽**이었다 — `DetectionEvent` 는 U1 의 의도적 설계로 자기 칸
(`data_source`)이 없고(칸을 만들면 「빈 과거」가 「훈련·씨앗 아님」으로 읽히는
문제, `apps/dsm/services.py::event_data_source` 머리말), probe·drill 과 달리
`track_id` 표식도 안 남는다(`seed_dsm_events.py` 가 K1 정식 경로로 심어서 화면에
고정값을 안 남기는 것이 원래 설계 요점). 그래서 `exclude_unbillable` 의 옛 세
갈래(㉠ track_id · ㉡ 제 칸 · ㉢ 곁표) 중 **아무것도 이 표에 안 걸렸다.**

**고침**: `common/billing_marks.py` 에 넷째 갈래(㉣) — 제 칸이 없는 표가
`stream_monitor` 관계로 이어지면 **카메라의 `data_source` 를 상속**해서 뺀다.
`CAMERA_RELATION_FIELD = "stream_monitor"` 상수 하나 · `exclude_unbillable` 안의
`elif` 한 줄. U1 의 "data_source 낱말 밭"(무엇이 씨앗인가의 **제품 판정**)은 안
건드렸다 — 그 파일(`stream_monitors/services/seed.py`)이 스스로 "청구 칸 배선은
… 다음에 간다"고 미뤄 둔 자리를 그대로 이었을 뿐이다. 곁들여
`seed_dsm_events.py::_camera()` 에 발급 순간 `data_source=SEED_SOURCE` 도
달았다(카메라가 마이그레이션 없이 재생성되는 미래를 방어).

**시험**: `TheSeedEventInheritsTheCamerasSourceTest` 신설 2건 — 씨앗 카메라 위
사건 3건 추가 → 청구 0 증가 / 고객 카메라 위 사건 3건 추가 → 청구 정확히 +3.
`verify_seed_p20.py` 고치기 전 rc 1(22건 유출) → 고친 뒤 rc 0(0건) — 조율자가
요청한 A/B 그대로.

## ⑨ 모르는 것

- 118·119·224·225(is_active=False)가 다시 활성화될 경로가 제품에 있는지 —
  있다면 이번 표식이 그 재활성화를 미리 막아 둔 것이고, 없다면 방어적 조치였다.
  실측 안 함(회색으로 남긴다).
- ②(온보딩 계측기)의 안전한 배선 방법 — 내가 제안한 "측정 종료 뒤 id 로 별도
  호출" 방식이 Q 의 파일 구조·소유권과 실제로 맞물리는지는 Q 의 판단이 필요하다.
- 미디어(저장) 장부의 씨앗 몫은 여전히 못 잰다(billing_marks.py 머리말 그대로,
  이 턴에서 손 안 댐 — 기존에 알려진 빚).
- `StreamMonitorAIModel`·`DrawingSession` 도 `stream_monitor` 관계를 갖고 있어
  새 갈래(㉣)의 대상이 되지만, 지금 어떤 청구 커널도 그 둘에 `exclude_unbillable`
  을 걸지 않는다 — **잠들어 있지만 해로운 잠은 아니다**(제네릭 필드 검사라 D-377
  이 말하는 "쓰는 데 없는 갈래를 미리 세운" 것과는 다르다고 판단했는데, 조율자가
  다르게 보면 좁혀야 한다).

— B
