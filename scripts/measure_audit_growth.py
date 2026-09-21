#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OPS-18 — **감사 표가 하루에 얼마나 자라는가**, 그리고 **무엇이 먼저 아픈가**.

왜 이 자리가 필요한가 — 「코드가 안 변해도 날마다 느려진다」
------------------------------------------------------------
`CoreLoggingMiddleware` 가 **요청 한 벌마다 감사 한 행**을 쓴다(턴 X · 차선 F).
그래서 `logger_auditlogs` 는 **배포와 무관하게** 자란다. 용량·보존·복구 시간·
그 표 위를 지나는 질의는 전부 이 증가율의 함수인데, 턴 Y 까지 대장에 있던 수는
**사람이 psql 로 한 번 손으로 낸 수** 하나였다. 한 번 잰 수를 「센다」로 적으면
다음 달에 아무도 세지 않아도 대장은 초록이다. 그래서 **자리**를 만든다.

이 도구가 **재는** 것 (전부 읽기 · SELECT 와 EXPLAIN 뿐)
--------------------------------------------------------
  ① **총량**   행 수 · 힙/인덱스/TOAST 바이트 · 죽은 튜플 · 인덱스 **개수**
  ② **하루 증분**  `create_datetime` 을 **KST 날짜로 묶어** 이레(기본 7일)
                   · 행 수 [실측]
                   · **논리 바이트** `sum(pg_column_size(t.*))` [실측]
                   · **디스크 바이트** = 행 수 × (총 바이트 ÷ 총 행) [산출]
  ③ **무엇이 먼저 아픈가**  세 후보를 **각각 눌러 본다** — 고르는 것이 아니라 재는 것이다
                   · 디스크  — 데이터 파일 시스템의 여유(밖에서 준 값) ÷ 하루 MB
                   · 인덱스  — 이 표의 인덱스 **개수**와 행당 인덱스 바이트
                   · 조회 지연 — 질의 셋을 `EXPLAIN (ANALYZE, BUFFERS)` 로

★ **논리 바이트 ≠ 디스크 바이트.** 둘을 한 칸에 적으면 용량 계획이 틀린다.
  TOAST 압축이 줄이고 인덱스·페이지 여백이 늘린다. 둘 다 내고 **이름을 다르게** 적는다.

★ **하루 한 벌로 「하루 증분」을 말하지 않는다.** 이 기계의 하루 폭은 2배가 넘는다
  (턴 Y 실측 8,363 ↔ 19,864). 그래서 **중앙값·평균·최소·최대를 함께** 낸다 —
  하나만 적으면 「어느 날을 골랐나」가 답을 정한다.

★ **오늘은 온전한 날이 아니다.** 아직 안 끝난 날을 일별 통계에 섞으면 평균이 내려간다.
  오늘은 `partial_today` 로 **따로** 적고 통계에서 뺀다.

★ **이 수는 「이 기계의 하루」다.** 차선 여덟이 두드리는 개발 기계이고 상용 부하가
  아니다. 「상용에서 하루 몇 MB」로 읽으면 틀린다 — 모수가 다르다.
  그래서 출력에 `population` 을 박는다(DB 이름 · 호스트). 지우지 말 것.

무엇을 **안** 하는가
--------------------
· **아무것도 안 쓴다.** dj-core(§0.4)의 표를 **읽기만** 한다 — 세는 것은 읽기다.
· **지우지 않는다.** 보존·삭제 정책은 이 절이 아니다(LAW-05 v0.4).
· **디스크 여유를 스스로 못 잰다.** DB 는 다른 컨테이너에 있고, 이 프로세스의 `df` 는
  **제 컨테이너**를 본다. 그 수를 DB 의 수인 척 적으면 착시 ⑤(환경)다.
  그래서 `--disk-free-bytes` 로 **밖에서 받는다.** 안 주면 「안 쟀다」로 적는다.

쓰는 법
-------
    MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
        python /repo/scripts/measure_audit_growth.py --days 7 \
            --out /docs/agent/evidence/OPS-18/audit_growth.json

    python scripts/measure_audit_growth.py --self-test    # DB 없이 셈만 (호스트에서도 돈다)
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from datetime import datetime, timedelta, timezone

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

#: dj-core 의 감사 표. **고치지 않는다 — 읽을 뿐이다** (§0.4).
TABLE = "logger_auditlogs"

#: 날짜를 묶는 시간대. 「하루」가 무엇인지 적지 않으면 날 경계가 사람마다 달라진다.
TZ_NAME = "Asia/Seoul"
KST = timezone(timedelta(hours=9))

MIB = 1024.0 * 1024.0
GIB = MIB * 1024.0

#: 조회 지연을 재는 질의 셋. **이름이 「어느 모양이 아픈가」를 가른다.**
#:   indexed   — 인덱스가 받는 질의(`stream_monitors/services/response_clock.py:224`)
#:               표가 커져도 **맞는 행만** 읽으므로 시간이 표 크기에 안 붙어야 한다
#:   chain_all — LAW-08 체인 검증이 읽는 **전건**(`common/evidence_chain.chain_entries`)
#:               이것은 **행 수에 비례**한다 — 자람이 그대로 시간이 되는 자리
#:   page      — 화면 목록 한 쪽(`AuditLog.tsx`) · pkey 역순 50행
PROBES = ("indexed", "chain_all", "page")

#: `response_clock.LOGGER_NAME` 과 같은 값. 정본은 `kernels/k1_event/response_flow.py`.
#: 여기서는 **읽기 질의의 모양을 흉내 내는 상수**일 뿐이다.
RESPONSE_LOGGER_NAME = "guardianx.dsm.response"

#: `evidence_chain.CHAIN_PREFIX`.
CHAIN_PREFIX = "guardianx."

#: `evidence_chain.HASHED_FIELDS` + `data_after` — 체인 검증이 실제로 끌어오는 칸들.
#: 칸을 줄여 재면 **TOAST 를 안 건드려서** 실제보다 빨라진다.
CHAIN_COLUMNS = (
    "id", "create_datetime", "logger_name", "level_name", "msg", "note",
    "api_name", "api_method", "status_http", "user_id", "username",
    "target_user_id", "data_before", "data_after",
)

#: ★★ [2026-09-21 · 분류 게이트 D-270 ③] **질의문을 인자로 넘기지 않는다 — 상수로 둔다.**
#:
#:   분류 게이트는 `cursor.execute()` 의 첫 인자를 **AST 로 읽어** 읽기인지 쓰기인지 가른다.
#:   상수로 못 읽으면 「**모호하므로 쓰기로 센다**」 — 그 보수성이 그 게이트의 값이고,
#:   고칠 자리는 게이트가 아니라 **읽히지 않게 쓴 이쪽**이다.
#:   전에는 `_explain(cur, sql, params)` 가 SQL 을 **매개변수로** 받아 이었다.
#:   매개변수는 AST 가 따라갈 수 없다 — 그래서 이 도구가 「쓰기 1건」으로 세어졌다.
#:   ⇒ 세 질의를 **EXPLAIN 까지 붙여 모듈 상수 셋**으로 둔다. 읽는 사람도 같이 편해진다.
#:
#:   ⚠ 이 상수들은 **전부 SELECT 다.** `--self-test` 가 **제 소스를 AST 로 다시 읽어**
#:     「이 파일의 모든 `execute` 는 select/explain 로 시작한다」를 매번 다시 센다.
#:     「읽기만 한다」는 머리말의 약속을 **말이 아니라 검사**로 둔다.
EXPLAIN_PREFIX = "explain (analyze, buffers, format json) "

#: 인덱스가 받는 질의 — `stream_monitors/services/response_clock.py:224 stamps_for` 의 모양.
SQL_EXPLAIN_INDEXED = EXPLAIN_PREFIX + (
    "select id, create_datetime, created_on, username, data_before, data_after"
    "  from logger_auditlogs"
    " where logger_name = %s and create_datetime >= %s"
    " order by create_datetime, id limit 20000")

#: LAW-08 체인 검증이 읽는 **전건** — `common/evidence_chain.chain_entries` 의 모양.
#: ⚠ 칸 목록은 `CHAIN_COLUMNS` 와 **같아야 한다.** 칸을 줄여 재면 TOAST 를 안 건드려
#:   실제보다 빨라진다. 자기시험이 두 목록이 갈리지 않았는지 매번 대조한다.
SQL_EXPLAIN_CHAIN_ALL = EXPLAIN_PREFIX + (
    "select id, create_datetime, logger_name, level_name, msg, note,"
    "       api_name, api_method, status_http, user_id, username,"
    "       target_user_id, data_before, data_after"
    "  from logger_auditlogs where logger_name like %s order by id")

#: 화면 목록 한 쪽 — `frontend/src/features/dsm/pages/AuditLog.tsx` 가 여는 자리.
SQL_EXPLAIN_PAGE = EXPLAIN_PREFIX + (
    "select id, create_datetime, logger_name, level_name, username, msg"
    "  from logger_auditlogs order by id desc limit 50")


# ══════════════════════════════════════════════════════════════════════════
# 1. 순수 셈 — DB 없이 돈다. 자기시험이 겨누는 과녁이 여기다.
# ══════════════════════════════════════════════════════════════════════════

def summarize_days(days: list[dict]) -> dict:
    """온전한 날들의 통계. **하나만 내지 않는다** (머리말 ★ 둘째).

    빈 목록이면 `None` 을 낸다 — 0 이 아니다. 「0행 늘었다」와 「못 쟀다」는 다르다.
    """
    if not days:
        return {"day_count": 0, "rows": None, "logical_bytes": None}
    rows = [int(d["rows"]) for d in days]
    logical = [int(d["logical_bytes"] or 0) for d in days]
    return {
        "day_count": len(days),
        "rows": {
            "median": statistics.median(rows),
            "mean": round(sum(rows) / len(rows), 1),
            "min": min(rows),
            "max": max(rows),
            "sum": sum(rows),
        },
        "logical_bytes": {
            "median": statistics.median(logical),
            "mean": round(sum(logical) / len(logical), 1),
            "min": min(logical),
            "max": max(logical),
            "sum": sum(logical),
        },
    }


def disk_bytes_per_row(total_bytes: int, total_rows: int) -> float | None:
    """행 하나가 **디스크에서** 차지하는 평균 바이트 (힙 + 인덱스 + TOAST).

    ⚠ **평균이다.** 같은 행을 `pg_column_size` 로 재면 더 작게 나온다 —
      그 차는 오류가 아니라 **논리 크기 ≠ 디스크 크기**다. 용량 계획은 이 값으로 한다.
    """
    if not total_rows:
        return None
    return total_bytes / float(total_rows)


def days_until(free_bytes: int | None, bytes_per_day: float | None) -> float | None:
    """이 속도로 가면 며칠 뒤에 여유가 바닥나는가. 못 재면 `None` — 0 이 아니다."""
    if not free_bytes or not bytes_per_day or bytes_per_day <= 0:
        return None
    return free_bytes / float(bytes_per_day)


def rank_pain(candidates: list[dict]) -> list[dict]:
    """세 후보를 **아픈 순서**로 세운다.

    ★ 「며칠 뒤」를 못 내는 후보는 **끝으로 보내되 지우지 않는다.** 못 잰 것을 빼면
      그 후보는 영원히 안 아픈 것처럼 보인다.
    """
    def key(c: dict) -> tuple[int, float]:
        d = c.get("days_until")
        if d is None:
            return (1, 0.0)
        return (0, float(d))
    return sorted(candidates, key=key)


# ══════════════════════════════════════════════════════════════════════════
# 2. 표에 붙는 부분
# ══════════════════════════════════════════════════════════════════════════

def _setup_django() -> None:
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, "/app")
    django.setup()


def _totals(cur) -> dict:
    cur.execute(
        "select pg_relation_size(%s::regclass),"
        "       pg_indexes_size(%s::regclass),"
        "       pg_total_relation_size(%s::regclass)",
        [TABLE, TABLE, TABLE])
    heap, idx, total = cur.fetchone()
    cur.execute(
        "select coalesce(pg_total_relation_size(reltoastrelid), 0)"
        "  from pg_class where oid = %s::regclass", [TABLE])
    toast = cur.fetchone()[0]
    cur.execute("select count(*) from " + TABLE)
    rows = cur.fetchone()[0]
    cur.execute(
        "select n_live_tup, n_dead_tup, last_autovacuum, last_autoanalyze"
        "  from pg_stat_user_tables where relname = %s", [TABLE])
    stat = cur.fetchone() or (None, None, None, None)
    cur.execute(
        "select count(*), coalesce(sum(pg_relation_size(indexrelid)), 0)"
        "  from pg_index where indrelid = %s::regclass", [TABLE])
    idx_count, idx_sum = cur.fetchone()
    return {
        "rows": int(rows),
        "heap_bytes": int(heap),
        "index_bytes": int(idx),
        "toast_bytes": int(toast),
        "total_bytes": int(total),
        "index_count": int(idx_count),
        "index_bytes_sum": int(idx_sum),
        "n_live_tup": stat[0], "n_dead_tup": stat[1],
        "last_autovacuum": str(stat[2]) if stat[2] else None,
        "last_autoanalyze": str(stat[3]) if stat[3] else None,
        "disk_bytes_per_row": disk_bytes_per_row(int(total), int(rows)),
    }


def _daily(cur, *, days: int, now_kst: datetime) -> tuple[list[dict], dict]:
    """KST 날짜별 증분. **오늘은 따로** 낸다 (머리말 ★ 셋째)."""
    today = now_kst.date()
    first = today - timedelta(days=days)
    start = datetime(first.year, first.month, first.day, tzinfo=KST)
    cur.execute(
        "select (create_datetime at time zone %s)::date as d,"
        "       count(*)::bigint,"
        "       sum(pg_column_size(t.*))::bigint,"
        "       min(create_datetime), max(create_datetime)"
        "  from " + TABLE + " t"
        " where create_datetime >= %s"
        " group by 1 order by 1", [TZ_NAME, start])
    rows = cur.fetchall()
    seen = {}
    partial = None
    for d, n, logical, lo, hi in rows:
        item = {"date": str(d), "rows": int(n),
                "logical_bytes": int(logical or 0),
                "first_row_at": str(lo), "last_row_at": str(hi),
                "empty": False}
        if d == today:
            partial = item
        else:
            seen[d] = item
    # ★ **행이 0인 날을 빠뜨리지 않는다.** GROUP BY 는 없는 날을 안 낸다 —
    #   그러면 「이레치」라고 적어 놓고 실제로는 닷새만 낸 표가 된다.
    #   기계가 꺼져 있던 날은 **0으로 적고 `empty` 로 표시**한 뒤 통계에서 뺀다.
    #   (0을 평균에 넣으면 「하루 증분」이 「기계가 꺼진 날까지 섞인 값」이 된다.)
    full = []
    for back in range(days, 0, -1):
        d = today - timedelta(days=back)
        full.append(seen.get(d, {"date": str(d), "rows": 0, "logical_bytes": 0,
                                 "first_row_at": None, "last_row_at": None,
                                 "empty": True}))
    return full, partial


def _rolling_24h(cur, *, now_utc: datetime) -> dict:
    cur.execute(
        "select count(*)::bigint, coalesce(sum(pg_column_size(t.*)), 0)::bigint"
        "  from " + TABLE + " t where create_datetime >= %s",
        [now_utc - timedelta(hours=24)])
    n, logical = cur.fetchone()
    return {"rows": int(n), "logical_bytes": int(logical)}


def _explain(cur, probe: str, params: list) -> dict:
    """`EXPLAIN (ANALYZE, BUFFERS)` 한 벌. **값은 안 적는다 — 시간과 행 수만.**

    (어느 테넌트의 무엇이 나왔는지는 이 증명에 필요 없다 — P-205 와 같은 규약.)

    ★ SQL 을 **인자로 받지 않는다.** 질의문은 모듈 상수 셋이고 여기서는 **이름**으로 고른다 —
      이유는 `EXPLAIN_PREFIX` 위 ★★ 에 적었다(분류 게이트가 읽을 수 있어야 한다).
      갈래를 늘릴 때는 상수를 하나 더 두고 이 분기에 한 줄을 더한다. 분기가 **보이는 것**이
      요점이다 — 사전에 담으면 AST 가 다시 못 읽는다.
    """
    if probe == "indexed":
        cur.execute(SQL_EXPLAIN_INDEXED, params)
    elif probe == "chain_all":
        cur.execute(SQL_EXPLAIN_CHAIN_ALL, params)
    elif probe == "page":
        cur.execute(SQL_EXPLAIN_PAGE, params)
    else:
        raise KeyError("모르는 질의 이름: %r — 상수를 먼저 둔다" % probe)
    plan = cur.fetchone()[0]
    if isinstance(plan, str):
        plan = json.loads(plan)
    root = plan[0]
    node = root["Plan"]
    return {
        "execution_ms": round(float(root["Execution Time"]), 3),
        "planning_ms": round(float(root["Planning Time"]), 3),
        "node": node["Node Type"],
        "actual_rows": node.get("Actual Rows"),
        "rows_removed_by_filter": node.get("Rows Removed by Filter"),
        "shared_hit": node.get("Shared Hit Blocks"),
        "shared_read": node.get("Shared Read Blocks"),
    }


def _probe_queries(cur, *, now_utc: datetime, repeat: int) -> dict:
    """질의 셋을 **각각 repeat 번** 눌러 중앙값을 남긴다. 한 벌은 수가 아니다."""
    #: 질의문은 **상수**이고(위 ★★) 여기 있는 것은 **묶는 값**뿐이다.
    params = {
        "indexed": [RESPONSE_LOGGER_NAME, now_utc - timedelta(days=7)],
        "chain_all": [CHAIN_PREFIX + "%"],
        "page": [],
    }
    out = {}
    for name in PROBES:
        runs = [_explain(cur, name, params[name]) for _ in range(repeat)]
        times = [r["execution_ms"] for r in runs]
        best = runs[len(runs) // 2]
        out[name] = dict(best, runs=repeat,
                         execution_ms_median=round(statistics.median(times), 3),
                         execution_ms_min=min(times), execution_ms_max=max(times))
    return out


def _population(cur) -> dict:
    cur.execute("select current_database(), inet_server_addr()::text,"
                "       version(), now()")
    db, host, ver, now = cur.fetchone()
    return {"database": db, "server": host,
            "postgres": ver.split(" on ")[0],
            "server_now_utc": str(now)}


# ══════════════════════════════════════════════════════════════════════════
# 3. 무엇이 먼저 아픈가 — 고르지 않고 **잰다**
# ══════════════════════════════════════════════════════════════════════════

def pain_candidates(*, totals: dict, per_day_disk_bytes: float | None,
                    per_day_rows: float | None, disk_free_bytes: int | None,
                    probes: dict, latency_budget_ms: float) -> list[dict]:
    """세 후보에 **각각 「며칠 뒤」**를 붙인다. 못 붙이면 사유를 적는다."""
    out: list[dict] = []

    out.append({
        "name": "디스크",
        "now": {"total_bytes": totals["total_bytes"],
                "free_bytes": disk_free_bytes},
        "per_day_bytes": per_day_disk_bytes,
        "days_until": days_until(disk_free_bytes, per_day_disk_bytes),
        "threshold": "데이터 파일 시스템 여유가 0",
        "unmeasured": None if disk_free_bytes else
                      "디스크 여유를 안 받았다(--disk-free-bytes) — DB 는 다른 컨테이너다",
    })

    # 인덱스 — 이 표는 인덱스가 여럿이다. 행 하나가 들어올 때마다 그 전부가 갱신된다.
    # 「언제 아픈가」를 쓰기 시간으로 환산할 자리가 이 도구에는 없다(쓰기를 안 한다).
    # 그래서 **개수와 바이트만** 내고 「며칠 뒤」는 `None` 으로 둔다 — 지어내지 않는다.
    idx_per_row = (totals["index_bytes"] / float(totals["rows"])
                   if totals["rows"] else None)
    out.append({
        "name": "인덱스",
        "now": {"index_count": totals["index_count"],
                "index_bytes": totals["index_bytes"],
                "index_bytes_per_row": idx_per_row},
        "per_day_bytes": (idx_per_row * per_day_rows
                          if idx_per_row and per_day_rows else None),
        "days_until": None,
        "threshold": "쓰기 지연 — 행 하나마다 인덱스 %d개가 갱신된다"
                     % totals["index_count"],
        "unmeasured": "쓰기 시간을 안 쟀다 — 이 도구는 읽기만 한다. "
                      "재려면 INSERT 를 트랜잭션 안에서 걸고 되돌려야 한다",
    })

    # 조회 지연 — **행 수에 비례하는 질의**가 있으면 그것이 시계다.
    chain = probes.get("chain_all") or {}
    chain_rows = chain.get("actual_rows") or 0
    chain_ms = chain.get("execution_ms_median")
    ms_per_row = (chain_ms / float(chain_rows)) if chain_ms and chain_rows else None
    # 하루에 느는 행 중 체인 접두사를 쓰는 비율은 모른다 — 그래서 **상한**(전부가 체인
    # 행이라고 가정)과 **현재 비율 유지** 둘을 나눠 적는다. 가정은 이름으로 적는다.
    chain_share = (chain_rows / float(totals["rows"])) if totals["rows"] else None
    chain_rows_per_day = (per_day_rows * chain_share
                          if per_day_rows and chain_share else None)
    headroom_ms = latency_budget_ms - (chain_ms or 0.0)
    days = (headroom_ms / (ms_per_row * chain_rows_per_day)
            if ms_per_row and chain_rows_per_day and headroom_ms > 0 else None)
    out.append({
        "name": "조회 지연",
        "now": {"chain_all_ms": chain_ms, "chain_all_rows": chain_rows,
                "ms_per_row": ms_per_row,
                "chain_share_of_table": chain_share,
                "indexed_ms": (probes.get("indexed") or {}).get("execution_ms_median"),
                "page_ms": (probes.get("page") or {}).get("execution_ms_median")},
        "per_day_bytes": None,
        "days_until": days,
        "threshold": "LAW-08 전건 검증 한 벌이 %.0f ms" % latency_budget_ms,
        "assumption": "체인 행 비율이 지금(%s)과 같게 유지된다고 본다 [가정]"
                      % ("%.1f%%" % (chain_share * 100) if chain_share else "미상"),
        "unmeasured": None,
    })
    return out


# ══════════════════════════════════════════════════════════════════════════
# 4. 사람이 읽는 줄
# ══════════════════════════════════════════════════════════════════════════

def render(report: dict) -> str:
    t = report["totals"]
    s = report["summary"]
    lines = []
    add = lines.append
    add("[OPS-18] 감사 표 성장률 — %s" % report["measured_at_kst"])
    add("  모수: DB %s · 표 %s" % (report["population"]["database"], TABLE))
    add("")
    add("  총량      %s행 · %.1f MiB (힙 %.1f + 인덱스 %.1f + TOAST %.1f) · 인덱스 %d개"
        % (f"{t['rows']:,}", t["total_bytes"] / MIB, t["heap_bytes"] / MIB,
           t["index_bytes"] / MIB, t["toast_bytes"] / MIB, t["index_count"]))
    add("  행당      디스크 %.1f B [산출: 총 바이트 ÷ 총 행] · 죽은 튜플 %s"
        % (t["disk_bytes_per_row"] or 0.0, f"{t['n_dead_tup'] or 0:,}"))
    add("")
    add("  날짜(KST)        행       논리 MiB   디스크 MiB [산출]")
    for d in report["days"]:
        add("  %s  %9s   %8.1f   %8.1f%s"
            % (d["date"], f"{d['rows']:,}", d["logical_bytes"] / MIB,
               d["disk_bytes"] / MIB,
               "   ← 행 0 · 기계가 안 돈 날 · 통계에서 뺐다" if d["empty"] else ""))
    p = report.get("partial_today")
    if p:
        add("  %s  %9s   %8.1f   %8.1f   ← 아직 안 끝난 날 · 통계에서 뺐다"
            % (p["date"], f"{p['rows']:,}", p["logical_bytes"] / MIB,
               p["disk_bytes"] / MIB))
    add("")
    if s["day_count"]:
        r, lg = s["rows"], s["logical_bytes"]
        add("  창 %d일 중 **행이 있는 날 %d일** (행 0인 날 %d일은 뺐다) — 하루 증분"
            % (s["window_days"], s["day_count"], s["empty_days"]))
        add("    중앙값  %s행 · 논리 %.1f MiB · 디스크 %.1f MiB [산출]"
            % (f"{r['median']:,}", lg["median"] / MIB,
               report["per_day"]["median_disk_bytes"] / MIB))
        add("    평균    %s행 · 논리 %.1f MiB · 디스크 %.1f MiB [산출]"
            % (f"{r['mean']:,}", lg["mean"] / MIB,
               report["per_day"]["mean_disk_bytes"] / MIB))
        add("    최소/최대  %s / %s행  (폭 %.1f배)"
            % (f"{r['min']:,}", f"{r['max']:,}",
               (r["max"] / r["min"]) if r["min"] else 0.0))
        add("    연 환산  %s행 · %.1f GiB/년 [추정 — 중앙값 × 365]"
            % (f"{int(r['median'] * 365):,}",
               report["per_day"]["median_disk_bytes"] * 365 / GIB))
    else:
        add("  온전한 날 0일 — **하루 증분을 못 쟀다.** 창을 넓히십시오(--days)")
    add("  직전 24시간(굴림)  %s행 · 논리 %.1f MiB"
        % (f"{report['rolling_24h']['rows']:,}",
           report["rolling_24h"]["logical_bytes"] / MIB))
    add("")
    add("  조회 지연 [EXPLAIN (ANALYZE, BUFFERS) · %d벌 중앙값]" % report["probe_runs"])
    for name in PROBES:
        q = report["probes"][name]
        add("    %-10s %8.3f ms · %s · %s행 · buffers hit=%s read=%s"
            % (name, q["execution_ms_median"], q["node"],
               f"{q['actual_rows'] or 0:,}", q["shared_hit"], q["shared_read"]))
    add("")
    add("  무엇이 먼저 아픈가")
    for i, c in enumerate(report["pain"], 1):
        d = c["days_until"]
        when = ("%.0f일 뒤 (%.1f년)" % (d, d / 365.0)) if d else "못 냈다"
        add("    %d) %-8s %-22s  문턱: %s" % (i, c["name"], when, c["threshold"]))
        if c.get("unmeasured"):
            add("       ⚠ %s" % c["unmeasured"])
        if c.get("assumption"):
            add("       · %s" % c["assumption"])
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# 5. 판정기 — **아무도 안 센 것**을 잡는다
# ══════════════════════════════════════════════════════════════════════════
#
# 왜 이 갈래가 있나 — 대장이 스스로 적은 닫는 조건이다:
#
#     「한 번 잰 수를 『센다』로 적으면 **다음 달에 아무도 세지 않아도 대장은 초록이다.**
#       닫는 모양: 증분을 **주기로 적는 자리** + **그 수를 읽는 판정기.**」
#       (`evidence/D-346/ga_readiness.yaml` · OPS-18)
#
# 그래서 이 판정기가 겨누는 것은 「숫자가 크다」가 아니라 **「그 수가 늙었다」**이다.
# 성장률의 상한을 여기서 정하지 않는다 — 그 수는 **선언**이고 주인이 따로 있다
# (LAW-05 보존 정책 · 세종). 선언이 없으면 `--max-mib-per-day` 는 안 주면 되고,
# 그 갈래는 **회색**으로 적힌다. 회색을 초록으로 세지 않는다.

def check(path: str, *, max_age_days: float,
          max_mib_per_day: float | None) -> int:
    """마지막으로 잰 수를 읽고 **셋**을 본다. 하나라도 못 보면 그 갈래는 회색이다."""
    from _gate_header import gate_header

    if not os.path.exists(path):
        gate_header(__file__, target="표 %s (마지막으로 잰 JSON)" % TABLE,
                    as_="자격증명 없음 — 파일을 읽는다",
                    source="파일 %s — **없다**" % path,
                    measured="아무것도 안 쟀다 · 분모 0")
        print("[OPS-18] 빨강 — 잰 자리가 **없다**: %s" % path)
        print("         이 절은 「센다」인데 아무도 센 적이 없다.")
        return 1
    with open(path, encoding="utf-8") as fh:
        report = json.load(fh)

    # ★ 머리글의 **분모는 「행이 있는 날의 수」**다 — 창의 길이가 아니다.
    #   창 7일에 기계가 하루 꺼져 있었으면 분모는 6이지 7이 아니다.
    _s = report.get("summary") or {}
    gate_header(
        __file__,
        target="표 %s · DB %s"
               % (TABLE, (report.get("population") or {}).get("database", "?")),
        as_="자격증명 없음 — 파일을 읽는다",
        source="파일 %s (기록 %s)" % (path, report.get("measured_at_kst", "?")),
        measured="OPS-18 하루 증분 · 분모 %d (행이 있는 날) / 창 %s일"
                 % (_s.get("day_count") or 0, _s.get("window_days", "?")))

    bad, gray = 0, 0
    measured = report.get("measured_at_kst", "")
    try:
        when = datetime.strptime(measured, "%Y-%m-%d %H:%M KST").replace(tzinfo=KST)
    except ValueError:
        print("[OPS-18] 빨강 — 잰 시각을 못 읽는다: %r" % measured)
        return 1
    age = (datetime.now(timezone.utc).astimezone(KST) - when).total_seconds() / 86400.0
    if age > max_age_days:
        print("[OPS-18] 빨강 ① 신선도 — 마지막으로 센 것이 %.1f일 전 (상한 %.1f일)"
              % (age, max_age_days))
        print("         자람은 멈추지 않는데 셈이 멈췄다. 그 사이의 수는 **없다.**")
        bad += 1
    else:
        print("[OPS-18] 초록 ① 신선도 — %.1f일 전에 쟀다 (상한 %.1f일) · %s"
              % (age, max_age_days, measured))

    s = report.get("summary") or {}
    if not s.get("day_count"):
        print("[OPS-18] 빨강 ② 분모 — 행이 있는 날이 **0일**이다. 분모 0인 초록은 초록이 아니다")
        bad += 1
    else:
        print("[OPS-18] 초록 ② 분모 — 행이 있는 날 %d일 / 창 %s일"
              % (s["day_count"], s.get("window_days", "?")))

    per_day = (report.get("per_day") or {}).get("median_disk_bytes")
    if max_mib_per_day is None:
        print("[OPS-18] 회색 ③ 상한 — **선언 없음**(--max-mib-per-day). "
              "상한은 선언이고 주인이 따로 있다 (LAW-05 보존 정책)")
        gray += 1
    elif per_day is None:
        print("[OPS-18] 회색 ③ 상한 — 하루 증분을 못 읽었다")
        gray += 1
    elif per_day / MIB > max_mib_per_day:
        print("[OPS-18] 빨강 ③ 상한 — 하루 %.1f MiB > 선언된 %.1f MiB"
              % (per_day / MIB, max_mib_per_day))
        bad += 1
    else:
        print("[OPS-18] 초록 ③ 상한 — 하루 %.1f MiB ≤ 선언된 %.1f MiB"
              % (per_day / MIB, max_mib_per_day))

    print("[OPS-18] => %s (회색 %d갈래)"
          % ("통과" if not bad else "빨강 %d갈래" % bad, gray))
    return 1 if bad else 0


# ══════════════════════════════════════════════════════════════════════════
# 6. 자기시험 — DB 없이 셈만 본다
# ══════════════════════════════════════════════════════════════════════════

def self_test() -> int:
    bad = 0

    def check(name: str, got, want):
        nonlocal bad
        if got != want:
            bad += 1
            print("  FAIL %s: %r != %r" % (name, got, want))
        else:
            print("  ok   %s" % name)

    print("[OPS-18] 자기시험 — 셈만 (DB 없이)")
    empty = summarize_days([])
    check("빈 날은 0이 아니라 None", (empty["day_count"], empty["rows"]), (0, None))

    days = [{"rows": 10, "logical_bytes": 100},
            {"rows": 30, "logical_bytes": 300},
            {"rows": 20, "logical_bytes": 200}]
    s = summarize_days(days)
    check("중앙값", s["rows"]["median"], 20)
    check("평균", s["rows"]["mean"], 20.0)
    check("최대", s["rows"]["max"], 30)

    check("행당 바이트", disk_bytes_per_row(1000, 4), 250.0)
    check("행 0이면 None", disk_bytes_per_row(1000, 0), None)

    check("며칠 뒤", days_until(1000, 100.0), 10.0)
    check("증가율 0이면 None", days_until(1000, 0.0), None)
    check("여유 미상이면 None", days_until(None, 100.0), None)

    ranked = rank_pain([{"name": "a", "days_until": None},
                        {"name": "b", "days_until": 50.0},
                        {"name": "c", "days_until": 5.0}])
    check("못 잰 후보는 끝으로 가되 안 사라진다",
          [c["name"] for c in ranked], ["c", "b", "a"])

    # ── 이 파일이 **정말 읽기만 하는가** — 말이 아니라 제 소스를 다시 읽어 센다 ──────
    #  머리말은 「아무것도 안 쓴다」고 약속한다. 약속은 검사가 아니다.
    #  그래서 제 소스를 AST 로 훑어 ① 모든 `execute` 의 첫 인자를 **상수로 읽을 수 있는지**
    #  ② 그 SQL 이 전부 `select`/`explain` 으로 시작하는지 센다.
    #  ①이 깨지면 분류 게이트(D-270 ③)도 못 읽는다 — 같은 검사가 두 가지를 지킨다.
    import ast as _ast                                    # noqa: PLC0415

    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    tree = _ast.parse(src)
    consts: dict[str, str] = {}
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Assign) and isinstance(node.value, _ast.Constant) \
                and isinstance(node.value.value, str):
            for t in node.targets:
                if isinstance(t, _ast.Name):
                    consts[t.id] = node.value.value

    def resolve(n):
        if isinstance(n, _ast.Constant) and isinstance(n.value, str):
            return n.value
        if isinstance(n, _ast.Name):
            return consts.get(n.id)
        if isinstance(n, _ast.BinOp) and isinstance(n.op, _ast.Add):
            a, b = resolve(n.left), resolve(n.right)
            return None if a is None or b is None else a + b
        return None

    # 위에서 모은 단순 상수로 `EXPLAIN_PREFIX + "..."` 꼴 상수도 한 번 더 풀어 둔다.
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Assign):
            got = resolve(node.value)
            if got is not None:
                for t in node.targets:
                    if isinstance(t, _ast.Name):
                        consts.setdefault(t.id, got)

    unreadable, writes = [], []
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Call) and isinstance(node.func, _ast.Attribute) \
                and node.func.attr in ("execute", "executemany"):
            sql = resolve(node.args[0]) if node.args else None
            if sql is None:
                unreadable.append(node.lineno)
            elif not sql.lstrip().lower().startswith(("select", "explain")):
                writes.append((node.lineno, sql[:40]))
    check("모든 execute 의 SQL 을 상수로 읽을 수 있다 (분류 게이트도 읽는다)",
          unreadable, [])
    check("모든 execute 가 select/explain 이다 — 이 도구는 쓰지 않는다", writes, [])

    #: 상수 SQL 의 칸 목록이 `CHAIN_COLUMNS` 와 갈리지 않았는가.
    #: 갈리면 체인 질의가 **TOAST 를 덜 건드려** 실제보다 빨라진다.
    check("chain_all 상수가 CHAIN_COLUMNS 를 전부 든다",
          [c for c in CHAIN_COLUMNS if c not in SQL_EXPLAIN_CHAIN_ALL], [])
    check("질의 상수 셋이 PROBES 셋과 짝이 맞는다",
          len([s for s in (SQL_EXPLAIN_INDEXED, SQL_EXPLAIN_CHAIN_ALL,
                           SQL_EXPLAIN_PAGE) if s.startswith(EXPLAIN_PREFIX)]),
          len(PROBES))

    print("  => %s" % ("통과" if not bad else "실패 %d건" % bad))
    return 1 if bad else 0


# ══════════════════════════════════════════════════════════════════════════

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="OPS-18 감사 표 성장률")
    ap.add_argument("--days", type=int, default=7, help="온전한 날 몇 개를 낼 것인가")
    ap.add_argument("--repeat", type=int, default=3, help="질의 한 벌을 몇 번 누를 것인가")
    ap.add_argument("--disk-free-bytes", type=int, default=None,
                    help="DB 데이터 파일 시스템의 여유 바이트 — **밖에서 잰 값**")
    ap.add_argument("--latency-budget-ms", type=float, default=1000.0,
                    help="조회 지연 문턱 (LAW-08 전건 검증 한 벌)")
    ap.add_argument("--out", default=None, help="JSON 을 쓸 자리")
    ap.add_argument("--check", default=None, metavar="JSON",
                    help="판정기 — 이미 잰 JSON 을 읽고 **늙었는지**를 본다")
    ap.add_argument("--max-age-days", type=float, default=30.0,
                    help="--check 의 신선도 상한 (기본 30일)")
    ap.add_argument("--max-mib-per-day", type=float, default=None,
                    help="--check 의 증가율 상한 — **선언**이다. 안 주면 그 갈래는 회색")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    if args.check:
        return check(args.check, max_age_days=args.max_age_days,
                     max_mib_per_day=args.max_mib_per_day)

    _setup_django()
    from django.db import connection

    now_utc = datetime.now(timezone.utc)
    now_kst = now_utc.astimezone(KST)

    with connection.cursor() as cur:
        population = _population(cur)
        totals = _totals(cur)
        days, partial = _daily(cur, days=args.days, now_kst=now_kst)
        rolling = _rolling_24h(cur, now_utc=now_utc)
        probes = _probe_queries(cur, now_utc=now_utc, repeat=args.repeat)

    bpr = totals["disk_bytes_per_row"] or 0.0
    for d in days:
        d["disk_bytes"] = int(d["rows"] * bpr)
    if partial:
        partial["disk_bytes"] = int(partial["rows"] * bpr)

    # 통계는 **행이 있는 날**로만 낸다 — 위 `_daily` 의 ★ 참조.
    worked = [d for d in days if not d["empty"]]
    summary = summarize_days(worked)
    summary["empty_days"] = sum(1 for d in days if d["empty"])
    summary["window_days"] = len(days)
    per_day = {"median_disk_bytes": None, "mean_disk_bytes": None,
               "max_disk_bytes": None}
    if summary["day_count"]:
        per_day = {
            "median_disk_bytes": summary["rows"]["median"] * bpr,
            "mean_disk_bytes": summary["rows"]["mean"] * bpr,
            "max_disk_bytes": summary["rows"]["max"] * bpr,
        }

    pain = rank_pain(pain_candidates(
        totals=totals,
        per_day_disk_bytes=per_day["median_disk_bytes"],
        per_day_rows=(summary["rows"]["median"] if summary["day_count"] else None),
        disk_free_bytes=args.disk_free_bytes,
        probes=probes,
        latency_budget_ms=args.latency_budget_ms))

    report = {
        "clause": "OPS-18",
        "table": TABLE,
        "measured_at_kst": now_kst.strftime("%Y-%m-%d %H:%M KST"),
        "timezone": TZ_NAME,
        "population": population,
        "totals": totals,
        "days": days,
        "partial_today": partial,
        "summary": summary,
        "per_day": per_day,
        "rolling_24h": rolling,
        "probe_runs": args.repeat,
        "probes": probes,
        "pain": pain,
        "caveat": ("이 수는 **이 개발 기계의 하루**다. 차선 여럿이 두드리는 날이고 "
                   "상용 부하가 아니다. 상용 수는 상용 트래픽에서 다시 재야 한다."),
    }

    print(render(report))
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2, default=str)
        print("\n  JSON -> %s" % args.out)
    # 「온전한 날 0일」은 **못 잰 것**이다 — 0 을 내면 다음 사람이 통과로 읽는다.
    return 0 if summary["day_count"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
