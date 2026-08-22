# W0-16 (d) — 대체역할 HTTP 시험: 자기 테넌트만 보이는가

**실행** 2026-08-22 · **환경** 로컬 기동본 · **대상 DB** `rolesplit_guardianx`
(= `database_guardianx` 의 TEMPLATE 복제본. **운영 복제본은 무변경** · D-245)
**엔드포인트** `GET /api/stream-monitors/stream-monitors` — W0-14 프로브와 **같은 엔드포인트·같은 방법**

---

## 0. 판정

> **경로①(역할 우회)은 닫혔다.** Anyang 운영자가 보던 남의 것 **15건 → 1건**.
> 남은 1건은 경로②(`created_by IS NULL`)이며 **W0-13 의 대상**이다. 예측과 일치한다.

---

## 1. 무엇을 바꾸고 쟀나

```
① scripts/role_split_local.py --apply
     gaion_global_admin(id=26)  신설 · superuser 권한행 복제(menus 101 · tabs 27) · GAION 6계정에 부여
     tenant_admin_6   (id=27)  신설 · 같은 권한행 복제               · Anyang 7계정에 부여
② scripts/role_split_local.py --apply --revoke 4
     파일럿 1계정(`man`, Anyang)에서만 레거시 superuser 역할 회수
③ scripts/probe_tenant_isolation.py 재실행 (W0-14 와 동일)
```

**대조군을 남겼다**: Gaion 의 `admin` 은 레거시 역할을 **그대로 두었다.** 값이 안 변해야 한다 —
변화가 환경 탓이 아니라 역할 회수 탓임을 이 한 줄이 증명한다.

## 2. 결과 (before = `evidence/W0-14/http_leak_probe.md` · 같은 데이터·같은 방법)

| 테넌트 | 계정 | 역할 (after) | 본 건수 | 자기것 | group NULL | **남의 것** | 판정 |
|---|---|---|---:|---:|---:|---:|---|
| **Anyang** | **`man`** | before: `superuser` | 30 | 7 | 8 | **15** | — |
| **Anyang** | **`man`** | **after: `tenant_admin_6`** | **9** | **7** | **1** | **1** | **경로① 닫힘** |
| Gaion (대조) | `admin` | before: `superuser` | 30 | 4 | 8 | 18 | — |
| Gaion (대조) | `admin` | after: `gaion_global_admin`,**`superuser` 유지** | 30 | 4 | 8 | 18 | **무변화 — 예상대로** |
| ETRI-Group | `thanh` | `admin` (무변경) | 3 | 0 | 3 | 0 | 무변화 |
| Group Default | `tuan` | `admin` (무변경) | 0 | 0 | 0 | 0 | 무변화 |
| Thailand | `thai01` | `delivery_admin` (무변경) | 0 | 0 | 0 | 0 | 무변화 |

### 2-1. `man` 에게 남은 1건 — 이것이 경로②다

```
id=8  Q02-0002  소유 group=7(Gaion)  created_by=NULL
```
`created_by IS NULL` 은 dj-core `core/base.py:430` 의 **명시적 OR** 로 통과한다.
**역할을 아무리 정리해도 이 경로는 닫히지 않는다** — W0-13(백필)의 대상이고,
D-247 이 두 티켓을 독립으로 둔 이유가 이것이다.

### 2-2. group NULL 8 → 1

소유 테넌트가 없는 레코드(`group_id IS NULL` 13건)도 대부분 사라졌다. 남은 1건은 §2-1 과 같은 레코드다.

---

## 3. 무중단 확인 — 화면이 죽지 않았다

`man` 은 레거시 역할을 잃었지만 **HTTP 200 으로 자기 테넌트 7건을 그대로 본다.**
대체역할이 `superuser` 역할의 메뉴/탭 권한 행(menus 101 · tabs 27)을 복제했기 때문이다.
복제 없이 역할만 뗐으면 `core/role/permission.py` 의 경로 권한 검사에서 화면이 통째로 막혔다.

> **한계**: 이 시험은 목록 API 1종으로 잰 것이다. "모든 화면이 그대로"를 증명하지 않는다.
> 나머지 화면은 W0-14 의 라우트 스코프 롤아웃(652개)에서 함께 확인한다.

---

## 4. 부수 발견 2건 (W0-16 범위 밖 · 기록만)

### 4-1. ★ 로그인 rate limit 이 HTTP **500** 으로 나간다 (→ W0-18)
프로브 9계정 중 6번째부터 로그인이 500 이다. 원인은 인증 실패가 아니라 **속도 제한**이다.
```
django_ratelimit.exceptions.Ratelimited        ← 핸들러 밖에서 raise
ERROR Internal Server Error: /api/v1/auth/login → HTTP 500
```
표준은 **429 Too Many Requests** 다. 500 이면 클라이언트·모니터링이 "서버 장애"로 읽는다.
W0-18(계약 정합)의 상태코드 목록에 추가한다. *이번 시험의 SKIP 4건은 이 때문이며 격리와 무관하다.*

### 4-2. 목록 API 는 외부 스트리밍 서버가 없으면 여전히 500 (→ W0-17)
이번 시험은 `STREAM_URL` 을 로컬 스텁(`{"items":[]}`)으로 돌려 200 을 얻었다.
스텁 없이는 이 엔드포인트가 통째로 500 이다 — **W0-17 의 대상이 이것이다.**
격리 시험을 하려면 매번 스텁이 필요하다는 사실 자체가 저하 운전 부재의 증거다.

---

## 5. 재현

```bash
# 0) 복제본 (운영 복제본은 건드리지 않는다)
docker exec postgres psql -U postgres -c "CREATE DATABASE rolesplit_guardianx TEMPLATE database_guardianx"
docker exec -e DB_NAME=rolesplit_guardianx gx-shell python manage.py migrate

# 1) 역할 분리 — dry-run 으로 계획을 먼저 본다 (D-209)
docker exec -i gx-shell python - < scripts/role_split_local.py
docker exec -i -e DB_NAME=rolesplit_guardianx gx-shell python - --apply < scripts/role_split_local.py
docker exec -i -e DB_NAME=rolesplit_guardianx gx-shell python - --apply --revoke 4 < scripts/role_split_local.py

# 2) 외부 스트리밍 스텁 + 서버 (스텁이 없으면 목록 API 가 500 — §4-2)
docker exec -d gx-shell python -c "<127.0.0.1:8099 에서 {'items':[]} 를 주는 최소 HTTP 서버>"
docker exec -d -e DB_NAME=rolesplit_guardianx -e STREAM_URL=http://127.0.0.1:8099 gx-shell \
  sh -c "cd /app && python manage.py runserver 0.0.0.0:8000 --noreload"

# 3) 프로브 (W0-14 와 동일 · 비밀번호는 회차마다 다른 값을 인자로 — 파일에 적지 않는다)
docker exec -i -e DB_NAME=rolesplit_guardianx gx-shell python - '<이번 회차 비밀번호>' \
  < scripts/probe_tenant_isolation.py
```

**정리**: 시험이 끝나면 `DROP DATABASE rolesplit_guardianx` — 이 복제본에는 프로브가 재설정한
비밀번호가 남는다 (D-245 와 같은 이유).
