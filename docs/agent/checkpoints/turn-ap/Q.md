# 턴 AP · 차선 Q(산출기 · 씨앗 · 술어) — 2026-09-29

시험 DB: `test_gx_lane_q`. 지금은 온보딩 여덟째·아홉째 회차 **사이**다(판정기 고침
허용 · 라이브 측정 금지) — 이 차선의 모든 코드 고침은 **가설**이고, 실제로 색이
바뀌는지는 다음 V 회차가 잰다.

---

## 1. P-422 — `onboarding_two_numbers.py` 기본값이 거짓 초록을 냈다

**무엇이 문제였나**: 인자 없이 부르면 `onboarding_48.md` 전체(여러 재측 절 누적)를
자동으로 훑어 그 문서의 모든 `**(c)**` 행을 모았다 — 실측 30/48 을 30/32(93.8%)로
찍었다. 이 문서는 절이 쌓이는 장부라, 자동으로 다 모으면 이번 회와 무관한 옛 절의
(c) 행까지 상한을 깎는다.

**고침**: `resolve_c_rows()` 순수 함수를 새로 두어 c 의 출처를 셋으로 가른다 —
① `--c-rows`(손으로 줌) ② `--c-from-ledger`(명시로 장부를 읽으라고 시킴) ③ 둘 다
없으면(기본) **c 미명시**로 회색을 찍고 숫자를 지어내지 않는다. `main()` 은 이제
`--c-from-ledger` 를 안 주면 `onboarding_48.md` 를 **절대 안 읽는다**(read 함수
자체를 주입해 자기시험이 "안 불림"을 스파이로 확인). `render()` 도 회색 줄에
c 출처 문장을 같이 적도록 고쳤다(종전엔 c=0 사유만 적혀 「c 미명시」와 「표를
봤는데 없더라」가 구별 안 됐다).

**자기시험 짝**(요청대로): `_self_test()` 에 기본 호출이 상한 수를 내면 실패하는
검사를 심었다(장부 읽기를 하면 예외를 던지는 스파이 + 기본 결과가 `by_cap=None`
인지 확인) — 미래에 누가 기본 경로에 장부 읽기를 도로 넣으면 `--self-test` 가
바로 빨개진다.

실측(호스트):
```
python scripts/onboarding_two_numbers.py --turn-file docs/agent/evidence/ONB-T/turn_an_7.json
  → ① 30/48=62.5% ② 회색·c 미명시(옛 93.8% 안 나옴)
python scripts/onboarding_two_numbers.py --turn-file ... --c-from-ledger
  → ① 30/48=62.5% ② 30/32=93.8%(48-c=16) — 옛 동작을 명시로 재현(회귀 없음 확인)
```

---

## 2. P-426 — `drill_seed_click.py --unjudged`

`seed_events()`(K1 `record_detection`)은 애초에 `verdict` 를 안 준다 — 새로 심은
사건은 태생적으로 미판정이다. 그런데 U1#11(`verify_click_completes.py`)의
「미판정 사건 없음」 회색은 실제로 반복해서 났다(다른 프로세스가 먼저 판정했거나,
심은 것 밖의 사건만 보였거나). `--unjudged` 는 **심는 규칙 자체는 안 바꾸고**
(기본값 불변 — 옵션 없이는 종전과 똑같다), 심은 뒤 DB 를 다시 읽어 `verdict` 가
실제로 비었는지 확인하는 **검증 단계**를 더한다. 그 잣대는
`verify_click_completes.py` 의 U1#11 표본 판정과 **글자 그대로 같은 잣대**
(`not e.get("verdict")`)를 쓴다 — 소스 문자열 대조로 두 파일이 갈리면 시험이
먼저 안다.

실제로 심지는 않았다(V 몫) — `--help` 만 gx-shell 안에서 확인.

---

## 3. P-425 — `measure_onboarding_t.py` U3#1(알림 수신) 술어 — 발신자=수신자 가정 제거

**무엇이 거짓이었나**: 종전 술어는 「알림 보내기」를 누른 **그 계정 자신**의
`/m/inbox` 화면 본문에 사건 카드(`#{seed_a}`)가 보이는지를 봤다 — u3 가 보낸다고
u3 자신이 그 사건의 수신자라는 보장은 없다(수신자는 `NotificationRule` 이 따로
정한다). U3#19(같은 파일)가 이미 실측해 적어 둔 이 화면의 정본은
`GET /api/dsm/deliveries?...&mine=true` 다.

**고침**: 카드 문자열 대조를 걷어내고, `/m/inbox` 가 실제로 `mine=true` 호출을
했는지로 술어를 바꿨다. 서버 기록이 실제로 늘었는지(`before`/`after` DB 직접
조회 — 수신자가 누구든 안 갈린다)는 그대로 유지. 근거는 코드 줄 주석(P-425 표식)
으로 남겼다.

**짝 시험**: `rows_u3()` 는 900행 넘는 Playwright 드라이버라 전체를 세우지 않고,
`out.append()` 가 U3#1 결과를 받는 **첫 호출**에서 멈추는 리스트로 U3#1 까지만
돌린다(모듈 전역 `goto`/`body`/`visible_text`/`delivery_count`/`result` 를 가짜로
갈아 끼운다). 카드 문자열이 전혀 없어도 `mine=true` 호출이 있으면 초록,
`mine=true` 가 없으면 카드 문자열이 있어도(옛 방식이면 초록이었을 상태) 더 이상
초록이 아님을 확인 — 이것이 "가정을 실제로 걷어냈는지"의 핵심 검증이다.

---

## 4. P-423 — `verify_click_completes.py` 「누를 자리 미선언」 9행

L(차선 L)이 `docs/agent/checkpoints/turn-ap/L.md` §1-A 에서 9행 중 5행에
`data-gx` 를 새로 달았다(나머지 4행은 결정 잠금이라 선언 없음). 그 표를 보고
5행의 **누를 자리 · 술어**를 채웠다.

### 4-A. 판정기에 더한 것(공용 메커니즘 — `gx` 없는 기존 40여 행은 안 갈린다)
- `btn(name, gx=None)` — L 이 단 `data-gx` 선택자를 함께 실을 수 있게.
- `find_control()` — `gx` 가 있으면 **그 선택자를 먼저** 본다(같은 글자 단추가
  화면에 둘 있어 텍스트만으로 못 가르던 문제의 고침 — 예: `CameraAddress.tsx` 의
  행별 「채우기」 vs 「아직 없는 카메라」 카드의 같은 글자 단추). 못 찾으면
  텍스트로 물러난다 — `gx` 없는 행은 이 변경으로 한 글자도 안 갈린다.
- `press(name=None, gx=None, wait_ms=1500)` + `prepare_steps()` 의 새 갈래
  `"button_prepare"` — **준비 단계에서 버튼을 누른다**(종전엔 드롭다운·글상자만
  가능했다). `CameraImport.tsx`(예시 채우기 → dry-run)처럼 메인 클릭 **전**에
  버튼을 눌러야 다음 단추가 DOM 에 나타나는 자리에 쓴다.
- `fill_label(label, text)` + `prepare_steps()` 의 새 갈래 `"fill_label"` —
  `put()` 은 `placeholder` 로 찾는데, `People.tsx` 「계정 만들기」 폼은
  `placeholder` 없이 **라벨만** 있다. `.ant-form-item` 을 라벨로 찾아 그 안의
  `input` 을 채운다.
- `F(..., attr_check=None)` + `_cell_state`/드라이버의 `server_reflect` 판정에
  새 갈래 — 값이 **글자로는 안 뜨고 `data-*` 속성에만 실리는 자리**
  (`NotifySettings.tsx` 의 `data-gx-channel`)를 위해, 본문 텍스트 대조 대신
  그 속성이 실제로 값을 담고 있는지를 DOM 에서 직접 읽는다(`img_check` 와
  나란한 셋째 갈래).

  ★ **구조 발견**: `find_control`/`prepare_steps` 는 바깥 모듈의 top-level
  함수가 **아니다** — `DRIVER`(gx-shell 안에서 **딴 프로세스**로 도는 문자열
  소스, `verify_click_completes.py:~2275`) 안에만 있다(`ast.parse` 로 실측
  확인). 위 넷 다 그 DRIVER 문자열 안에서 고쳤다. `attr_check` 의 on_screen
  계산도 DRIVER 안이다. `_cell_state`(평가만 하는 바깥 모듈 함수)는 이미 계산된
  `on_screen` 불리언만 읽으므로 안 건드렸다 — 두 계층이 하는 일이 다르다.

### 4-B. 다섯 행
| 행 | 제어 | 콜 | 상태 | revert |
|---|---|---|---|---|
| U5#1 | `btn("계정 만들기", gx="people-create-submit")` + `fill_label()` ×4 | POST `/settings/people/create` | `srv_change(GET /audit?page_size=1, "total")`(people 전용 GET 이 코드에 없어 U4#16 이 쓰는 감사 총수를 돌려 씀) | `no_revert`(새로 만드는 문) |
| U5#4 | `btn("이 표대로 적용", gx="camera-import-apply")` + `prepare=[press("예시 채우기"), press(gx="camera-import-dryrun")]` | POST `/cameras/import` | `srv_change(GET cameras/pulse, "total")` | `no_revert`(누르면 카메라가 남는다 — 옛 note 그대로) |
| U5#5 | `btn("채우기", gx="camera-address-row-submit")` + `prepare=[press(gx="camera-address-row-start"), put(...)]` | POST `/cameras/{id}/address` | `srv_change(GET address-gap, "without_address")` | `no_revert`(빈 칸을 채우는 문) |
| U3#16 | `btn("설정 저장", gx="prefs-save-submit")` + `prepare=[put("22:00","21:47",restore=True), put("07:00","06:13",restore=True)]` | PUT `/me/notify-prefs` | `srv_change(GET notify-prefs, "quiet_start")` | `revert_redo(...)` |
| U5#10 | U5#9 와 **같은 단추** 재사용(새 클릭 자리 아님 — L 의 표 그대로) | POST `/notify-rules/save` | `srv_reflect(rules)` + `attr_check='[data-gx="notify-rule-channel"]'` | `revert_toggle()`(U5#9 와 같음) |

### 4-C. 선언할 자리가 없는 행 — 그대로 둠(목록)
- **U1#4**(`/multi-stream-monitor`) — 인수 스트림, §0.4 인접(`rj-core` 임포트),
  P-205 로 정본이 이미 「정본 없음」 확정.
- **U3#14**(모바일 실시간 구간 참조) — D-306 계약 11조 영구 잠금.
- **U4#9**(증빙 영상 추출) — D-306 계약 11조 영구 잠금.
- **U6#14**(스키마 버전 확인) — 기계 행, 화면 자체가 없다(control=`api()`,
  콜·상태는 이미 서 있다 — 없는 것은 **화면 쪽** `data-gx` 자리이지 컨트롤이
  아니다). L.md §1-B 와 동일 결론.

### 4-D. 자기시험 회귀 — 실제로 한 번 걸렸다
5행에 POST/PUT 컨트롤을 달면서 `revert` 선언을 처음엔 빠뜨렸는데,
`verify_click_completes.py --self-test` 자신의 검사(「상태를 바꾸는 클릭인데
되돌림 선언이 없다」)가 그것을 잡았다 — 고친 뒤 자기시험 재통과 확인(아래 ②).

---

## 5. P-429 — 새 실행기 `scripts/run_with_gates.py`

`.env.gates` 를 **이 프로세스의 환경에만**(`os.environ`) 싣고
`verify_route_alive.expand_env_refs` 로 `${NAME}` 을 셸과 같은 뜻으로 펼친 뒤,
인자로 받은 판정기 명령을 `subprocess.run` 으로 그대로 부른다. 값은 어디에도
안 찍는다(이름·읽은 개수만) — argv 도 안 고친다(비밀은 환경으로만 간다).

`--self-test` 는 파일·자식 없이 순수 함수(`parse_env_text`·`unresolved_names`·
`fingerprint`)만 잰다. **자기시험**: 펼친 뒤에도 `${` 가 남으면 `unresolved_names`
가 잡는다(=빨강 조건) — 시험 1개로 이 둘을 짝지었다.

**호스트 실측(실제 `.env.gates`)**: 이 실행기가 실은 값의 sha256(앞 12자)이
`verify_route_alive.load_local_env()` 가 읽은 같은 이름의 값과 **정확히 일치**
(`GX_API`·`GX_ROUTE_USER`·`GX_ROUTE_PASSWORD`·`GX_ROUTE_CONTAINER`) —
`GX_ROUTE_PASSWORD`(`${GX_SEED_ROLE_PASSWORD}` 간접)와 `GX_SEED_ROLE_PASSWORD`
의 fingerprint 도 같아 **간접 참조가 올바로 펼쳐졌음**을 확인했다(값은 어디에도
안 적었다 — 비교만 했다).

---

## 6. 바꾼/만든 파일
- `scripts/onboarding_two_numbers.py` — `resolve_c_rows()` 새 함수 · `--c-from-ledger`
  플래그 · `render()` 회색 줄에 c 출처 · `_self_test()` 에 자기시험 짝 5건 추가.
- `scripts/drill_seed_click.py` — `verify_unjudged()` 새 함수 · `--unjudged` 플래그.
- `scripts/measure_onboarding_t.py` — U3#1 술어만(`rows_u3()` 안의 그 블록).
- `scripts/verify_click_completes.py` — `btn(gx=)` · `press()` · `fill_label()` ·
  `F(attr_check=)` · `find_control()`/`prepare_steps()`/`attr_check` 판정(DRIVER
  문자열 안) · U5#1·U5#4·U5#5·U3#16·U5#10 F() 행.
- `scripts/run_with_gates.py` — 새 파일.
- `backend/tests/test_ap_q_p422_onboarding_default_no_c.py` — 새 파일(15건).
- `backend/tests/test_ap_q_p426_drill_seed_unjudged.py` — 새 파일(9건).
- `backend/tests/test_ap_q_p425_u3_1_mine_predicate.py` — 새 파일(5건).
- `backend/tests/test_ap_q_p429_run_with_gates.py` — 새 파일(10건).
- `backend/tests/test_ap_q_p423_click_declares.py` — 새 파일(19건 + 26 subtests).
- `docs/agent/checkpoints/turn-ap/Q.md` — 이 파일.

## 7. 시험 이름과 결과
```
MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e DB_TEST_NAME=test_gx_lane_q -w /app gx-shell python -m pytest \
  tests/test_ap_q_p422_onboarding_default_no_c.py \
  tests/test_ap_q_p426_drill_seed_unjudged.py \
  tests/test_ap_q_p425_u3_1_mine_predicate.py \
  tests/test_ap_q_p429_run_with_gates.py \
  tests/test_ap_q_p423_click_declares.py \
  -q -p no:randomly
→ 49 passed, 4 warnings (0 failed)
```
도구 자기시험(호스트 + gx-shell 양쪽 확인):
```
python scripts/onboarding_two_numbers.py --self-test        → exit 0, 26건 통과
python scripts/run_with_gates.py --self-test                → exit 0, 8건 통과
python scripts/verify_click_completes.py --self-test        → exit 0, 자기시험 통과
```
인접 시험(같은 판정기 파일을 건드렸으니 L 의 시험 · 근처 U56 시험도 확인 —
결과는 실행 로그가 도착하는 대로 별도로 덧붙인다: `test_ap_l_click_declares.py` ·
`test_u56_settings_api_keys.py` · `test_u56_webhook_signing_key.py`).

## 8. 닫은 절 · 못 닫은 절
이 차선은 §0.10 기능명세 절을 새로 닫지 않았다(산출기·씨앗·술어·실행기 정직화
작업이라 별표 절 승격 대상 밖). P-422·P-426·P-425·P-423·P-429 다섯 절 다
**코드로는 끝났지만 가설**이다 — 라이브 미측정(§ 규약)이라 다음 V 회차가 실제로
색이 바뀌는지 가른다.

## 9. 조율자에게 넘길 줄
- 공용 파일(`backend/apps/fws/api.py` · `urls.py` · `App.tsx` · `routes.ts` ·
  `copy.ts` · `constants.py`) — 손대지 않았다. 넘길 줄 없음.
- `EVENT_ENTRY_SURFACE` — 새 `/api/dsm/` 라우트를 안 열었다. 넘길 줄 없음.
- L 에게(확인 요청): U5#1 의 `group_id=4` 는 **가정**이다(이 저장소의 다른 도구가
  이미 쓰는 관례값을 재사용했을 뿐, People.tsx 자체엔 기본값이 없다) — L 이 실제
  테넌트 id 를 안다면 고쳐 달라.

## 10. 스스로 의심하는 점
- **U5#1 group_id=4** — 가정이다. 틀리면 이 행은 서버 거절로 빨강이 되고, 그것은
  술어가 틀렸다는 신호이지 클릭 메커니즘이 틀렸다는 뜻은 아니다.
- **U5#4/U5#5 잔여 위험** — 같은 CSV/주소를 두 번 적용하면 `unchanged` 라 총수가
  안 변한다(옛 note 가 이미 적어 둔 사실). 매 회 새 시험 자료가 없으면 이 두
  행은 여전히 빨강일 수 있다 — 못 잰 것이 아니라 「제품이 실제로 아무것도 새로
  안 썼다」는 뜻이다.
- **U3#16 되돌리기** — 처음 시간대가 **빈 칸**(둘 다 미설정, 아마 흔한 기본
  상태)이면 `restore_steps()` 가 빈 문자열을 「못 적어 뒀다」로 보고 되돌리기를
  스스로 포기한다(판정은 그대로, 「되돌리지 못한 자리」로만 남는다). 그러면 다음
  회의 `quiet_start` before 값이 이번 회의 "21:47" 로 남아, 다음 실측에서 같은
  값을 다시 쓰면 거짓 빨강이 날 수 있다 — V 가 반복 측정할 때 주의.
- **U5#5 행 선택** — `find_control` 의 gx 선택자는 화면에 여러 행이 있으면
  `.first`(첫 시각 행)를 집는다. 그 카메라가 이미 주소가 있으면(표 자체가
  「주소 없는 카메라」만 보여 준다는 가정이 틀리면) `without_address` 가 안
  줄어 거짓 빨강이 날 수 있다.
- **U5#10 attr_check** — 어느 행의 채널인지까지는 안 가른다(존재 확인만) —
  L 이 원한 "안 눌러도 읽을 수 있는 자리"라는 목표에는 맞지만, "저장한 그 행의
  값이 맞는지"까지는 이 술어가 증명하지 못한다.
- **DRIVER 문자열 구조** — `find_control`/`prepare_steps` 가 바깥 모듈이 아니라
  `DRIVER`(딴 프로세스 문자열) 안에 있다는 것을 게이트 파일을 한참 읽고서야
  알았다. 이 구조는 문서화가 약하다 — 다음에 이 판정기를 고치는 사람도 같은
  시간을 쓸 수 있다(넘길 줄로 L·조율자에게 한 줄 남긴다면 도움이 될 것 같다).
