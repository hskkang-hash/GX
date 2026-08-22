# WP-1 goal 직접 실측 — HTTP 레벨 교차 테넌트 노출

**실행** 2026-08-22 · **에이전트** Claude Code · **환경** 로컬 기동본(`review/LOCAL_BRINGUP_결과.md`)
**대상 데이터** `02_database_gx_deploy.sql`(2026-02-10 운영 덤프)의 **로컬 복제본** — 운영에 접속하지 않았다
**대상 엔드포인트** `GET /api/stream-monitors/stream-monitors` (dj-core `BaseModelWithGroup` · `group` FK)

> **goal**: *group A 토큰으로 group B 데이터에 도달 불가함을 HTTP 레벨로 증명*
>
> **판정: 거짓이다. 도달한다.** 그리고 경로가 **두 개**다.

---

## 0. 왜 이 문서가 따로 있나

`tests/test_tenant_isolation.py` 의 `TenantIsolationAPITest` 가 픽스처 결함으로 죽어 있고(P-LOCAL-2),
그 파일은 절대금지 #5 로 수정이 막혀 있다. 그래서 **저장소 밖에 별도 프로브를 만들어** 같은 질문을 물었다.
저장소 코드는 한 줄도 바뀌지 않았다. 프로브는 `scripts/probe_tenant_isolation.py`.

이 방식이 오히려 낫다 — 합성 픽스처가 아니라 **실제 테넌트·실제 사용자·실제 레코드**로 물었다.

---

## 1. 진실 대장 (DB 가 말하는 소유 관계)

```
stream_monitors_streammonitor  총 39건 (deleted IS NULL)
  · group_id 별 : Anyang(6)=7  Gaion(7)=7  Fire_Drone(11)=11  Gongju(14)=1  NULL=13
  · created_by IS NULL : 15건
  · group_id  IS NULL : 13건
```

## 2. 실측 — 테넌트 9곳, 각 1명씩 로그인해 목록을 받았다

사용자 선정 기준: 그 그룹 소속 · `is_active` · **`is_superuser=false`** · 역할 1개 이상 · id 최소값.
각자에게 로컬 전용 비밀번호를 설정하고 `POST /api/v1/auth/login` 으로 실제 토큰을 받았다.

| 테넌트 | 사용자 | 역할 | DB `is_superuser` | 본 건수 | 자기것 | group NULL | **남의 것** |
|---|---|---|---|---|---|---|---|
| ETRI-Group | thanh | admin | false | 3 | 0 | 3 | 0 |
| Group Default | tuan | admin | false | 0 | 0 | 0 | 0 |
| **Anyang** | **man** | **superuser** | **false** | **30** | 7 | 8 | **15** |
| **Gaion** | **admin** | **superuser** | **false** | **30** | 4 | 8 | **18** |
| Thailand | thai01 | delivery_admin | false | 0 | 0 | 0 | 0 |
| Fire_Drone | fire_user1 | fire_admin,fire_user | false | 10 | 10 | 0 | 0 |
| DRONE-ROBOT | dronerobot_user_1 | drone_robot_admin | false | 0 | 0 | 0 | 0 |
| Gongju | gongju_admin01 | delivery_admin | false | 1 | 1 | 0 | 0 |
| GeumSan-ETRI | order_geumsan | order | false | 0 | 0 | 0 | 0 |

**추가 실측** (별도 회차, 같은 방법): Anyang 의 `anyang01`(역할 `delivery_admin`) →
본 건수 9 · 자기것 7 · group NULL 1 · **남의 것 1** — Gaion 소유 `Q02-0002`.
그 레코드의 `created_by` 는 **NULL** 이다.

원자료: `leak_matrix.json`

---

## 3. 경로 ① — **`superuser` 역할** (규모가 큰 쪽)

dj-core `core/base.py:308`:

```python
is_super = user.is_superuser or user.roles.filter(code='superuser').exists()
...
if is_super:
    queryset._permission_context = {...}
    return queryset          # ← 그룹 필터 없음. 전량 반환.
```

**`is_superuser` 플래그가 false 여도 `code='superuser'` 역할이 붙으면 전 테넌트가 열린다.**

### 누가 갖고 있나 — 13명, 3개 테넌트에 흩어져 있다

| 소속 테넌트 | `superuser` 역할 보유(활성) | 그중 DB `is_superuser=true` |
|---|---|---|
| **Anyang** | **7** | **0** |
| **Gaion** | **4** | **0** |
| Group Default | 2 | 0 |
| **계** | **13** | **0** |

> **13명 전원이 DB 플래그상으로는 평범한 사용자다.**
> `is_superuser` 를 기준으로 특권 계정을 세는 감사·점검은 **0명**을 보고한다.

### 실제로 무엇이 새는가

| 보는 사람 | 새어 나온 상대 테넌트 | 건수 |
|---|---|---|
| `man` (Anyang · superuser) | Gaion 4 · **Fire_Drone 10** · Gongju 1 | **15** |
| `admin` (Gaion · superuser) | **Anyang 7** · **Fire_Drone 10** · Gongju 1 | **18** |

**Fire_Drone 은 자기 소유 11대 중 10대를 두 외부 테넌트에 노출하고 있다.**
그리고 Fire_Drone 자신의 사용자(`fire_user1`)는 남의 것을 하나도 못 본다 —
**노출은 일방적이다. 당하는 쪽은 그 사실을 알 수 없다.**

> **이것이 결함인지 사양인지는 대표가 판정할 사항이다.** `superuser` 라는 이름의 역할이
> 전 테넌트를 보는 것 자체는 의도일 수 있다. 문제는 **그 역할이 고객 테넌트 안에 배포돼 있다**는 것이다.
> Anyang 직원 7명이 Gaion·Fire_Drone 의 운영 데이터를 읽을 수 있다.

## 4. 경로 ② — **`created_by IS NULL`** (규모는 작고 원인은 깊다)

dj-core `core/base.py:430`:

```python
return queryset.filter(
    Q(**{group_field_name: user_group}) |
    Q(created_by__isnull=True)          # ← group 이 정확해도 이 한 줄이 뚫는다
)
```

**실증**: `anyang01`(superuser 아님)이 Gaion 소유 `Q02-0002` 를 봤다. 그 레코드의 `created_by` 는 NULL 이다.
`thanh`(ETRI)가 본 3건도 전부 `group_id`·`created_by` 가 NULL 인 레코드다.

W0-11 §5-2 가 정적 분석으로 예고한 구멍이 **HTTP 레벨에서 실제로 재현됐다.**
W0-13 이 실측한 **`created_by IS NULL` 65.9%** 가 이 경로의 모수다.

---

## 5. 무엇이 증명됐나

| 문장 | 판정 |
|---|---|
| group A 토큰으로 group B 데이터에 도달 **불가**하다 | **거짓** |
| 도달 경로가 있다 | **참 — 2개** |
| 경로 ①(`superuser` 역할)이 규모가 크다 | **참 — 13계정 / 3테넌트** |
| 경로 ②(`created_by IS NULL`)가 W0-11 예고대로 존재한다 | **참** |
| 두 경로 모두 **뷰 레벨 스코프(W0-14)로만 막힌다** | ORM 매니저 안에 원인이 있고 그 매니저는 §0.4 금지구역이다 |

**W0-13 C안(뷰 레벨 스코프)이 유일한 경로라는 판단이 여기서 확정된다.**
경로 ①은 특히 그렇다 — ORM 매니저가 **의도적으로** 필터를 건너뛰는 지점이므로,
매니저를 신뢰하는 어떤 설계도 이것을 막을 수 없다.

## 6. 이 실측의 한계 (적어 둔다)

- **엔드포인트 1개**만 봤다. 652개 라우트 중 하나다. 다른 라우트가 더 나을 이유도 나쁠 이유도 없다.
- **테넌트당 1명**만 봤다. 같은 테넌트 안에서도 역할에 따라 결과가 갈린다 — `man` vs `anyang01` 이 그 예다.
- 데이터는 **2026-02-10 덤프**다. 그 이후 운영 데이터는 다르다.
- `seen=0` 인 테넌트 6곳은 격리가 잘 돼서가 아니라 **소유 레코드가 없거나 `drone__active` 조건에
  걸린 것**일 수 있다. 격리 성공의 증거로 읽으면 안 된다.
- 프로브는 대상 사용자의 **비밀번호를 로컬 복제본에서 재설정**했다. 운영에는 손대지 않았다.
  비밀번호 재사용 금지 정책은 끄지 않았고 이력도 지우지 않았다 — 실행마다 새 값을 썼다.

## 7. 재현

```bash
# 로컬 기동 (review/LOCAL_BRINGUP_결과.md §1-1) 후
docker exec postgres psql -U postgres -c "CREATE DATABASE probe_guardianx TEMPLATE database_guardianx"
# DB_NAME=probe_guardianx 로 컨테이너를 띄우고
python manage.py migrate
python manage.py runserver 0.0.0.0:8000 --noreload &
python scripts/probe_tenant_isolation.py '<이번 회차 비밀번호>'
```

> 외부 스트리밍 서버가 없으면 이 엔드포인트는 **HTTP 500** 이다(§8). 스텁이 필요하다.

## 8. 부수 발견 3건 (격리와 별개)

1. **외부 의존 1개가 죽으면 목록 API 전체가 죽는다.** `GET /api/stream-monitors/stream-monitors` 는
   `STREAM_URL` 을 동기 호출하고, 실패하면 500 을 낸다. 저하 운전(graceful degradation)이 없다.
2. **권한 거부를 HTTP 200 으로 반환한다.** 본문은 `{"success": false, ..., "status_code": 403}` 인데
   HTTP 상태는 200 이다. 상태 코드로 판정하는 클라이언트·시험·스캐너는 **성공으로 읽는다.**
3. **`/api/v1/auth/delete-session` 은 body 로 호출할 수 없다.** 핸들러가 `data: dict` 로 선언돼
   ninja 가 쿼리 파라미터로 잡는다(`loc: ["query","data"]`). 문서화된 사용법대로 부르면 422 다.
4. `POST /api/token/pair` 로 받은 토큰은 `CustomJWTAuth` 가 거부한다(`user.token` 미설정 →
   `core/auth.py:38` "Token expired"). 실제 로그인 경로는 `POST /api/v1/auth/login` 이다.
   **공개된 표준 엔드포인트가 동작하지 않는 것**이므로 연동 문서에 영향이 있다.
