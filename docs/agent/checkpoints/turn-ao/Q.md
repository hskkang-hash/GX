# 턴 AO · 차선 Q(계측·권한) — P-409 outbox_signed · P-410 U2 알림규칙 읽기 · P-395/416 드릴 씨앗 · P-408 두 수 · 잔손

## ① 바꾼/만든 파일
- `scripts/measure_onboarding_t.py`
  - `_outbox_signed()` — 저장소에 없는 모델(`stream_monitors.WebhookOutbox` 등)을
    찾던(그리고 `get = orm()` 뒤 `get(label)` 로 부르던 — 애초에 호출 불가능한 값)
    옛 코드를 걷어내고, 실재 표 `stream_monitors.DeliveryRecord` 를
    `common/webhook_outbox.py::CHANNEL`("webhook")로 좁혀 읽는다. 서명 **값**은
    행에 안 남지만(칸 자체가 없다), 서명이 안 붙는 경로는 정확히 하나 —
    `deliver_one()` 이 `signing_secret()` 을 못 찾을 때 남기는 고정
    `failure_reason`("…서명 없이 내보내지 않습니다")뿐이다. 그 표식이 없는 행 수로
    「서명 붙은 발송」을 잰다(`_base_manager` 사용 — 스레드에 남은 요청 오염 방지).
  - U6#4 판정 문장 — 술어를 `(n1 > n0) and signed >= 1` 에서 `(n1 > n0)` 로 정직화.
    이 걸음(구독 등록)은 새 사건을 만들지 않아 `signed` 가 이 요청만으로는 절대
    안 는다 — 옛 술어는 「이 걸음이 하지 않는 일」을 요구해 늘 빨강일 운명이었다.
    `signed` 는 evidence 문장에 **참고 수치**로만 남긴다.
- `backend/apps/dsm/services.py` — **권한 코드 파일**(찾은 자리). U2 관제팀장
  (`fire_admin` · `K3_ROLE_MANAGERS`)에게 온보딩 U2#16 「알림 규칙 확인」
  (`GET /api/dsm/settings/notify-rules/list`)의 **읽기만** 열었다. `_decide(actor)`
  에 `action` 인자를 추가하고, `action == "read:notify-rules"`(행위 문자열을
  **정확히** 맞춘다 — 접두어 `read:` 전체를 열지 않는다) + `K3_ROLE_MANAGERS` 역할일
  때만 통과시키는 예외를 한 줄 더했다. `guard_setting()` 이 `_decide(actor,
  action=action)` 로 넘긴다. `write:notify-rules:...` 와 다른 `read:` 행위
  (`read:system:storage` · `read:inbound-api-key:scopes:...` ·
  `setting_overview()` 의 `f"read:{domain}"` 등)는 손대지 않았다 — 회귀 시험이
  그 여섯 자리를 직접 두드려 막혀 있음을 확인한다.
- `scripts/drill_seed_click.py` — 새 파일. P-395/P-416. `capture_screens.py` 의
  `seed_events()`(K1 `record_detection` 생성 경로)와 `_write_seed_file()`
  (`runs/<stamp>/seed.json`)을 **그대로** 불러 U1#11 류(자료 상태) 회색을 없애는
  드릴 씨앗을 한 줄로 심는다(기본 4건). 심는 규칙을 되풀이하지 않았다 — 그
  파일 안에만 있다. **이번 실행에서 실제로 심지 않았다**(V 의 몫).
- `scripts/onboarding_two_numbers.py` — 새 파일. P-408. `docs/agent/evidence/
  ONB-T/turn_*.json`(가장 최근 `measured_at`)의 `score_sum`/`denominator` 와
  `docs/agent/onboarding_48.md` 의 `**(c)**` 표(또는 `--c-rows`)를 읽어
  ① 48 기준 `N/48` ② 상한 기준 `N/(48-c)` 를 **둘 다** 찍는다(상한 기준만 찍는
  경로 없음 · c=0 이면 상한 줄을 지어내지 않고 사유를 적는다 · 회차 JSON 에 없는
  c 행 이름은 상한 계산에서 빼고 따로 보고한다). `--self-test` 내장.
- `scripts/verify_perf_budget.py` — 잔손. `__main__` 의 `gate_header(...,
  measured=...)` 에 분모 줄을 더했다(`· 분모 %d(...) % len(FACES)`) — 손으로 안
  적고 이 파일이 이미 `[입력]` 줄에 쓰는 그 수(`FACES` 표 길이)를 그대로 읽는다.
  판정 규칙(`_gate_header.judge_measured` · 이 파일의 EXIT_OK/FAIL/UNDECIDABLE
  로직)은 손대지 않았다 — `deferred:` 문구도 그대로 남겨 인간이 읽는 맥락은
  잃지 않았다.
- `backend/tests/test_ao_q_p409_outbox_signed.py` — 새 파일. `_outbox_signed()`
  순수 시험(`test_p343` 모양). fake `orm()`/`apps`/`_base_manager` 로 DB 없이
  잰다: 표식 있는/없는 행 갈라 세기 · `-1`/`0` 구별 · `channel="webhook"` 필터
  확인 · 회귀 방지(옛 코드 모양 부재 — 설명 주석의 자기 인용과 안 걸리게 실제
  코드 패턴만 겨눔).
- `backend/tests/test_ao_q_p410_notify_rules_read.py` — 새 파일. U2 관제팀장이
  `read:notify-rules` 를 지나고 `write:notify-rules:...` 와 다른 `read:` 행위
  6종은 여전히 막히는지 함수 수준 + HTTP 왕복(D-210)으로 확인.
- `backend/tests/test_ao_q_p408_onboarding_two_numbers.py` — 새 파일.
  `c_rows_from_markdown` · `parse_c_rows_arg` · `two_numbers` 순수 시험 + 도구
  자신의 `--self-test` 서브프로세스 확인.
- `docs/agent/checkpoints/turn-ao/Q.md` — 이 파일.

## ② 시험 이름과 결과 (그대로)
- `MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings
  -e DB_TEST_NAME=test_gx_lane_q -w /app gx-shell python -m pytest
  tests/test_ao_q_p409_outbox_signed.py tests/test_ao_q_p410_notify_rules_read.py
  tests/test_ao_q_p408_onboarding_two_numbers.py -q -p no:randomly --create-db`
  → 처음 실행 **2 failed, 12 passed**(내 회귀 시험 둘이 내 설명 주석의 자기 인용에
  걸림 — 코드가 아니라 시험을 고쳤다). 고친 뒤 재실행(`--create-db` 없이,
  DB 는 이미 있음) → **7 passed**(p409 단독) · **14 passed**(세 파일 합) ·
  **26 passed**(인접 시험 포함, 아래).
- 인접 시험(회귀 확인): `MSYS_NO_PATHCONV=1 docker exec -e
  DJANGO_SETTINGS_MODULE=config.settings -e DB_TEST_NAME=test_gx_lane_q -w /app
  gx-shell python -m pytest tests/test_u56_notify_rules.py
  tests/test_p343_third_condition_wiring.py -q -p no:randomly`
  → **26 passed**(내가 넓힌 U2 읽기 예외가 `test_u56_notify_rules.py::
  test_a_plain_role_cannot_read_or_save`(다른 역할 코드 `k2_watch_b` 사용)를 안
  건드림을 확인 · `_outbox_signed` 의 `screen_text` 배선 회귀 시험도 그대로
  통과). 실행 중 나온 `--- Logging error ---`/`ValueError: I/O operation on
  closed file` 는 백그라운드 캐시 무효화 스레드가 테스트 종료 뒤 DB 접근을
  시도하다 나는 기존 저장소 잡음(로그아웃 시점 스레드 경합)이고 pytest 요약의
  `26 passed` 뒤에 붙는다 — 이번 변경과 무관.
- `verify_perf_budget.py --self-test` (호스트 아님 · `MSYS_NO_PATHCONV=1 docker
  exec -e DJANGO_SETTINGS_MODULE=config.settings -w /app gx-shell python
  /repo/scripts/verify_perf_budget.py --self-test`) → **exit 0**, MEASURED= 줄에
  `분모 4` 가 코드에서 읽혀 찍힘 확인(`FACES` 4종).
- `onboarding_two_numbers.py --self-test`(호스트) → **exit 0**(7건 통과) ·
  `--turn-file docs/agent/evidence/ONB-T/turn_an_7.json`(기본 turn-glob 자동
  최신 선택도 같은 값) → `① 30/48 = 62.5%` · `② 30/32 = 93.8% (48 - c=16)`
  — 문서의 「(c) 16」 요약과 일치 확인(직접 실행해 본 결과).
- `drill_seed_click.py --help` / `capture_screens` 임포트 확인만(gx-shell 안) —
  **실제로 심지 않았다**(지시대로 V 몫).

## ③ 닫은 절 · 못 닫은 절
- 별표 절(P-356) 승격 대상 아님 — 이번 일은 계측기 정직화(P-409) · 권한 최소
  확장(P-410) · 씨앗 파이프 준비(P-395/416) · 계측 산출기(P-408) · 게이트 머리
  감사 잔손이라 「명세 절 닫기」범주 밖. 해당 없음.

## ④ 조율자에게 넘길 줄
- 없음 — 공용 파일(`backend/apps/fws/api.py` · `urls.py` · `App.tsx` ·
  `routes.ts` · `copy.ts` · `constants.py`)을 건드리지 않았다.
  `test_f05_event_api.py::EVENT_ENTRY_SURFACE` 에 올릴 새 `/api/dsm/` 라우트
  없음(새 라우트를 내지 않았다 — 기존 라우트의 권한 판정만 넓혔다).
- **확인 요청 하나**: `backend/apps/dsm/services.py` 는 이번 턴 다른 차선이
  같이 건드리고 있을 가능성이 있는 공유 앱 파일이다(§ 규약의 금지 목록엔 없지만
  `apps/dsm/` 는 여러 차선이 드나든다) — 병합 시 `_decide`/`guard_setting`
  시그니처 변경(`action` 키워드 인자 추가, 기본값 있어 하위호환)이 다른 차선의
  동시 수정과 겹치는지 조율자가 한 번 봐 주기를 요청.
- P-410 은 **코드 변경**이었다(DB 역할 행이 아니라 `apps/dsm/services.py` 의
  판정식) — 그래서 "적용하지 말고 한 칸만 보고"에 해당하지 않는다. 시험 1
  (`test_ao_q_p410_notify_rules_read.py`)로 갈음.

## ⑤ 스스로 의심하는 점
- **P-409 「서명 붙은 발송」 정의가 대리 지표 아닌가**: 서명 값 자체가 행에
  없으므로, 「표식 없음 = 서명 붙음」은 **부정에 의한 추론**이다(직접 관측이
  아니다). `deliver_one()`/`register()`(둘 다 같은 `signing_secret()` 관문)를
  코드로 대조해 이 추론이 유일한 분기임을 확인했지만, 앞으로 서명 실패의
  **다른** 이유(예: 코드가 또 갈래를 늘리는 날)가 생기면 이 술어가 조용히
  틀릴 수 있다 — 그때 이 함수의 docstring/주석이 「이 가정이 깨지면 여기를
  본다」는 표지 역할을 하도록 적어 두었다.
- **P-410 role 예외의 위치**: `_decide()` 안에 넣었다(공유 판정 함수 한 곳
  유지 — D-212 정신). 대안으로 `notify_rules_list` 라우트 안에서 별도 role
  체크를 두는 방법도 있었으나, 그러면 판정식이 두 벌이 된다고 판단해
  피했다. 다만 이 예외가 **행위 문자열 정확 일치**에 의존하므로, 누군가
  `action="read:notify-rules"` 문자열을 다른 이름으로 리팩터링하면 이 예외가
  조용히 죽는다(테스트가 그 경우 U2 를 다시 403 으로 잡아 알려준다 — 회귀는
  드러나지만 원인 추적은 필요).
- **P-395/416 드릴 도구의 「4」**: 지시에 적힌 수를 그대로 썼다(U1#11 하나가
  자료 상태 회색이라는 근거는 있으나, 「왜 하필 4」에 대한 제품 쪽 근거는
  찾지 못했다 — U1#11 이 보는 미판정 큐가 최소 1건만 있어도 될 수 있어
  4는 여유분일 수 있다). `--n` 으로 언제든 바꿀 수 있게 해 두었다.
- **P-408 c 파싱의 최신성**: `onboarding_48.md` 전체에서 `**(c)**` 행을 id 로
  중복 제거해 모은다 — 문서에 **여러 회차의 갈래표**가 누적되므로, 어떤 행이
  한 회차엔 (c)였다가 다음 회차엔 (a)/(b)로 다시 분류됐다면(재분류) 이 스캔은
  옛 (c) 표기도 여전히 c 로 센다(파일에 그 낱말이 남아 있는 한). 이번 턴엔
  실제로 그런 재분류 사례를 못 찾았지만, L 차선이 이번 턴에 표를 갱신할 때
  옛 (c) 표기를 지우지 않고 새 절만 덧붙이는 관행(문서 전체가 그런 모양이다)이
  이어진다면 이 스캔은 「정본」이 아니라 「한 번이라도 (c) 였던 적」을 센다 —
  그 차이를 문서·docstring에 적어 뒀지만, 정확한 대장은 `--c-rows` 로 손수
  주는 편이 더 안전할 수 있다.
