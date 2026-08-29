# 사고 기록 — 주석 처리된 권한이 남긴 열린 문 15자리 (D-334)

**발견** 2026-09-07 · **판정 근거** 실호출 · **기록자** Claude Code
**되돌림이 아니라 기록이다** (D-105 계열). 고친 것과 못 고친 것을 같은 칸에 두지 않는다.

---

## 0. 한 줄

`@path_permission` 이 주석 처리된 **39자리** 중 **15자리**는 `auth=` 도 없어서
**익명 요청이 인증 관문을 지나 핸들러에 닿고 있었다.** 그중 **3자리는 익명에게 200 과 데이터를 돌려주고 있었다.**
15자리 전부에 인증 관문을 붙였고, 붙인 뒤 다시 호출해서 **익명 도달 0건**을 확인했다.

---

## 1. 어떻게 셌는가 — 분모부터 (D-301)

권한 계열의 술어는 **행위**로 그었다 (D-324): 「없어지면 접근이 넓어지는 데코레이터」.

| 갈래 | 대상 | 사유 |
|---|---|---|
| 포함 | `path_permission` · `oauth2_required` · `scope_required` · `tenant_scoped` · `ensure_csrf_cookie` | 없어지면 접근이 넓어진다 |
| 제외 | `csrf_exempt` | 주석 처리되면 접근이 **좁아진다** — 권한 계열의 반대편이다 |
| 제외 | `require_http_methods` | 메서드 제한이지 권한 판정이 아니다 |

```
[실측 · scripts/probe_commented_guards.py · 2026-09-07]

  권한 계열 데코레이터 사용   320자리   ← 분모
    · 활성                    281자리
    · 주석 처리               39자리   (전부 path_permission · 10개 파일)
```

주석 39자리를 **인증 관문 유무로** 갈랐다. `@path_permission` 은 **권한**이고
`auth=` 는 **인증**이다 — 같은 이름이 아니다 (D-337 동음이의 계열).

```
  authn_only          24자리   `auth=CustomJWTAuth()` 살아 있음 · 익명 요청은 401
  no_authn_no_authz   15자리   인증 관문 없음 · ★ 익명 요청이 핸들러에 닿는다
```

---

## 2. 열려 있었는가 — **호출로** 답했다 (D-210)

코드를 읽어서 답하지 않았다. 15자리 전부를 익명으로(Authorization 헤더 없이) 때렸다.

- **GET 8자리**: 그냥 때렸다.
- **POST 7자리**: 쓰기는 부작용이 남는다. 그렇다고 안 때리면 「auth 콜백이 비었으니 열려
  있을 것」이라는 **추정**이 된다(D-280 금지). 그래서 등록된 `view_func` 를 **도달 표시만
  남기는 대체물**로 잠시 바꾸고 때렸다 — **본체는 한 줄도 돌지 않았다.**

```
[실측 · 익명 요청 · 수정 전]

  POST   /api/delivery/processing/update-delivery-event                        422
  GET    /api/dronehw/drone-communication-management/online-drones             200  ★ 데이터 반출
  GET    /api/operational-data/.../download-operational-data                   422
  POST   /api/operational-data/.../{id}/upload-operational-log-drone           도달
  POST   /api/operational-data/.../{id}/upload-operational-log-robot           도달
  POST   /api/operational-data/.../{id}/upload-operational-video-drone         도달
  POST   /api/operational-data/.../{id}/upload-operational-video-robot         도달
  GET    /api/operational-data/.../{id}/download-operational-log-drone         400
  GET    /api/operational-data/.../{id}/download-operational-log-robot         400
  POST   /api/surveillance/surveillance-profiles/{id}/completed-profile        도달
  GET    /api/terminals/days-of-week                                           200  ★ 데이터 반출
  GET    /api/terminals/days-of-week/{id}                                      404
  GET    /api/terminals/terminal-types                                         200  ★ 데이터 반출
  GET    /api/terminals/terminal-types/{id}                                    404
  GET    /api/terminals/functions/function-types                               500

  15/15 이 401 이 아니다.  200(데이터 반출) 3자리.
```

**「도달」의 뜻**: 대체물이 실제로 호출됐다는 것 — 인증 관문이 그 요청을 막지 않았다.
400·404·422·500 도 마찬가지다. **401 이 아닌 모든 것은 관문을 지났다는 뜻이다.**

> 익명 POST 4자리가 **운행 로그·운행 영상 업로드**다. 무게를 낮춰 적지 않는다.

---

## 3. 경위 — 아는 것과 모르는 것을 가른다 (D-280)

```
[실측] 39자리 전부 git blame 이 4afca2b (2026-08-13, 「베이스라인 커밋 — 실키 제거 후 초기화」)
[실측] 한 자리에 사유가 주석으로 남아 있다:
       api_key_controller.py:54  # @path_permission(...)  # Tạm thời comment out để test
                                    (베트남어. 「시험용으로 임시 주석 처리」)
[모름] 언제·왜 주석 처리됐는지. 우리 저장소는 그 시점 **이후**에 시작한다.
       주석 처리는 베이스라인 이전 공급자 이력에서 일어났고, 그 이력은 이 환경에 없다.
```

**「임시」가 사유란에 적힌 채로 베이스라인을 넘어왔다.** 그것이 우리가 아는 전부다.
그 이상은 적지 않는다 — 매끄러운 경위는 문장으로는 낫지만 사실이 아니다 (D-322 계열).

---

## 4. 무엇을 고쳤고 무엇을 안 고쳤는가

### 고쳤다 — 15자리에 인증 관문 (즉시 · 래칫 대상 아님)

```
+ auth=CustomJWTAuth()   ← 6개 파일 · 15자리. 같은 파일 형제 라우트의 표기 그대로다
```

| 파일 | 자리 |
|---|---|
| `backend/operational_data/views/operational_data_view.py` | 7 |
| `backend/terminals/views/terminal_views.py` | 3 |
| `backend/terminals/views/day_of_week_views.py` | 2 |
| `backend/delivery/views/api.py` | 1 |
| `backend/drone_communication/views/drone_views.py` | 1 (import 추가) |
| `backend/surveillance/views/surveillance_profile_view.py` | 1 |

**확인 [실측 · 수정 후 재호출]**: `익명2xx=0 · 익명도달=0 · 판정={'authn_only': 39}`

### 안 고쳤다 — 권한(`@path_permission`) 복구 39자리 (래칫 · D-311)

열려 있던 것은 **인증**이고 그것이 사고다. 권한 복구는 역할·경로 대장이 필요한 별개의 일이라
나머지 24자리와 함께 래칫에 둔다. **열린 문에는 유예가 없고, 느슨한 권한에는 있다.**
지금 39자리는 전부 `authn_only` — 인증된 사용자면 역할과 무관하게 통과한다.

> 이건 이 저장소가 이미 세어 둔 더 큰 자리의 일부다:
> `test_auth_surface.py` [실측 2026-08-25] — 652 라우트 중 `auth=` 없음 **143**,
> 그중 `@path_permission` 부착 **24**. 이번 15자리는 그 143 안에 있었다.

---

## 5. ★ 곁가지로 잡힌 것 — **캐시가 코드 수정보다 오래 산다**

수정 직후 재호출에서 **2자리가 여전히 200** 이었다. 코드는 고쳐졌는데 값이 나갔다.

```
[실측] common/universal_optimization.py::UniversalCacheMiddleware
       · 캐시 적중 시 뷰를 부르지 않고 JsonResponse(200) 을 돌려준다 (universal_optimization.py:872)
       · 캐시 키에 사용자 권한 서명이 들어가고, 익명은 "anon" 이다 (:711)
       → 열려 있던 동안 **익명 키로 채워진 항목**이 코드 수정 뒤에도 익명에게 그대로 나갔다
[실측] cache.clear() 뒤 재호출 → 익명2xx 0건
```

**원칙으로 올릴 값이 있다: 관문을 고치는 것과 이미 새어 나간 것을 거두는 것은 다른 일이다.**
그리고 **관문을 재는 시험이 캐시를 재면 안 된다** — 회귀 시험은 `X-No-Cache` 로 우회해서 때린다.

> 운영 함의: 이 사고가 운영에 있었다면 코드 배포만으로는 부족하고 **캐시를 비워야** 한다.
> 개발 환경에서는 비웠다. 운영 서버·운영 DB 는 직접 건드리지 않는다(불변 제약).

---

## 6. 재발을 막는 것 (D-286 — 절차는 도구로)

| 무엇 | 어디 | 규칙 |
|---|---|---|
| 게이트 | `scripts/verify_commented_guards.py` | ① 주석 권한 + `auth=` 없음 → **exit 1, 래칫 아님** ② 기준선에 없던 자리에 새 주석 → exit 1 (래칫) |
| 훅 | `.pre-commit-config.yaml::gx-commented-guards` | `backend/**/*.py` 전체를 본다 — 열린 문은 새 파일에서도 태어난다 |
| 기준선 | `docs/agent/evidence/D-334/commented_guards_baseline.txt` | 39자리. 줄 번호가 아니라 **파일::클래스::핸들러::데코레이터**로 잠근다 |
| 회귀 시험 | `backend/tests/test_commented_guards.py` | 15자리 목록을 fixture 로 박았다 · 4건 통과 |
| 계측기 | `scripts/probe_commented_guards.py` | 「지금 열려 있는가」를 **호출로** 답한다 (게이트는 정적) |

**출생 표본** (D-310): 게이트의 자기시험 첫 갈래가 `drone_views.py:29` 의 실제 두 줄이다.

```python
@route.get('/online-drones')        # auth= 가 없다
# @path_permission("read")          # 권한은 주석 처리되어 있다
```

**음성 대조 [실측]**: 그 자리의 `auth=` 를 지우고 게이트를 돌렸더니 `열린 문 1건 · exit 1`.
되돌리니 `열린 문 0건 · exit 0`. 게이트가 실제로 이 사고를 잡는다.

---

## 7. 남은 것

```
· 권한(@path_permission) 복구 39자리 — 래칫. 역할·경로 대장이 선 뒤에 갚는다
· auth= 없는 라우트 143자리 [실측 2026-08-25] 중 이번에 15자리를 갚았다 → 재실측 필요
· 「임시」라고 적힌 주석이 베이스라인을 넘어온다 — 공급자 스냅샷을 받을 때 보는 자리로 등재할 값이 있다
```
