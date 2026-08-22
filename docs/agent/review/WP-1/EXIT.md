<!-- 승인 시 사람이 이 파일 첫 줄에 다음 한 줄을 넣는다. 에이전트는 절대 쓰지 않는다.
APPROVED: 2026-__-__ 강희석
-->
# WP-1 완료검토서 — 테넌트 격리 완결 (실제 노출 차단)

**작성** 에이전트 · 2026-08-15 · **착수검토 승인** 2026-08-15 (대표 · 구두 3문항)
**정본** tickets v3.1 / WP 2/9 · **티켓** W0-12 · W0-14 · W0-11 · W0-13

> **판정을 먼저 적는다. goal 은 거짓이고, 그렇게 될 것을 착수 때부터 알고 있었다**(ENTRY §1 #10).
> 이 WP 가 실제로 만든 것은 격리가 아니라 **격리를 셀 수 있는 자**다.
> 그리고 그 자로 재 보니 **티켓 두 개의 전제가 틀려 있었다**(§6).

---

## 1. 판정 — goal 한 문장이 참인가

**goal**: group A 토큰으로 group B 데이터에 도달 불가함을 **HTTP 레벨로** 증명

**판정**: ☐ 참 · ☐ 부분적으로 참 · **☑ 거짓**

**거짓인 이유는 하나다 — 증명 수단이 실행되지 않았다.**
"HTTP 레벨로 증명"의 증명 도구는 `TenantIsolationAPITest` 5건과 신규
`test_route_tenant_scope` 9건인데, **둘 다 이 머신에서 한 줄도 돌지 않았다.**
그리고 이번에 그 원인이 처음으로 특정됐다(§1-2). Docker 나 DB 가 아니었다.

### 1-1. 증명 — 오프라인에서 실행 가능한 전부 (실제 명령과 출력)

```
$ cd /c/GuardianX/guardianx-source

### W0-12 verify #1 — 정본 명령 그대로
$ git grep -n 'UserGroup\.objects\.first()' -- backend/
(출력 없음)                                    ← PASS · 착수 시점 2건

### W0-12 dod ③ 동등 가드 — 로직을 실제로 실행
$ python - <<'PY'   # ServiceLayerGroupSelectionTest 와 같은 검사
...
offenders: 없음 → PASS

### 순수 로직 시험 30건 — Django 6.0.7 설정 후 모듈을 실제로 import 해 실행
$ python scratchpad/probe_tenant_scope.py
  === 1. _join 경로 조립 ===                       PASS ×3
  === 2. PUBLIC 판정 ===                           PASS ×4
  === 3. ScopeSpec — 사유 없는 면제는 만들 수 없다 === PASS ×2
  === 4. RouteInfo.state 三분류 ===                 PASS ×3
  === 5. summarize 집계 ===                        PASS ×8
  === 6. tenant_scoped — 경고 모드 vs 차단 모드 ===   PASS ×7
  === 7. require_user_group ===                    PASS ×3
  결과: 30 passed, 0 failed

### 컴파일 · 기존 게이트 (회귀 없음)
$ python -m py_compile <변경 6파일>                 OK 6/6
$ python scripts/check_key_divergence.py           exit=0
$ python scripts/check_demo_isolation.py           exit=0
$ grep -REn '192\.168\.[0-9]+\.[0-9]+' backend/.env.example frontend/.env.example
(출력 없음)                                        ← W0-10 회귀 없음
```

### 1-2. ★ 실행하지 못한 이유가 이번에 특정됐다 — Docker 가 아니었다

```
$ ls backend/core/
advanced_table
data                                   ← 이 둘뿐

$ python -c "import importlib.util as u; print(u.find_spec('core'))"
ModuleSpec(name='core', loader=None, ...)
                        ^^^^^^^^^^^ 암묵 네임스페이스 패키지
```

`core.base` · `core.user.models` · `core.api.v1.auth` · `core.role.permission` ·
`core.middleware.*`(5종)가 **전부 사내망 pip 배포본에 있다.**

> **열두 스프린트에 걸친 "오프라인 시험 0건"의 원인은 `django.setup()` 이 ImportError 로
> 죽는 것이다. DB 를 띄워도, Docker 를 켜도 달라지지 않는다.**
> 지금까지 이것이 "Docker 미기동"으로 기록돼 왔고, 그래서 해소 조건이 잘못 적혀 있었다.
> 유일한 해소 경로는 **사내망 pip 인덱스** 하나다.

---

## 2. 티켓별 결과

| 티켓 | 상태 | 한 줄 요약 |
|---|---|---|
| **W0-12** | verify-pending | ①② **충족.** 소유자 임의 선택 2지점 제거(폴백 없음). 전역 19건 분류 → 결함2·위험1·무해16. ③ 은 지목한 테스트가 실재하지 않아 동등 가드를 신규 파일에 두었다 |
| **W0-14** | verify-pending | 구현물 전부 투입 — 주입 지점 300줄 · 누락 탐지 테스트 309줄(9건) · 현황표. **데코레이터는 아직 아무 컨트롤러에도 안 붙였다(의도)** |
| **W0-11** | verify-pending | dj-core 부재를 **구조적으로 확정**(§1-2). 방문 스크립트 4개 준비. 확인항목 1·2 는 소스 수령 후 |
| **W0-13** | verify-pending | ① 정적 부분 완료. **실효 범위가 17종 중 2종(11.8%)** 임을 확정 — 티켓이 전제하지 않았다 |

**신규 파일 6개(소스 2 · 문서 4) 합 1,217줄 / 변경 파일 6개.**

### 2-1. 커밋 (2026-08-22 · baseline `4afca2b` → `faebd91`)

STEP 3-5 규약대로 **조사·증거를 먼저, 소스 변경을 나중에** 쪼갰다. 앞 커밋만으로도
사내망 방문 전에 확정된 사실 4건이 남는다.

| 해시 | 종류 | 내용 | 티켓 |
|---|---|---|---|
| `195888b` | docs | 증거 4종 + WP-0 EXIT + WP-1 ENTRY/EXIT (1,408줄) | W0-11·W0-12·W0-13·W0-14 |
| `c38576f` | chore | pre-commit 훅 공백 정리 — handover 2파일. **기능 diff 16줄이 공백 313줄에 묻히지 않도록 분리**(선례 `7af88b6`) | — |
| `faebd91` | feat | `tenant_scope.py` 300줄 · `test_route_tenant_scope.py` 309줄 · `require_user_group()` · `TENANT_SCOPE_ENFORCE` · handover 2건 수정 | W0-14·W0-12 |

커밋 시점 게이트: gitleaks **Passed** · GCS 키 분리(D-003) **Passed** · detect-private-key
**Passed** · large-files **Passed** · py_compile **6/6** · `UserGroup.objects.first()` grep **0건**.
작업 트리 clean.

> 이 절이 EXIT 제출 시점에 비어 있었다. 산출물이 **커밋되지 않은 채** 떠 있었기 때문이고,
> 그 상태로는 다음 WP 의 baseline 이 어긋난다. 2026-08-22 에 채웠다.

---

## 3. 자가검증 — KPI 4축

| 축 | 지표 | 착수(baseline) | 완료 | 판정 |
|---|---|---|---|---|
| **편리성** | 신규 라우트에 격리를 거는 데 필요한 추가 코드 | **표준 경로 없음** (헬퍼 호출처 0) | **1줄** (`@tenant_scoped()`) + 핸들러 내 필터 | **개선** |
| " | 그 격리가 걸렸는지 확인하는 방법 | **없음** | 테스트 1개 실행 → 수치 출력 | **신설** |
| **완결성** | 소유자 임의 선택 지점 | **2** | **0** | **달성** |
| " | `tenant_filters` 호출처 | **0** | **2** (+ 스코프 모듈 1) | 개선 |
| " | 라우트 스코프 커버리지 | **0 / 466 (0.0%)** | **0 / 466 (0.0%)** | **의도적 미변경** (§4-2) |
| " | 누락 탐지 테스트 | **0건** | **9건** (미실행) | 신설 |
| " | 오프라인 실행 가능 verify 명령 | 4/4 통과 | **4/4 통과** | 유지 |
| " | DB·dj-core 필요 verify 명령 | 0/6 실행 | **0/6 실행** | **미달** |
| **안정성** | 순수 로직 시험 | 0건 | **30건 통과** | 신설 |
| " | `py_compile` | — | **6/6** | 통과 |
| " | 기존 게이트 회귀 | 2/2 | **2/2** | 회귀 없음 |
| " | 격리 테스트(`test_tenant_isolation`) | 0/10 실행 | **0/10 실행** | 변화 없음 |
| **참신성** | 경쟁 대비 차별점 | — | **1건** ↓ | 확보 |

**참신성 근거** — 경쟁 제품이 못 하는 것:

- **"전 엔드포인트의 테넌트 격리 커버리지"를 회귀 테스트가 매번 숫자로 출력하고, 그 수가
  늘면 빌드를 깨뜨린다.** 공공 조달 보안성 심사의 "다기관 데이터 분리" 항목에 **문서가
  아니라 테스트 출력으로** 답할 수 있게 된다. 통상 이 질문에는 설계서로 답하고,
  설계서는 구현과 어긋나도 아무도 모른다.
- 부수: **면제 대장을 두 층으로 나눠 "면제"와 "미검토"를 구별**한다. 커버리지 지표를 가진
  제품은 있어도, **지표를 올리는 손쉬운 도피로(면제로 옮기기)를 테스트로 막는** 구조는 드물다
  (`test_public_list_does_not_grow`).

---

## 4. 자가검증 — 보안

| 항목 | 결과 | 명령/근거 |
|---|---|---|
| 시크릿 스캔 | **0건 (대체 검사)** | `gitleaks`·`pre-commit` 미설치 → `check_key_divergence.py` exit 0 + `.env.example` 신규 1행이 `TENANT_SCOPE_ENFORCE=false` (비밀값 아님) |
| 권한 우회 목록 증가 | **☑ 없음** | `base_model.py` 잔여 7종 불변. 업무모델 매칭 0 |
| 테넌트 격리 테스트 | **0/10 실행** | dj-core 부재(§1-2) |
| 신규 외부 통신 목적지 | **0건** | 네트워크 호출 추가 없음 |
| 새로 열린 엔드포인트 | **0건** | 신규 라우트 0 |
| **실제로 닫은 노출** | **2건** | 인수인계 문서·공지의 소유 group 오배정 경로. 이제 group 없으면 **만들지 않는다** |

> **이 WP 의 보안 성과는 커버리지가 아니라 이 마지막 줄이다.** 466개 중 0개에 스코프를
> 걸었지만, **남의 테넌트에 레코드를 만드는 경로 2개는 실제로 사라졌다.**
> 오배정은 오열람보다 고치기 어렵다 — 잘못 만들어진 데이터는 필터로 되돌릴 수 없다.

---

## 5. 자가검증 — 코드

| 항목 | 결과 | 근거 |
|---|---|---|
| Coding Convention 위반 | **0건** | 신규 Django 모델 0 · 신규 앱 0 · 신규 FE 화면 0 → 해당 규칙 대상 없음 |
| " | | 신규 설정 1개는 `env.bool(...)` 단일 지점 — D-212 준수 |
| Design Convention 위반 | **0건** | UI 변경 0 |
| 신규 파일 컨벤션 적용률 | **100%** | 소스 2파일 전부 `from __future__ import annotations` · 타입 힌트 · 모듈 독스트링에 근거 결정 명시 |
| 테스트 커버리지 | **측정 불가** | `coverage.py` 에 `django.setup()` 필요 |
| 남은 TODO / FIXME | **0건** | 신규 소스 2파일 |
| 미사용 import | **2건 (의도적 잔존)** | `handover` 2파일의 `UserGroup`. 제거하면 무관한 줄을 건드리게 되어 4원칙 ④로 남겼다 |

---

## 6. AUTHOR-ERROR — 지시서가 틀렸던 것

> D-214: 실측대로 구현하고 차이를 여기 적는다. `spec`·`dod`·`verify` 는 수정하지 않았다(금지 #11).

| # | 티켓 | 무엇이 틀렸나 | 실측 | 내가 어떻게 했나 |
|---|---|---|---|---|
| 1 | **W0-14 ①** | *"DRF: `TenantScopedViewSetMixin` 을 만들고 `get_queryset`/`get_object` 에서 group 강제"* | **DRF 뷰가 0개다.** `ViewSet` 0 · `APIView` 0 · `from rest_framework` import **0파일**. 전부 django-ninja-extra | DRF 갈래는 **사문(死文)이라 구현하지 않았다.** Ninja 갈래만 |
| 2 | **W0-14 ②** | *"`config/urls.py` 에서 등록된 전 라우트를 열거"* | 거기엔 `include` 23개뿐. 실 표면은 `@route.*` **466건** / `@api_controller` 78 / API 인스턴스 18 | 열거 지점을 **API 인스턴스 순회**로 바꿈. 런타임 레지스트리를 읽는다 |
| 3 | **W0-12 ③** | *"`test_service_layer_does_not_pick_arbitrary_group` 통과 (W0-3 의 `@expectedFailure` 해제)"* | 그 테스트는 **없고** `@expectedFailure` 도 **0건** | 격리 테스트 파일 수정은 금지 #5 → **동등 가드를 신규 파일에.** 이름은 dod 문구 그대로 → P-W0-12-2 |
| 4 | **W0-13** | 필터를 **단수**로 지칭 | `created_by__isnull` OR 는 **5곳**. 156·158 은 요청 캐시 히트 경로라 조건이 **복제**돼 있다 | 5곳 전부를 대상으로 기록. **한 곳만 고치면 캐시 살아있는 요청에서 결함 잔존** |
| 5 | **W0-13** | 이 수정으로 노출이 닫힌다는 전제 | **실효 범위 17종 중 2종(11.8%).** `CustomManagerGroup` 은 `common.base_model.BaseModelWithGroup` 에만 `objects` 로 붙고, 상속 모델은 dashboard 2개뿐 | ①의 정적 부분을 그 사실 확정에 썼다. ②는 W0-11 결과 전까지 보류 |
| 6 | **W0-11** | *"사내망 접속 시 dj-core 소스를 받아"* | 전제는 맞으나 **이유가 기록된 적 없었다.** `backend/core/` 는 암묵 네임스페이스 조각 | §1-2 로 구조를 확정. **해소 조건이 "Docker"가 아니라 "사내망 pip"임을 정정** |
| 7 | 부수 · `test_tenant_isolation.py` 머리말 | B 사용처를 *"dashboard 2개 모델뿐"* | 모델 수는 정확. 다만 `import` 는 3개 앱(`devices`·`operation_settings` 는 **미사용 import**) | 파일 수정은 금지 #5 → `impact.md` §2-1 에 기록만 |

---

## 7. ★ 사람이 답해야 하는 것

| ID | 질문 | 내 의견 | 왜 내가 못 정하나 |
|---|---|---|---|
| **P-W0-14-1** | `@tenant_scoped` 를 실 컨트롤러에 언제 붙이나 | **A** — 사내망에서 `ScopeDecoratorIntegrationTest` 2건이 초록이 된 뒤 파일럿 1개부터 | ninja 미설치로 **등록 경로 미실행.** 시그니처를 가리면 차단이 아니라 **기동 실패**가 나고 경고 모드로 안 막힌다 |
| **P-W0-12-2** | W0-12 dod ③ 의 테스트 경로 정정 | **A** — 신규 파일의 동등 가드로 dod 정정 | `dod` 수정 권한 밖(금지 #11) |
| **P-W0-12-1** | `print_format/models.py:98` 미리보기 표본 오열람 | **A** — W0-14 롤아웃 ②에서 함께 | 호출 규약 변경은 금지 #3 |
| **신규 7-1** | **W0-13 을 계속할 것인가.** spec 대로 완수해도 **노출의 88%가 남는다**(§6 #5) | **W0-11 결과를 보고 정한다.** dj-core 에 같은 OR 가 있으면 W0-13 은 `is_system` 을 A·B 양쪽에 요구하는데 A 는 §0.4 다 → **설계가 W0-14 우회로 바뀐다.** 없으면 B 2모델만 고치면 끝 | **두 설계의 작업량이 배 이상 차이 나고**, 판정 입력이 아직 없다 |
| **신규 7-2** | `delivery/services/status_mapping_service.py` 의 7개 주석이 **실재하지 않는 보호를 주장**할 가능성 (`impact.md` §2-2) | 사실이면 그 서비스는 **필터 없는 것으로 보고 다시 읽어야 한다.** W0-11 과 같은 방문에서 10분 | §0.4 금지구역 · 미수정 |
| **신규 7-3** | **사내망 방문일** — WP-0·WP-1 을 동시에 푸는 유일한 조건 | WP-0 2시간 + WP-1 검증 30분 + W0-11 10분 = **약 3시간, 1회** | 일정은 사람의 것 |

**되돌릴 수 없어 보류한 것: 2건.**
W0-13 ③ 백필(dry-run 리포트 선행 · hard_stop `data-destructive`) · `is_system` 스키마 변경.
**둘 다 이번 WP 에서 손대지 않았다.**

---

## 8. 남은 미완결

| 티켓 | 푸는 조건 | 실행할 명령 |
|---|---|---|
| (전제) | **사내망 pip** — Docker 아님(§1-2) | `pip install -r requirements.txt` → `python -c "import core.base"` |
| **W0-14** | 위 전제 | `python manage.py test tests.test_route_tenant_scope -v 2` → `[TENANT_SCOPE]` 줄을 `coverage.md` §3 에 · **생성된 `route_baseline.json` 을 커밋** |
| **W0-12** | 위 전제 | `python manage.py test tests.test_route_tenant_scope.ServiceLayerGroupSelectionTest` (dod ③ 대체 경로) |
| **W0-11** | 위 전제 | `dj-core-findings.md` §4 의 스크립트 4개 (약 10분) → §5 기입 |
| **W0-13** | 위 전제 + **DB** | `impact.md` §4 의 집계 스크립트 → §5 기입. **`_base_manager` 를 쓸 것** — `objects` 로 세면 결함이 결함을 숨긴다 |
| 전체 | 위 전제 + DB | `python manage.py test tests.test_tenant_isolation -v 2` (goal 의 최종 증명) |

**예상 결과를 미리 못박아 둔다** (사후 합리화 방지):

| 테스트 | 예상 |
|---|---|
| `test_enumerator_finds_routes` | **불확실.** 열거기가 API 인스턴스를 못 찾으면 여기서 먼저 깨진다 — **그러라고 넣은 테스트다** |
| `test_all_routes_are_tenant_scoped` | **통과** (대장 최초 생성 → 통과 후 커밋 요구) |
| `ScopeDecoratorIntegrationTest` 2건 | **불확실.** 이 둘이 롤아웃 가부를 정한다 |
| `ServiceLayerGroupSelectionTest` | **통과 예상** (오프라인에서 같은 로직 실행 확인) |
| `test_registry_covers_all_isolatable_models` | **실패 확정** (미등록 11종 · WP-0 승계) |

---

## 9. 다음 WP 착수 전 필요한 사람 작업

1. **§7 신규 7-1 판정** — W0-13 의 설계가 W0-11 결과에 달려 있다. **방문 전에는 답할 수 없다.**
2. **§7 신규 7-3 방문일 확정.** WP-0·WP-1 이 같은 조건 하나를 공유하며, 이제 **3시간 1회**로 둘 다 풀린다.
3. **WP-0 EXIT · WP-1 EXIT 승인**, 그리고 `decisions_pending` 11건 중 open 11건의 D-### 발행.
4. **WP-2 착수 가부.**
   - **의견: 열 수 있다.** WP-2(릴리스 위생)의 goal 은 *"외부에 내보낼 수 있는 빌드가
     재현 가능하게 나온다"* 이고, 그 티켓 대부분(W0-1b·W0-8·W0-6·W0-9)이 **사내망 방문
     그 자체**다. WP-1 의 미완결과 **같은 방문에 묶인다.**
   - 다만 WP-2 는 `human_gate: true` 가 4건이라 실질 진행은 사람 작업이 대부분이다.
     **방문일이 정해지기 전에는 WP-2 를 열어도 에이전트가 할 일이 거의 없다.**
   - 방문일이 멀면 대안: **WP-3(AI 이벤트 센터)** 의 `W2-2`(이벤트 수집)는 `DetectionEvent`
     모델이 이미 있고(W2-1) 서버 코드라 오프라인 작성이 가능하다. **단 WP 순서 변경은
     대표 승인 사항(금지 #18)이라 내가 정하지 않는다.**

---

**승인 요청 사항**: **§1-2(오프라인 시험 0건의 원인이 Docker 가 아니었다는 것)** 와
**§6 #5(W0-13 의 실효 범위가 11.8% 라는 것)**, 그리고 **§7 신규 7-1(W0-13 을 계속할 것인가)** 을
특히 봐 주십시오. 앞의 둘은 **지금까지의 해소 조건 기록이 틀려 있었다**는 뜻이고,
셋째는 **다음 스프린트의 작업량을 배 이상 가르는 분기**입니다.
