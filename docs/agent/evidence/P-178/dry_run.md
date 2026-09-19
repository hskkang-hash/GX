# P-178 앱 DB 역할 분리 — **dry-run** (턴 V · 차선 U56 · 2026-09-18)

> **집행하지 않았다.** D-209 규약의 ①·② 까지다 — 영향 조사(읽기 전용)와 준비물.
> 실제 GRANT · 실제 전환은 **창 2** 이고 **대표 결정**이다.
> 이 턴에 DB 에 만든 역할 **0** · 바꾼 권한 **0** · 바꾼 `.env` 값 **0**.

## 0. 무엇을 갚는가

세종 결정: 분리한다. `gx_app`(DDL 없음 · 앱 스키마 DML 만) + `gx_migrate`(마이그레이션 전용).
지금은 **앱이 superuser 로 돈다** — 그 사실을 먼저 실측으로 못박는다.

## 1. 지금 [실측 2026-09-18 · gx-shell → 개발 DB]

| 잰 것 | 값 |
|---|---|
| `current_user` | `postgres` |
| `rolsuper` / `rolcreatedb` / `rolcreaterole` | **t / t / t** |
| `current_database()` | `database_guardianx` |
| `public` 스키마 표 | **231** |
| 로그인 가능한 superuser 역할 | `postgres` · `pgroot` (**둘**) |
| 남아 있는 시험 DB | **12** (`test_gx_*` 9 · `test_database_guardianx*` 2 · `test_gx_fix1` 1) |
| 런타임 DDL(이주 파일·시험 제외) | **0곳** — `common/management/commands/migrate_bootstrap.py` 의 `call_command("migrate")` 하나뿐이고 그것은 `gx_migrate` 의 일이다 |

⇒ **DDL 없는 앱 역할이 실제로 가능하다.** 「앱이 도중에 표를 만든다」는 자리가 없다.
  (`delivery/services/processing_service.py` 의 `Truncate …` 주석 둘은 SQL 이 아니라
  파이썬 리스트 자르기다 — 이름만 보고 판정하지 않았다.)

## 2. 산출물

- `docs/agent/evidence/P-178/p178_app_db_roles.sql` — 역할·권한 SQL (비밀번호는 psql 변수)
- 아래 §3 compose 배선 diff
- 아래 §4 「무엇이 깨질 수 있나」

## 3. compose 배선 diff (제안 · **적용 안 함**)

지금 `backend` · `celery` · `beat` · `shell` 은 전부 `env_file: ./backend/.env` 하나를 읽고,
그 파일의 `DB_USER` 는 `postgres` 다. `environment:` 는 `env_file` 을 **덮는다** —
그래서 파일 하나를 고치지 않고 **서비스마다** 역할을 갈라 줄 수 있다.

```diff
   backend:
     env_file:
       - ./backend/.env
     environment:
       - GIT_SSH_COMMAND=ssh -o StrictHostKeyChecking=no -v
       - REDIS_HOST=redis
       - REDIS_PORT=6379
+      # ★ P-178 — 앱은 DDL 을 못 한다. 마이그레이션은 이 컨테이너가 하지 않는다.
+      - DB_USER=${DB_APP_USER:?DB_APP_USER 가 없다 — 뿌리 .env 를 보라}
+      - DB_PASSWORD=${DB_APP_PASSWORD:?DB_APP_PASSWORD 가 없다 — 뿌리 .env 를 보라}

   celery:
     environment:
+      - DB_USER=${DB_APP_USER:?DB_APP_USER 가 없다 — 뿌리 .env 를 보라}
+      - DB_PASSWORD=${DB_APP_PASSWORD:?DB_APP_PASSWORD 가 없다 — 뿌리 .env 를 보라}

   beat:
     environment:
+      - DB_USER=${DB_APP_USER:?DB_APP_USER 가 없다 — 뿌리 .env 를 보라}
+      - DB_PASSWORD=${DB_APP_PASSWORD:?DB_APP_PASSWORD 가 없다 — 뿌리 .env 를 보라}

   shell:
     environment:
+      # ★ 이 컨테이너만 마이그레이션·시험 DB 를 만든다 (OPS-24 와 같은 자리).
+      - DB_USER=${DB_MIGRATE_USER:?DB_MIGRATE_USER 가 없다 — 뿌리 .env 를 보라}
+      - DB_PASSWORD=${DB_MIGRATE_PASSWORD:?DB_MIGRATE_PASSWORD 가 없다 — 뿌리 .env 를 보라}
```

⚠ `:?` 를 쓴 이유: 이름이 없으면 **멈춘다.** 기본값을 `postgres` 로 두면 「분리했다」고
적힌 채 그대로 superuser 로 도는 날이 온다 — 그 상태는 지금보다 **나쁘다**(믿게 되므로).
⚠ 뿌리 `.env` 에 이름 넷이 새로 필요하다(`DB_APP_USER` · `DB_APP_PASSWORD` ·
`DB_MIGRATE_USER` · `DB_MIGRATE_PASSWORD`). **값을 만드는 것은 대표 결정**이다 —
이 턴에 `.env` 는 한 자도 안 건드렸다.
⚠ 재생성 창 함정: `environment:` 를 더하면 **컨테이너를 다시 만들어야** 적용된다
(`restart` 로는 안 된다). 창 2 의 순서표에 그 줄이 있어야 한다.

## 4. 무엇이 깨질 수 있나

| # | 깨지는 자리 | 왜 | 지금 할 수 있는 확인 |
|---|---|---|---|
| 1 | **시험 전부** | pytest 가 `CREATE DATABASE test_gx_*` 를 한다. `gx_app` 은 `NOCREATEDB` 라 한 줄도 못 돈다 | 시험은 `shell`(= `gx_migrate`)에서만 돈다. 그런데 `gx_migrate` 도 `NOCREATEDB` 다 — **창 2 에서 정해야 한다**: ㉠ `gx_migrate` 에 `CREATEDB` 를 준다 ㉡ 시험 전용 셋째 역할을 둔다. SQL 파일은 지금 ㉠㉡ 어느 쪽도 **안 골랐다**(고르는 것은 대표) |
| 2 | **다음 마이그레이션이 만든 표** | `ALTER DEFAULT PRIVILEGES` 를 빼면 `gx_app` 이 새 표에 못 닿는다. 장애는 **배포 다음날** 처음 보인다 | SQL ⑤가 그것이다. 창 2 에서 새 표 하나를 만들어 `gx_app` 으로 `SELECT` 해 본다 |
| 3 | **INSERT 전부** | 시퀀스 권한을 빼먹는 것이 가장 흔한 누락이다 | SQL ④의 `GRANT USAGE, SELECT ON ALL SEQUENCES` |
| 4 | **dj-core 의 숨은 DDL** | 이 저장소에서 0곳으로 쟀지만, **못 읽는 코드가 있다**(rj-core 번들). grep 은 `site-packages/core` 까지만 닿았다 | 창 2 에서 `gx_app` 으로 하루 돌려 `permission denied` 로그를 센다 — **0 을 초록으로 적지 않는다** |
| 5 | **`migrate_bootstrap --check`** | 앱 컨테이너가 기동 때 이것을 부르면 `django_migrations` 를 읽는다 — 읽기는 되지만 **적용은 안 된다.** 「미적용이 있다」로 죽을 수 있다 | 기동 명령을 창 2 전에 읽는다 |
| 6 | **되돌리기** | `DROP ROLE` 은 그 역할이 소유한 것이 없어야 한다. 소유권을 안 옮겼으므로(SQL ⑥) 되돌리기는 **`.env` 두 줄을 옛 값으로 + 컨테이너 재생성**이다 | 그래서 `REASSIGN OWNED` 를 안 넣었다 |
| 7 | **연결 풀** | `dj_db_conn_pool` 이 기동 때 자격을 잡는다 — 자격이 틀리면 **첫 요청이 아니라 기동에서** 죽는다. 그것이 낫다(조용히 반쯤 도는 것보다) | 창 2 에서 기동 로그를 본다 |

## 5. OPS-24 — 시험 DB 격리 회수 (이 조사에서 함께 나온 수)

지금 남아 있는 시험 DB **12**. 차선마다 이름을 가르는 규약(P-18)은 섰지만 **지우는 규약이
없다.** 그래서 이름만 늘고 디스크는 안 돌아온다. 창 2 항목 「시험 DB 4 삭제(127MB)」가
그 일부이고, OPS-24 는 그것을 **한 번의 삭제가 아니라 규약으로** 만든다.

    test_gx_f · test_gx_q · test_gx_u3b · test_gx_u24 · test_gx_fix1 · test_gx_lane_f ·
    test_gx_lane_u3 · test_gx_lane_u24 · test_gx_lane_u24b · test_gx_lane_u56 ·
    test_database_guardianx · test_database_guardianx_e2e

⚠ **지우지 않았다.** 어느 것이 도는 차선의 것인지 이 차선은 모른다 — 남의 시험을
지우는 것은 남의 빨강을 만드는 일이다. 목록만 낸다.


---

# 턴 W 이어서 — **P-187 로 이름이 바뀌었고, 여전히 dry-run 이다** (2026-09-19 · U56)

> 세종 P-187 판정문: 「dry-run SQL · compose 배선 · OPS-23/24 **등재만**. 전환은 창 2.」
> **이 턴에도 집행하지 않았다.** DB 에 만든 역할 **0** · 바꾼 권한 **0** ·
> 바꾼 `.env` 값 **0** · 돌린 `GRANT`/`REVOKE` **0줄**.

## 6. 다시 쟀다 — 전제가 아직 참인가 [실측 2026-09-19 · gx-shell → 개발 DB · 읽기만]

| 잰 것 | 턴 V(09-18) | 턴 W(09-19) | 읽는 법 |
|---|---|---|---|
| `current_user` | `postgres` | **`postgres`** | 그대로다 — 앱은 아직 superuser 로 돈다 |
| `rolsuper`/`rolcreatedb`/`rolcreaterole` | t/t/t | **t/t/t** | 그대로 |
| `public` 스키마 표 | 231 | **231** | 그대로 |
| 로그인 가능한 superuser | `postgres`·`pgroot` | **`postgres`·`pgroot`** | 그대로 |
| 역할 `gx_app`·`gx_migrate` | 없음 | **없음(0)** | ★ **이 줄이 「안 돌렸다」의 증거다** — `SELECT rolname FROM pg_roles WHERE rolname IN ('gx_app','gx_migrate')` → 빈 결과 |
| 남은 시험 DB | 12 | **12** (목록은 아래 · 한 벌 바뀌었다) | 수는 같은데 **이름이 돈다** — 회수 규약이 없다는 뜻이다(OPS-24) |

턴 W 의 시험 DB 12:

    test_database_guardianx · test_database_guardianx_e2e · test_gx_fix1 ·
    test_gx_lane_f · test_gx_lane_u24 · test_gx_lane_u24b · test_gx_lane_u3 ·
    test_gx_lane_u56 · test_gx_u24 · test_gx_u24c · test_gx_u3b · test_gx_u56

⚠ 턴 V 목록과 대 보면 `test_gx_f`·`test_gx_q` 가 **사라지고** `test_gx_u24c`·`test_gx_u56`
이 **새로 생겼다**. 총수는 12 로 같다 — 그래서 **총수만 보면 아무 일도 없어 보인다.**
이것이 OPS-24 가 「한 번의 삭제」가 아니라 **회수 규약**이어야 하는 이유다: 지우는
사람이 없으면 수는 우연히 제자리이고, 그 제자리는 안정이 아니라 **덮어씀**이다.

⚠ **지우지 않았다.** 어느 것이 도는 차선의 것인지 이 차선은 모른다.

## 7. 이 턴에 더한 준비물 (집행이 아니다)

| 무엇 | 어디 | 상태 |
|---|---|---|
| 역할·권한 SQL | `p178_app_db_roles.sql` (턴 V) | **그대로 · 안 돌렸다** |
| compose 배선 diff | 위 §3 (턴 V) | **그대로 · 안 붙였다** |
| `.env` 이름 넷 | **`.env.example`** 「앱 DB 역할 분리」 절 (턴 W) | **이름만 · 전부 주석 · 값 없음** |
| 대장 등재 | **`docs/agent/remaining_40.md` §2-2** — OPS-23 · OPS-24 (턴 W) | **등재함** |

⚠ `.env.example` 에 적은 넷은 **전부 `#` 로 막아 두었다.** 주석을 벗기는 순간
`docker-compose` 가 `${DB_APP_USER:?...}` 를 요구하게 되는 것이 아니라(그 배선은
아직 안 붙였다), **사람이 값을 채워야 하는 줄**이 생긴다. 값은 대표 결정이다.

## 8. 창 2 에 대표가 **고를 것 둘** (이 차선이 안 골랐다)

1. **시험 DB 를 누가 만드는가.** pytest 는 `CREATE DATABASE test_gx_*` 를 한다.
   `gx_app` 도 `gx_migrate` 도 `NOCREATEDB` 다 — 그대로 전환하면 **시험이 전부 죽는다.**
   ㉠ `gx_migrate` 에 `CREATEDB` 를 준다(마이그레이션 역할이 커진다)
   ㉡ 시험 전용 셋째 역할을 둔다(역할이 셋이 된다)
   SQL 파일은 **어느 쪽도 안 골랐다.**
2. **뿌리 `.env` 의 값 넷.** 이름은 `.env.example` 에 섰다. 값은 대표가 만든다.

## 9. 되돌리기

`DROP ROLE` 은 그 역할이 소유한 것이 없어야 한다 — SQL ⑥ 이 소유권을 안 옮겼으므로
되돌리기는 **`.env` 두 줄을 옛 값으로 + 컨테이너 재생성**이다. 그것이 `REASSIGN OWNED`
를 안 넣은 이유이고, 이 절은 창 2 순서표의 마지막 줄이어야 한다.
