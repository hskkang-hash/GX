#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""D-368 / P-83 강제 도구 — **쓰기 메서드에 인증 관문이 없으면 exit 1.**

    읽기 유출 — 나간 것은 되돌릴 수 없다. 그러나 **무엇이 나갔는지는 안다**
    쓰기 오염 — 들어온 것도 되돌릴 수 없고, **게다가 조용하다**

D-358 은 「한꺼번에 막으면 제품이 깨진다」였고 그 신중함은 옳았다. D-368 이 그
문장의 **범위를 좁혔다**: 그것은 읽기 면의 규칙이다. 쓰기는 다르다.

★★ P-83 [세종 판정 2026-09-06 · 턴 I] — **401·403 과 422 는 다른 칸이다**
--------------------------------------------------------------------------
이 게이트는 턴 H 까지 **거짓 초록**이었다. 「관문 17」이라고 냈는데 그 17 중
**13이 실제로는 422**였다. 422 는 스키마 검증의 답이지 관문의 답이 아니다 —
「인증 없이도 여기까지 왔고 본문 형식에서 떨어졌다」는 뜻이고, 본문만 맞추면
그대로 들어간다. 그 셋을 한 칸에 넣었기 때문에 **열일곱 자리가 지켜지고 있다**고
읽혔다. 실제로 그랬던 것은 **둘**이었다.

    관문        = 401 · 403 **만**
    도달·검증   = 422 · 400   ← 관문이 아니다. 그리고 그 자리는
                                 **관문이 있는지 못 쟀다**로 센다(회색)
    도달 실패   = 404 · 405   ← 그 자리에 그 메서드가 없다

그래서 게이트의 **첫 줄**은 언제나 이 세 수로 시작한다. 총합만 적는 보고는 받지 않는다.

★★ P-99 [2026-09-07 · 턴 K] — **분모를 손으로 적지 않는다**
------------------------------------------------------------
턴 J 까지 이 게이트가 판정한 분모는 **30자리**였다. 그 30 은 탐침이 「`auth=` 콜백이
없는 쓰기 라우트」만 골라 만든 **정적 부분집합**이었다. 그리고 턴 J 의 P0
(`POST /api/delivery/etri-integration/receive-from-etri` — 익명이 남의 배송을 취소)은
**그 30 안**에 있었지만, 그 30 을 만든 규칙 자체는 이렇게 말하고 있었다:

    「콜백이 있으니 관문이 있을 것이다」 — 그것은 **추정**이고 (D-280 금지),
    347자리가 그 추정 뒤에 숨어 있었다. **한 번도 불려 보지 않은 채로.**

이제 분모는 **살아 있는 라우터의 쓰기 메서드 전수**다 (경로×메서드).
[실측 2026-09-07 · 라우터 705행 → 쓰기 377행]

    인증 필수  auth_required     익명이 **401/403** 을 받았다 [실측, 실제로 불렀다]
    공개 도달  public_reachable  익명이 핸들러 자리까지 갔다 → **선언 목록에
                                 사유와 함께** 이름이 있어야 한다. 없으면 **빨강**
    회색       grey              **못 쟀다.** 초록이 아니다 (exit 2)

★ 분모는 **줄 수 없다** (⑧). 증거의 쓰기 행수가 D-343 라우트 인벤토리의 쓰기 행수보다
  적으면 그것은 누군가 분모를 손으로 줄인 것이다 — 늘어나는 것만 허락한다.

보는 것 — 아홉
--------------
  ① ★ **`writes` 0건**   익명이 도달하고 그 핸들러가 쓰는 자리. **래칫이 없다.**
                          기존분 면제도 없다 — 여기만은 소급해서 갚는다
  ② **새 면 100%**       우리가 만드는 면(`NEW_SURFACE_PREFIXES`)은 관문 의무.
                          한 자리라도 관문 없이 태어나면 exit 1
  ③ **래칫** (D-311)     **관문이 아닌** 갈래의 건수가 기준선을 넘으면 exit 1.
                          `gated` 에는 래칫이 없다 — 관문은 늘어도 좋다
  ④ **선언 대조**        `public_by_design` 은 면제가 아니라 **선언**이다.
                          프로브의 선언 목록과 증거의 갈래가 어긋나면 잡는다
  ⑤ **증거 신선도**      낡은 증거로 내는 초록은 아무것도 재지 않은 것이다 (D-301)
  ⑥ ★ **탐침 방식**      증거가 **스키마를 통과하는 본문**으로 잰 것인가.
                          빈 본문 하나로 잰 옛 증거(=422 를 관문으로 세던 증거)로는
                          초록을 못 낸다. 판정 규칙이 바뀌면 **증거도 다시 떠야** 한다
  ⑦ ★ **못 잰 자리**     회색 칸은 「막혔다」가 아니라 **「모른다」**다.
                          빨강이 없고 이것만 있으면 **회색(exit 2)** — 0 으로 내지 않는다
  ⑧ ★★ **분모** (P-99)   증거가 **살아 있는 라우터 전수**로 잰 것인가.
                          손으로 추린 분모, 또는 D-343 인벤토리보다 **작은** 분모는 잡는다
  ⑨ ★★ **빨강** (P-99)   익명이 도달한 쓰기 자리가 **선언 목록에 없으면** 빨강이다.
                          선언에는 **한 줄 사유**가 붙어 있어야 한다

★ 왜 게이트가 컨테이너를 부르지 않나 (verify_route_inventory.py 와 같은 이유)
------------------------------------------------------------------------------
분류는 **런타임 레지스트리를 때려야** 나온다. 게이트가 매번 컨테이너를 띄우면 게이트가
환경에 매이고, 환경이 죽으면 게이트가 **초록으로** 죽는다. 그래서 게이트는 커밋된
증거를 본다. 증거를 다시 뜨는 것은 사람의 일이고, 낡은 증거는 ⑤가, 낡은 **방식**은
⑥이 잡는다.

    python scripts/verify_write_auth.py            # 판정
    python scripts/verify_write_auth.py --list     # 갈래별 목록
    python scripts/verify_write_auth.py --freeze   # 기준선 갱신
    python scripts/verify_write_auth.py --self-test
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "docs" / "agent" / "evidence" / "D-368"
SURFACE = EVIDENCE / "write_surface.json"
BASELINE = EVIDENCE / "write_auth_baseline.json"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: **우리가 만드는 면.** 여기서는 관문이 100% 다 — 기존분 래칫이 닿지 않는다 (D-358).
#: 새 커널 App 이 생기면 여기에 접두어를 더한다.
NEW_SURFACE_PREFIXES = ("/api/dsm/",)

#: 증거가 이보다 오래되면 판정을 못 한 것으로 본다.
MAX_AGE_DAYS = 30

#: ★ 탐침이 **스키마를 통과하는 본문**으로 쟀다는 표시. 이 표시가 없는 증거는
#:   빈 본문 하나로 잰 옛 증거이고, 그 증거의 「관문」 칸에는 422 가 섞여 있다.
#:   ★★ P-99 로 표시를 올렸다 — **분모가 바뀌면 증거도 다시 떠야 한다.**
REQUIRED_PROBE_MODE = "live-router-schema-passing-body"

#: ★ 세 칸 (P-99). 게이트가 읽는 것은 이 셋이다.
BUCKET_AUTH, BUCKET_PUBLIC, BUCKET_GREY = "auth_required", "public_reachable", "grey"
BUCKETS = (BUCKET_AUTH, BUCKET_PUBLIC, BUCKET_GREY)

#: ⑧ 분모 대조의 상대. **다른 차선이 다른 도구로 뜬 전수**다 — 두 수가 갈리면
#: 둘 중 하나가 거짓말이고, 우리 쪽이 **작으면** 우리가 추린 것이다.
INVENTORY = ROOT / "docs" / "agent" / "evidence" / "D-343" / "route_inventory.json"
WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")

#: 여섯 갈래 + 선언. 순서는 보고에 나오는 순서다.
VERDICTS = ("writes", "read_only_in_practice", "gated", "schema_rejected",
            "unreachable", "blocked_other", "public_by_design")

#: ★ **관문이 아닌 갈래.** 여기만 래칫이 걸린다 — 관문(`gated`)은 늘어도 좋다.
#:   `writes` 는 여기 없다: 그 갈래에는 래칫이 아니라 **0건 절대선**이 걸린다.
RATCHETED = ("read_only_in_practice", "schema_rejected", "unreachable",
             "blocked_other", "public_by_design")


def bucket_of(row: dict) -> str:
    """★ 게이트가 **스스로** 세 칸을 다시 센다 (P-99).

    증거가 적어 온 `bucket` 을 그대로 믿지 않는다 — 탐침과 게이트가 갈리면 그
    사실 자체가 잡혀야 한다(아래 `judge` 의 ⑨-b). 규칙은 `probe_write_surface.bucket()`
    과 **같아야 한다**; 사본을 두는 것은 게이트가 Django 없이 돌아야 하기 때문이다.
    """
    v = row.get("measured_verdict") or row.get("verdict")
    if v == "gated":
        return BUCKET_AUTH
    if v == "writes":
        return BUCKET_PUBLIC
    if v == "read_only_in_practice":
        # 대체물이 `@path_permission` 을 함께 지운 자리 — 「도달」이 탐침 인공물이다
        return BUCKET_GREY if row.get("authz_path_permission") else BUCKET_PUBLIC
    if v == "public_by_design":
        return BUCKET_PUBLIC            # 옛 증거 호환 (P-99 이전의 이름표 칸)
    return BUCKET_GREY


def buckets_of(rows: list[dict]) -> dict[str, int]:
    return {b: sum(1 for r in rows if bucket_of(r) == b) for b in BUCKETS}


def declared_of(payload: dict, baseline: dict) -> dict:
    """**선언 목록** — 이름마다 사유 한 줄. 정본은 탐침이 증거에 실어 보낸다."""
    d = payload.get("public_by_design_declared")
    if isinstance(d, dict) and d:
        return d
    return {p: "" for p in (baseline.get("public_by_design_paths") or [])}


def inventory_write_rows() -> int | None:
    """D-343 인벤토리의 **쓰기 메서드 행수**. 없으면 None (모른다고 적는다)."""
    if not INVENTORY.exists():
        return None
    try:
        inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    return sum(1 for r in (inv.get("routes") or [])
               if str(r.get("method", "")).upper() in WRITE_METHODS)


def counts_of(rows: list[dict]) -> dict[str, int]:
    return {v: sum(1 for r in rows if r.get("verdict") == v) for v in VERDICTS}


def headline(counts: dict[str, int]) -> str:
    """★ **첫 줄은 언제나 세 수로 시작한다** (P-83). 총합만 적는 보고는 받지 않는다."""
    return ("관문 %d · 도달·검증 %d · 도달 실패 %d"
            % (counts.get("gated", 0),
               counts.get("schema_rejected", 0),
               counts.get("unreachable", 0) + counts.get("blocked_other", 0)))


def headline3(boxes: dict[str, int], total: int, red: int) -> str:
    """★★ P-99 의 첫 줄 — **세 칸과 분모.** 분모 없는 비율은 수가 아니다 (D-301)."""
    return ("분모 %d(살아 있는 라우터 쓰기 전수) · 인증 필수 %d · 공개 도달 %d · 회색 %d "
            "· ★빨강 %d"
            % (total, boxes.get(BUCKET_AUTH, 0), boxes.get(BUCKET_PUBLIC, 0),
               boxes.get(BUCKET_GREY, 0), red))


def judge(payload: dict, baseline: dict, today: datetime) -> list[str]:
    """판정식은 **여기 한 곳에만** 둔다 (D-212). 파일 없이 시험할 수 있게 순수 함수로."""
    problems: list[str] = []
    rows = payload.get("routes") or []
    counts = counts_of(rows)

    # ⑥ 탐침 방식 — **판정 규칙이 바뀌면 증거도 다시 떠야 한다**
    mode = payload.get("probe_mode")
    if mode != REQUIRED_PROBE_MODE:
        problems.append(
            "★ 증거를 **옛 방식**으로 쟀다(probe_mode=%r · 필요한 값 %r) — 빈 본문 "
            "하나로 재면 422 가 나오고, 그 422 를 관문으로 세던 것이 턴 H 의 거짓 "
            "초록이었다. `probe_write_surface.py` 를 다시 돌려라 (P-83)"
            % (mode, REQUIRED_PROBE_MODE))

    # ① writes 0건 — 래칫 없음
    writing = [r for r in rows if r.get("verdict") == "writes"]
    for r in writing:
        problems.append(
            "★ 관문 없는 쓰기: %s %s (%s) — 익명이 핸들러에 도달하고 그 핸들러가 쓴다. %s "
            "쓰기 오염은 조용하고, 심어진 행은 진짜와 섞여 나중에 못 골라낸다 (D-368)"
            % (r.get("method"), r.get("path"), r.get("view", "?"), r.get("writes_by", "")))

    # ⑧ ★★ 분모 — **살아 있는 라우터로 셌는가.** 손으로 추린 분모는 잡는다 (P-99)
    den = payload.get("denominator") or {}
    if den.get("source") != "live-router":
        problems.append(
            "★★ 분모를 **손으로 추렸다**(denominator.source=%r · 필요한 값 "
            "'live-router') — 「auth= 콜백이 있으니 관문이 있을 것」은 추정이고(D-280), "
            "그 추정이 347자리를 한 번도 안 불러 본 채로 분모 밖에 두었다 (P-99)"
            % den.get("source"))
    elif den.get("write_method_rows") != len(rows):
        problems.append(
            "★ 증거가 스스로와 어긋난다: denominator.write_method_rows=%r 인데 routes "
            "는 %d줄이다 — 둘 중 하나는 잰 수가 아니다 (D-301)"
            % (den.get("write_method_rows"), len(rows)))
    inv = inventory_write_rows()
    if inv is None:
        problems.append(
            "D-343 라우트 인벤토리를 못 읽었다(%s) — 분모를 **대조할 상대가 없다.** "
            "`probe_route_inventory.py` 를 먼저 돌린다" % INVENTORY.name)
    elif len(rows) < inv:
        problems.append(
            "★★ 분모가 **줄었다**: 이 증거의 쓰기 행 %d < D-343 인벤토리의 쓰기 행 %d. "
            "분모는 늘기만 한다 — 줄었다면 누군가 손으로 추린 것이다 (P-99)"
            % (len(rows), inv))

    # ⑨ ★★ 빨강 — 익명이 **도달한** 쓰기 자리인데 선언 목록에 없다 (P-99)
    declared = declared_of(payload, baseline)
    for r in rows:
        if bucket_of(r) != BUCKET_PUBLIC:
            continue
        path = r.get("path")
        if path not in declared:
            problems.append(
                "★★ 선언되지 않은 공개 쓰기 면: %s %s (%s · 실측 %s) — 익명이 핸들러 "
                "자리까지 **갔다.** `public_by_design` 은 면제가 아니라 **선언**이고, "
                "선언에는 사람이 적은 **사유 한 줄**이 붙어야 한다 (P-99 · D-264)"
                % (r.get("method"), path, r.get("view", "?"),
                   r.get("measured_verdict") or r.get("verdict")))
        elif isinstance(payload.get("public_by_design_declared"), dict)                 and not str(declared.get(path) or "").strip():
            problems.append(
                "★ 선언에 **사유가 없다**: %s — 이름만 적힌 선언은 면제와 같다" % path)

    # ⑨-b 탐침과 게이트가 갈리면 그 사실을 잡는다 (판정식이 두 곳에 있으면 갈린다)
    for r in rows:
        if r.get("bucket") and r["bucket"] != bucket_of(r):
            problems.append(
                "★ 탐침과 게이트의 칸이 갈렸다: %s %s — 탐침 %r · 게이트 %r. "
                "판정식이 두 곳에 있으면 언젠가 갈린다 (D-212)"
                % (r.get("method"), r.get("path"), r["bucket"], bucket_of(r)))

    # ② 새 면 100%
    for r in rows:
        if any(str(r.get("path", "")).startswith(p) for p in NEW_SURFACE_PREFIXES):
            if bucket_of(r) != BUCKET_AUTH and r.get("path") not in declared:
                problems.append(
                    "★ 새 면인데 관문이 없다: %s %s (지금 %s) — 새 면은 100%% 의무다. "
                    "기존분 래칫은 여기 닿지 않는다 (D-358 · D-368)"
                    % (r.get("method"), r.get("path"), r.get("verdict")))

    # ③-b ★ 칸 래칫 (P-99) — **공개 도달과 회색은 늘 수 없다.** 인증 필수는 늘어도 좋다
    boxes = buckets_of(rows)
    for b in (BUCKET_PUBLIC, BUCKET_GREY):
        base = (baseline.get("buckets") or {}).get(b)
        if base is None:
            problems.append("기준선에 %r 칸이 없다 — `--freeze` 로 먼저 잠근다 (P-99)" % b)
        elif boxes[b] > base:
            problems.append(
                "★ 래칫: %s 칸이 %d자리 → %d자리로 **늘었다.** 인증 필수 칸만 늘 수 "
                "있다 (D-311 · P-99)" % (b, base, boxes[b]))

    # ③ 래칫 — **관문이 아닌 갈래만**
    for v in RATCHETED:
        base = baseline.get(v)
        if base is None:
            problems.append("기준선에 %r 갈래가 없다 — `--freeze` 로 먼저 잠근다" % v)
        elif counts[v] > base:
            problems.append(
                "★ 래칫: %s 가 %d자리 → %d자리로 **늘었다.** 관문이 아닌 갈래는 "
                "줄기만 한다 (D-311)" % (v, base, counts[v]))

    # ④ 선언 대조 — 옛 증거(`verdict=public_by_design`)도 같은 잣대로 본다.
    #   ⑨ 가 실측 칸으로 이미 보지만, 실측 칸이 회색인 선언 자리는 ⑨ 를 안 지난다.
    for r in rows:
        if r.get("verdict") == "public_by_design" and r.get("path") not in declared:
            problems.append(
                "★ 선언되지 않은 공개 쓰기 면: %s — `public_by_design` 은 면제가 아니라 "
                "**선언**이다. 사람이 목록에 이름을 적어야 한다" % r.get("path"))

    # ⑤ 신선도
    stamp = payload.get("measured_at")
    if not stamp:
        problems.append("증거에 측정 시각이 없다 — 언제 잰 것인지 모르는 수는 수가 아니다")
    else:
        try:
            when = datetime.fromisoformat(stamp)
            age = (today - when).days
            if age > MAX_AGE_DAYS:
                problems.append(
                    "증거가 %d일 됐다(상한 %d일) — 낡은 증거로 내는 초록은 아무것도 "
                    "재지 않은 것이다 (D-301)" % (age, MAX_AGE_DAYS))
        except ValueError:
            problems.append("측정 시각을 읽지 못했다: %r" % stamp)

    return problems


def undecided(payload: dict) -> list[str]:
    """⑦ **못 쟀다** — 빨강이 아니라 회색이다. 0 으로 내지 않는다 (규칙 ①).

    `schema_rejected` 는 「스키마를 맞춰 주고도 422 였다」는 뜻이다. 그 자리 뒤에
    관문이 있는지 **우리는 모른다** — 본문을 못 맞춰서 못 가 봤을 뿐이다.
    「막혔다」로 세면 그것이 곧 턴 H 의 거짓 초록이고, 「열렸다」로 세면 없는 빨강을
    만든다. 그래서 자기 칸에 두고 **판정 불가**로 낸다 (D-301 · P-12 ④).
    """
    out = []
    for r in payload.get("routes") or []:
        if bucket_of(r) != BUCKET_GREY:
            continue
        why = r.get("bucket_by") or ("실측 %s · 상태 %s"
                                     % (r.get("measured_verdict") or r.get("verdict"),
                                        r.get("status")))
        tail = ""
        if (r.get("measured_verdict") or r.get("verdict")) == "schema_rejected":
            tail = " (스키마 %d바퀴 · 못 채운 칸: %s)" % (
                r.get("rounds", 0),
                ", ".join(r.get("unresolved") or []) or "없음")
        out.append("%s %s — %s%s" % (r.get("method"), r.get("path"), why, tail))
    return out


def _fake(verdicts, *, measured_at=None, paths=None, mode=REQUIRED_PROBE_MODE,
          source="live-router", rows_declared=None, authz=()):
    now = measured_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []
    for i, v in enumerate(verdicts):
        rows.append({"method": "POST", "path": (paths or {}).get(i, "/api/x/%d" % i),
                     "verdict": v, "measured_verdict": v, "view": "m.f",
                     "writes_by": "", "rounds": 1, "unresolved": [],
                     "authz_path_permission": i in set(authz)})
    return {"measured_at": now, "probe_mode": mode, "routes": rows,
            "denominator": {"source": source,
                            "write_method_rows": (rows_declared
                                                  if rows_declared is not None
                                                  else len(rows))}}


def self_test() -> int:
    now = datetime.now(timezone.utc)
    base = {"read_only_in_practice": 4, "schema_rejected": 3, "unreachable": 3,
            "blocked_other": 2, "public_by_design": 11,
            "public_by_design_paths": ["/api/x/0"],
            "buckets": {BUCKET_AUTH: 999, BUCKET_PUBLIC: 99, BUCKET_GREY: 99}}

    # ★ 출생 표본 (D-310) — **이 도구를 만들게 한 바로 그 네 자리.**
    #   [실측 2026-09-11 · probe_write_surface.py] 익명이 핸들러에 도달하고
    #   그 핸들러가 쓰던 자리들이다. 첫 갈래가 이것을 잡지 못하면 이 게이트는
    #   초록을 내도 아무것도 재지 않은 것이다.
    BIRTH_SAMPLE = _fake(
        ["writes", "writes", "writes", "writes"],
        paths={
            0: "/api/media-data/detect-callback",
            1: "/api/media-data/upload-detection",
            2: "/api/flight-log/flight-log/delete/{ids}",
            3: "/api/stream-monitors/stream-monitors/external-stream-monitors/{id}",
        })

    # ★★ **두 번째 출생 표본** (P-83) — 턴 H 의 거짓 초록 그 자체.
    #   그때 이 게이트가 본 것은 「관문 17」이었고, 그 17 중 13이 422 였다.
    #   같은 모양을 넣었을 때 첫 줄이 **관문 4 · 도달·검증 13** 으로 나와야 한다.
    FALSE_GREEN_SAMPLE = _fake(["gated"] * 4 + ["schema_rejected"] * 13)

    checks = [
        ("★★ 턴 H 의 그 모양에서 첫 줄이 **관문 4 · 도달·검증 13** 으로 갈린다",
         headline(counts_of(FALSE_GREEN_SAMPLE["routes"]))
         == "관문 4 · 도달·검증 13 · 도달 실패 0"),
        ("★★ 422 를 관문으로 세지 않는다 — 세 수가 한 칸으로 합쳐지지 않는다",
         counts_of(FALSE_GREEN_SAMPLE["routes"])["gated"] == 4),
        ("★ 첫 줄은 언제나 세 수로 시작한다",
         headline({}).startswith("관문 0 · 도달·검증 0 · 도달 실패 0")),
        ("★ 도달 실패 칸에 blocked_other 를 함께 센다(사라지지 않게)",
         headline(counts_of(_fake(["unreachable", "blocked_other"])["routes"]))
         == "관문 0 · 도달·검증 0 · 도달 실패 2"),

        ("★ 출생 표본 — 관문 없이 쓰던 네 자리를 **넷 다** 잡는다",
         len([p for p in judge(BIRTH_SAMPLE, base, now)
              if "관문 없는 쓰기" in p]) == 4),
        ("★ writes 가 한 자리라도 있으면 잡는다",
         any("관문 없는 쓰기" in p
             for p in judge(_fake(["writes"]), base, now))),
        ("writes 가 0건이면 그 갈래로는 안 잡는다",
         not any("관문 없는 쓰기" in p
                 for p in judge(_fake(["gated"]), base, now))),
        ("★ 새 면(/api/dsm/)에 관문이 없으면 잡는다",
         any("새 면" in p for p in judge(
             _fake(["schema_rejected"], paths={0: "/api/dsm/things"}), base, now))),
        ("★ 새 면이라도 **관문이 있으면** 안 잡는다 (음성 대조)",
         not any("새 면" in p for p in judge(
             _fake(["gated"], paths={0: "/api/dsm/things"}), base, now))),
        ("★ 래칫 — 관문 아닌 갈래가 늘면 잡는다",
         any("래칫" in p for p in judge(
             _fake(["read_only_in_practice"] * 5), base, now))),
        ("★★ 관문(gated)이 **늘어도** 래칫에 안 걸린다 — 관문은 늘어야 한다",
         not any("래칫" in p for p in judge(_fake(["gated"] * 99), base, now))),
        ("갈래가 줄면 안 잡는다",
         not any("래칫" in p for p in judge(
             _fake(["read_only_in_practice"]), base, now))),
        ("★ 선언되지 않은 공개 면은 잡는다",
         any("선언되지 않은" in p for p in judge(
             _fake(["public_by_design"], paths={0: "/api/surprise"}), base, now))),
        ("선언된 공개 면은 안 잡는다",
         not any("선언되지 않은" in p for p in judge(
             _fake(["public_by_design"], paths={0: "/api/x/0"}), base, now))),
        ("★ 증거가 낡으면 잡는다",
         any("낡은 증거" in p for p in judge(
             _fake(["gated"], measured_at="2020-01-01T00:00:00+00:00"), base, now))),
        ("★★ 옛 방식(빈 본문)으로 잰 증거로는 초록을 못 낸다",
         any("옛 방식" in p for p in judge(
             _fake(["gated"], mode=None), base, now))),
        ("★ 기준선이 없으면 초록을 내지 않는다",
         bool(judge(_fake(["gated"]), {}, now))),
        ("★ schema_rejected 는 **못 쟀다**로 샌다 (0 으로 내지 않는다)",
         len(undecided(_fake(["schema_rejected", "gated"]))) == 1),
        ("관문만 있으면 못 잰 것이 없다 (음성 대조)",
         undecided(_fake(["gated"])) == []),

        # ═══ P-99 · 분모 (⑧) — **손으로 적은 분모를 잡는다** ═══
        ("★★ 분모를 손으로 추린 증거는 초록을 못 낸다",
         any("분모를 **손으로 추렸다**" in p for p in judge(
             _fake(["gated"], source="auth-callback-missing"), base, now))),
        ("★ 살아 있는 라우터로 잰 분모는 그 갈래로 안 잡는다 (음성 대조)",
         not any("분모를 **손으로 추렸다**" in p
                 for p in judge(_fake(["gated"]), base, now))),
        ("★★ 증거가 스스로와 어긋나면 잡는다 (분모 칸 ≠ routes 줄수)",
         any("스스로와 어긋난다" in p for p in judge(
             _fake(["gated"], rows_declared=999), base, now))),
        ("★★ D-343 인벤토리보다 **작은** 분모는 잡는다 — 분모는 늘기만 한다",
         (lambda inv: inv is None or any(
             "분모가 **줄었다**" in p
             for p in judge(_fake(["gated"]), base, now)))(inventory_write_rows())),

        # ═══ P-99 · 세 칸 (게이트가 스스로 센다) ═══
        ("★★ 401/403 만 **인증 필수** 칸이다",
         bucket_of({"measured_verdict": "gated"}) == BUCKET_AUTH),
        ("★★ 422 는 인증 필수 칸이 **아니다** — 회색이다",
         bucket_of({"measured_verdict": "schema_rejected"}) == BUCKET_GREY),
        ("★ 404/405 도 회색이다", bucket_of({"measured_verdict": "unreachable"})
         == BUCKET_GREY),
        ("★★ 도달·쓴다는 공개 도달이다",
         bucket_of({"measured_verdict": "writes"}) == BUCKET_PUBLIC),
        ("★★ `@path_permission` 이 붙은 「도달·안 씀」은 회색이다 (턴 J)",
         bucket_of({"measured_verdict": "read_only_in_practice",
                    "authz_path_permission": True}) == BUCKET_GREY),
        ("★ 권한 대장이 없으면 「도달·안 씀」은 공개 도달이다 (음성 대조)",
         bucket_of({"measured_verdict": "read_only_in_practice"}) == BUCKET_PUBLIC),
        ("★ 첫 줄에 **분모**가 들어간다 (분모 없는 비율은 수가 아니다)",
         headline3({BUCKET_AUTH: 1}, 377, 0).startswith("분모 377")),

        # ═══ P-99 · 빨강 (⑨) ═══
        ("★★ 익명이 도달한 쓰기 자리가 선언에 없으면 **빨강**이다",
         any("선언되지 않은 공개 쓰기 면" in p for p in judge(
             _fake(["read_only_in_practice"], paths={0: "/api/surprise"}), base, now))),
        ("★ 선언에 있으면 빨강이 아니다 (음성 대조)",
         not any("선언되지 않은 공개 쓰기 면" in p for p in judge(
             _fake(["read_only_in_practice"], paths={0: "/api/x/0"}), base, now))),
        ("★★ 이름만 적고 **사유가 없는 선언**은 잡는다",
         any("사유가 없다" in p for p in judge(
             dict(_fake(["read_only_in_practice"], paths={0: "/api/x/0"}),
                  public_by_design_declared={"/api/x/0": "   "}), base, now))),
        ("★ 사유가 있으면 안 잡는다 (음성 대조)",
         not any("사유가 없다" in p for p in judge(
             dict(_fake(["read_only_in_practice"], paths={0: "/api/x/0"}),
                  public_by_design_declared={"/api/x/0": "로그인"}), base, now))),
        ("★★ 회색은 빨강이 아니다 — 선언이 없어도 ⑨ 로는 안 잡힌다",
         not any("선언되지 않은 공개 쓰기 면" in p for p in judge(
             _fake(["read_only_in_practice"], paths={0: "/api/surprise"},
                   authz=(0,)), base, now))),
        ("★★ 그러나 회색은 **초록도 아니다** — 못 잰 자리로 샌다 (exit 2)",
         len(undecided(_fake(["read_only_in_practice"], authz=(0,)))) == 1),

        # ═══ P-99 · 탐침과 게이트가 갈리면 잡는다 ═══
        ("★★ 탐침이 적어 온 칸과 게이트가 센 칸이 갈리면 잡는다",
         any("칸이 갈렸다" in p for p in judge(
             (lambda f: (f["routes"][0].update({"bucket": BUCKET_AUTH}), f)[1])(
                 _fake(["writes"])), base, now))),
        ("★ 같으면 안 잡는다 (음성 대조)",
         not any("칸이 갈렸다" in p for p in judge(
             (lambda f: (f["routes"][0].update({"bucket": BUCKET_PUBLIC}), f)[1])(
                 _fake(["writes"])), base, now))),

        # ═══ P-99 · 칸 래칫 (③-b) ═══
        ("★★ 공개 도달 칸이 기준선을 넘으면 잡는다",
         any("public_reachable 칸이" in p for p in judge(
             _fake(["writes"] * 100), base, now))),
        ("★ 인증 필수 칸은 **늘어도** 안 잡는다 — 그 칸은 늘어야 한다",
         not any("칸이" in p and "래칫" in p
                 for p in judge(_fake(["gated"] * 500), base, now))),
        ("★ 기준선에 칸이 없으면 초록을 내지 않는다",
         any("칸이 없다" in p for p in judge(
             _fake(["gated"]), {k: v for k, v in base.items() if k != "buckets"},
             now))),
    ]
    for name, ok in checks:
        print("  %s  %s" % ("OK  " if ok else "FAIL", name))
    bad = [n for n, ok in checks if not ok]
    pos = sum(1 for n, _ in checks if n.startswith("★"))
    print("[WRITEAUTH] 자기시험 %d건 %s (양성 %d · 음성 %d)"
          % (len(checks), "통과" if not bad else "실패", pos, len(checks) - pos))
    return EXIT_OK if not bad else EXIT_FAIL


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--freeze", action="store_true")
    args = ap.parse_args()

    rc = self_test()
    if args.self_test:
        return rc
    if rc != EXIT_OK:
        print("[WRITEAUTH] 자기시험이 실패했다 — 판정기를 먼저 고친다 (D-350)")
        return rc

    if not SURFACE.exists():
        print("[WRITEAUTH] 증거가 없다: %s — `probe_write_surface.py` 를 컨테이너에서 "
              "먼저 돌린다. **판정 불가**다" % SURFACE.relative_to(ROOT))
        return EXIT_UNDECIDABLE
    payload = json.loads(SURFACE.read_text(encoding="utf-8"))
    rows = payload.get("routes") or []
    counts = counts_of(rows)

    boxes = buckets_of(rows)
    declared = declared_of(payload, json.loads(BASELINE.read_text(encoding="utf-8"))
                           if BASELINE.exists() else {})
    reds = [r for r in rows
            if bucket_of(r) == BUCKET_PUBLIC and r.get("path") not in declared]

    # ★★ 첫 줄 — **분모와 세 칸** (P-99). 이 순서와 이 낱말을 바꾸지 마라.
    print("[WRITEAUTH] %s" % headline3(boxes, len(rows), len(reds)))
    # ★★ 둘째 줄 — 세 수로 시작한다 (P-83). 이 순서와 이 낱말을 바꾸지 마라.
    print("           %s · ★관문없이 도달·쓰기 %d · 도달·안씀 %d · 선언 %d "
          "(잰 때 %s · 방식 %s · 분모 %s)"
          % (headline(counts), counts["writes"], counts["read_only_in_practice"],
             counts["public_by_design"],
             payload.get("measured_at", "?"), payload.get("probe_mode", "?"),
             (payload.get("denominator") or {}).get("source", "?")))
    for v in VERDICTS:
        star = " ★" if v == "writes" and counts[v] else ""
        print("    %-24s %3d자리%s" % (v, counts[v], star))
    for r in reds:
        print("    ★빨강 %s %s (%s)" % (r.get("method"), r.get("path"),
                                        r.get("view", "?")))

    if args.list:
        for v in VERDICTS:
            names = ["%s %s" % (r["method"], r["path"]) for r in rows if r["verdict"] == v]
            if names:
                print("  [%s]" % v)
                for n in sorted(names):
                    print("    %s" % n)

    if args.freeze:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        frozen = {
            "note": ("D-368 · P-83 · P-99 래칫 기준선. **`writes` 도 `gated` 도 "
                     "여기 없다** — `writes` 에는 래칫이 아니라 0건 절대선이 걸리고, "
                     "`gated`(관문)는 늘어야 하는 갈래라 래칫을 걸지 않는다. "
                     "★ `buckets` 는 P-99 의 세 칸 기준선이다: `public_reachable` 과 "
                     "`grey` 는 늘 수 없고 `auth_required` 만 늘 수 있다. "
                     "`write_method_rows` 는 **분모 자체의 기준선**이다 — 분모는 "
                     "살아 있는 라우터에서 세며, 줄어들면 손으로 추린 것이다."),
            "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "public_by_design_paths": sorted(
                r["path"] for r in rows if r["verdict"] == "public_by_design"),
            # ★ P-99 — 칸 래칫의 기준선과, **분모 자체의 기준선**
            "buckets": buckets_of(rows),
            "write_method_rows": len(rows),
            "denominator_source": (payload.get("denominator") or {}).get("source"),
        }
        for v in RATCHETED:
            frozen[v] = counts[v]
        BASELINE.write_text(json.dumps(frozen, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        print("[WRITEAUTH] 기준선 기록 → %s" % BASELINE.relative_to(ROOT))
        return EXIT_OK

    if not BASELINE.exists():
        print("[WRITEAUTH] 기준선이 없다 — `--freeze` 로 오늘 현황을 먼저 잠근다. "
              "기준선 없이 내는 초록은 아무것도 재지 않은 것이다 (D-301)")
        return EXIT_FAIL
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    problems = judge(payload, baseline, datetime.now(timezone.utc))
    grey = undecided(payload)

    if problems:
        print("[WRITEAUTH] 위반")
        for p in problems:
            print("  · %s" % p)
        if grey:
            print("  (그리고 **못 잰 자리** %d — 아래 회색 목록)" % len(grey))
            for g in grey:
                print("    ? %s" % g)
        return EXIT_FAIL

    if grey:
        # ★ 규칙 ① — 못 잰 것은 exit 2 로 낸다. 0 으로 내지 않는다.
        print("[WRITEAUTH] **못 쟀다** — 회색 칸이 %d자리 있다(400/422·404/405·그 밖의 "
              "상태·탐침 인공물). 그 자리에 관문이 있는지 없는지 이 증거로는 말할 수 "
              "없다 — 0 으로 내지 않는다 (D-301 · P-99)" % len(grey))
        for g in grey:
            print("    ? %s" % g)
        return EXIT_UNDECIDABLE

    print("[WRITEAUTH] 통과 — **익명이 도달해서 쓰는 자리 0건.** 새 면은 100% (D-368 · P-83)")
    return EXIT_OK


if __name__ == "__main__":
    from _gate_header import gate_header, file_stamp  # P-107 — TARGET/AS/SOURCE
    from _gate_header import count_json as _cj
    _n_surf = _cj(SURFACE, "buckets")
    _n_inv = _cj(INVENTORY, "routes")
    gate_header(
        __file__,
        measured=("**역할 0개 계정이 쓰는 자리**가 있는가 — **분모 %s건**"
                  "(커밋된 라우트 인벤토리 전수 · 지금 셌다)에서 뽑은 쓰기 표면 "
                  "· 통 %s · 쓰기 메서드 %d종 · 잠근 자리 %d. ★ 분모는 "
                  "**손 목록 30 이 아니다** — 손 목록이었을 때 347자리가 한 번도 "
                  "안 불렸다(출생 표본 ②)"
                  % (_n_inv if _n_inv else "못 셌다",
                     _n_surf if _n_surf else "못 셌다",
                     len(WRITE_METHODS), len(RATCHETED))),
        target="쓰기 표면 " + str(SURFACE.relative_to(ROOT)).replace("\\", "/") + " — 살아 있는 라우터 705행에서 뽑은 377행(손 목록 30 아님)",
        as_="이 게이트 자신은 자격 없이 증거를 읽는다. 표면을 **때린** 쪽은 `probe_write_surface.py` 이고 익명·비인가 두 결로 때렸다 (탐침 모드 " + REQUIRED_PROBE_MODE + ")",
        source=file_stamp(SURFACE) + " + " + file_stamp(BASELINE) + " + " + file_stamp(INVENTORY),
    )
    sys.exit(main())
