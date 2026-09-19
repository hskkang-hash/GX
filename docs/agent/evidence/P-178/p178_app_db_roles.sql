-- ═══════════════════════════════════════════════════════════════════════════
-- P-178 — 앱 DB 역할 분리: gx_app(DDL 없음) + gx_migrate(마이그레이션 전용)
-- 발행: 2026-09-18 · WO-GX-20260915-01 파 3 턴 2 · 차선 U56
--
-- ★★ 이 파일은 **집행되지 않았다.** 이번 턴은 D-209 규약의 ①②(조사 · 준비)까지다.
--    실제 GRANT · 실제 전환은 **창 2 이고 대표 결정**이다. 지금 DB 에 역할을 만들지
--    않았다 — 만들었다면 그 순간 앱이 무슨 권한으로 도는지가 바뀌고, 되돌리기가
--    「지우면 됨」이 아니게 된다.
--
-- ★ 비밀번호가 이 파일에 **없다.** `:app_password` · `:migrate_password` 는 psql
--   변수이고, 집행자가 `psql -v app_password="'...'"` 로 넣는다. 값을 여기 적는 순간
--   그 값은 저장소·백업·화면으로 흘러나간다(D-204 · D-319).
--
-- 실측 전제 [2026-09-18 · 개발 DB]
--   current_user           = postgres   (rolsuper=t · rolcreatedb=t · rolcreaterole=t)
--   current_database()     = database_guardianx
--   public 스키마 표       = 231
--   런타임 DDL             = 0곳 (grep: CREATE/ALTER/DROP TABLE·INDEX — 이주 파일과
--                            시험을 빼면 `migrate_bootstrap` 의 `call_command("migrate")`
--                            하나뿐이고 그것은 gx_migrate 의 일이다)
-- ═══════════════════════════════════════════════════════════════════════════

\set ON_ERROR_STOP on

-- ── ① 역할 둘 ────────────────────────────────────────────────────────────
-- ★ `NOSUPERUSER NOCREATEDB NOCREATEROLE` 을 **명시한다.** 기본값에 기대면
--   다음 사람이 이 파일만 읽고 「무엇이 없는지」를 모른다.
CREATE ROLE gx_app     LOGIN PASSWORD :'app_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
CREATE ROLE gx_migrate LOGIN PASSWORD :'migrate_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;

-- ── ② 접속 ───────────────────────────────────────────────────────────────
REVOKE ALL ON DATABASE database_guardianx FROM PUBLIC;
GRANT CONNECT ON DATABASE database_guardianx TO gx_app, gx_migrate;

-- ── ③ 스키마 ─────────────────────────────────────────────────────────────
-- gx_app 은 **USAGE 만**. CREATE 가 없으면 표·인덱스를 만들 수 없다 — 그것이 이 절의 본체다.
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE          ON SCHEMA public TO gx_app;
GRANT USAGE, CREATE  ON SCHEMA public TO gx_migrate;

-- ── ④ 앱 스키마 DML 만 ───────────────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES    IN SCHEMA public TO gx_app;
-- ★ 시퀀스를 빼먹으면 **모든 INSERT 가 죽는다** — 가장 흔한 누락이다.
GRANT USAGE, SELECT                  ON ALL SEQUENCES IN SCHEMA public TO gx_app;
GRANT ALL                            ON ALL TABLES    IN SCHEMA public TO gx_migrate;
GRANT ALL                            ON ALL SEQUENCES IN SCHEMA public TO gx_migrate;

-- ── ⑤ 앞으로 태어나는 표에도 (DEFAULT PRIVILEGES) ────────────────────────
-- ★ `FOR ROLE gx_migrate` 다 — **표를 만드는 쪽**의 기본 권한을 정해야 한다.
--   여기를 빼면 다음 마이그레이션이 만든 표에 gx_app 이 못 닿고, 그 장애는
--   **배포 다음날 처음** 보인다.
ALTER DEFAULT PRIVILEGES FOR ROLE gx_migrate IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO gx_app;
ALTER DEFAULT PRIVILEGES FOR ROLE gx_migrate IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO gx_app;

-- ── ⑥ 소유권은 옮기지 않는다 ─────────────────────────────────────────────
-- ⚠ `REASSIGN OWNED BY postgres TO gx_migrate` 를 **넣지 않았다.** 231개 표의 소유자를
--   한 문장으로 바꾸는 것은 되돌리기 어렵고, 지금 확인된 요구(앱이 DDL 을 못 하게 한다)에
--   필요하지도 않다. 필요해지는 날 따로 결정한다(대표).

-- ── ⑦ 확인 — 집행 직후 이 셋을 **눌러서** 본다 ───────────────────────────
-- \c database_guardianx gx_app
-- SELECT has_schema_privilege('gx_app','public','CREATE');   -- 기대: f
-- SELECT has_table_privilege('gx_app','django_migrations','SELECT');  -- 기대: t
-- CREATE TABLE gx_app_should_fail(i int);                    -- 기대: ERROR (permission denied)
