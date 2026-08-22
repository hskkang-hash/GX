# W0-14 — 파일럿 1개 라우트 스코프 부착 + 전환 플래그 실측

**실행** 2026-08-22 · **티켓** W0-14 (WP-2 · D-247 순서) · **환경** 로컬 기동본
**대상 DB** `w014_guardianx` (= `database_guardianx` 의 TEMPLATE 복제본. **운영 복제본 무변경** · D-245)
**엔드포인트** `GET /api/stream-monitors/stream-monitors` — W0-14 프로브·W0-16 시험과 **같은 엔드포인트**

---

## 0. 판정

> **경로②(`created_by IS NULL`)도 닫혔다.** 회수 완료 계정(`man`)의 남의 것 **1건 → 0건**.
>
> 그리고 그보다 큰 것 하나 — **역할을 회수하지 않아도, 설정 한 줄로 닫힌다.**
> 아직 레거시 `superuser` 역할을 들고 있는 `son` 이 `TENANT_TRUST_LEGACY_SUPERUSER=False`
> 하나로 **15건 → 0건**이 됐다. 코드 변경 없음 · 역할 회수 없음 · 재기동만.
>
> 이것이 회수 계획(revocation_runbook)의 순서를 바꾼다: **플래그가 먼저이고 역할 회수는 정리 작업**이다.

---

## 1. 무엇을 바꿨나 — 세 곳

| # | 파일 | 변경 | 근거 |
|---|---|---|---|
| ① | `common/tenant_filters.py` | 지역 `is_superuser()` **삭제** → 판정을 `tenant_roles.is_global_admin()` 하나로 | D-247 · D-212 |
| ② | `common/tenant_scope.py` `_check` | 같은 교체 + 레거시로 통과한 건에 `[LEGACY_GLOBAL]` 경고 | D-247 |
| ③ | `stream_monitors` 목록 뷰·서비스 | `@tenant_scoped()` 부착 + `get_stream_monitors(user=…)` 로 **명시적 group 필터** | D-207 · coverage.md §4 ② |

①②는 **판정 대상**을 바꾸고(누가 경계를 넘는가), ③은 **실제 좁힘**을 한다.
데코레이터는 표식일 뿐이라 ③의 `user=` 인자가 없으면 아무것도 좁혀지지 않는다 (D-249).

### 왜 ③이 필요한가 — 매니저만으로는 안 되는 이유
`StreamMonitor.objects` 는 dj-core `CustomManagerGroup` 이고 그 필터는
`Q(created_by__isnull=True)` 를 **OR 로 포함**한다(`core/base.py:430`). §0.4 라 고칠 수 없다.
그래서 서비스가 `filter_by_group_field()` 로 한 번 더 좁힌다 — 이 필터에는 OR 절이 없다.

---

## 2. 결과 — 같은 데이터·같은 방법 (진실대장: monitors 39 · created_by NULL 15 · group NULL 13)

| 계정 (테넌트) | 역할 | 시점 | 본 건수 | 자기것 | group NULL | **남의 것** |
|---|---|---|---:|---:|---:|---:|
| `man` (Anyang) | `superuser` | 착수 (W0-14 프로브) | 30 | 7 | 8 | **15** |
| `man` (Anyang) | `tenant_admin_6` | W0-16 역할 회수 후 | 9 | 7 | 1 | **1** |
| **`man` (Anyang)** | **`tenant_admin_6`** | **W0-14 파일럿 후 (지금)** | **7** | **7** | **0** | **0** |
| `son` (Anyang) | `superuser` 보유 · 플래그 **True** | 지금 | 30 | 7 | 8 | **15** |
| **`son` (Anyang)** | **`superuser` 보유 · 플래그 False** | **지금** | **7** | **7** | **0** | **0** |
| `admin` (Gaion) | `gaion_global_admin` · 플래그 False | 지금 | 30 | 4 | 8 | 18 |

### 2-1. `admin` 의 18건은 누출이 아니다

`admin` 은 W0-16 에서 **전역 역할(`gaion_global_admin`)을 명시적으로 받은** GAION 운영 계정이다.
전 테넌트를 보는 것이 그 역할의 정의다. 플래그를 내려도 값이 변하지 않는다는 것이 오히려 증거다 —
통제가 **의도한 전역 접근과 레거시 무차별 우회를 구분**하고 있다.

> 그러므로 D-249 의 "누출 0건"은 **비전역 계정 기준**으로 읽는다. 전역 계정의 광범위 접근은
> 누출이 아니라 정의이며, 그 계정 수(현재 6)를 줄이는 것은 W0-16 회수 절차의 몫이다.

### 2-2. `man` 에게 남아 있던 1건이 사라진 경로

```
id=8  Q02-0002  소유 group=7(Gaion)  created_by=NULL
```
W0-16 시험은 이것을 "역할을 정리해도 닫히지 않는 경로②"로 남겼다.
③의 명시적 `group` 필터에는 `created_by__isnull` OR 이 없으므로 이 레코드는 더 이상 넘어오지 않는다.
**W0-13(백필)을 기다리지 않고 이 엔드포인트에서는 먼저 닫혔다.**

### 2-3. ⚠ 대가 — group 이 비어 있는 13건은 아무에게도 보이지 않는다

`group_id IS NULL` 13건(39건 중 33%)은 이제 비전역 계정 화면에서 사라진다.
**의도한 방향이다** — 소유 테넌트를 말할 수 없는 레코드를 모두에게 보여 온 것이 누출이었다.
다만 운영 반영 전에 W0-13(백필)로 **귀속**시켜야 화면 손실이 없다. 두 티켓의 의존은 여기다.

---

## 3. 무중단 확인

`man` 은 HTTP **200** 으로 자기 7건을 그대로 본다. 화면이 죽지 않는다.
`son` 은 플래그를 내려도 **200 / 자기 7건** — 레거시 역할을 들고 있어도 자기 테넌트는 그대로다.

> **한계**: 목록 API 1종으로 잰 것이다. "모든 화면이 그대로"를 증명하지 않는다.
> 나머지 651 라우트는 롤아웃 ③(앱 단위 확대)에서 같은 방법으로 확인한다.

---

## 4. 라우트 대장 — 이번에 처음 실측한 것

`scripts/dump_openapi_routes.py` 로 21개 ninja API 의 openapi 스키마를 합쳐
**경로 + 허용 메서드** 대장을 만들었다 → `evidence/W0-14/openapi_routes.json` (531 오퍼레이션).

`route_baseline.json` 은 **개수만** 센다(652). 격리 시험이 실제로 부를 수 있는 경로를 고르려면
경로 문자열과 메서드가 필요하다 — 그것이 `P-W0-14-2`(§5)의 근거다.

두 수가 다른 이유: 652 는 런타임 오퍼레이션(메서드 단위 · docs/openapi 포함),
531 은 openapi 스키마에 실린 경로 단위다. **줄어든 것이 아니라 다른 것을 센다.**

---

## 5. 이번에 하지 않은 것 (그리고 왜)

| 하지 않은 것 | 왜 |
|---|---|
| `tests/test_tenant_isolation.py` 배선 수정 (api_base 404 4건 · 401 1건 · 픽스처 24건) | **절대금지 #5.** D-250 이 승인한 것은 픽스처 email 한 줄뿐이다. 근거를 갖춰 `P-W0-14-2` 로 적재했다 |
| `is_group_isolatable()` 확장 (group FK 인정) | `P-LOCAL-3` **미결**. 같은 파일이고 판정 로직이다 |
| 652 라우트 일괄 부착 | coverage.md §4 롤아웃 ②→③. 파일럿 관찰이 먼저다 |
| 운영 반영 (플래그·역할) | 대표 승인 사안. 이 문서는 로컬 실측이다 |

---

## 6. 재현

```bash
# 0) 복제본 (운영 복제본은 건드리지 않는다 · D-245)
docker exec postgres psql -U postgres -c "CREATE DATABASE w014_guardianx TEMPLATE database_guardianx"
docker exec -e DB_NAME=w014_guardianx gx-shell sh -c "cd /app && python manage.py migrate"

# 1) W0-16 상태 재현 (역할 분리 + 파일럿 1계정 회수)
docker exec -i -e DB_NAME=w014_guardianx -w /app gx-shell python - --apply --revoke 4 \
  < scripts/role_split_local.py

# 2) 외부 스트리밍 스텁(없으면 목록 API 가 500 — W0-17) + 서버
docker exec -d gx-shell python /tmp/stub.py          # 127.0.0.1:8099 → {"items":[]}
docker exec -d -e DB_NAME=w014_guardianx -e STREAM_URL=http://127.0.0.1:8099 \
  [-e TENANT_TRUST_LEGACY_SUPERUSER=False] gx-shell sh -c "cd /app && python manage.py runserver 0.0.0.0:8000 --noreload"

# 3) 프로브 (비밀번호는 회차마다 다른 값을 인자로 — 파일에 적지 않는다 · D-204)
docker exec -i -e DB_NAME=w014_guardianx -w /app gx-shell python - '<이번 회차 비밀번호>' \
  < scripts/probe_tenant_isolation.py

# 4) 단위시험
docker exec gx-shell sh -c "cd /app && python manage.py test tests.test_tenant_filters_scope \
  tests.test_tenant_roles tests.test_route_tenant_scope -v 2 --keepdb"
```

**정리**: `DROP DATABASE w014_guardianx` — 이 복제본에는 프로브가 재설정한 비밀번호가 남는다 (D-245).

## 7. 부수 확인 — 기록만

* 로그인 rate limit 이 여전히 **HTTP 500** (표준은 429). W0-18 대상 — 이번에도 4계정이 이것으로 SKIP 됐다.
* 목록 API 는 외부 스트리밍 스텁 없이는 통째로 **500**. W0-17 대상.
* 복제본은 `manage.py migrate` 가 필요했다 — `database_guardianx` 에 `stream_monitors.0015` 가
  **미적용**이다(운영 덤프 기준). 저장소에는 있고 운영 스키마에는 없다. P-LOCAL-4(저장소/운영 정합)의 실례다.
