#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-105 강제 도구 — **역할 없는 계정이 자료를 읽으면 exit 1.**

    쓰기 오염 — 들어온 것도 되돌릴 수 없고, 게다가 조용하다
    읽기 유출 — **나간 것은 되돌릴 수 없다.** 다만 무엇이 나갔는지는 안다

`verify_write_auth.py` 가 쓰기 면에 하는 일을 이 게이트가 **읽기 면**에 한다.
다른 점은 하나다: 쓰기 게이트가 세는 것은 「익명이 도달했는가」이고, 이 게이트가
세는 것은 **「무엇이 나왔는가」**다. 도달만 세면 턴 L 의 15장이 안 잡힌다.

이 게이트를 만들게 한 것 (P-98 · 턴 L)
--------------------------------------
`gxprobe_e2e` 는 **인증된 계정인데 역할이 0개**다 (`user.roles` M2M 이 비어 있다.
이 제품에는 단수 `role` 필드가 **없어서** `getattr(u,"role",None)` 이 조용히 None 을
돌려주었고, 그 None 이 인덱스에 `NO_ROLE` 로 적혔다 — 채워져 있었지만 아무것도
재고 있지 않았다). 그 계정으로 찍은 33장을 전부 열어 세었더니 **15장이 실제 자료를
그렸다** — 카메라 이름·발생 시각이 든 이벤트 표, NOTAM 기록, 휴대전화 수신함, 프로필.
제대로 거부를 낸 것은 **2장**뿐이었다.

제품 판정 (CPO · 2026-09-07)
----------------------------
    역할이 없는 계정이 볼 수 있는 화면은 **정확히 하나**다:
        「역할이 아직 없습니다 · 관리자에게 역할 부여를 요청했습니다」
    **그 밖의 모든 화면과 모든 API 는 403 이다.**

보는 것 — 열
------------
  ① ★★ **빨강 0건**      역할 0개 계정이 자료를 받은 자리. **래칫이 없다** —
                          기존분 면제도, 예외 슬롯도 없다 (D-327). 0건이 절대선이다
  ② ★ **익명 빨강 0건**   자격증명 없이 자료가 나가는 자리. 선언 목록에 없으면 빨강
  ③ **분모** (P-99)      증거가 **살아 있는 라우터 전수**로 잰 것인가.
                          손으로 추린 분모, D-343 인벤토리보다 **작은** 분모는 잡는다
  ④ **탐침 방식**        판정 규칙이 바뀌면 **증거도 다시 떠야 한다**
  ⑤ **회색 래칫**        못 잰 자리는 늘 수 없다. 회색은 「막혔다」가 아니라 「모른다」다
  ⑥ **선언 대조**        허용목록은 면제가 아니라 **선언**이다. 이름마다 **사유 한 줄**이
                          있어야 하고, 그 이름이 **라우터에 실재**해야 한다
  ⑦ ★ **역할 0개 허용목록**  CPO 판정은 화면 하나다. 이 목록이 커지면 그 판정이
                          조용히 뒤집힌 것이다 — 상한을 걸어 잡는다
  ⑧ ★★ **거짓 초록 401**  `admin 도 같은 401` 인 자리를 관문으로 세지 않는다.
                          그것은 탐침의 토큰이 죽은 것이다 (턴 M 출생 표본 151자리)
  ⑨ **증거 신선도**      낡은 증거로 내는 초록은 아무것도 재지 않은 것이다 (D-301)
  ⑩ ★ **못 잰 자리**     회색만 남으면 **회색(exit 2)** 이다. 0 으로 내지 않는다

★ 왜 게이트가 컨테이너를 부르지 않나 (`verify_write_auth.py` 와 같은 이유)
--------------------------------------------------------------------------
분류는 **살아 있는 서버를 때려야** 나온다. 게이트가 매번 컨테이너를 띄우면 게이트가
환경에 매이고, 환경이 죽으면 게이트가 **초록으로** 죽는다. 그래서 게이트는 커밋된
증거를 보고, 증거를 다시 뜨는 것은 사람의 일이다. 낡은 증거는 ⑨가, 낡은 **방식**은
④가, 손으로 줄인 분모는 ③이 잡는다.

    python scripts/verify_read_auth.py            # 판정
    python scripts/verify_read_auth.py --list     # 칸별 목록
    python scripts/verify_read_auth.py --freeze   # 기준선 갱신
    python scripts/verify_read_auth.py --self-test
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "docs" / "agent" / "evidence" / "P-105"
SURFACE = EVIDENCE / "read_surface.json"
BASELINE = EVIDENCE / "read_auth_baseline.json"
INVENTORY = ROOT / "docs" / "agent" / "evidence" / "D-343" / "route_inventory.json"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

READ_METHODS = ("GET", "HEAD")
MAX_AGE_DAYS = 30

#: ★ 탐침이 **역할 0개 계정으로 진짜 불러서** 쟀다는 표시. 이 표시가 없는 증거는
#:   도달만 세던 옛 증거이고, 그 증거로는 15장이 그린 표를 못 본다.
REQUIRED_PROBE_MODE = "live-router-authenticated-role0-real-call"

#: ★ CPO 판정은 화면 **하나**다. 역할 0개 허용목록이 이보다 커지면 그 판정이
#:   조용히 뒤집힌 것이다 — 사람이 다시 판정해야 한다.
ROLE0_ALLOW_MAX = 2

BUCKET_RED, BUCKET_GREEN = "red", "green"
BUCKET_PUBLIC, BUCKET_GREY = "public_by_design", "grey"
BUCKETS = (BUCKET_RED, BUCKET_GREEN, BUCKET_PUBLIC, BUCKET_GREY)

#: ⑤ 래칫이 걸리는 칸. **초록만 늘 수 있다.**
RATCHETED_BUCKETS = (BUCKET_RED, BUCKET_PUBLIC, BUCKET_GREY)


def bucket_of(row: dict) -> str:
    """★ 게이트가 **스스로** 칸을 다시 센다. 증거가 적어 온 칸을 그대로 믿지 않는다.

    규칙은 `probe_read_surface.classify()` 와 **같아야 한다**; 사본을 두는 것은
    게이트가 Django 도 서버도 없이 돌아야 하기 때문이다. 갈리면 아래 `judge` 가 잡는다.
    """
    st = row.get("subject_status")
    if row.get("subject_data"):
        if row.get("declared_public") or row.get("declared_role0"):
            return BUCKET_PUBLIC
        return BUCKET_RED
    if st in (401, 403):
        # ★★ 출생 표본 — admin 도 같은 401 이면 그것은 관문이 아니라 죽은 토큰이다
        if st == 401 and row.get("control_status") == 401:
            return BUCKET_GREY
        return BUCKET_GREEN
    if st is not None and 200 <= int(st) < 300:
        why = row.get("subject_why") or ""
        if "거부 봉투" in why:
            return BUCKET_GREEN
        if row.get("control_data"):
            return BUCKET_GREEN
        return BUCKET_GREY
    return BUCKET_GREY


def buckets_of(rows: list) -> dict:
    return {b: sum(1 for r in rows if bucket_of(r) == b) for b in BUCKETS}


def anon_red_rows(rows: list) -> list:
    """익명이 자료를 받았는데 **공개 선언에 없는** 자리. 역할 0개 허용목록은 안 먹는다."""
    return [r for r in rows if r.get("anon_data") and not r.get("declared_public")]


def inventory_read_rows():
    """D-343 인벤토리의 **읽기 메서드 행수**. 없으면 None (모른다고 적는다)."""
    if not INVENTORY.exists():
        return None
    try:
        inv = json.loads(INVENTORY.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    return sum(1 for r in (inv.get("routes") or [])
               if str(r.get("method", "")).upper() in READ_METHODS)


def headline(boxes: dict, total: int) -> str:
    """★★ 첫 줄 — **분모와 네 칸.** 분모 없는 비율은 수가 아니다 (D-301).
    이 순서와 이 낱말을 바꾸지 마라."""
    return ("분모 %d(살아 있는 라우터 읽기 전수) · ★빨강 %d · 초록 %d · 공개 %d · 회색 %d"
            % (total, boxes.get(BUCKET_RED, 0), boxes.get(BUCKET_GREEN, 0),
               boxes.get(BUCKET_PUBLIC, 0), boxes.get(BUCKET_GREY, 0)))


def judge(payload: dict, baseline: dict, today: datetime) -> list:
    """판정식은 **여기 한 곳에만** 둔다 (D-212). 파일 없이 시험할 수 있게 순수 함수로."""
    problems = []
    rows = payload.get("routes") or []
    boxes = buckets_of(rows)

    # ④ 탐침 방식
    mode = payload.get("probe_mode")
    if mode != REQUIRED_PROBE_MODE:
        problems.append(
            "★ 증거를 **옛 방식**으로 쟀다(probe_mode=%r · 필요한 값 %r) — 도달만 세던 "
            "증거로는 「무엇이 나왔는가」를 말할 수 없다. `probe_read_surface.py` 를 "
            "다시 돌려라 (P-105)" % (mode, REQUIRED_PROBE_MODE))

    # ★ 주인공이 정말 역할 0개인가. 여기가 틀리면 아래 전부가 무효다
    subj = payload.get("subject") or {}
    if subj.get("roles"):
        problems.append(
            "★★ 주인공 계정에 역할이 있다(%s) — 이 게이트는 **역할 0개** 계정을 재는 "
            "자다. 역할 있는 계정으로 잰 증거는 이 판정의 증거가 아니다" % subj.get("roles"))

    # ① ★★ 빨강 0건 — 래칫 없음, 예외 슬롯 없음 (D-327)
    for r in rows:
        if bucket_of(r) != BUCKET_RED:
            continue
        problems.append(
            "★★ 역할 0개 계정이 **자료를 읽는다**: %s %s (%s) — %d B · %d덩이 · 열쇠 %s. "
            "CPO 판정은 「역할 없는 계정은 화면 하나 말고 전부 403」이다 (P-105)"
            % (r.get("method"), r.get("path"), r.get("view", "?"),
               r.get("subject_bytes", 0), r.get("subject_units", 0),
               ", ".join((r.get("subject_keys") or [])[:6]) or "?"))

    # ② 익명 빨강 0건
    for r in anon_red_rows(rows):
        problems.append(
            "★ 익명이 **자료를 읽는다**: %s %s — %d B. 공개 선언 목록에 사유와 함께 "
            "이름이 없으면 빨강이다 (D-264 계열)"
            % (r.get("method"), r.get("path"), r.get("anon_bytes", 0)))

    # ③ 분모
    den = payload.get("denominator") or {}
    if den.get("source") != "live-router":
        problems.append(
            "★★ 분모를 **손으로 추렸다**(denominator.source=%r · 필요한 값 "
            "'live-router') — 손으로 고른 목록은 분모가 아니다 (P-99 · D-280)"
            % den.get("source"))
    elif den.get("read_method_rows") != len(rows):
        problems.append(
            "★ 증거가 스스로와 어긋난다: denominator.read_method_rows=%r 인데 routes 는 "
            "%d줄이다 — 둘 중 하나는 잰 수가 아니다 (D-301)"
            % (den.get("read_method_rows"), len(rows)))
    inv = inventory_read_rows()
    if inv is None:
        problems.append(
            "D-343 라우트 인벤토리를 못 읽었다(%s) — 분모를 **대조할 상대가 없다**"
            % INVENTORY.name)
    elif len(rows) < inv:
        problems.append(
            "★★ 분모가 **줄었다**: 이 증거의 읽기 행 %d < D-343 인벤토리의 읽기 행 %d. "
            "분모는 늘기만 한다 (P-99)" % (len(rows), inv))

    # ⑥ 선언 대조 — 사유 한 줄 · 라우터에 실재
    for name, decl in (("공개", payload.get("public_read_by_design") or {}),
                       ("역할0", payload.get("role0_allowed") or {})):
        for path, why in decl.items():
            if not str(why or "").strip():
                problems.append(
                    "★ %s 선언에 **사유가 없다**: %s — 이름만 적힌 선언은 면제와 같다"
                    % (name, path))
    ghosts = payload.get("declared_not_in_router")
    if ghosts is None:
        problems.append(
            "증거에 `declared_not_in_router` 칸이 없다 — 선언한 이름이 라우터에 "
            "실재하는지 못 쟀다. 탐침을 다시 돌린다")
    elif ghosts:
        problems.append(
            "★ 선언했는데 라우터에 **없는** 이름: %s — 없는 자리를 향한 선언은 "
            "아무것도 면제하지 않으면서 「열어 뒀다」고 읽힌다" % ", ".join(ghosts))

    # ⑦ 역할 0개 허용목록 상한
    r0 = payload.get("role0_allowed") or {}
    if len(r0) > ROLE0_ALLOW_MAX:
        problems.append(
            "★ 역할 0개 허용목록이 %d자리다(상한 %d) — CPO 판정은 화면 **하나**다. "
            "이 목록이 커지면 그 판정이 조용히 뒤집힌 것이다" % (len(r0), ROLE0_ALLOW_MAX))

    # ⑧ ★★ 거짓 초록 401 — 탐침이 적어 온 칸과 게이트가 센 칸이 갈리면 잡는다
    for r in rows:
        if r.get("bucket") and r["bucket"] != bucket_of(r):
            problems.append(
                "★ 탐침과 게이트의 칸이 갈렸다: %s %s — 탐침 %r · 게이트 %r. "
                "판정식이 두 곳에 있으면 언젠가 갈린다 (D-212)"
                % (r.get("method"), r.get("path"), r["bucket"], bucket_of(r)))

    # ⑤ 래칫 — 초록만 늘 수 있다
    for b in RATCHETED_BUCKETS:
        base = (baseline.get("buckets") or {}).get(b)
        if base is None:
            problems.append("기준선에 %r 칸이 없다 — `--freeze` 로 먼저 잠근다" % b)
        elif boxes[b] > base:
            problems.append(
                "★ 래칫: %s 칸이 %d자리 → %d자리로 **늘었다.** 초록 칸만 늘 수 있다 "
                "(D-311)" % (b, base, boxes[b]))

    # ⑨ 신선도
    stamp = payload.get("measured_at")
    if not stamp:
        problems.append("증거에 측정 시각이 없다 — 언제 잰 것인지 모르는 수는 수가 아니다")
    else:
        try:
            age = (today - datetime.fromisoformat(stamp)).days
            if age > MAX_AGE_DAYS:
                problems.append(
                    "증거가 %d일 됐다(상한 %d일) — 낡은 증거로 내는 초록은 아무것도 "
                    "재지 않은 것이다 (D-301)" % (age, MAX_AGE_DAYS))
        except ValueError:
            problems.append("측정 시각을 읽지 못했다: %r" % stamp)

    return problems


def undecided(payload: dict) -> list:
    """⑩ **못 쟀다** — 빨강이 아니라 회색이다. 0 으로 내지 않는다."""
    out = []
    for r in payload.get("routes") or []:
        if bucket_of(r) != BUCKET_GREY:
            continue
        out.append("%s %s — %s" % (r.get("method"), r.get("path"),
                                   r.get("bucket_by")
                                   or ("상태 %s" % r.get("subject_status"))))
    return out


# ─────────────────────────────────────────────────────────────────────────────
def _row(path="/api/x", status=200, data=False, why="", control_status=200,
         control_data=False, anon_data=False, pub=False, r0=False, bucket=None):
    row = {"method": "GET", "path": path, "view": "m.f",
           "subject_status": status, "subject_data": data, "subject_why": why,
           "subject_bytes": 100, "subject_units": 1, "subject_keys": ["id"],
           "control_status": control_status, "control_data": control_data,
           "anon_data": anon_data, "anon_bytes": 100,
           "declared_public": pub, "declared_role0": r0}
    if bucket:
        row["bucket"] = bucket
    return row


def _fake(rows, *, measured_at=None, mode=REQUIRED_PROBE_MODE, source="live-router",
          declared=None, r0=None, ghosts=(), roles=(), rows_declared=None):
    return {
        "measured_at": measured_at or datetime.now(timezone.utc).isoformat(
            timespec="seconds"),
        "probe_mode": mode,
        "subject": {"username": "gxprobe_e2e", "roles": list(roles)},
        "routes": rows,
        "declared_not_in_router": list(ghosts),
        "public_read_by_design": declared if declared is not None else {},
        "role0_allowed": r0 if r0 is not None else {},
        "denominator": {"source": source,
                        "read_method_rows": (rows_declared if rows_declared is not None
                                             else len(rows))},
    }


def self_test() -> int:
    now = datetime.now(timezone.utc)
    base = {"buckets": {BUCKET_RED: 999, BUCKET_GREEN: 0, BUCKET_PUBLIC: 99,
                        BUCKET_GREY: 999}}

    # ★★ 출생 표본 (D-310) — **이 게이트를 만들게 한 바로 그 자리들.**
    #   [실측 2026-09-07 · probe_read_surface.py] 역할 0개 계정이 받은 본문이다.
    BIRTH = _fake([
        _row("/api/dsm/events", data=True),                    # 이벤트 표 8,963 B
        _row("/api/v1/user/list", data=True),                  # 사용자 29명 44,209 B
        _row("/api/delivery/drone-monitoring/drone-status", data=True),   # 17,416 B
        _row("/api/dsm/deliveries", data=True),                # 16,044 B
    ])

    # ★★ **두 번째 출생 표본** (턴 M) — 이 탐침 자신의 거짓 초록.
    #   첫 실행은 151자리에서 401 을 받고 그것을 「관문」으로 셌다. 그런데 같은
    #   자리에서 **admin 도 401** 이었다 — 관문이 admin 을 막을 리가 없다.
    FALSE_GREEN = _fake([_row(status=401, control_status=401) for _ in range(151)])

    checks = [
        # ═══ ① 빨강 0건 — 절대선 ═══
        ("★★ 출생 표본 — 역할 0개가 자료를 읽던 네 자리를 **넷 다** 잡는다",
         len([p for p in judge(BIRTH, base, now) if "자료를 읽는다" in p]) == 4),
        ("★★ 자료가 한 자리라도 나가면 잡는다",
         any("자료를 읽는다" in p for p in judge(_fake([_row(data=True)]), base, now))),
        ("★ 403 이면 그 갈래로는 안 잡는다 (음성 대조)",
         not any("자료를 읽는다" in p
                 for p in judge(_fake([_row(status=403)]), base, now))),
        ("★★ **예외 슬롯이 없다** — 빨강은 래칫에 기대 살아남지 못한다 (D-327)",
         any("자료를 읽는다" in p for p in judge(
             _fake([_row(data=True)]),
             dict(base, buckets={BUCKET_RED: 9999, BUCKET_GREEN: 0,
                                 BUCKET_PUBLIC: 99, BUCKET_GREY: 999}), now))),

        # ═══ ⑧ 거짓 초록 401 (턴 M 출생 표본) ═══
        ("★★ 151자리 그 모양에서 **초록이 하나도 안 나온다** — 전부 회색이다",
         buckets_of(FALSE_GREEN["routes"])[BUCKET_GREEN] == 0),
        ("★★ 그 151자리는 회색으로 샌다 (초록이 아니다)",
         buckets_of(FALSE_GREEN["routes"])[BUCKET_GREY] == 151),
        ("★ admin 은 200 인데 나만 401 이면 그것은 **관문**이다 (음성 대조)",
         bucket_of(_row(status=401, control_status=200)) == BUCKET_GREEN),

        # ═══ 칸 세기 ═══
        ("★★ 자료가 나오면 빨강", bucket_of(_row(data=True)) == BUCKET_RED),
        ("★★ 선언된 자리는 빨강이 아니다",
         bucket_of(_row(data=True, pub=True)) == BUCKET_PUBLIC),
        ("★ 역할 0개 선언도 빨강을 지운다",
         bucket_of(_row(data=True, r0=True)) == BUCKET_PUBLIC),
        ("★★ 403 은 초록", bucket_of(_row(status=403)) == BUCKET_GREEN),
        ("★★ 200 인데 거부 봉투면 초록 (D-349 착시 ⑧)",
         bucket_of(_row(why="★ 거부 봉투다 — 200 안에 든 403")) == BUCKET_GREEN),
        ("★★ 200 인데 비었고 **admin 도 비었으면 회색** (초록이 아니다)",
         bucket_of(_row()) == BUCKET_GREY),
        ("★★ 200 인데 비었고 admin 은 자료를 받으면 초록 (관문이 비웠다)",
         bucket_of(_row(control_data=True)) == BUCKET_GREEN),
        ("★ 404 는 회색이다", bucket_of(_row(status=404)) == BUCKET_GREY),
        ("★ 500 도 회색이다", bucket_of(_row(status=500)) == BUCKET_GREY),
        ("★ 네 칸 말고는 나오지 않는다",
         all(bucket_of(_row(status=s)) in BUCKETS
             for s in (200, 401, 403, 404, 422, 500, 503, None))),
        ("★ 첫 줄에 **분모**가 들어간다",
         headline({BUCKET_RED: 0}, 329).startswith("분모 329")),

        # ═══ ② 익명 ═══
        ("★★ 익명이 자료를 읽으면 잡는다",
         any("익명이 **자료를 읽는다**" in p
             for p in judge(_fake([_row(anon_data=True)]), base, now))),
        ("★ 공개 선언이 있으면 안 잡는다 (음성 대조)",
         not any("익명이 **자료를 읽는다**" in p
                 for p in judge(_fake([_row(anon_data=True, pub=True)]), base, now))),
        ("★★ **역할 0개 선언은 익명에 안 먹는다** — 익명은 로그인도 안 했다",
         any("익명이 **자료를 읽는다**" in p
             for p in judge(_fake([_row(anon_data=True, r0=True)]), base, now))),

        # ═══ ③ 분모 ═══
        ("★★ 분모를 손으로 추린 증거는 초록을 못 낸다",
         any("손으로 추렸다" in p for p in judge(
             _fake([_row(status=403)], source="hand-picked"), base, now))),
        ("★ 살아 있는 라우터면 그 갈래로 안 잡는다 (음성 대조)",
         not any("손으로 추렸다" in p
                 for p in judge(_fake([_row(status=403)]), base, now))),
        ("★★ 증거가 스스로와 어긋나면 잡는다 (분모 칸 ≠ routes 줄수)",
         any("스스로와 어긋난다" in p for p in judge(
             _fake([_row(status=403)], rows_declared=999), base, now))),

        # ═══ ⑥⑦ 선언 ═══
        ("★★ 사유 없는 선언은 잡는다",
         any("사유가 없다" in p for p in judge(
             _fake([_row(status=403)], declared={"/api/x": "  "}), base, now))),
        ("★ 사유가 있으면 안 잡는다 (음성 대조)",
         not any("사유가 없다" in p for p in judge(
             _fake([_row(status=403)], declared={"/api/x": "로그인 전에 부른다"}),
             base, now))),
        ("★★ 라우터에 **없는** 이름을 선언하면 잡는다 (첫 실행이 그랬다)",
         any("없는** 이름" in p for p in judge(
             _fake([_row(status=403)], ghosts=["/api/v1/auth/me"]), base, now))),
        ("★ 증거에 그 칸이 아예 없어도 잡는다 (옛 증거로 초록을 못 낸다)",
         any("declared_not_in_router" in p for p in judge(
             {k: v for k, v in _fake([_row(status=403)]).items()
              if k != "declared_not_in_router"}, base, now))),
        ("★★ 역할 0개 허용목록이 상한을 넘으면 잡는다 — CPO 판정은 화면 하나다",
         any("허용목록이" in p for p in judge(
             _fake([_row(status=403)],
                   r0={"/a": "x", "/b": "y", "/c": "z"}), base, now))),

        # ═══ 주인공 확인 ═══
        ("★★ 역할 **있는** 계정으로 잰 증거는 이 판정의 증거가 아니다",
         any("주인공 계정에 역할이 있다" in p for p in judge(
             _fake([_row(status=403)], roles=[[3, "User"]]), base, now))),
        ("★ 역할 0개면 안 잡는다 (음성 대조)",
         not any("주인공 계정에 역할이 있다" in p
                 for p in judge(_fake([_row(status=403)]), base, now))),

        # ═══ ⑤ 래칫 · ⑨ 신선도 · ⑩ 회색 ═══
        ("★ 회색이 늘면 잡는다",
         any("grey 칸이" in p for p in judge(
             _fake([_row(status=404) for _ in range(1000)]), base, now))),
        ("★★ 초록은 **늘어도** 안 잡힌다 — 그 칸은 늘어야 한다",
         not any("래칫" in p for p in judge(
             _fake([_row(status=403) for _ in range(500)]), base, now))),
        ("★ 기준선이 없으면 초록을 내지 않는다",
         bool(judge(_fake([_row(status=403)]), {}, now))),
        ("★ 증거가 낡으면 잡는다",
         any("낡은 증거" in p for p in judge(
             _fake([_row(status=403)], measured_at="2020-01-01T00:00:00+00:00"),
             base, now))),
        ("★★ 옛 방식으로 잰 증거로는 초록을 못 낸다",
         any("옛 방식" in p for p in judge(
             _fake([_row(status=403)], mode=None), base, now))),
        ("★★ 회색은 **못 잰 자리**로 샌다 (0 으로 내지 않는다)",
         len(undecided(_fake([_row(status=404), _row(status=403)]))) == 1),
        ("★ 관문만 있으면 못 잰 것이 없다 (음성 대조)",
         undecided(_fake([_row(status=403)])) == []),
    ]
    for name, ok in checks:
        print("  %s  %s" % ("OK  " if ok else "FAIL", name))
    bad = [n for n, ok in checks if not ok]
    neg = sum(1 for n, _ in checks if "음성 대조" in n)
    pos = len(checks) - neg
    print("[READAUTH] 자기시험 %d건 %s (양성 %d · 음성 %d)"
          % (len(checks), "통과" if not bad else "실패", pos, neg))
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
        print("[READAUTH] 자기시험이 실패했다 — 판정기를 먼저 고친다 (D-350)")
        return rc

    if not SURFACE.exists():
        print("[READAUTH] 증거가 없다: %s — `probe_read_surface.py` 를 컨테이너에서 "
              "먼저 돌린다. **판정 불가**다" % SURFACE.relative_to(ROOT))
        return EXIT_UNDECIDABLE
    payload = json.loads(SURFACE.read_text(encoding="utf-8"))
    rows = payload.get("routes") or []
    boxes = buckets_of(rows)
    reds = [r for r in rows if bucket_of(r) == BUCKET_RED]
    a_reds = anon_red_rows(rows)

    # ★★ 첫 줄 — 분모와 네 칸. 이 순서와 이 낱말을 바꾸지 마라.
    print("[READAUTH] %s" % headline(boxes, len(rows)))
    print("           역할 0개 계정 %s(역할 %s) · 익명 빨강 %d · 되살린 토큰 %s "
          "(잰 때 %s · 방식 %s · 분모 %s)"
          % ((payload.get("subject") or {}).get("username", "?"),
             (payload.get("subject") or {}).get("roles", "?"), len(a_reds),
             payload.get("relogins", "?"), payload.get("measured_at", "?"),
             payload.get("probe_mode", "?"),
             (payload.get("denominator") or {}).get("source", "?")))
    for r in sorted(reds, key=lambda x: -(x.get("subject_bytes") or 0))[:20]:
        print("    ★빨강 %s %s — %d B · %d덩이"
              % (r.get("method"), r.get("path"), r.get("subject_bytes", 0),
                 r.get("subject_units", 0)))
    if len(reds) > 20:
        print("    … 그리고 %d자리 더" % (len(reds) - 20))

    if args.list:
        for b in BUCKETS:
            names = ["%s %s" % (r["method"], r["path"])
                     for r in rows if bucket_of(r) == b]
            if names:
                print("  [%s] %d자리" % (b, len(names)))
                for n in sorted(names):
                    print("    %s" % n)

    if args.freeze:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps({
            "note": ("P-105 래칫 기준선. ★ `red` 칸에는 래칫이 아니라 **0건 절대선**이 "
                     "걸린다 — 이 수가 0 보다 크면 게이트는 언제나 exit 1 이다. "
                     "여기 적힌 red 수는 **면제가 아니라 기록**이다(오늘 몇 자리였는지). "
                     "`green` 만 늘 수 있고 `public_by_design`·`grey` 는 줄기만 한다."),
            "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "buckets": boxes,
            "read_method_rows": len(rows),
            "denominator_source": (payload.get("denominator") or {}).get("source"),
            "public_read_by_design_paths": sorted(
                payload.get("public_read_by_design") or {}),
            "role0_allowed_paths": sorted(payload.get("role0_allowed") or {}),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[READAUTH] 기준선 기록 → %s" % BASELINE.relative_to(ROOT))
        return EXIT_OK

    if not BASELINE.exists():
        print("[READAUTH] 기준선이 없다 — `--freeze` 로 오늘 현황을 먼저 잠근다. "
              "기준선 없이 내는 초록은 아무것도 재지 않은 것이다 (D-301)")
        return EXIT_FAIL
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    problems = judge(payload, baseline, datetime.now(timezone.utc))
    grey = undecided(payload)

    if problems:
        print("[READAUTH] 위반 %d건" % len(problems))
        for p in problems[:60]:
            print("  · %s" % p)
        if len(problems) > 60:
            print("  · … 그리고 %d건 더" % (len(problems) - 60))
        if grey:
            print("  (그리고 **못 잰 자리** %d — `--list` 로 본다)" % len(grey))
        return EXIT_FAIL

    if grey:
        print("[READAUTH] **못 쟀다** — 회색 칸이 %d자리 있다. 그 자리에서 역할 0개 "
              "계정이 무엇을 보는지 이 증거로는 말할 수 없다 — 0 으로 내지 않는다 "
              "(D-301)" % len(grey))
        for g in grey[:40]:
            print("    ? %s" % g)
        return EXIT_UNDECIDABLE

    print("[READAUTH] 통과 — **역할 0개 계정이 자료를 읽는 자리 0건.** 익명도 0건 (P-105)")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
