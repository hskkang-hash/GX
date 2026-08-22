# W0-16 (b) — 전역 관리 역할 vs 테넌트 운영 역할 · 분리 정의

**작성** 2026-08-22 · **티켓** W0-16 · **결정** D-243 · D-247
**이 문서가 W0-14 의 전제다.** W0-14 는 여기서 정의한 판정을 뷰에서 강제한다.

---

## 0. 한 문장

> **전역으로 통과시킬 자격은 "GAION 운영 역할" 하나뿐이고, 나머지는 전부 자기 테넌트 안에서만 관리한다.**

---

## 1. 왜 정의가 먼저인가 (D-247)

지금 "테넌트 경계를 넘어도 되는가"의 답은 두 곳이 내리는데 **판정식이 같다.**

```
dj-core   core/base.py:308        user.is_superuser or user.roles.filter(code='superuser').exists()
이 저장소 common/tenant_filters.py:72  getattr(user,'is_superuser') or any(r.code=='superuser' ...)
```

앞의 것은 §0.4 라 못 고친다. 뒤의 것을 고쳐도 **판정 기준이 같으면 결과가 같다.**
그래서 뷰(W0-14)보다 **기준(W0-16)이 먼저**다. 지시서의 원래 순서대로 갔으면 두 번 고쳤다.

---

## 2. 정의

### 2-1. 전역 관리자 (테넌트 경계를 넘을 수 있다)

다음 중 **하나라도** 참이면 전역이다. 판정은 `common/tenant_roles.is_global_admin()` **한 곳**에서만 한다.

| # | 조건 | 현재 해당 | 성격 |
|---|---|---:|---|
| ① | DB 플래그 `is_superuser = True` | **0명** | Django 원형. 실계정에 없다 |
| ② | `TENANT_GLOBAL_ADMIN_ROLE_CODES` 의 역할 보유 (`gaion_global_admin`) | 신설 → 6명 | **GAION 운영자 전용. 목표 상태** |
| ③ | 레거시 `superuser` 역할 보유 **AND** `TENANT_TRUST_LEGACY_SUPERUSER=True` | 13명 | **전환기에만 참** |

③ 이 무중단의 실체다 (D-243 ②). 대체역할을 다 주기 전에는 켜 두고, 다 준 뒤에 끈다.
**③ 을 끄는 순간 "레거시 superuser 역할"은 전역이 아니게 된다** — 회수 전에 미리 효과를 볼 수 있다.

### 2-2. 테넌트 운영자 (자기 테넌트 안에서만)

`<TENANT_ADMIN_ROLE_PREFIX>_<group_id>` 규약. 기본 접두어 `tenant_admin` → `tenant_admin_6`.

판정(`is_tenant_admin()`)은 **역할 코드만 보지 않는다.** 그 역할의 `group_id` 가 요청자의 소속 group 과
같아야 한다. 코드 문자열만 보면 남의 테넌트 admin 역할을 얻어 붙이는 경로가 열린다.

권한 내용은 **레거시 `superuser` 역할의 메뉴/탭 권한 행을 그대로 복제**한다 (menus 101 · tabs 27).
달라지는 것은 하나뿐이다 — **우회가 없으므로 테넌트 필터가 실제로 걸린다.**

> 왜 복제인가: `superuser` 역할은 권한 행을 갖고 있지만 `core/role/permission.py:475` 가
> **검사 자체를 건너뛴다.** 그래서 역할만 떼면 화면이 통째로 사라진다. 복제가 무중단의 조건이다.

### 2-3. 설정 (한 곳 · D-212)

`backend/config/settings.py`:

```python
TENANT_GLOBAL_ADMIN_ROLE_CODES = env.list("TENANT_GLOBAL_ADMIN_ROLE_CODES",
                                          default=["gaion_global_admin"])
TENANT_TRUST_LEGACY_SUPERUSER  = env.bool("TENANT_TRUST_LEGACY_SUPERUSER", default=True)
TENANT_ADMIN_ROLE_PREFIX       = env.str("TENANT_ADMIN_ROLE_PREFIX", default="tenant_admin")
```

되돌리기: `TENANT_TRUST_LEGACY_SUPERUSER=True` 한 줄. 코드 되돌림 불필요.

---

## 3. 계정 배치 — 무엇이 어디로 가나

| group | 이름 | 판정 | 인원 | 받는 역할 |
|---:|---|---|---:|---|
| 5 | Group Default | GAION 운영 | 2 (`hans` `ldk`) | `gaion_global_admin` |
| 7 | Gaion | GAION 운영 | 4 (`admin` `gaion01` `gaion09` `jaechol`) | `gaion_global_admin` |
| 6 | **Anyang** | **고객 테넌트** | **7** | **`tenant_admin_6`** |

**GAION 운영 테넌트 목록(`--global-groups 5,7`)이 이 정의에서 유일하게 사람이 정한 값이다.**
group 5(Group Default)를 포함한 근거는 두 계정의 이메일 도메인이 `gaion.kr` 이라는 것뿐이다
(§`superuser_accounts.md` §2). 조직도로 확인이 필요하면 `--global-groups 7` 로 좁히면 되고,
그 경우 `hans`·`ldk` 는 `tenant_admin_5` 를 받는다. **되돌리는 비용은 인자 하나다.**

---

## 4. 이 정의를 W0-14 가 어떻게 쓰는가 (다음 티켓)

```
common/tenant_filters.py  is_superuser()            → tenant_roles.is_global_admin() 로 교체
  · _check (tenant_scope.py:165)
  · filter_by_group_field
  · filter_users_by_group
  · get_scoped_or_404
```
4곳 전부 같은 함수를 부른다. **판정식을 복사하지 않는다** — 복사본 하나가 우회 지점 하나다 (D-212).

---

## 5. 산출물

| 파일 | 무엇 |
|---|---|
| `backend/common/tenant_roles.py` | 정의 본체 (`is_global_admin` · `is_tenant_admin` · `global_admin_reason`) |
| `backend/config/settings.py` | 설정 3개 (§2-3) |
| `scripts/role_split_local.py` | 역할 생성·부여·회수 실행기 (dry-run 기본 · 운영 복제본 쓰기 거부) |
| `backend/tests/test_tenant_roles.py` | 판정 단위시험 |
| `evidence/W0-16/http_role_split_test.md` | (d) HTTP 시험 결과 |
| `evidence/W0-16/revocation_runbook.md` | (e) 회수 절차서 |
