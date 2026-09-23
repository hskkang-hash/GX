# K+Q(판정기·배선) → 조율자 · 턴 AE · 2026-09-23(기계)

## ① 실측 명령과 출력 그대로

### 1) `verify_spec_coverage.py` — 여섯째 부류(`measured_red`) 눈금 문제

정본 호출(호스트에서 — 이 파일은 `verify_ga_readiness.py` 를 부른다):
```
python scripts/verify_spec_coverage.py
```
**고치기 전**:
```
[SPEC] [입력] 명세서 3 · 표식 136건 · 대장 절 155 · 등재 136 · 미등재 0
...
[SPEC]   · 눈금: N 쪽 `verify_ga_readiness.py::KIND_SCORE` 를 import 로 가져왔다 — 눈금이 같다 ...
[SPEC] ? **기능명세 포함 완료율 — 회색.** 분모(?)는 섰으나 **분자를 못 읽었다**
[SPEC]   ? [세종 판독] 줄을 못 읽었다 — `WO-GX-20260921-04_report_wave1_turn1.md` 에서 …
[SPEC]   X 대장에 **눈금 밖의 부류**가 있다: measured_red — 모르는 부류를 0 으로도 1 로도 세지 않는다
[SPEC] X **빨강** 1건
```
**고친 뒤**:
```
[SPEC] [입력] 명세서 3 · 표식 136건 · 대장 절 155 · 등재 136 · 미등재 0
...
[SPEC]   · 눈금: N 쪽 `verify_ga_readiness.py::KIND_SCORE` 를 import 로 가져왔다 — 눈금이 같다 …
  · **measured_red 0.0 을 `KIND_POINTS`(같은 모듈의 거르기 전 원본)에서 마저 읽었다** —
    `KIND_SCORE` 의 다섯 칸 필터 자체는 그대로 둔다(그 파일은 이번 턴 소유표 밖 · 걷어내는
    것은 그 필터를 세운 차선의 몫)

[SPEC] ★ **기능명세 포함 완료율 27.5 %**  = 대장 kind 점수 80.0 ÷ **분모 291**(대장 절 155 + 별표 전수 136)
[SPEC]    상한(별표를 1 로) 74.2 %  …
[SPEC]   ? [세종 판독] 줄을 못 읽었다 — `WO-GX-20260921-04_report_wave1_turn1.md` 에서 …
[SPEC] ? **회색(exit 2)** — 회색은 초록이 아니다 (D-301). …
```
`--self-test`: `자기시험 24건 통과`(고치기 전 자기시험 항목은 그대로 다 유지 — 새 항목을
더하지 않았다. 이 함수는 순수 조회이고 별도 표본 없이도 회귀는 이미 돈다).

**「완료율이 수로 나야 한다」는 조건은 만족했다** — 27.5% 로 실측치가 났다.
⚠ **전체 rc 는 여전히 2(회색)** — 남은 회색은 `measured_red` 와 **무관한 별개 원인**이다:
`WO-GX-20260921-04_report_wave1_turn1.md` 에서 「DSM 지침 N · FWS N · 운영자 콘솔 N」
줄을 못 읽는다(고치기 전에도 있던 회색 · git diff 로 이 문서를 이번 턴에 내가 안 건드렸음을
확인했다). 이건 그 문서 소유자(세종/조율자) 쪽 문제라 손대지 않았다.

### 2) `verify_seed_p20.py` — 머리글 거짓말 + 실제 위임 배선

**고치기 전** (호스트에서):
```
[P20] 자기시험 통과 — …
[P20] **판정 불가** — 환경을 세우지 못했다: ModuleNotFoundError: No module named 'config'
[P20] 컨테이너 안에서 DJANGO_SETTINGS_MODULE 를 주고 돌린다
```
**고친 뒤** — `GX_ROUTE_CONTAINER=gx-shell` 을 주고 호스트에서 그대로 호출(실물 컨테이너로 확인):
```
GX_ROUTE_CONTAINER=gx-shell python scripts/verify_seed_p20.py
```
```
[P20] 자기시험 통과 — … + 위임 판단 양성 1 · 음성 2(재귀 · 이름 없음)
[P20] 컨테이너 위임: gx-shell (호스트에는 `config` 패키지가 없다 · GX_ROUTE_CONTAINER · MinIO 자격은 안 넘긴다 — 컨테이너가 이미 들고 있다)
[P20] 자기시험 통과 — …           ← (컨테이너 안에서 다시 도는 그 프로세스 자신의 자기시험)
[P20] [입력] 시드 이벤트 23건 · 알림 규칙 8건
[P20]   발송 기록                  238행
[P20]   스냅샷 참조                 20건
[P20]   MinIO 목록 ↔ DB 참조       객체 20개 · 참조 20건 · 하나하나 이름으로 대조했다
[P20]   시스템 이벤트                2건 (기대 2)
[P20]   P-251 씨앗은 청구·KPI 0건    씨앗 23건 중 청구 셈에 남은 것 0건
[P20] 통과 — P-20 네 수가 전부 섰다
```
`docker exec ... gx-shell ...` 이 실제로 나갔다(줄 2), 안이 실제로 pytest·Django 를 다시
돌렸다(줄 3 — 자기시험이 컨테이너 안에서 한 번 더 찍힘)는 것이 위임이 **진짜**라는 증거다.

★ **A/B 실측 — `docker exec -e NAME`(값 없이) 은 호스트에 그 이름이 없으면 무해하지 않다.**
저장소의 기존 문(`verify_route_alive.delegate_to_container`)의 주석은 「호스트에 없으면
그냥 안 넘긴다(무해)」라고 적혀 있는데, 실측은 반대였다:
```
docker exec gx-shell sh -c 'echo -n "$MINIO_ACCESS_KEY" | wc -c'   → 20   (원래 값 길이)
docker exec -e MINIO_ACCESS_KEY gx-shell sh -c 'echo -n "$MINIO_ACCESS_KEY" | wc -c'
  (호스트 셸에 그 이름 없음)                                        → 0    (빈 값으로 덮였다)
```
**그래서 `delegate_to_container` 를 그대로 재사용하지 않았다** — 그 문은 MinIO 자격 이름
넷을 늘 `-e` 로 얹는데, `verify_seed_p20.py` 는 MinIO 자격을 os.environ 으로 안 읽는다
(Django 설정이 컨테이너 안에서 이미 들고 있는 값을 씀 · `collect()`). 그래서 이 파일
전용의 좁은 위임(`_delegate`)을 새로 뒀다 — 값 자체가 비밀이 아닌 `DJANGO_SETTINGS_MODULE`·
`PYTHONIOENCODING` 만 리터럴 값으로 준다. 이 A/B 는 `verify_route_alive.py` 소유자에게
쪽지로 넘긴다(§9).

### 3) `measure_onboarding_t.py` — 청구 배선 (가장 급한 것)

단위시험(브라우저 0 · 로그인 0 — Django 테스트 DB 만 씀):
```
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -w /app gx-shell python -m pytest tests/test_p237_onboarding_probe_billing.py -q --create-db -p no:randomly
```
```
..........                                                               [100%]
10 passed, 5 warnings in 23.69s
```
기존 billing_marks 시험과 함께(간섭 없음 확인):
```
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -w /app gx-shell python -m pytest tests/test_b_billing_marks.py tests/test_p237_onboarding_probe_billing.py -q --create-db -p no:randomly
```
```
41 passed, 5 warnings in 39.29s
```
`python -m py_compile scripts/measure_onboarding_t.py` → 통과(구문 오류 없음).

## ② 고친 파일:줄

- `scripts/verify_spec_coverage.py:257-283`(`kind_table()`) — `aa_kind_score_table()` 이
  준 5키 표에 `measured_red` 가 없으면, **같은 모듈**(`verify_ga_readiness`)의 거르기 전
  원본 `KIND_POINTS` 에서 그 한 값(0.0)만 마저 읽어 채운다. 새 눈금을 베끼지 않았다
  (D-369) — `verify_ga_readiness.py`·`verify_readiness_scores.py` 자체는 **이번 턴 소유표
  밖**이라 안 건드렸다(둘 다 §2 표에 임자가 없다).
- `scripts/verify_seed_p20.py`:
  - `+from pathlib import Path`(수입줄)
  - `345`: `_should_delegate(container, in_container)` — 순수 함수, 자기시험이 양성 1·
    음성 2(재귀 방지·이름 없음)로 잰다.
  - `350`: `_delegate(container, json_mode)` — 실제 `docker exec`(값이 아니라 이름을
    덮지 않는 좁은 집합만 리터럴로 준다).
  - `371`(`main()`): `load_local_env()`(호출만 · `verify_route_alive` 소유표 밖) →
    `_should_delegate` 로 갈라 `_delegate` 또는 기존 `collect()` 갈래.
  - `429` 근방(P-107 `target=`): 「호스트에서 부르면 docker exec 로 위임한다」(거짓) →
    「`GX_ROUTE_CONTAINER` 가 서 있을 때만 **실제로** 위임한다(코드로 있다) — 없으면
    `No module named 'config'` 로 판정 불가」(정직 + 참).
  - 자기시험에 위임 판단 양성/음성 3건 추가.
- `scripts/measure_onboarding_t.py`:
  - `307`: `_mark_probe_unbillable(app_label, model_name, pk, reason)` 새 함수 —
    `common.billing_marks.mark_unbillable` 을 호출만 한다(그 파일은 안 고쳤다).
  - `1928~1941`(U5#4 카메라 등록): `posts`/`c1` 로 성공을 확인한 **바로 다음 줄**에서
    `code=probe_cam` 으로 방금 만든 StreamMonitor 를 찾아 표식.
  - `2013~2027`(U5#1 계정 생성): `new_id` 를 읽은 **바로 다음 줄**(비활성화 클릭보다 앞)
    에서 `user.CoreUser` 를 표식.
  - 두 evidence 문자열에 `[청구] {mark_note}` 를 덧붙여 판정문에 성공/실패가 그대로 남게 함.
- `backend/tests/test_p237_onboarding_probe_billing.py`(신규 · 10개 시험) — 이 배선의
  시험 파일. `tests.test_b_billing_marks.BillingMarkFixture` 를 **재사용**(복제 안 함).

## ③ 안 한 것과 사유

- **카드 완료 서버 기록 시험 6 · U4③ 카드 열림 — 안 했다.** 지시서 §5 에 "시간이 남으면
  한다. 1~3 이 먼저다"로 적혀 있었고, 1~3(특히 3번 청구 배선 + 그 실측·시험)에 시간을
  다 썼다. 다음 차선/턴으로 넘긴다.
- **기존에 이미 떠 있는 청구 잔재(계정 id 227 · 카메라 16→17, WO-07 §5 가 실측)를
  소급 표식하지 않았다.** 지시받은 것은 "돌 때마다 느는 것을 막는 배선"이었고, 이미 떠
  있는 특정 행을 지금 수동으로 마킹하는 것은 다른 결정(어떤 pk 가 정말 그 계측기가
  만든 것인지 재확인 필요)이라 손대지 않았다 — 필요하면 `mark_unbillable("stream_monitors",
  "StreamMonitor", <pk>, "소급")` 한 줄로 되지만, pk 확정은 조율자/원 실측자 몫으로 남긴다.
- **`verify_route_alive.py`(`delegate_to_container`)의 landmine(위 A/B)을 고치지 않았다.**
  그 파일은 이번 턴 소유표 밖이다 — §9 쪽지로 넘긴다.
- **전량 시험을 내가 돌리지 않았다.** §1 규약이 "전량 1회"는 조율자 몫이라 적었다 —
  대신 내가 건드린 파일과 겹치는 기존 시험(`test_b_billing_marks.py`)만 같이 돌려 간섭
  없음을 확인했다(41 passed).

## ④ 청구 전/후 표 — 서버 기록(단위시험, 브라우저 0)

배선 전(고치기 전 상태 재현): U5#1/U5#4 블록에 `_mark_probe_unbillable` 호출이 없었다 —
계정·카메라가 **기본값 `live`** 로 남아 청구 셈(`apps.dsm.metering.usage()`)에 그대로 든다.
(이것이 바로 WO-07 §5 가 실측한 "계정 1 · 카메라 1 이 늘었다"는 상태다.)

배선 후 — 시험이 **같은 실행 안에서** 두 번 실제로 센 수(`test_p237_onboarding_probe_billing.py`):

| 대상 | 표식 전 청구 셈 | 표식 직후 청구 셈 | 행 자체(`data_source`) | 운영 화면 수 |
|---|---|---|---|---|
| 카메라(StreamMonitor, 새로 만든 것) | N | **N − 1** | `live` 그대로(안 고침) | 안 변함 |
| 계정(CoreUser, 새로 만든 것) | M | **M − 1** | (해당 없음 — dj-core, 곁표만 씀) | 안 변함 |

같은 행을 두 번 표식해도(`update_or_create`) 청구 셈이 또 안 줄어드는 것도 확인
(`test_calling_twice_does_not_double_count_or_raise`). pk 를 못 읽거나(`None`) 모르는
모델이면 표식하지 않고 실패를 문자열로 알린다(조용히 삼키지 않음 · 2개 음성 시험).

## ⑤ 내가 틀렸던 것

- 처음에 `verify_route_alive.delegate_to_container` 를 **그대로** 재사용하려 했다 —
  「이미 있는 문을 두 벌로 안 만든다(D-369)」는 규약을 곧이곧대로 따르려 한 것인데,
  A/B 로 재보니 그 문은 MinIO 자격 이름 넷을 조건 없이 `-e` 로 얹고, 호스트에 그 이름이
  없으면 컨테이너의 실제 값을 **빈 값으로 덮는다**(그 파일 자신의 주석 "무해하다"와
  반대). `verify_seed_p20.py` 는 애초에 MinIO 자격을 안 읽어서 이 landmine 을 안
  밟지만, 그 문을 그대로 가져다 썼다면 **다른 날 다른 호스트에서** 밟았을 것이다.
  실측 없이 "기존 문을 재사용하면 안전하다"고 넘겨짚을 뻔했다.
- `kind_table()` 을 고칠 때 처음엔 `verify_ga_readiness.py::KIND_SCORE` 의 필터를
  직접 없애고 싶었다(가장 "깨끗한" 수정처럼 보였다) — 그런데 그 파일은 이번 턴
  소유표에 없다는 것을 §2 를 다시 읽고서야 확인했다. 소유표를 먼저 대조하지 않고
  "더 깨끗해 보이는 수정"부터 고르려 한 것이 순서가 틀렸다.
