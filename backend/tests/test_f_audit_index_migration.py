# -*- coding: utf-8 -*-
"""P-205 — **감사 인덱스가 마이그레이션으로 태어나는가** (턴 X · 차선 F).

왜 이 시험이 있어야 하나 — **「지금 DB 에서 빠르다」는 「다른 데서도 빠르다」가 아니다**
-------------------------------------------------------------------------------------
턴 X 에 대표 결정으로 `gx_audit_logger_dt_idx` 를 **운영 DB 에 직접** 넣었고, 그 자리가
실제로 닫혔다 [조율자 실측]:

    전 : Parallel Seq Scan · Rows Removed by Filter 47,203(워커마다) · 42.227 ms
    후 : Index Only Scan   · 54행 직행 · 버린 행 0                    ·  0.242 ms

그런데 **마이그레이션에는 없었다.** 그러면 스테이징·재생성 DB 는 인덱스 **없이** 태어나고,
`CoreLoggingMiddleware` 가 요청마다 감사 한 행을 쓰는 이 표는 거기서 **날마다 느려진다.**
`common/migrations/0001_audit_logger_name_index.py` 가 그 간격이고, 이 시험이 그 파일이
**있다**가 아니라 **듣는다**를 잰다.

무엇을 재나 — 네 가지
---------------------
    ① **규격** (DB 없이)    `atomic=False` · `IF NOT EXISTS` · 역방향 `DROP` · 모델 상태 안 건드림
    ② **태어나는가**        마이그레이션을 **처음부터** 돌린 DB 에 인덱스가 있는가
    ③ **성한가**            `indisvalid` — 실패한 CONCURRENTLY 는 **INVALID 인덱스**를 남기고,
                            그건 이름만 있고 플래너가 안 쓴다(있는데 안 듣는 가장 나쁜 모양)
    ④ **두 번 걸어도 되나**  이미 있는 DB 에서 **no-op** 인가 (`IF NOT EXISTS` 의 요점)

★ ②는 **실 마이그레이션 DB 에서만 뜻이 선다.** `--nomigrations` 로 돌리면 표를 모델에서
  바로 만들어서 **이 마이그레이션이 아예 안 돌고**, 그래도 시험은 초록이 될 수 있다 —
  그 초록은 아무것도 안 잰 초록이다. 그래서 `_migrations_ran()` 으로 **먼저 가르고**,
  안 돌았으면 **건너뛴다(skip)**. 건너뛴 것은 통과가 아니다.

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings -e DB_TEST_NAME=test_gx_f_mig \\
        gx-shell python -m pytest tests/test_f_audit_index_migration.py -q -p no:randomly
    (⚠ `--nomigrations` 를 주지 말 것 — 주면 ②③④ 가 건너뛰어진다)
"""
from __future__ import annotations

import pytest
from django.db import connection

from common.migrations import __name__ as _pkg           # noqa: F401  (패키지 존재 확인)

MIGRATION = "common.migrations.0001_audit_logger_name_index"
INDEX_NAME = "gx_audit_logger_dt_idx"
TABLE_NAME = "logger_auditlogs"


def _module():
    """마이그레이션 모듈. 이름에 숫자가 있어 `import` 문으로는 못 가져온다."""
    import importlib

    return importlib.import_module(MIGRATION)


def _one(sql, *params):
    with connection.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    return row


def _migrations_ran() -> bool:
    """이 DB 가 **마이그레이션으로** 세워졌나. 아니면 ②③④ 는 잴 것이 없다."""
    row = _one("SELECT count(*) FROM information_schema.tables "
               "WHERE table_name = 'django_migrations'")
    if not row or not row[0]:
        return False
    row = _one("SELECT count(*) FROM django_migrations WHERE app=%s AND name=%s",
               "common", "0001_audit_logger_name_index")
    return bool(row and row[0])


needs_migrations = pytest.mark.skipif(
    False, reason="")          # 실제 판단은 픽스처가 한다(DB 가 있어야 물을 수 있다)


# ── ① 규격 — DB 없이 돈다 ──────────────────────────────────────────────────
def test_트랜잭션_밖에서_돈다():
    """`CREATE INDEX CONCURRENTLY` 는 트랜잭션 안에서 **못 돈다.**

    `atomic = True` 로 두면 `CREATE INDEX CONCURRENTLY cannot run inside a
    transaction block` 으로 죽는다 — 그리고 그 죽음은 배포 한가운데서 난다.
    """
    assert _module().Migration.atomic is False, "atomic=False 가 아니면 배포에서 죽는다"


def test_이미_있는_DB_에서_안_터지게_되어_있다():
    sql = _module().FORWARD_SQL.upper()
    assert "IF NOT EXISTS" in sql, "IF NOT EXISTS 가 없으면 있는 DB 에서 두 번째 적용이 죽는다"
    assert "CONCURRENTLY" in sql, "감사 표는 쓰기 길목이다 — 잠그면 전 요청이 멈춘다"


def test_되돌릴_수_있다():
    sql = (_module().REVERSE_SQL or "").upper()
    assert "DROP INDEX" in sql, "역방향이 없으면 되돌릴 수 없는 변경이다"
    assert "IF EXISTS" in sql, "인덱스 없이 태어난 DB 를 되감을 때 죽는다"


def test_남의_모델_상태는_안_건드린다():
    """`logger_auditlogs` 는 dj-core 의 표다(§0.4). **표만 빌리고 선언은 안 만진다.**

    `state_operations` 를 주면 우리 마이그레이션이 남의 모델 상태를 들고 있게 되고,
    dj-core 를 올리는 날 두 선언이 어긋난다.
    """
    ops = _module().Migration.operations
    assert len(ops) == 1, "한 벌이어야 한다 — 곁가지가 붙으면 되돌리기가 반쪽이 된다"
    assert not getattr(ops[0], "state_operations", None), "남의 모델 상태를 들지 않는다"
    deps = dict(_module().Migration.dependencies)
    assert "logger" in deps, "표가 먼저 있어야 인덱스를 얹는다 — 읽기 의존은 있어야 한다"


def test_표와_칸_이름이_진짜다():
    """이름을 문자열로 박아 두면 dj-core 가 바꾸는 날 **조용히 안 듣는 인덱스**가 된다."""
    from django.apps import apps

    model = apps.get_model("logger", "AuditLogs")
    assert model._meta.db_table == TABLE_NAME
    cols = {f.name for f in model._meta.fields}
    assert {"logger_name", "create_datetime"} <= cols, "인덱스가 없는 칸을 가리킨다"


# ── ② ③ ④ 진짜 DB — **실 마이그레이션에서만 뜻이 선다** ────────────────────
@pytest.mark.django_db
def test_마이그레이션으로_태어난다():
    if not _migrations_ran():
        pytest.skip("이 DB 는 마이그레이션으로 안 세워졌다(--nomigrations) — 잴 것이 없다")
    row = _one("SELECT count(*) FROM pg_indexes WHERE tablename=%s AND indexname=%s",
               TABLE_NAME, INDEX_NAME)
    assert row[0] == 1, ("마이그레이션을 처음부터 돌린 DB 에 인덱스가 없다 — "
                         "스테이징·재생성은 인덱스 없이 태어난다")


@pytest.mark.django_db
def test_성한_인덱스다():
    """**있는데 안 듣는** 모양을 잡는다. 실패한 CONCURRENTLY 는 INVALID 를 남기고,
    플래너는 그것을 안 쓴다 — 이름만 보는 `IF NOT EXISTS` 는 그 찌꺼기도 「있다」로 읽는다."""
    if not _migrations_ran():
        pytest.skip("이 DB 는 마이그레이션으로 안 세워졌다 — 잴 것이 없다")
    row = _one("SELECT i.indisvalid, i.indisready FROM pg_index i "
               "JOIN pg_class c ON c.oid = i.indexrelid WHERE c.relname=%s", INDEX_NAME)
    assert row is not None, "인덱스가 아예 없다"
    assert row[0] is True, "INVALID 인덱스다 — 이름은 있고 플래너는 안 쓴다"
    assert row[1] is True, "아직 쓸 준비가 안 된 인덱스다"


@pytest.mark.django_db(transaction=True)
def test_두_번_걸어도_no_op_이다():
    """이미 인덱스가 있는 DB(지금 개발 DB가 그렇다)에서 **아무 일도 안 일어나야** 한다.

    ★ `transaction=True` 인 이유: `CONCURRENTLY` 는 트랜잭션 안에서 못 돈다.
      마이그레이션의 `atomic=False` 와 **같은 제약**이고, 여기서도 같은 모양으로 재야 한다.
    """
    if not _migrations_ran():
        pytest.skip("이 DB 는 마이그레이션으로 안 세워졌다 — 잴 것이 없다")
    before = _one("SELECT count(*) FROM pg_indexes WHERE indexname=%s", INDEX_NAME)[0]
    with connection.cursor() as cur:
        cur.execute(_module().FORWARD_SQL)        # 두 번째 적용 — 터지면 안 된다
    after = _one("SELECT count(*) FROM pg_indexes WHERE indexname=%s", INDEX_NAME)[0]
    assert before == after == 1, "두 번 걸었더니 수가 달라졌다"


@pytest.mark.django_db(transaction=True)
def test_되감았다_다시_걸_수_있다():
    """역방향이 **말로만** 있는 것이 아니라 실제로 듣는지 본다. 되감고 다시 건다."""
    if not _migrations_ran():
        pytest.skip("이 DB 는 마이그레이션으로 안 세워졌다 — 잴 것이 없다")
    mod = _module()
    try:
        with connection.cursor() as cur:
            cur.execute(mod.REVERSE_SQL)
        gone = _one("SELECT count(*) FROM pg_indexes WHERE indexname=%s", INDEX_NAME)[0]
        assert gone == 0, "역방향을 걸었는데 인덱스가 남아 있다"
    finally:
        #: ⚠ 무슨 일이 있어도 되돌려 놓는다 — 시험이 DB 를 인덱스 없이 두고 나가면
        #:   다음 시험·다음 사람이 **내가 만든 느림**을 재게 된다.
        with connection.cursor() as cur:
            cur.execute(mod.FORWARD_SQL)
    back = _one("SELECT count(*) FROM pg_indexes WHERE indexname=%s", INDEX_NAME)[0]
    assert back == 1, "다시 걸었는데 인덱스가 없다"
