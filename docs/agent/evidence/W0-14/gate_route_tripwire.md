# 신규 경로 트립와이어 — 실측 (D-275 §5-1)

**측정** 2026-08-28 · **대상** WP-2 EXIT 승인의 **유일한 필수 부대조건**
**판정기** `backend/common/tenant_tripwire.py` (한 벌) · **눈** 정적 / 런타임 (둘)

---

## 0. 첫 줄 — 분모와 술어를 함께 적는다 (D-274)

```
정적 눈    465 라우트  (술어 = 소스의 @route.* 전수 · AST)
           unguarded 346 · guarded 32 · public 5 · clean 82 · unresolved 0

런타임 눈  652 라우트  (술어 = 등록된 오퍼레이션 전수 · enumerate_operations)
           unguarded 343 · guarded 31 · outside 197 · clean 81 · unresolved 0

트립와이어 신규 위반 0/0   (술어 = 등재부에 **이름이 없던** unguarded·unresolved·outside 가
                            나타났는가. 수 비교가 아니라 키 집합 비교)
시험       97 passed       (술어 = pytest tests/ --nomigrations · 직전 90 + 신설 7)
게이트     exit 0          (술어 = python scripts/verify_tenant_scope.py)
```

`unguarded 346` 은 **초록이 아니다.** 오늘 실재하는 빚이고, 이 게이트는 그 빚을
**갚는 것이 아니라 늘지 않게 잠그는 것**이다. 갚는 일은 P1(`W0-21`)에 있다.

---

## 1. 무엇을 잠갔나

WP-2 EXIT §5-1 이 남긴 미지는 이랬다:

> 주인 없는 행(`created_by IS NULL`)은 매니저 수준에서 여전히 보인다.
> 근원(`CustomManagerGroup` 의 `created_by__isnull` OR 절)은 저장소 밖이라 고칠 수 없다(§0.4).
> 지금 닫혀 있는 이유는 **라우트마다 문지기를 손으로 달았기 때문**이고,
> **문지기 없는 새 경로가 하나 생기면 그 순간 다시 샌다.**

D-275 는 그 문장을 사람의 기억이 아니라 **게이트가 지키게** 하라고 했다. 그것이 이 트립와이어다.
고칠 수 없는 결함을 고치는 것이 아니라 **다시 열리지 않게 잠그는** 방식이다.

**판정 한 줄** — 라우트가 **테넌트 모델을 만지는데** 문지기가 하나도 없으면 `unguarded`.
등재부에 **이름이 없던** `unguarded` 가 나타나면 **fail**.

---

## 2. 수가 아니라 이름으로 잠근다 (D-249 · D-277)

`PUBLIC_BASELINE = 4` 같은 **수 래칫**은 이 자리에서 통하지 않는다.
낡은 라우트 하나가 지워질 때마다 새 라우트 하나가 조용히 들어올 자리가 생기기 때문이다 —
**수는 그대로인데 노출은 바뀐다.**

그래서 등재부(`tripwire_baseline.json`)는 라우트 **하나하나의 키**를 적는다:

```
DELETE checklist_setting.views.ChecklistSettingCategoryController.delete_category
GET    flight_log.views.FlightLogController.get_flight_log_detail
...
```

키는 `METHOD module.qualname` 이라 **두 눈이 같은 키를 만든다.** 경로 문자열을 쓰지 않은 이유가
이것이다 — 정적 눈은 마운트 접두사를 모르고 런타임 눈은 안다. 경로로 잠그면 두 눈의 등재부가
갈라지고, 갈라진 등재부는 어느 쪽이 사실인지 아무도 모르는 상태가 된다.

---

## 3. ★ 양성 대조 — 탐지기가 실제로 탐지하는가 (D-277)

D-277 이 없었으면 이 절은 없었을 것이다. `assertNotContains('"id":N')` 이 응답의
`"id": N`(공백) 때문에 **구조적으로 실패할 수 없었던** 일이 있었다.
그래서 "위반 0" 을 적기 전에 **재는 기계가 작동하는지 먼저 증명한다.**

### 3-1. 순수 판정기 대조 (시험 4건 · `tests/test_route_tripwire.py`)

| 시험 | 심은 것 | 기대 | 결과 |
|---|---|---|---|
| `test_census_is_not_empty` | — | 모수 ≥ 100 · `flight_log.FlightLog` 포함 | **pass** (모수 142) |
| `test_detector_catches_a_planted_unguarded_route` | 문지기 없이 `FlightLog._base_manager.get()` | `unguarded` | **pass** |
| `test_detector_clears_a_guarded_route` | 같은 핸들러 + `assert_scoped` | `guarded` | **pass** |
| `test_decorator_alone_counts_as_a_gatekeeper` | `@tenant_scoped` 표식만 | `guarded` | **pass** |

음성 대조(3행)를 같이 두는 이유: **늘 빨간불인 탐지기는 늘 초록인 탐지기와 똑같이 쓸모가 없다.**

### 3-2. 실물 대조 — 진짜 라우트를 심고 게이트를 돌렸다

`backend/checklist_setting/views.py` 에 무방비 라우트를 **실제로 한 줄 심었다.**

```python
@route.get("/__probe_leak__/{id}", auth=CustomJWTAuth())
def probe_leak(self, request, id: int):
    return ChecklistSetting._base_manager.get(id=id)
```

**런타임 눈** — `pytest tests/test_route_tripwire.py`

```
[TRIPWIRE:runtime] 라우트 653건 — clean 81 · guarded 31 · outside 197 · unguarded 344
FAILED  [runtime] 새 unguarded 라우트:
        GET checklist_setting.views.ChecklistSettingController.probe_leak
        경로 GET /api/checklist-setting/__probe_leak__/{id}
        만지는 테넌트 모델: checklist_setting.ChecklistSetting
        → 테넌트 모델을 만지는데 문지기가 없다
1 failed, 6 passed
```

**정적 눈** — `python scripts/verify_tenant_scope.py`

```
[TRIPWIRE:static] 라우트 466건 — clean 82 · guarded 32 · public 5 · unguarded 347
[SCOPE] 위반 1건 — 멈춘다
  · [static] 새 unguarded 라우트: GET checklist_setting.views.ChecklistSettingController.probe_leak
      경로 GET /__probe_leak__/{id}  (checklist_setting/views.py:273)
EXIT=1
```

**되돌리는 대조** — 같은 라우트에 `assert_scoped(ChecklistSetting, id, request.user)` 한 줄을 붙이자

```
7 passed
```

즉 **탈출구는 "등재부를 고치는 것"이 아니라 "문지기를 다는 것"이다.**
심은 라우트는 `git checkout` 으로 되돌렸다 (저장소에 남아 있지 않다).

---

## 4. 눈이 둘인 이유 — 중복이 아니다

| | 정적 눈 | 런타임 눈 |
|---|---|---|
| 어디서 | `scripts/verify_tenant_scope.py` (pre-commit) | `tests/test_route_tripwire.py` (컨테이너) |
| 열거 | 소스의 `@route.*` (AST) | `enumerate_operations()` — 등록 실측 |
| Django | 불필요 | 필요 |
| 세는 수 | 465 | 652 |
| 잡는 것 | 커밋 시점에 **먼저** | 동적 등록·타 앱 register 까지 **전수** |

**판정기는 한 벌이다** (`tenant_tripwire.judge`). 눈만 둘이다 —
같은 것을 두 곳에서 세는 것이 아니라 **한 판정을 두 각도에서 먹인다.**
지시(D-275 §5-1)가 요구한 것은 **런타임 전수 열거**이고 그것은 시험 쪽이 한다.
정적 눈은 그것을 대신하지 않는다. 커밋 시점에 4초로 먼저 걸러 주는 앞눈이다.

`pre-commit` 훅의 대상 파일을 `backend/kernels/…` 3건에서 **`^backend/.*\.py$`** 로 넓혔다 —
새 라우트는 어느 `views.py` 에서든 생긴다. **좁은 필터는 곧 감긴 눈이다.**

---

## 5. `outside` 197건 — 관할 밖을 관할 밖이라고 적는다 (D-279)

런타임 눈이 센 652 중 **197건은 핸들러 소스가 `backend/` 안에 없다** (dj-core · ninja-jwt).
고칠 수 없으므로 문지기를 달 수 없다. 그러나 **자동 면제하지 않는다**(D-263):

- `outside` 도 등재부에 **이름으로** 올렸다. dj-core 가 새 라우트를 들고 오면 게이트가 멈춘다
  ("모르는 것을 만나면 멈춘다" — D-264).
- 판정 근거는 추정이 아니라 **파일 경로**다 (D-279): 그 모듈의 소스가 `backend/` 색인에 있는가.
  문지기 7곳을 §0.4 로 잘못 적었던 사고가 추정으로 붙인 "금지구역" 때문이었다.

`unresolved` 는 0 이다 — 저장소 안 모듈인데 핸들러를 못 되짚은 경우가 없다는 뜻이고,
생기면 **통과가 아니라 실패**로 센다.

---

## 6. 이 게이트가 **못** 하는 것 — 지우지 않고 적는다

문지기 판정은 **AST 호출 그래프 3단계**다. 그래서:

- 동적 디스패치(`getattr(svc, name)()`)로 부른 문지기는 못 본다 → **거짓 양성**(과다 검출).
- 미들웨어·시그널에 숨은 문지기도 못 본다 → 거짓 양성.
- 반대로 **문지기를 부르기만 하고 결과를 안 쓰는 코드**는 통과로 본다 → **거짓 음성**.

거짓 양성은 등재부에 사유와 함께 올려 해소한다.
거짓 음성은 이 게이트가 아니라 `tests/test_tenant_isolation.py` 의 **실 HTTP 프로브**가 잡는다.
여기서 둘을 다 하려 들지 않는다 — 한 게이트가 모든 것을 본다는 주장이 착시의 시작이다.

또 하나: **이 게이트는 빚을 갚지 않는다.** `unguarded 346` 은 그대로 남아 있고,
갚는 일정은 `W0-21`(배치별 FK 실증)과 P1 계획에 있다.

---

## 7. 재현

```bash
# 정적 눈 (호스트, Django 불필요)
python scripts/verify_tenant_scope.py                    # exit 0
python scripts/verify_tenant_scope.py --write-baseline   # 등재부 정적 구획 갱신

# 런타임 눈 (컨테이너)
docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
  PYTHONPATH=/app python -m pytest tests/test_route_tripwire.py -q --nomigrations -p no:randomly'
```

**산출물**: `docs/agent/evidence/W0-14/tripwire_baseline.json` (정적·런타임 두 구획)
