# Q 보고 — 턴 AC (13:35~13:56 기계 KST · 창 1)

## ① 실측 — 명령 + 결과

**로캘 버그 재현(코드 확인)**
```
scripts/measure_onboarding_t.py:351(HEAD)  btn = page.get_by_role("button", name="Confirm")
```
→ 영어 이름 하나만 찾음. 화면이 한국어면 못 찾음.

**Chromium 기본 로캘 실측** (gx-shell 안 · `browser.new_context()` 에 `locale` 인자 없이):
```
docker exec gx-shell python3 -c "... p.evaluate('() => navigator.language') ..."
→ en-US   (LANG 환경변수 없을 때)
→ ko      (LANG=ko_KR.UTF-8 줄 때)
```
⇒ **판정기가 지금까지 en-US 로 떠서 고객 화면(ko-KR)을 본 적이 없었다** — 컨테이너 기본 로캘이 en-US 였기 때문에 「Confirm」이 실제로 화면에 있었고, 그래서 지금까지 이 버그가 판정기 자기 눈에는 안 보였다.

**i18n 출처 대조**(지어내지 않음 — 코드에서 옮김):
- `frontend/src/features/login/LoginDesktop.tsx:343` → `label={t('Confirm')}`
- `frontend/src/i18n/locales/ko.json:1297` → `"Confirm": "확인"`
- `frontend/src/i18n/locales/en.json:1105` → `"Confirm": "Confirm"`
- `frontend/src/i18n/index.ts::getStoredLanguage()` → `navigator.language` 를 읽어 `en/ko/th` 중 고른다(기본 `en`)

## ③ 로캘 A/B 전/후 수 — **한 회차, 실제로 눌러서**

계정 `gxseed_u1_operator` 에 살아있는 세션을 미리 하나 깔아 「다른 기기」 창이 **반드시** 뜨게 만든 뒤, 같은 컨테이너·같은 ko-KR 컨텍스트에서 baseline(HEAD) `login()` 과 fixed(고친 뒤) `login()` 을 번갈아 실측:

| 단계 | 판정기 | 결과 | `still_login` |
|---|---|---|---|
| 0(세션 심기) | fixed | ok=true · confirmed=true | false |
| **1 BASELINE** | HEAD(영어 「Confirm」만) | **ok=false · confirmed=false · why="로그인 뒤에도 /login"** | **true** |
| 2 FIXED | 고친 뒤(사전 `["확인","Confirm"]`) | ok=true · confirmed=true · `/dsm/queue` 도달 | false |

화면에서 실제로 읽은 모달 문구(1단계 직후 `body` 스냅샷 그대로):
```
세션 종료
현재 이 계정은 다른 기기에서 사용 중입니다. 이전 세션을 종료하고 새로 로그인하시겠습니까?
확인
취소
```

**분모는 정본(`canon_rows()`)에서 그대로 읽음(손으로 안 적음)**: U1 의 두 칸 행 = **8** (`U1#1,2,3,4,8,9,11,19`).
`measure()` 의 `if not lg["ok"]:` 분기는 로그인 실패 시 그 사람 몫 **모든** 두 칸 행을 `gray_kind="env"` 로 회색 처리한다. 즉 이 세션-충돌 조건에서:
- **고치기 전(BASELINE)**: 로그인 실패 → **U1 몫 8/8 행 강제 회색**
- **고친 뒤(FIXED)**: 로그인 성공 → **강제 회색 0/8** — 각 행이 실제 측정 기회를 얻는다

세션 충돌은 지어낸 조건이 아니다 — U1·U3 두 페르소나가 같은 계정(`gxseed_u1_operator`)을 쓰고, 여러 차선이 하루 종일 로그인하는 이 환경에서 실제로 자주 일어나는 조건이다(테스트 시작 전 첫 로그인(0단계)조차 이미 `confirmed=true` 였다 — 즉 그 계정에 이미 남의 세션이 있었다).

## ⑥ 음성 대조(negative control)
```
p.get_by_role('button', name='존재하지않는단추이름XYZ').count() == 0   ← 통과(거짓 양성 없음)
p.get_by_role('button', name='로그인').count() == 1                    ← 통과(실재 단추는 잡힘)
```
매처가 항상 참을 내는 고무도장이 아님을 확인했다.

## ② 고친 파일:줄
- `scripts/measure_onboarding_t.py`
  - `:72-80` `CONFIRM_LABELS = ["확인","Confirm"]` · `DEFAULT_LOCALE = "ko-KR"` 신설(사전은 위 i18n 출처에서 그대로 옮김)
  - `:360-370` `login()` 의 Confirm 단추 탐색을 `CONFIRM_LABELS` 순회로 교체
  - `:585,607,623` `measure()` 에 `locale` 매개변수 추가 · `browser.new_context(viewport=vp, locale=locale)`
  - `:2142-2147` `--locale` CLI 인자 추가(기본 `GX_LOCALE` env → `ko-KR`)
  - `:2206` `measure(...)` 호출에 `locale=args.locale` 전달
  - (U6 의 `browser.new_context()` — `:664` — 는 그대로 둠: `actx.request` 로 API 만 두드리고 화면을 안 그리므로 로캘 무관 · 좁게 넓힘)
- `scripts/_gate_header.py`
  - `:93-107` `KEY_DEFERRED`/`_DEFERRED_WHEN` 신설
  - `:213-224` `judge_measured()` 에 `deferred:<언제>` 갈래 추가 — **여전히 회색(문제 목록에 남는다) · 면제 아님** · 「언제」없으면 「없다」와 동급
  - `:847-856` `--self-test` 에 자기시험 4건 추가(양성 1 · 무when 거절 1 · 음성 대조 1 · 회귀 없음 1) — 전부 통과 확인

## ④ 고친 뒤 색이 움직인 절 — **전부**
세 갈래(코드·번들·화면)로 확인:
1. **코드**: `frontend/src/features/dsm/**/*.tsx` 34개 전수 grep → `useTranslation`/`react-i18next` **0건**. DSM 앱(U1~U6 화면, 즉 온보딩 48행이 재는 대상)은 i18n 을 전혀 안 쓴다.
2. **코드**: `ADVANCE_LABELS`·`STATE_WORDS`·`PRODUCT_LINE`(`frontend/src/features/dsm/copy.ts:515`·`constants/kick.ts:16`)·`FIRST_TIME`(`frontend/src/App.tsx:418`) — 전부 하드코딩 한국어 리터럴, 번역 키 아님.
3. **번들**: 실서비스 청크 `/app/_fe_dist/assets/severity-B3kRS_Cy.js` 를 직접 읽어 `접수하기` 주변을 봄 → `c={acknowledged:"접수하기",in_progress:"조치 시작",closed:"종결하기"}` (순수 객체 리터럴) · 그 청크에 `i18next`/`useTranslation` 문자열 **0건**.
4. `login()` 안의 「Log In」/「로그인」 이중 탐색은 이미 로캘 무관하게 둘 다 시도하던 코드라 **바뀐 게 없다**.

⇒ **결론: 로캘 기본값을 ko-KR 로 바꿔서 색이 움직인 절은 로그인의 「다른 기기」 확인 창 하나뿐이다.** 온보딩 48행의 나머지 절(DSM 화면 전체)은 로캘에 영향받지 않는다 — 번들까지 열어 실측했으므로 이것은 추론이 아니라 관측이다.
(단, `§0.4` 금지구역인 delivery/orders 쪽 컴포넌트들은 실제로 `t('Confirm')` 을 쓰지만 온보딩 48행 U1~U6 경로가 거기를 지나가지 않는다 — 손 안 댐, 확인만 함.)

## ⑤ 회색 게이트 11(P-243) — 실측 및 처분
`python scripts/verify_gate_header.py` 를 지금 직접 돌려 **재측정**(지시서의 "11" 을 그대로 안 믿음):

```
HEADER_DECLARED  81개 중 80개 머리글 — 회색 1: verify_backup_recovery.py
HEADER_LIVE      어긋남 1: verify_backup_recovery.py(세 줄 중 0줄)
MEASURED_LINE    81개 중 69개 분모 있음 — 회색 12
  [verify_alarm_budget.py, verify_backup_recovery.py, verify_bundle_api_base.py,
   verify_bundle_hash.py, verify_camera_address.py, verify_camera_pulse.py,
   verify_event_drop.py, verify_minio.py, verify_perf_budget.py, verify_purge.py,
   verify_release_candidate.py, verify_seed_p20.py]
```
**지시서 전제가 틀렸다(⑧)**: "회색 게이트 11" 이 아니라 지금 **12**다. 그중 `verify_backup_recovery.py` 는 MEASURED 문제가 아니라 **머리글 자체가 0/3줄**(더 심각한, 다른 종류의 고장) — E 소유(backup*) 라 내가 손 안 댐, E 에게 별도 쪽지 필요.

나머지 **진짜 11개**를 하나씩 읽고 분류:

| 파일 | 분류 | 근거 |
|---|---|---|
| verify_alarm_budget.py | **지금 잴 수 있다(미배선)** | `gate_header()` 가 이미 live ORM target/as/source 를 찍는다 — 배선만 안 됐다 |
| verify_bundle_api_base.py | **지금 잴 수 있다(미배선)** | 지금 뜬 SPA 번들을 HTTP 로 직접 읽음 — 즉시 분모 가능 |
| verify_bundle_hash.py | **지금 잴 수 있다(미배선)** | 살아있는 번들 바이트 해시 — 즉시 가능 |
| verify_camera_address.py | **지금 잴 수 있다(미배선)** | live ORM |
| verify_camera_pulse.py | **지금 잴 수 있다(미배선)** | live ORM(트랜잭션 되돌림) |
| verify_event_drop.py | **불확실** | 라이브 트래픽 의존 — 표본이 실제로 희소할 수 있음. 소유(K1 이벤트) 판단 필요 |
| verify_minio.py | **지금 잴 수 있다(미배선)** | live HTTP + root 자격, 객체 수 즉시 가능 |
| verify_perf_budget.py | **부분적으로 진짜 deferred** | 이 파일은 내(Q) 소유(`PERF-04 · 차선 Q`). 「기준선」 수치는 **지금** 가능. 그러나 파일 자체 docstring:20-24 이 "**합격선은 gunicorn+nginx 에서 다시 잰다(OPS-13 뒤)**" 라고 이미 적어 놓음 — 합격선 쪽은 **OPS-13 이라는, 이미 문서화된 이름의 미래 사건**에 진짜로 달려 있다 |
| verify_purge.py | **불확실** | E 소유(P-57). 퇴거/파기 주기 스케줄 여부를 내가 모름 |
| verify_release_candidate.py | **불확실 — 「언제」가 없다** | 개념적으로는 "다음 RC 컷" 에 달렸을 법하나, 그 시각을 적은 결정문·일정을 못 찾음. 날짜 없이 `deferred:` 를 붙이면 내가 방금 만든 규칙("「언제」 없으면 「없다」와 동급") 에도 걸리고, 억지로 붙이면 그 자체가 **얼버무림**이 된다 |
| verify_seed_p20.py | **deferred 대상 아님 — 결정 공백** | 파일 자기 주석(48-53행)이 "몇 장이 옳은지는 지시서가 정하지 않았다" 라고 **명시**함. 이건 "시간이 지나면 안다"가 아니라 "**아무도 숫자를 안 정했다**" — 세종 결정이 필요하지 deferred 로 적으면 거짓말이다 |

**처분**:
1. `_gate_header.py::judge_measured()` 에 `deferred:<언제>` 문법을 **신설·자기시험 4건과 함께 등재 완료**(위 ②). 이 문법은 **여전히 회색으로 센다** — D-511 09-23 기한이 오면 다른 회색과 **똑같이 빨강**이 된다. 어디에도 게이트 이름을 뺀 허용 목록을 만들지 않았다(D-350 위반 없음) — `verify_gate_header.py` 의 집계 로직·기한 로직은 **한 글자도 안 건드림**.
2. 오늘 시간 안에서 **실제로 `deferred:` 를 박은 게이트는 0개다.** 이유(⑦): 11개 중 6개는 "지금 잴 수 있는데 안 쟀다"(미배선) 로 보이는데, 이건 deferred 문제가 아니라 **배선 문제** — deferred 로 적으면 그게 바로 P-243 이 경계한 "모양만 바꾼 면제"가 된다. 나머지는 소유·근거(구체적 날짜) 가 부족해 **지어내지 않았다**.
3. **회색 ≤ 3 목표는 달성 못 함** — 12(또는 backup_recovery 제외 11) 그대로. 정직하게 미달로 적는다.

## ⑦ 못 한 것과 왜
- 11개 회색 게이트 각각에 실제 `deferred:`/실측 분모를 박는 일 — **다른 차선 소유 영역(alarm/camera/minio/purge/event_drop 등)** 이고, 오늘 남은 창 안에 각 도메인을 제대로 이해하지 않고 분모를 넣으면 "분모를 손으로 넣는" 실수를 반복할 위험이 커서 보류. `verify_perf_budget.py` 는 내 소유지만, 기준선 분모 배선도 이 창에서 급히 하면 회귀 위험이 있어 **다음 회차로 넘김**(코드는 손 안 댐).
- 48행 `--measure` V 전 준비·CR 검산 — 지시서에 "시간이 남을 때만" 이라 손 안 댐(시간 소진).
- `verify_backup_recovery.py` 의 머리글 파손(HEADER_LIVE 0/3) — E 소유, 고치지 않고 **여기 기록**만.

## ⑧ 지시서 전제 중 틀린 것
- "회색 게이트 **11**" → 지금 실측하면 **12**(+ `verify_backup_recovery.py` 는 애초에 종류가 다른 고장).
- WO 목표 "회색 ≤ 3" 은 이 창 안에서 달성 불가로 판단(도메인 지식·안전 배선 시간 부족) — 억지로 줄이면 부정확한 분모가 생긴다.

## ⑨ 모르는 것(회색으로 남길 것)
- `verify_event_drop.py`·`verify_purge.py` 가 정말 "돌고 나서 말한다"(시간 의존) 인지 "미배선"(지금도 가능)인지 — 소유자(K1/E) 확인 필요.
- `verify_release_candidate.py`·`verify_perf_budget.py`(합격선 쪽) 의 구체적 "언제"(RC 컷 날짜 · OPS-13 완료 예정일) — 결정문에 없음, 세종/해당 차선에게 물어야 함.
- U1 외 다른 페르소나(U2~U5)에서도 같은 「다른 기기」 세션충돌 조건이 실제로 몇 % 확률로 일어나는지 — 오늘은 U1 한 회차만 강제로 만들어 확인했고, 전수(48행) 재측은 못 함(시간).

## 자기시험/회귀 확인
```
python scripts/_gate_header.py --self-test        → 전부 O (기존 19건 + 신규 4건)
python scripts/verify_gate_header.py --self-test   → 전부 O (회귀 없음)
python -m py_compile scripts/measure_onboarding_t.py scripts/_gate_header.py → OK (호스트·gx-shell 둘 다)
```

삭제 0 · `--no-verify` 안 씀 · 커밋 안 함(작업 트리에만 있음) · 컨테이너 안 임시 시험 파일(`/tmp/baseline_measure.py`,`/tmp/ab_locale_test.py`) 정리함 · 비밀은 이름만 사용(`GX_SEED_ROLE_PASSWORD` 값은 어디에도 안 적음).
