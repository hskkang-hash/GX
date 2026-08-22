# W0-14 라우트 테넌트 스코프 적용 현황표

**작성** 에이전트 · 2026-08-15 · WP-1 (ENTRY 승인분)
**티켓** W0-14 ③ · **상태** verify-pending (런타임 수치는 사내망 대기)
**모드** **경고(warning)** — `TENANT_SCOPE_ENFORCE=False` (대표 승인 2026-08-15)

---

## 0. 측정 방법

두 가지 수가 있고, **둘은 다른 것을 센다.**

```bash
# (a) 정적 — 소스에 적힌 데코레이터. 주석·문자열도 센다. 동적 등록은 놓친다.
cd backend
grep -rEc '@route\.(get|post|put|patch|delete)' --include=*.py . | awk -F: '{s+=$2} END {print s}'

# (b) 런타임 — 실제로 등록된 오퍼레이션. **이쪽이 정본이다.**
python manage.py test tests.test_route_tenant_scope -v 2
#   → [TENANT_SCOPE] total=… scoped=… public=… unreviewed=… no_auth=… coverage=…%
```

(b)는 `django.setup()` 이 필요하고, **dj-core 부재로 이 머신에서는 돌지 않는다**
(`evidence/W0-11/dj-core-findings.md` §1). 그래서 아래 §1 은 (a)이고 §3 이 (b)다.

> **(a)를 커버리지로 보고하지 않는다.** 정적 수를 진짜 수인 척 쓰는 것이
> `tickets.sha256`(WP-0 EXIT §6-1)과 같은 종류의 착시다.

---

## 1. 정적 실측 — HTTP 표면의 규모 (2026-08-15)

| 항목 | 수 |
|---|---|
| `NinjaExtraAPI` 인스턴스 | **18** |
| `@api_controller` | **78** (46 파일) |
| **`@route.*` 데코레이터** | **466** |
| — `@route.get` | 204 |
| — `@route.post` | 156 |
| — `@route.put` | 62 |
| — `@route.delete` | 43 |
| — `@route.patch` | 1 |
| **`auth=` 미선언** | **102 (21.9%)** |
| `config/urls.py` 의 `path()` | 23 (**전부 `include` — 라우트 아님**) |
| DRF `ViewSet` / `APIView` | **0 / 0** |
| `common/tenant_filters` 호출처 (착수 시점) | **0** |

### `auth=` 미선언 102건의 분포 (상위)

| 파일 | 건수 | §0.4 금지구역 |
|---|---|---|
| `terminals/views/terminal_views.py` | **14** | ✅ |
| `delivery/views/api.py` | **10** | ✅ |
| `stream_monitors/views/stream_monitors.py` | 9 | |
| `print_format/views.py` | 8 | |
| `operational_data/views/operational_data_view.py` | 8 | |
| `surveillance/views/surveillance_profile_view.py` | 4 | |
| `partner/views/partner_callback_mockup_controller.py` | 4 | |
| `flight_log/views.py` | 4 | |
| `checklist_setting/views.py` | 4 | |
| `orders/views/order_views.py` | 3 | ✅ |
| 기타 | 34 | |

**컨트롤러(`@api_controller`)에도 `NinjaExtraAPI(...)` 에도 전역 auth 기본값이 없다.**
따라서 102건은 정적으로는 **미인증 도달 가능**으로 보인다. 다만 `settings.MIDDLEWARE` 의
`core.middleware.jwt_user_restore.JWTUserRestoreMiddleware` 가 사용자 복원을 하므로,
**실제 익명 도달 가능 여부는 런타임 확인이 필요하다.** 정적 판정으로 단정하지 않는다.

---

## 2. 면제 대장 — **두 층으로 나눈 이유**

`common/tenant_scope.py` 가 라우트를 셋으로 가른다.

| 상태 | 뜻 | 지금 |
|---|---|---|
| `scoped` | `@tenant_scoped` 가 붙었다 | **0** |
| `public` | 인증 불요로 **판정이 끝났다.** 사유 필수 | 4 + 접두어 2종 |
| `unreviewed` | **아직 아무도 보지 않았다.** 잔여값 | 나머지 전부 |

**한 층이면 미분류가 면제로 위장한다.** 그러면 테스트는 초록이 되고 노출은 그대로 남는다.
`test_public_list_does_not_grow` 가 정확히 그 도피로를 막는다 — 미분류를 줄이는 가장 쉬운
방법이 PUBLIC 으로 옮기는 것이기 때문이다.

현재 `PUBLIC_ROUTES` (전부 사유 있음):

| 메서드 | 경로 | 사유 |
|---|---|---|
| POST | `/api/token/pair` | JWT 발급 — 인증 전 경로 |
| POST | `/api/token/refresh` | JWT 갱신 — 인증 전 경로 |
| POST | `/api/token/verify` | JWT 검증 — 인증 전 경로 |
| GET | `/api/stream-monitors/auth/csrf-token/` | CSRF 토큰 — 로그인 폼 선행 요청 |

접두어 면제: `/admin/` · `/api/docs`

> **업무 데이터 경로는 여기 없다.** 티켓 spec ③ 의 한정 조건(health·login·공개 문서)을 지켰다.
> 미인증 102건을 여기 밀어 넣지 **않았다** — 전부 `unreviewed` 로 남긴다(대표 승인 2026-08-15).

---

## 3. 런타임 현황 (사내망 방문 후 기입)

`python manage.py test tests.test_route_tenant_scope -v 2` 의 출력을 그대로 붙인다.

| 항목 | 값 | 비고 |
|---|---|---|
| `total` (런타임 라우트 수) | _(미기입)_ | 정적 466 과의 차이가 **동적 등록분** |
| `scoped` | _(미기입 · 예상 0)_ | |
| `public` | _(미기입)_ | |
| `unreviewed` | _(미기입)_ | **이 수가 대장이 된다** |
| `no_auth` | _(미기입 · 정적 102)_ | |
| `coverage_pct` | _(미기입 · 예상 0.0%)_ | |
| 라우트 미발견 소유 앱 | _(미기입)_ | 열거기 누락 점검 |

첫 실행이 `docs/agent/evidence/W0-14/route_baseline.json` 을 만든다. **그 파일을 커밋해야**
다음 실행부터 증가 금지가 걸린다.

---

## 4. ★ 롤아웃 순서 — 데코레이터를 아직 아무 데도 붙이지 않은 이유

**착수 시점 커버리지가 0/466 인 채로 이 스프린트를 닫는다. 의도한 것이다.**

`@tenant_scoped` 는 오프라인 순수 로직 시험 **30건을 통과**했다(WP-1 EXIT §3).
그러나 `ninja`·`ninja_extra` 가 이 머신에 없어 **등록 경로는 한 번도 실행되지 않았다.**

ninja 는 `inspect.signature` 로 핸들러 인자를 읽어 요청 스키마를 만든다.
래퍼가 원 시그니처를 가리면 **엔드포인트의 요청 파싱이 깨지고, 그것은 경고 모드로도
막히지 않는다 — 앱이 기동하지 않는다.** 466개에 붙여 놓고 그것을 사내망에서 처음 알게 되는
것이 이 WP 에서 가능한 최악의 결과다.

그래서 순서를 이렇게 고정한다.

```
① tests.test_route_tenant_scope.ScopeDecoratorIntegrationTest  ← 사내망에서 먼저 초록
      · test_decorator_preserves_handler_signature
      · test_decorated_route_registers_and_is_seen_as_scoped
                    │
                    ▼  초록이면
② 파일럿 1개 컨트롤러에만 부착 → 화면에서 실제 동작 확인 + WOULD_BLOCK 로그 관찰
                    │
                    ▼  1주 관찰 후
③ 앱 단위 확대. 매 확대마다 unreviewed 수가 줄어드는 것을 대장이 기록
                    │
                    ▼  unreviewed → 0 수렴 후
④ TENANT_SCOPE_ENFORCE=True  (설정 한 줄. 코드 되돌림 불필요)
```

**①이 초록이 되기 전에는 ②로 가지 않는다.** 이 문장이 이 파일에 적힌 이유는,
다음 사람이 "데코레이터가 있는데 왜 안 붙였지" 하고 일괄 부착하는 것을 막기 위해서다.

---

## 5. 이 표가 아직 답하지 못하는 것

| 항목 | 왜 못 답하나 | 해소 |
|---|---|---|
| 라우트별 상태 466행 | 런타임 열거 필요 | 사내망 1회 |
| 미인증 102건의 **실제** 익명 도달 가능 여부 | 미들웨어 상호작용은 정적으로 못 읽는다 | 사내망 · 인증 없이 curl |
| `optimization` 진단 API 노출 범위 | `evidence/W0-12/scan.md` §4 의 조건부 무해 판정이 여기 달려 있다 | 위와 동일 |
| 금지구역(terminals·delivery·orders) 라우트의 스코프 반응 | 부착 전 | 롤아웃 ②③ |
