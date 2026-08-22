# W0-16 (a) — `superuser` 역할 보유 계정 전수 목록

**측정** 2026-08-22 · **대상** 로컬 복제본 `database_guardianx` (읽기 전용 질의만)
**티켓** W0-16 · **결정** D-243 · D-247 · **선행 실측** `evidence/W0-14/http_leak_probe.md`

> 운영 DB 에는 접속하지 않았다. 이 문서의 모든 수치는 로컬 복제본 조회 결과다.
> 이메일 전체 값은 적지 않는다 — 판단에 필요한 것은 **도메인**뿐이다.

---

## 1. 결론 3줄

1. `superuser` 역할 보유 **13계정 · 전원 활성 · 전원 `is_superuser=false`** — DB 플래그로 세는 감사는 **0명**을 보고한다.
2. 13계정이 **3개 테넌트에 걸쳐 있다**: Anyang 7 · Gaion 4 · Group Default 2.
   그중 **Anyang 7계정은 고객 테넌트 안에 있다** — 이들이 전역 권한을 갖고 있을 이유가 없다.
3. **부여자·부여시각은 복원 불가능하다.** `user_coreuser_roles` 는 `(id, coreuser_id, role_id)` 3열뿐이고
   `created_on`·`created_by_id` 가 없다. 감사 추적이 스키마 수준에서 존재하지 않는다.

---

## 2. 전수 목록 (13계정)

| # | id | username | 테넌트(group) | 이메일 도메인 | 활성 | `is_superuser` 플래그 | 마지막 로그인 | 보유 역할 전체 |
|---:|---:|---|---|---|:--:|:--:|---|---|
| 1 | 49 | `hans` | 5 Group Default | gaion.kr | ✔ | false | 2026-01-20 | admin, drone_robot_admin, **superuser** |
| 2 | 50 | `ldk` | 5 Group Default | gaion.kr | ✔ | false | 2026-02-03 | drone_robot_admin, **superuser** |
| 3 | 4 | `man` | 6 Anyang | yopmail.com | ✔ | false | 2025-11-19 | **superuser** |
| 4 | 5 | `son` | 6 Anyang | yopmail.com | ✔ | false | 2026-01-30 | admin, **superuser** |
| 5 | 9 | `rin` | 6 Anyang | yopmail.com | ✔ | false | 2025-12-17 | **superuser** |
| 6 | 12 | `kimchi` | 6 Anyang | yopmail.com | ✔ | false | 2026-01-30 | **superuser** |
| 7 | 13 | `kimchi1` | 6 Anyang | yopmail.com | ✔ | false | 2025-11-25 | **superuser** |
| 8 | 91 | `rin_superuser` | 6 Anyang | yopmail.com | ✔ | false | **없음** | **superuser** |
| 9 | 92 | `tuan_superuser` | 6 Anyang | yopmail.com | ✔ | false | **없음** | **superuser** |
| 10 | 2 | `admin` | 7 Gaion | guardianx.com | ✔ | false | 2026-02-09 | **superuser** |
| 11 | 33 | `gaion01` | 7 Gaion | yopmail.com | ✔ | false | 2026-01-29 | **superuser** |
| 12 | 41 | `gaion09` | 7 Gaion | yopmail.com | ✔ | false | 2026-01-19 | delivery_admin, delivery_order, **superuser** |
| 13 | 78 | `jaechol` | 7 Gaion | gaion.kr | ✔ | false | 2025-12-04 | **superuser** |

**부여자 / 부여시각: 전부 `unknown`** — 스키마에 그 열이 없다 (§4-1).

### 2-1. 테넌트별 집계

| group | 이름 | 성격 | 전체 사용자 | superuser 보유 | 비율 |
|---:|---|---|---:|---:|---:|
| 5 | Group Default | GAION 내부(추정) | 4 | 2 | 50.0% |
| 6 | **Anyang** | **고객 테넌트** | 26 | **7** | **26.9%** |
| 7 | Gaion | GAION 운영 | 14 | 4 | 28.6% |
| 4·8·11·12·13·14·15 | ETRI / Thailand / Fire_Drone / DRONE-ROBOT / Gaion Test / Gongju / GeumSan-ETRI | 고객·시험 | 47 | **0** | 0% |

전체 10테넌트 · 91사용자 중 13명(14.3%)이 전역 권한을 갖는다.

---

## 3. 이 역할이 실제로 무엇을 여는가 (코드 실측)

`superuser` **역할 코드**가 통과시키는 지점 3곳. 앞의 둘은 §0.4 금지구역이라 고칠 수 없다.

| # | 위치 | 무엇을 통과시키나 | 우리가 고칠 수 있나 |
|---|---|---|---|
| 1 | `core/base.py:308` (dj-core) | **ORM 매니저의 group 필터 전체** — 모든 테넌트 데이터 | ✘ §0.4 |
| 2 | `core/role/permission.py:475` | **메뉴/탭 권한 검사 전체** (`view_func` 즉시 실행) | ✘ §0.4 |
| 3 | `common/tenant_filters.py:72` `is_superuser()` | 이 저장소의 뷰 레벨 필터 4곳 | **✔ — W0-14 의 대상** |

즉 **저장소가 손댈 수 있는 것은 3번 하나다.** 1·2번이 열려 있는 한
"역할을 그대로 두고 뷰만 고친다"로는 ORM 직접 호출 경로가 남는다 →
**역할 자체의 회수(§W0-16 (c)(e))가 필요한 이유가 여기서 확정된다.**

---

## 4. 부수 실측 — 이번 조사에서 새로 나온 것 3건

### 4-1. 역할 부여에 감사 추적이 없다
```
user_coreuser_roles(id, coreuser_id, role_id)     ← created_on · created_by_id 없음
```
"누가 언제 이 계정에 superuser 를 줬는가"는 **DB 로 답할 수 없다.** 목록의 부여자/시각이
전부 `unknown` 인 것은 조사 부족이 아니라 스키마의 상태다.
→ 회수 절차서(§W0-16 (e))는 **회수 이력을 별도로 남기는 것**을 포함해야 한다.

### 4-2. `superuser` 역할에 `is_default = true` 가 켜져 있다
```
role_role: id=1 code=superuser is_default=t group_id=NULL holders=13
           id=3 code=user      is_default=t group_id=NULL holders=3
```
현재 사용자 생성 경로는 `Role.objects.filter(code='user')` 로 **코드**를 찍어 고르므로
(`core/api/v1/user.py:588`) 이 플래그로 superuser 가 자동 부여되지는 **않는다.**
다만 `is_default` 로 기본역할을 고르는 코드가 하나라도 생기면 그 순간
**신규 계정이 전역 권한을 받는다.** 지금은 결함이 아니고 **함정**이다.
→ 회수 시 `is_default` 를 false 로 내리는 것을 절차에 넣는다.

### 4-3. 전역 역할과 테넌트 역할이 같은 테이블에서 구분되지 않는다
```
group_id IS NULL : superuser · admin · user · operator · order      (5종 — 전역)
group_id 있음    : delivery_* · drone_robot_* · fire_* · surveillance_* · view_only_-_anyang (10종)
```
`role_role.group_id` 가 이미 "이 역할이 어느 테넌트 것인가"를 담고 있다.
**분리 정의(§W0-16 (b))는 새 개념을 만들 필요가 없다 — 이 열을 판정에 쓰면 된다.**

---

## 5. 재현 명령

```bash
docker exec postgres psql -U postgres -d database_guardianx -P pager=off -c "
SELECT u.id, u.username, u.is_active, u.is_superuser, l.group_id, g.name,
       (SELECT string_agg(r2.code, ',' ORDER BY r2.code) FROM user_coreuser_roles ur2
          JOIN role_role r2 ON r2.id=ur2.role_id WHERE ur2.coreuser_id=u.id) AS roles
FROM user_coreuser_roles ur
JOIN user_coreuser u ON u.id=ur.coreuser_id
LEFT JOIN user_profile_link l ON l.user_id=u.id AND l.deleted IS NULL
LEFT JOIN user_usergroup g ON g.id=l.group_id
WHERE ur.role_id=(SELECT id FROM role_role WHERE code='superuser')
ORDER BY l.group_id NULLS FIRST, u.id;"
```
