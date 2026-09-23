# K+Q(판정기) → 조율자 · 턴 AF · 2026-09-23(기계)

## ① 실측 명령과 출력 그대로

### 1) U2#3 술어 강화 — `measure_onboarding_t.py`

바꾸지 않았다(브라우저를 이 차선이 재지 않는다는 §1 규약) — **구문·단위 확인만** 했다:
```
python -m py_compile scripts/measure_onboarding_t.py
```
```
(무출력 — 통과)
```

`audit_count_for()` 를 고치며 발견한 것(고치기 전에는 이 함수가 **모든 사건에 대해
언제나 -1** 을 냈다 — U2#3 의 새 술어가 그대로 쓰면 절대 초록이 안 났을 것이다):
```
cd guardianx-source && MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings -w /app gx-shell python -c "
import django; django.setup()
from django.apps import apps
AL = apps.get_model('logger','AuditLogs')
names = sorted({f.name for f in AL._meta.get_fields()})
print('FIELDS', names)
"
```
```
FIELDS ['access_type', 'access_type_text', 'action', 'action_text', 'api_method',
'api_name', 'client_ip', 'command', ... , 'id', ... ]   ← event_id·object_id·target_id 없다
```
사건 4802 의 실측 두 행(조율자가 어제 누른 것):
```
340014 {'api_name': 'severity:set:4802', 'data_before': {'severity': 'critical'},
        'data_after': {..., 'severity': 'warning', ...}, 'note': 'U-on diagnostic test — will revert'}
340015 {'api_name': 'severity:set:4802', 'data_before': {'severity': 'warning'},
        'data_after': {..., 'severity': 'critical', ...}, 'note': 'U-on diagnostic revert'}
```
⇒ 사건 id 는 표의 열이 아니라 **`api_name` 문자열의 접미사**(`f"{동사}:set:{event_id}"`)
에 실린다. `audit_count_for()` 를 `api_name__endswith=f":{event_id}"` 로 다시 썼다(고친
뒤 재확인): `audit_count_for(4802) = 4`(340014·340015 + 과거 실측 2건).

사건 4802 **현재 상태 재확인**(내가 손대지 않았다 — 조율자가 어제 이미 되돌렸다):
```
docker exec gx-shell python -c "...DE.filter(pk=4802).values('severity')..."
→ {'pk': 4802, 'severity': 'critical', 'response_state': 'closed'}
```
**심각(critical) 그대로다 — 되돌려져 있다.** 이 턴에 내가 그 사건을 누르지 않았다
(§1 규약 — 차선은 브라우저를 안 잰다. 실물 클릭·검증은 조율자 몫).

### 2) `verify_route_alive.py` 늙은 주석 + 자기시험

```
python scripts/verify_route_alive.py --self-test
```
```
[P-107] TARGET=http://localhost:8000 (gx-shell 안 · 호스트에 포트가 없다)
...
[ALIVE] 자기시험 통과 — 판정 규칙 8종 + 출생 표본 /api/dsm/events 500 + 출생 표본 ②
토큰 먹통 24/26 401 + 로그인 판독 양성1·음성2 + 자기표본 /api/dsm/events +
`-e NAME` A/B 재확인(빈 값으로 덮음 — 주석과 일치)
EXIT=0
```
음성 대조(고장 낸 버전을 강제로 통과시키면 자기시험이 잡는가):
```python
m._selftest_dash_e_blanks_missing_name = lambda: 'FAKE MISMATCH — docker no longer blanks it'
m.self_test()
```
```
[ALIVE] 자기시험 실패:
    FAKE MISMATCH — docker no longer blanks it
RC= 1
```
잡는다.

### 3) RC-1 판정기(`scripts/verify_release_candidate.py`) — 실물 실행

```
python scripts/verify_release_candidate.py --json /tmp/gx_rc1_out2.json
echo "REAL_EXIT=$?"
```
(요약 — 전문은 스크립트를 다시 돌리면 그대로 나온다):
```
[RC1] [입력] RC-1 칸 분모 13(세 수 3 · 기능명세 1 · 상용 1 · S1~S7 7 · 전량 1) · 잰 칸 7
[RC1] FC 63.5[잰 칸 2/3] · PR 51.6[잰 칸 1/4] · CR 31.2[잰 칸 8/8]
[RC1] 기능명세 포함 완료율 27.5%(분모 291)
[RC1] 상용 /100 회색 — 8영역 게이트를 못 불렀거나 kind 합을 못 냈다
[RC1] S1 [○ red] 첫 근무일에 제 일이 끝난다 — 29.0/48 (60.4%) · 문턱 ≥90%
[RC1] S2 [○ red] 누르면 끝난다 — 초록 32 · 빨강 2 · 회색 14 / 48 · 문턱 ≥44/48
[RC1] S3 [○ red] 아무도 없는 아침에 서 있다 — OPS-19 FAIL(호출자 'beat' 아님) ·
      OPS-04 OK(11.4시간 전 덤프) · 재부팅 10/10 은 이 판정기가 안 잰다(대표 손)
[RC1] S4 [◐? gray] 틀린 것을 틀렸다고 말한다 — 가짜 헤더 경계: 분모 364 · 자료
      나온 자리 0 · 나머지 둘은 안 잰다
[RC1] S5 [◐? gray] 밖에서 닿는다 — 코드 게이트 없음(인용만)
[RC1] S6 [◐? gray] 청구서가 정직하다 — 코드 게이트 없음(인용만)
[RC1] S7 [◐? gray] 종이가 나간다 — 코드 게이트 없음(인용만)
[RC1] 전량 시험: **회색** — 기본으로 안 돈다(비용) · --full-tests 로 켜라
[RC1] ── 빨강 목록(3건) — 등재 ──
[RC1] ── 회색 목록(10건) — 등재 ──
[RC1] `rc-1-internal` 태그: 안 선다 — 전량 시험을 못/안 쟀다 — 태그 조건 ①이 안 선다
REAL_EXIT=2   ← (host 셸에서 $? 를 직접 읽었다 — | tail 함정 피함)
```
자기시험 + 음성 대조(태그를 항상 `True` 로 바꾸면 잡히는가):
```
python scripts/verify_release_candidate.py --self-test
[RC1] 자기시험 통과 — cell() 판정값 검사 · S1 문턱 4종 · S2 「안 쟀다」 구분 3종 ·
S3/S4 결합 규칙 2종 · 태그 음성 대조 4종(회색·실패·0실패·무관 원칙)
```
```python
m.decide_tag = lambda full: (True, '항상 초록')
m.self_test()
```
```
[RC1] 자기시험 실패:
    태그: 전량 시험을 안 돌렸는데(회색) 태그가 섰다 — 회색을 초록으로 셌다
    ★★ 태그: 전량 실패 3건인데 태그가 섰다 — ... 뚫렸다
```
잡는다.

### 4) 카드 완료 서버 기록 시험 6(+ 격리 대조 3)

```
docker exec -e DJANGO_SETTINGS_MODULE=config.settings -w /app gx-shell \
  python -m pytest tests/test_onboarding_progress.py -q --create-db -p no:randomly
```
1차(고치기 전 — 세 곳이 진짜로 죽어 있었다는 증거):
```
FAILED ...OnboardingU1ReviewAndHandoverCardsTest::test_a_handover_note_closes_the_handover_card
FAILED ...OnboardingU5AddressRecipientRetentionCardsTest::test_a_declared_retention_closes_the_retention_card
FAILED ...OnboardingU6InboundKeyCardTest::test_another_tenants_key_does_not_close_my_card
3 failed, 62 passed, 36 warnings in 442.60s
```
고친 뒤(전량 재실행):
```
65 passed, 35 warnings in 209.67s (0:03:29)
PYEXIT=0
```

## ② 고친 파일:줄

- `scripts/measure_onboarding_t.py`
  - `327~345`(`audit_count_for`): `event_id`/`object_id`/`target_id` 열이 **표에
    아예 없어** 언제나 -1 이던 것을, 실측한 `api_name` 접미사(`":{event_id}"`)로
    세게 고쳤다. 이걸 안 고치면 U2#3 의 새 술어가 **절대로 초록이 안 난다.**
  - `1078~1157`(U2#3): 「자리가 있다」 술어를 지우고 **「눌렀다 → [서버 기록]
    severity 변경 + 감사 행 증가 → 되돌린다」**로 바꿨다. `press(sev_key)` 도우미가
    단추 「{아이콘} {라벨}」을 누르고 `Modal.confirm` 의 okText 「등급 재판정」을
    누른 뒤 `POST /events/{id}/severity` 200 을 확인한다. 바뀌었으면 **함수 안에서**
    원래 등급으로 되돌리고 되돌아간 것까지 evidence 에 적는다.
- `scripts/verify_route_alive.py`
  - `458~471`(`delegate_to_container` 의 `-e` 목록 주석): 「이름이 없으면 무해」 →
    실측 A/B 결과(길이 20→0)를 그대로 옮겨 적었다.
  - `277~325`(신설 `_selftest_dash_e_blanks_missing_name`): `MINIO_ACCESS_KEY`
    (LOCAL_ENV_KEYS 밖이라 이 프로세스도 오염 안 됨)로 `docker exec` 두 번을 직접
    때려 「덮어 지운다」를 **다시 잰다.** docker·컨테이너가 없으면 회색(`None`),
    표본이 오염됐으면도 회색 — 실패로 안 적는다.
  - `392~403`·`414~420`(`self_test`): 위 함수를 불러 어긋나면 `bad` 에 얹고, 맞으면
    통과 줄에 한 문구를 덧붙인다.
- `scripts/verify_release_candidate.py` — **신규**(RC-1 판정기). 구조는 ①번 출력
  참조. `verify_readiness_scores.aa_report()`·`verify_spec_coverage.measure()`·
  `verify_backup_autonomy.run()`·`verify_backup_recovery.run()` 를 **import** 로
  부르고(D-369), S4 만 `probe_fake_bearer.py` 를 gx-shell 안에서 `docker exec` 로
  부른다. `decide_tag()` 의 유일한 문턱은 **전량 시험 실패 0**(P-269) — S1~S7 의
  빨강·회색은 태그를 막지 않는다.
- `backend/tests/test_onboarding_progress.py` — 파일 끝(구 875행 뒤)에 세 클래스
  신설: `OnboardingU1ReviewAndHandoverCardsTest`(2+1) ·
  `OnboardingU5AddressRecipientRetentionCardsTest`(2+2) ·
  `OnboardingU6InboundKeyCardTest`(2). `_closed_by_my_review`·`_closed_by_handover`·
  `_closed_by_address_gap`·`_closed_by_critical_recipients`·`_closed_by_retention`·
  `_closed_by_inbound_key` — 이 여섯이 기존 875행 파일 **어디에도 이름으로 안 걸렸다**
  (grep 으로 확인 — 나머지 여덟 술어는 이미 걸려 있었다). 제품 문(커널·서비스 공개
  함수: `services.review_event`·`issue_key`·`override_settings` 등)으로 서버 기록을
  만들고 「전엔 안 닫힘 → 기록 생기면 닫힘(+source_ref)」을 잠갔다.

## ③ 안 한 것과 사유

- **U4③ 카드 열기(「검색한 사실을 서버에 남긴다」)는 안 했다.** `_규약.md` §3 K+Q
  둘째 줄에 있지만, 내게 온 직접 지시(네 일 넷)에는 없었고 — 그걸 하려면
  `backend/apps/dsm/onboarding.py`(카드 표 + 새 `_closed_by_search` 술어)와 아마
  `api.py`(검색 API 에 감사를 남기는 배선)를 고쳐야 하는데 **둘 다 이번 턴 내
  소유표 밖**이다(§2 표: 내 것은 `measure_onboarding_t.py`·`verify_readiness_scores.py`·
  `verify_route_alive.py`·RC-1 새 파일·카드 시험 파일뿐). 대신 이번 시험 여섯으로
  「U4③ 이 왜 아직 열려 있지 않은가」의 **다른 여섯 카드**(이미 열려 있었어야 하는데
  시험이 없어 회귀를 못 잡던 것들)를 잠갔다. U4③ 을 열려면 onboarding.py 임자에게
  쪽지가 필요하다 — 검색 API(`GET /api/dsm/events?...`)가 검색을 감사에 남기게
  할지(비용 — 조회마다 쓰기가 는다), 남기지 않고 계속 BLOCKED 로 둘지는 제품 판단이다.
- **RC-1 의 S5·S6·S7 을 못 채웠다.** 그 수를 내는 코드 게이트가 이 저장소에
  아직 없다(지어내지 않았다 — 09-21 리뷰 문서 문장을 **인용만** 하고 회색으로
  뒀다). S6 의 「씨앗 청구 0」은 `test_p237_onboarding_probe_billing.py` 가 이미
  재지만 RC-1 이 다시 돌리면 `--full-tests` 와 중복이라 안 돌렸다.
- **RC-1 의 「상용 /100」이 지금 회색이다.** `verify_ga_readiness --static`(로그인
  없는 정적 갈래)으로 불러서 `kind_total`/`ga_total` 계산에 필요한 영역 kind 줄을
  못 얻었다 — 로그인 있는 창에서 조율자가 돌리면 이 칸이 설 것이다(코드는 그대로
  두면 자동으로 선다 · 손대지 않았다).
- **RC-1 의 `--full-tests` 를 내가 이번에 직접 돌리지 않았다** — 전량은 조율자
  몫(§1 규약)이라 기본값(회색·생략)으로 실행 결과를 보여만 줬다. 조율자가
  `--full-tests` 를 붙여 한 번 돌리면 `rc-1-internal` 태그가 실제로 서는지까지
  나온다.
- **U2#3 의 실물 클릭도 내가 안 했다**(§1 규약 — 차선은 브라우저를 안 잰다).
  코드는 고쳤고 구문·되돌림 상태만 확인했다 — 실제로 초록이 나는지는 조율자가
  `measure_onboarding_t.py --only U2` 로 재야 한다.

## ④ RC-1 판정기가 지금 내는 수 · 회색 칸 목록

**세 수**: FC 63.5[2/3] · PR 51.6[1/4] · CR 31.2[8/8] · 기능명세 포함 27.5%(분모 291) ·
상용 /100 **회색**.

**S1~S7**:
| 칸 | 색 | 근거 |
|---|---|---|
| S1 | 빨강 | 29.0/48(60.4%) < 문턱 90% |
| S2 | 빨강 | 초록32·빨강2·회색14/48 < 문턱 44 |
| S3 | 빨강 | OPS-19 FAIL(호출자 'beat' 아님) — OPS-04 는 OK 지만 섞지 않는다 |
| S4 | 회색 | 가짜 헤더 0/364 는 쟀다(양호) · 감사체인·시험자료 두 조건은 안 쟀다 |
| S5 | 회색 | 코드 게이트 없음(인용만) |
| S6 | 회색 | 코드 게이트 없음(인용만) |
| S7 | 회색 | 코드 게이트 없음(인용만) |
| 전량 | 회색 | 기본으로 안 돌림(`--full-tests` 로 켬) |

**태그**: `rc-1-internal` **안 섰다** — 유일한 문턱(전량 0실패)을 아직 안 쟀기 때문
(회색이지 실패가 아니다). 조율자가 `--full-tests` 로 한 번 돌리면 그 자리에서
태그 여부가 정직하게 난다.

## ⑤ 조율자가 돌려 줄 명령

```
# RC-1 전체 태그까지 보려면(분 단위)
python scripts/verify_release_candidate.py --full-tests --json docs/agent/evidence/RC1/turn_af.json

# U2#3 실물(브라우저) — 강화된 술어가 실제로 초록/빨강을 내는지
python scripts/measure_onboarding_t.py --only U2
```
브라우저 계정·주소는 기존 규약 그대로(§1) — U2#3 은 `/dsm/events/{snap_event or seed_a}`
에서 지금 등급이 아닌 버튼(예: 「▲ 경계」)을 누르고 확인창 「등급 재판정」을 누르면
된다. 초록이면 **자동으로 원래 등급까지 되돌아가 있다**(함수 안에서 되돌림).

## ⑥ 내가 틀렸던 것

- 처음에 U2#3 술어를 고치면서 `audit_count_for()` 를 **그대로 재사용**하려 했다 —
  코드가 이미 있으니 됐다고 넘겨짚을 뻔했는데, 실측해 보니 그 함수는 이 저장소의
  실제 `logger.AuditLogs` 스키마(열 38개 · `event_id`/`object_id`/`target_id` 없음)
  와 안 맞아 **언제나 -1** 을 내고 있었다. 새 술어가 그 값을 게이트 조건으로 쓰므로,
  고치지 않았으면 「강화한 술어」가 실은 **절대 못 여는 문**이 됐을 것이다 — A/B로
  직접 찍어 보고서야 알았다.
- `test_onboarding_progress.py` 끝에 정체를 알 수 없는 한 줄
  (`self.assertEqual(1, body["kick"]["done"])`, 정의 안 된 `body` 참조)이 파일 맨
  끝에 남아 있었다 — 내가 새 테스트를 이어 붙인 뒤에야 pytest 가 `NameError`로
  잡았다. 어디서 왔는지 확정 못 했다(내가 쓴 `new_string` 에는 없던 줄이다) —
  지우고 넘어갔다. 혹시 다른 차선이 같은 파일을 건드릴 계획이 있었다면 쪽지 바란다.
- RC-1 S3/S4 의 결합 규칙(「재는 부분이 빨강이면 행도 빨강, 아니면 회색」)을 처음엔
  「셋 다 초록이면 초록」으로 짤 뻔했다 — 그러면 재부팅 10/10 을 못 재면서도 S3 가
  초록이 되어 **「내부 RC」의 뜻을 배반**한다. 자기시험에 그 규칙 전용 음성 대조
  둘을 넣고 나서야 명시적으로 고정했다.
