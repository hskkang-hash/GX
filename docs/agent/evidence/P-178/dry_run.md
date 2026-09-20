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

---

# 턴 X — **절차서를 냈다. 여전히 dry-run 이다** (2026-09-20 · U56)

> 세종 P-194 가 창을 2a/2b 로 쪼갰다. 이 차선의 몫은 **창 2a 의 절차서**이고,
> 창은 조율자가 연다. **이 턴에도 집행하지 않았다**: DB 에 만든 역할 **0** ·
> 바꾼 권한 **0** · 돌린 `GRANT`/`REVOKE` **0줄** · 바꾼 `.env` 값 **0** ·
> 재생성한 컨테이너 **0**.

## 10. 산출물 — `RUNBOOK_창2a.md`

`docs/agent/evidence/P-178/RUNBOOK_창2a.md` · **16단계** · **★(되돌릴 수 없음) 셋** ·
**「여기서 멈춤 — 대표 결정 필요」 한 자리(C0)에 결정 세 칸**.
이 문서(`dry_run.md`)는 **조사**이고 그것은 **순서**다 — 둘을 한 파일에 두지 않았다.

## 11. 다시 쟀다 [실측 2026-09-20 13:1x~13:2x · 읽기만]

| 잰 것 | 턴 V(09-18) | 턴 W(09-19) | **턴 X(09-20)** |
|---|---|---|---|
| `current_user` | `postgres` | `postgres` | **`postgres`** |
| super/createdb/createrole | t/t/t | t/t/t | **t/t/t** |
| `public` 스키마 표 | 231 | 231 | **231** |
| 로그인 superuser | 둘 | 둘 | **둘** (`postgres`·`pgroot`) |
| 역할 `gx_app`·`gx_migrate` | 없음 | 없음 | ★ **빈 결과** (`gx_test` 까지 함께 물었다) |
| 남은 시험 DB | 12 | 12 | **13 · 426MB** |

새로 쟀고 전엔 없던 수:
**PostgreSQL 18.1** · 로그인 **가능한 역할은 둘뿐** · **PUBLIC 이 `schema public` 에
`USAGE,CREATE`** 를 갖고 있다(18 의 기본이 아니다 — 누가 되돌려 줬다) ·
시험 DB **소유자 전부 `postgres`**.

## 12. ★ 자진 오판 — **§3 의 compose diff 는 집행 수단이 아니다**

§3 은 「지금 넷은 전부 `env_file: ./backend/.env` 를 읽고 그 파일의 `DB_USER` 는
`postgres`」라고 적었다. **그 전제가 틀렸다** [실측 2026-09-20]:

```
도는 컨테이너 10개 전부 compose 라벨이 비어 있다 (손으로 docker run 한 것)
뿌리 .env 의 키: MINIO_ROOT_USER · MINIO_ROOT_PASSWORD · MINIO_BUCKET_NAME ·
                 GX_STORAGE_CAPACITY_GB  — DB_USER 도 DB_PASSWORD 도 **0줄**
앱 넷의 DB 자격 출처: --env-file C:/GuardianX-vault/recreate/<이름>.new.env
DB_USER 넷이 같다: sha256 앞 12자 a942b37ccfaf = sha256("postgres") 앞 12자
```

⇒ 「compose 를 고치는 것은 선언이지 집행이 아니다」(위임 이의 #3)가 **내 산출물에도
걸린다.** `RUNBOOK_창2a.md` C4 는 compose 가 아니라 **env-file 교체**로 썼다.
§3 의 diff 는 *compose 가 이 컨테이너들을 소유하는 날*을 위한 **선언으로만** 남긴다.

## 13. 턴 X 에 새로 드러난 순서 제약 — OPS-24 가 OPS-23 보다 먼저다

시험 DB 13개의 **소유자가 전부 `postgres`** 이고 `DROP DATABASE` 는 **소유자나
superuser** 라야 한다. `CREATEDB` 를 줘도 남의 DB 는 못 지운다.
⇒ 그 13개를 회수하기 전에 `gx-shell` 을 `gx_migrate` 로 옮기면 pytest 가
`--create-db`·`--reuse-db` 어느 쪽이든 **「permission denied to drop database」로 죽는다.**
두 절을 가른 것이 행정이 아니라 **집행 순서**였다는 것이 여기서 처음 수로 나왔다.

## 14. 시험 DB — **총수는 거짓말한다**(세 턴째 같은 증거 · 이번엔 근거를 셋으로)

```
턴 V 12 → 턴 W 12 → 턴 X 13.  총수만 보면 「거의 안 변했다」이다.
그런데 턴 W 의 test_gx_u56 은 **사라졌고**, test_gx_f · test_gx_s 가 **새로 생겼다.**
지금 살아 있는 것 둘: test_gx_f(11연결) · test_gx_s(8연결) — **절대 안 지운다.**
회수 후보 3 (95MB): test_database_guardianx · test_database_guardianx_e2e · test_gx_u3b
```
회수 규약의 세 근거와 재는 법은 `RUNBOOK_창2a.md` §C0-ⓒ 에 있다.
⚠ **지우지 않았다.** 이 차선이 이 턴에 지운 DB **0개**.

## 15. ★ **같은 턴 안에서 40분 만에 다시 쟀다 — 총수는 13 그대로인데 세 자리가 돌았다**

「총수는 거짓말한다」를 세 턴에 걸쳐 적어 왔는데, 이번엔 **한 턴 안에서** 잡혔다.

| 잰 시각 | 총수 | 합 | 무슨 일이 있었나 |
|---|---|---|---|
| 13:2x | **13** | 426MB | `test_gx_f`(11연결) · `test_gx_s`(8연결) 이 살아 있었다 |
| 14:0x | **13** | 428MB | `test_gx_s` **사라짐** · `test_gx_u56` **새로 생김**(이 차선이 시험을 돌렸다) · `test_gx_u24` 는 **재생성됐다**(`xact_commit` 3,894 → **691** — 카운터가 리셋됐다는 것은 DB 가 지워지고 다시 만들어졌다는 뜻이다) |

⇒ **40분 동안 세 자리가 바뀌었는데 총수는 13 → 13 이다.**
  총수를 보는 사람은 **아무 일도 없었다고 읽는다.**
  회수 규약이 총수가 아니라 **DB 마다 세 근거**(`numbackends` · `xact_commit` ·
  디렉터리 시각)로 서야 하는 이유가 이것이다.

⇒ 그리고 **회수 후보 셋은 두 판 모두 같았다**: `test_database_guardianx` ·
  `test_database_guardianx_e2e` · `test_gx_u3b` (둘 다 `numbackends 0` · `xact_commit 0`).
  **돌아다니는 것과 버려진 것은 이 규약으로 실제로 갈린다** — 후보가 흔들리지 않았다는
  것이 그 증거다.

⚠ 이 차선이 이 턴에 만든 시험 DB **1개**(`test_gx_u56` · 표적 pytest) · 지운 것 **0개**.
