# S → 조율자 [턴 AF] — 가짜 헤더 회귀 게이트 신설(탐침 자체의 결함 2건 포함) · 접속기록 근거조문 확정 · 세 곳 정렬은 미완(소유표 밖)

## 요약
1. `probe_fake_bearer.py`(P-273의 「364·0건」을 낸 그 탐침)를 실측해 보니 **문서에
   적힌 그대로는 한 번도 돌 수 없었다** — 결함 둘을 찾아 고쳤다(아래 ①). 고친 뒤
   다시 재니 **정말로 364·0건**이었다. RC-1 판정기(`verify_release_candidate.py`
   S4)도 이 결함 때문에 **영구 회색**이었다는 것을 실측으로 확인했다(K+Q 몫이라
   고치진 않았고, 여기 적는다).
2. 회귀 게이트를 새로 세웠다: `scripts/gate_fake_bearer_regression.py` +
   `backend/tests/test_p273_fake_bearer_gate.py`. 음성 대조 둘로 **실제로 빨강이
   나는 것**을 증명했다(아래 ④).
3. 접속기록 보존기간 — 근거 조문을 확정해 `LEGAL_BASIS` 의 `[추정]` 을 지웠다.
   세 곳(730/365/90) 정렬은 **못 했다** — 안전성은 확인했지만 실제로 값을
   맞추려면 이 턴 내 소유표 밖 파일 둘을 만져야 한다(아래 §2).

---

## ① 실측 명령과 출력 그대로

### 1-a. `probe_fake_bearer.py` 를 문서에 적힌 그대로 불러 봤다 — 죽었다

```
$ MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings -w /app gx-shell \
    python /repo/scripts/probe_fake_bearer.py /tmp/fake_bearer.json

[FAKE-BEARER] **못 쟀다** — 환경을 못 세웠다: ModuleNotFoundError: No module named 'config'
[FAKE-BEARER] gx-shell 안에서 DJANGO_SETTINGS_MODULE 을 주고 -w /app 으로 부른다
```

원인 둘(둘 다 고쳤다 — `scripts/probe_fake_bearer.py:62-99` 머리말에 실측을 남겼다):
- **① `sys.path`** — `-w /app` 은 현재 디렉터리만 옮길 뿐, `django.setup()` 이
  찾는 `config` 패키지(`/app/config`)를 자동으로 얹지 않는다. 자매 탐침
  `probe_read_surface.py:849` 는 이미 `sys.path.insert(0, "/app")` 을 했는데
  여기 빠져 있었다.
- **② 더 심각한 것** — `P.measure(caller, method, url, principal, query)` 의
  다섯째 자리는 **질의값**이지 헤더가 아니다. 원래 코드
  (`P.measure(caller, method, url, None, {"Authorization": FAKE})`)는 그 글자를
  `?Authorization=Bearer+...` 로 **URL 뒤 질의 문자열**로 붙였을 뿐, 실제
  `Authorization:` HTTP 헤더는 **한 번도 실리지 않았다**(`Caller.call()` 은
  `token` 인자로만 그 헤더를 만든다 — `principal` 이 계속 `None` 이었다).
  즉 이전의 `anon` 호출과 `fake` 호출이 **완전히 같은 요청**이었다.

⇒ 「가짜 헤더 0/364」라는 수는 **원래 스크립트로는 물리적으로 나올 수 없었던
수**였다. 세종 판정 P-273(「분모·증거·회귀 게이트가 있어야 closed」)을 지키려면
먼저 이 결함을 고쳐야 했다.

### 1-b. 고친 뒤 다시 잰 결과 — 정말로 364 · 0건

```
$ MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings -w /app gx-shell \
    python /repo/scripts/probe_fake_bearer.py /tmp/fake_bearer.json

[P-107] TARGET=http://localhost:8000 (gx-shell 안에서 HTTP 로 때린다)
[P-107] AS=**없는 토큰** — 로그인하지 않는다 · 실계정·실토큰 0
[P-107] SOURCE=살아 있는 라우터 레지스트리(런타임 전수)
[P-107] MEASURED=읽기 면 전수를 **두 번** 때린다(익명 · 가짜 헤더) — **분모 364**(지금 셌다). ...
[FAKE-BEARER] [입력] 읽기 자리 364 · 20.5초
[FAKE-BEARER] 가짜 헤더로 **자료가 나온 자리 0** (그중 익명으로는 막히던 자리 **0**)
[FAKE-BEARER] 기록 → /tmp/fake_bearer.json
[FAKE-BEARER] 초록 — 가짜 자격증명으로 자료가 나오는 자리가 **0** 이다. 관문의 경계가 넓어도 그 뒤가 서 있다
```
```json
{"measured_at": "2026-09-23T14:10:20", "base": "http://localhost:8000",
 "total": 364, "elapsed_s": 20.5, "leaked": 0, "only_fake": 0, "rows_leaked": []}
```
증거: `docs/agent/evidence/P-270/fake_bearer_gate.json`(같은 값, 새 게이트로
낸 것 — 아래 ②).

### 1-c. 새 게이트 — 자기시험(도커 없이)

```
$ python scripts/gate_fake_bearer_regression.py --self-test
[P-273] [입력] 자기시험 facts 3개(흉내 · 실제 라우트 0개) — 도커·DB 없이 판정 규칙(judge_rows)만 잰다
[P-273] AS=**없는 토큰**(Bearer gx.nonexistent.probe.token.do-not-issue-this) · SOURCE=자기시험 흉내 facts(레지스트리 아님) · MEASURED=judge_rows() 순수 함수 하나
[P-273] 자기시험 통과 — 정상 갈래 2(401 · 공개선언) · 음성 대조 1(★ auth= 없는 자리를 빨강으로 잡았다: ['/api/fake/no-auth-oops'])
```

### 1-d. 새 게이트 — 실측(gx-shell 안, Django in-process, 로그인 0회)

```
$ MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings -w /app gx-shell \
    python /repo/scripts/gate_fake_bearer_regression.py /repo/docs/agent/evidence/P-270/fake_bearer_gate.json

[P-273] TARGET=Django in-process Client (gx-shell 안 · 로그인 0회 · localhost:8000 과 무관)
[P-273] MEASURED=읽기 면 전수를 가짜 헤더로 두드린다 — **분모 364**(지금 셌다). ...
[P-273] [입력] 읽기 자리 364 · 20.7초 · 자기시험 통과 뒤 실측
[P-273] 가짜 헤더로 **자료가 나온 자리 0**
[P-273] 초록 — 가짜 자격증명으로 자료가 나오는 자리가 **0** 이다
EXIT=0
```
★ HTTP 기반 탐침(1-b)과 Django in-process 게이트(1-d) **둘이 서로 다른 경로로
같은 수(364·0)를 냈다** — 한쪽만 쟀으면 그쪽의 버그를 못 잡는다.

### 1-e. pytest 정본 회차 (backend/tests 새 시험, gx-shell 안 -w /app)

```
$ MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings -w /app gx-shell \
    python -m pytest tests/test_p273_fake_bearer_gate.py -q -p no:randomly

........                                                                 [100%]
8 passed, 35 warnings in 285.10s (0:04:45)
```
⚠ **느리다(4~5분)** — 가짜 값이 JWT 모양이 아니라서 dj-core `CustomJWTAuth` 가
보호된 라우트마다 디코드 예외를 잡아 긴 traceback 을 로그에 찍는다(§0.4 이관
자산, 못 고친다). 판정 자체엔 영향 없다 — `logging.disable()` 로 그 구간만
죽였는데도 느린 것은 이 시각 옆 차선(예: `test_onboarding_progress.py`)이 같은
컨테이너에서 동시에 돌고 있어 CPU 를 나눠 쓰기 때문으로 보인다(단독 실행 시
`ps aux` 로 대조하지 못했다 — 회색으로 남긴다).

### 1-f. `common/log_retention_policy.py` 편집 뒤 소비자 재확인 (내가 안 건드린 파일들이 안 깨졌는가)

```
$ python scripts/ops_retention_policy.py --self-test
[P-230] 자기시험 통과 — 정상 1 · 음성 5 · 삭제손 대조 1 (제 소스에 지우는 손이 없다 ...)

$ python scripts/ops_retention_policy.py --evidence docs/agent/evidence/OPS-07/retention_marks_turn_af.json
...
| audit | 730일 | now() - 730 days | 0 | — |
표 전체 195,769행 · 가장 오래된 행 2026-08-27 13:28:44.947815+00:00
  OK   ① 선언             부류 3개가 임자·근거와 함께 선언돼 있다
  FAIL ② 선언↔집행          **갈렸다** — 선언 730일인데 dj-core 가 읽는 자리는 365일다. ...
[P-230] 삭제 실행 **0건**
판정 **실패**.
```
(② 는 원래도 실패였다 — 내가 새로 깨뜨린 게 아니라 그대로다. 아래 §2 참조.)

```
$ python scripts/verify_threshold_table.py --self-test
[THRESHOLD] 자기시험 15건 통과 (양성 7 · 음성 6 · 출생 표본 포함 · 계약 대조 D-336)
```
전체 실행(EXIT=1)은 저장소 전역에 82건의 미등재 매직 넘버를 낸다 — **그중
`log_retention_policy.py` 는 0건**(grep 대조). 내 편집이 새로 만든 빨강이 아니라
기존 백로그다(내 소유표 밖이라 손 안 댔다).

---

## ② 고친 파일:줄

| 파일 | 무엇을 |
|---|---|
| `scripts/probe_fake_bearer.py:62-99` | 결함 둘 수정 — ① `sys.path.insert(0, "/app")` 추가 ② `FAKE_PRINCIPAL`/`caller.tokens` 로 진짜 `Authorization` 헤더를 싣게 바꿈(질의값이 아니라) |
| `scripts/gate_fake_bearer_regression.py` | **신규.** 순수 판정기 `judge_rows()` + 자기시험(음성 대조 내장) + `collect_rows()`(Django in-process, 로그인 0회) + CLI(`--self-test` / 실측) |
| `backend/tests/test_p273_fake_bearer_gate.py` | **신규.** `pytest tests` 정본 회차에 들어가는 시험 8개 — 음성 대조 5개(judge_rows 단위) + 실측 3개(전수 364·분모 부작위 방지·data 칸 검증) |
| `backend/common/log_retention_policy.py:54-73` | `LEGAL_BASIS` 의 `[추정]` 을 제8조① 인용으로 교체 |
| `backend/common/log_retention_policy.py:115-129` | `POLICY["audit"].why` 에 2026-09-23 재확인(심긴 값 여전히 365) + 안전성 실측(파기 스위치 둘 다 꺼짐) 추가 |
| `docs/design/GX-LAW-09_접속기록_설계_v1.0.md` §5 | 항목 1 을 완료로 표시, 항목 5 신설(세 곳 정렬에 필요한 미배정 파일 둘을 명시) |

## ③ 안 한 것과 사유

- **세 곳(730/365/90) 정렬을 실제로 맞추지 않았다.** 이 턴 내 소유표는
  `common/log_retention_policy.py`(선언 — 이미 730과 일치) 한 파일뿐이다. 실제
  집행값을 365→730 으로 옮기려면:
  1. `backend/config/retention_seed.py` 의 `SEED["AUDIT_LOG_RETENTION_DAYS"]` 를
     365→730 으로 고치고
  2. `scripts/seed_retention_declaration.py --unseed` 로 심긴 365 를 지운 뒤
     `--apply` 로 730 을 다시 심어야 하는데(그 스크립트는 **이미 값이 있으면
     거부**하도록 설계돼 있다 — 남의 선언을 조용히 덮지 않으려는 안전장치),
  둘 다 **§2 소유표에 이 턴 임자가 없다.** 파일 하나 = 차선 하나 규약을 지키려고
  손대지 않았다. **안전성은 확인했다** — [실측 2026-09-23]
  `PeriodicTask(name="ops-audit-purge-daily").enabled=False` ·
  `PeriodicTask(name="purge-audit-logs-daily").enabled=False` 둘 다 꺼져 있다.
  지금은 365 든 730 이든 **아무 것도 안 지운다** — 365→730 은 늘리는 쪽이라
  스위치가 나중에 켜져도 그 사이 지워진 행은 없다. 다음 턴에 이 두 파일을
  누구 소유로 배정할지 정해 달라(⑤ 참조).
- **dj-core 코드 기본값(90)은 안 건드렸다** — §0.4 금지구역.
- **가짜 헤더 탐침을 쓰기(POST/PUT/DELETE) 면으로 넓히지 않았다** — 지시대로
  읽기 면만 쟀다. 넓히고 싶으면 별도 승인이 필요하다(제품 상태를 바꿀 수 있다).
- **실계정·실토큰을 쓰지 않았다** — 탐침도 게이트도 로그인 0회(HTTP 탐침은
  기존 `Caller` 로 로그인 없는 요청만, 게이트는 `django.test.Client` — 세션 자체가
  없다).
- `verify_release_candidate.py`(RC-1, K+Q 소유)의 S4 셀이 내 fix 로 회색을 벗을
  가능성이 높다는 것만 실측해서 적었다 — **그 파일은 내가 고치지 않았다**(K+Q
  소유표). 아래 ⑤에 적어 K+Q/조율자에게 넘긴다.
- **CI 성능**: 새 시험이 4~5분 걸린다(①-1e). dj-core 의 JWT 디코드 예외 로깅이
  원인이라 우리 층에서 근본 수정은 안 되고, `logging.disable()` 로 소음만
  줄였다. 필요하면 이 시험을 `slow`/`nightly` 마커로 분리하는 것도 방법인데,
  그건 시험 전략 결정이라 조율자 판단에 맡긴다.

## ④ ★★ 음성 대조가 빨강을 내는 출력 그대로

**방법 1 — 순수 판정기 자기시험** (①-1c 에 이미 실었다): `judge_rows()` 에
`auth=` 가 없다고 흉내 낸 facts 행을 먹여 정확히 그 행만 빨강으로 잡았다.

**방법 2 — 진짜 364행 + 흉내 낸 누출 행 1개를 섞음** (증거:
`docs/agent/evidence/P-270/negative_control.md`):
```
진짜 실측 행 수: 364

=== BEFORE(진짜 364행만) ===
leaked: 0 -> 게이트 판정: 초록

=== AFTER(가짜 누출 행 1개를 섞음) ===
leaked: 1 -> 게이트 판정: **빨강**
  · GET /api/fake/no-auth-planted-by-negative-control 200 ★ 음성 대조 — auth= 를 뺐다고 흉내 낸 자리(실제 라우트 아님, 섞어 넣은 행)
```

**방법 3 — 시도했으나 포기함(정직하게 적는다)**: 실제 라이브 라우트
(`/api/article`)의 `op.auth_callbacks` 를 프로세스 메모리에서 지워 "방금
auth= 를 뺐다"를 흉내 내려 했다. BEFORE/AFTER 모두 500(가짜 토큰이 JWT 모양이
아니라 `CustomJWTAuth` 디코드가 먼저 죽고, 그 자리는 `auth_callbacks` 유무와
무관해 보였다 — ninja_extra 디스패치가 그 속성을 실행 중에 다시 안 읽는 것
같다). 이 레버는 못 믿을 레버였다 — 그래서 방법 1·2 로 바꿨다.

## ⑤ 대장에 걸 절 이름·`gate:` 경로 제안 (대장은 E 소유라 여기 청한다)

```yaml
- id: P-273
  title: 가짜 Authorization 으로 읽기 면이 안 뚫린다 (회귀)
  gate: scripts/gate_fake_bearer_regression.py
  # 동반: backend/tests/test_p273_fake_bearer_gate.py 가 pytest 정본 회차에 상시 포함된다
```
추가로 청한다:
- `config/retention_seed.py` + `scripts/seed_retention_declaration.py` 를
  다음 턴 누군가에게 배정해 365→730 실제 정렬을 마쳐 달라(§③ 참조, 안전 확인 완료).
- `scripts/verify_release_candidate.py` S4 셀을 K+Q 가 다시 돌려 보게 해 달라 —
  내 fix 전에는 **구조적으로 영구 회색**이었다(①-실측: 문서 그대로 부르면 rc=2).
  fix 후 실측(RC-1 이 실제로 쓰는 호출 모양 그대로, `-w /app` 없이 default
  workdir=/app 확인 포함):
  ```
  $ docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
      sh -c "python /repo/scripts/probe_fake_bearer.py /tmp/gx_rc1_test.json; echo GXRC=$?"
  ...
  GXRC=0
  ```

## ⑥ 내가 틀렸던 것

- 처음엔 「auth= 없는 라우트 흉내」를 **실제 살아있는 라우트의 `auth_callbacks`
  런타임 조작**으로 하려고 했다. ninja_extra 내부 구조를 안다고 가정한
  지름길이었는데, 실측해 보니 그 속성이 디스패치 시점에 다시 안 읽히는 것
  같았고(BEFORE/AFTER 가 500 으로 똑같았다), 그 상태로 밀어붙였으면 「고쳤다」로
  거짓 보고할 뻔했다. facts 를 직접 먹이는 방법(순수 함수 시험)과 실제 수집
  결과에 가짜 행을 섞는 방법으로 바꾼 게 옳았다.
- P-273 의 「364·0건」이 이미 난 수라고 믿고 회귀 게이트만 얹으려 했었다 —
  탐침 자체를 실행해 보지 않았으면 **부러진 탐침 위에 게이트를 얹을 뻔했다**.
  실행 → `ModuleNotFoundError` 를 직접 본 뒤에야 방향을 바꿨다. "혼자 재면
  통과"를 걸러내려면 인용된 수치도 일단 내 손으로 다시 재봐야 한다는 것을
  다시 배웠다.
- `judge_rows` 자기시험 안에 `logging.disable` 최적화를 넣으면 시험이 훨씬
  빨라질 거라 기대했는데, 재측정해 보니(259s → 285s) 별 차이가 없었다 — 이
  시각 컨테이너 공유 부하가 더 큰 변수였던 것 같다. 성능 주장은 재지 않고
  적지 않는 게 맞았는데, 처음엔 "빨라질 것"이라고 적을 뻔했다.
