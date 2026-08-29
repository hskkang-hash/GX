#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""남은 55자리 **전수 종결** — 진술이 아니라 호출로 (D-362 · D-323).

왜 도구가 하나 더인가 — `probe_authn_gap_calls.py` 를 넓히지 않은 이유
----------------------------------------------------------------------
그 도구는 **GET 만 때린다**. 그것이 그 도구의 규약이고, 규약에는 사유가 있다:
*"쓰기 메서드는 부작용이 있어 부르지 않는다."* 그 줄을 지우면 그 도구의 판정이
무엇을 잰 것인지가 바뀌고, **지난 턴의 수(2 → 0)를 다시 읽을 수 없게 된다.**

D-362 가 요구하는 것은 다른 술어다:

    「전역 기본값 거절이 덮는다」는 **진술**이다. 55자리 전부를 익명으로 때려
    그 진술이 사실인지 본다. **확인 행위가 잠금을 내린다** (D-323).

술어가 다르면 도구가 다르다 — 같은 도구에 스위치를 달면 두 술어가 한 이름을 쓴다(D-337).

★ 쓰기를 어떻게 부르나 — **DB 는 되돌리고, 되돌릴 수 없는 것은 적는다**
------------------------------------------------------------------------
쓰기 24자리를 부르지 않으면 그 24자리는 영원히 「모른다」로 남는다. 그런데 부르면
부작용이 있다. 둘 다 나쁘므로 **가를 수 있는 부작용을 가른다**:

    · DB 쓰기      → `transaction.atomic()` 안에서 부르고 **언제나 되돌린다.**
                     남는 행이 없다
    · DB 밖 부작용 → 되돌릴 수 없다(외부 호출·파일·장비 명령). 그래서 **관문에 막힌
                     자리는 애초에 핸들러에 닿지 않고**, 닿은 자리는 그 사실 자체가
                     이 측정이 찾던 결과다. 닿은 자리를 `still_reached` 로 **이름을 적는다** —
                     "혹시 부작용이 있었을 자리" 가 곧 "관문이 없는 자리" 다

    ★ 그래서 이 도구를 **운영 환경에서 돌리지 않는다.** 개발 컨테이너 전용이다.
      운영에서 돌리려면 그때 판단을 다시 받는다(불변 제약: 운영 서버 직접 변경 금지).

3갈래 — D-362 가 정한 이름 그대로
---------------------------------
    blocked_by_middleware  실효 401/403. **관문이 걸렸다**
    still_reached          실효 2xx + 본문. **익명에게 데이터가 나갔다** ← 1건이면 최우선
    not_applicable         405(그 메서드 자리가 아니다) 등 이 호출로는 관문을 못 가르는 자리

★ 네 번째 수를 **따로 낸다** — 접지 않는다 (D-301 · D-349)
----------------------------------------------------------
404·422·400·500 은 **관문을 지났으나 본문을 못 낸 것**이다. D-362 의 술어(「본문 반환」)로는
`still_reached` 가 아니고, 그렇다고 `not_applicable` 도 아니다 — 관문은 분명히 없었다.
셋 중 하나에 접어 넣으면 그 수가 사라지고, 사라진 수는 다음 사람이 다시 판다.
그래서 `reached_no_data` 를 **따로 세어 함께 출력한다.** 3갈래는 3갈래대로 낸다.

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
        python /repo/scripts/probe_gap_route_settlement.py

호스트에서는 `--self-test` 만 돈다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 캐시 우회 (D-341 착시 ⑦). 우회하지 않으면 관문이 아니라 캐시를 잰다.
NO_CACHE_HEADER = {"HTTP_X_NO_CACHE": "true"}

_PARAM = re.compile(r"\{[^}]+\}")

#: dj-core 는 §0.4 — 세되 우리 분모에 넣지 않는다.
DJ_CORE_TOPS = ("core", "ninja", "ninja_extra", "ninja_jwt", "django")

#: ★ 음성 대조 (D-289). 닫혀 있다고 **아는** 자리에서 401 이 안 나오면 이 측정은 무효다.
CONTROL_CLOSED = (
    "/api/terminals/days-of-week",
    "/api/terminals/terminal-types",
    "/api/dronehw/drone-communication-management/online-drones",
)

BLOCKED = "blocked_by_middleware"
STILL_REACHED = "still_reached"
NOT_APPLICABLE = "not_applicable"
#: 3갈래에 안 들어가는 넷째. **접지 않고 따로 낸다.**
REACHED_NO_DATA = "reached_no_data"


def concrete(path: str) -> str:
    return _PARAM.sub("1", path)


def _ours(view: str) -> bool:
    return view.split(".")[0] not in DJ_CORE_TOPS


def effective_status(status: int, body: bytes) -> tuple[int, bool]:
    """봉투가 아니라 **내용**을 읽는다 (D-349 착시 ⑧ · D-284).

    이 저장소의 200 은 200 이 아닐 수 있다 — 본문에 `status_code: 403` 이 들어 있다.
    `probe_authn_gap_calls.effective_status` 와 **같은 판정식**이다. 복사한 것이 아니라
    아래 `_borrow()` 로 **그 함수를 빌려 온다** — 두 벌이면 언젠가 갈린다(D-337).
    """
    return _borrow()[0](status, body)


_BORROWED: tuple | None = None


def _borrow():
    """판정식을 **원본에서 가져온다.** 복사본을 두지 않는다.

    두 도구가 같은 질문("이 응답은 막힌 것인가")에 다른 답을 내면, 어느 쪽이 맞는지
    아무도 모른다. 그 상태가 D-337(같은 이름 다른 것)의 반대 얼굴이다.
    """
    global _BORROWED
    if _BORROWED is None:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import probe_authn_gap_calls as gap

        _BORROWED = (gap.effective_status, gap.verdict)
    return _BORROWED


def settle(status: int, body: bytes, *, method: str) -> str:
    """3갈래 + 넷째. **「안전하다」를 말하지 않는다** — 무엇이 일어났는지만 적는다."""
    eff, _ = effective_status(status, body)
    if eff in (401, 403):
        return BLOCKED
    if eff == 405:
        # 그 메서드 자리가 아니다. 관문의 유무를 이 호출로는 못 가른다.
        return NOT_APPLICABLE
    if 200 <= eff < 300 and body:
        return STILL_REACHED
    return REACHED_NO_DATA


def self_test() -> int:
    """출생 표본 (D-310) — 이 도구를 태어나게 한 문장이 그대로 fixture 다.

    태어난 사유: *"「덮는다」는 진술이다. 55자리를 전수 호출해 3갈래로 적어라"* (D-362).
    그러므로 첫 갈래는 **「본문 없는 200 을 데이터로 세는가」**이고,
    둘째는 **「404 를 막힌 것으로 세는가」**다. 404 를 막힌 것으로 읽으면
    관문 없는 자리가 통째로 초록이 된다 — 그것이 2026-09-07 사고 ①의 모양이었다.
    """
    cases = [
        ("★ 출생표본 401 — 관문이 걸렸다", 401, b"", "GET", BLOCKED),
        ("★ 출생표본 403 — 권한이 막았다. 이것도 막힌 것이다", 403, b"", "GET", BLOCKED),
        ("★ 출생표본 200+본문 — 익명에게 데이터가 나갔다", 200, b'{"data":[1]}', "GET",
         STILL_REACHED),
        ("★ 출생표본 404 — **관문을 지났다.** 막힌 것이 아니다", 404, b"", "GET",
         REACHED_NO_DATA),
        ("422 — 검증에서 떨어진 것도 관문을 지난 것이다", 422, b"{}", "POST",
         REACHED_NO_DATA),
        ("500 — 핸들러가 돌다 터진 것도 관문을 지난 것이다", 500, b"", "POST",
         REACHED_NO_DATA),
        ("405 — 그 메서드 자리가 아니다. 관문을 못 가른다", 405, b"", "PUT",
         NOT_APPLICABLE),
        ("★ 200 봉투 안의 403 은 **막힌 것**이다 (D-349)", 200,
         b'{"success": false, "status_code": 403}', "GET", BLOCKED),
        ("본문 없는 200 은 데이터가 아니다", 200, b"", "GET", REACHED_NO_DATA),
        ("204 는 본문이 없다 — 데이터가 나간 것이 아니다", 204, b"", "DELETE",
         REACHED_NO_DATA),
    ]
    bad = 0
    for label, status, body, method, expect in cases:
        got = settle(status, body, method=method)
        ok = got == expect
        bad += 0 if ok else 1
        print("  %s   %s  (실측 %s)" % ("OK  " if ok else "FAIL", label, got))

    for raw, want in (("/api/x/{id}", "/api/x/1"),
                      ("/api/f/flight-log/delete/{ids}", "/api/f/flight-log/delete/1")):
        got = concrete(raw)
        ok = got == want
        bad += 0 if ok else 1
        print("  %s   경로 파라미터를 채운다 %s → %s" % ("OK  " if ok else "FAIL", raw, got))

    print("[SETTLE] 자기시험 %d건 중 %d건 실패" % (len(cases) + 2, bad))
    return 1 if bad else 0


class _Rollback(Exception):
    """DB 를 되돌리기 위한 신호. 예외로 나가야 `atomic()` 이 되돌린다."""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("inventory", nargs="?",
                    default="/docs/agent/evidence/D-343/route_inventory.json")
    ap.add_argument("out", nargs="?",
                    default="/docs/agent/evidence/D-362/gap_route_settlement.json")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    sys.path.insert(0, "/app")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()

    from django.db import transaction
    from django.test import Client

    with open(args.inventory, encoding="utf-8") as f:
        inventory = json.load(f)

    targets = [
        r for r in inventory["routes"]
        if r["inbound_key"] == "open_anonymous" and _ours(r["view"])
    ]
    if not targets:
        print("[SETTLE] 대상 0건 — 인벤토리에 관문 없는 우리 층 자리가 없다")
        return 1

    client = Client(raise_request_exception=False, **NO_CACHE_HEADER)

    def _raw(method: str, path: str):
        target = concrete(path)
        # ★ 리다이렉트를 **따라간다** (D-350 — 측정기를 먼저 의심한다).
        #   첫 실행에서 GET 5자리가 301 로 나왔다. 301 은 관문의 답이 아니라
        #   `APPEND_SLASH` 의 답이다 — 따라가지 않으면 그 5자리를 **못 잰 채로**
        #   「관문을 지났다」칸에 넣게 된다. 잰 것과 못 잰 것을 가르는 자리다.
        if method == "GET":
            return client.get(target, follow=True)
        # 빈 본문으로 부른다. **스키마를 채워 주지 않는다** — 우리가 재는 것은 관문이지
        # 핸들러의 기능이 아니고, 채워 주면 부작용만 커진다.
        return client.generic(method, target, data=b"",
                              content_type="application/json", follow=True)

    def call(method: str, path: str) -> dict:
        """부른다. **쓰기는 언제나 되돌린다.**"""
        holder: dict = {}
        try:
            if method == "GET":
                resp = _raw(method, path)
            else:
                try:
                    with transaction.atomic():
                        holder["resp"] = _raw(method, path)
                        raise _Rollback
                except _Rollback:
                    pass
                resp = holder.get("resp")
                if resp is None:
                    raise RuntimeError("응답이 없다")
        except Exception as exc:                        # 터진 것도 **도달**이다
            return {"status": 500, "effective": 500, "bytes": 0,
                    "settlement": REACHED_NO_DATA, "note": type(exc).__name__}
        body = getattr(resp, "content", b"") or b""
        eff, split = effective_status(resp.status_code, body)
        return {"status": resp.status_code, "effective": eff, "envelope_split": split,
                "bytes": len(body), "settlement": settle(resp.status_code, body,
                                                         method=method),
                "note": ""}

    # ★ 음성 대조를 **먼저**. 여기가 깨지면 아래 숫자는 읽을 가치가 없다.
    control = [dict(path=p, **call("GET", p)) for p in CONTROL_CLOSED]
    control_ok = all(c["settlement"] == BLOCKED for c in control)

    rows = []
    for r in targets:
        rows.append(dict(method=r["method"], path=r["path"], view=r["view"],
                         authz=r["authz_path_permission"],
                         **call(r["method"], r["path"])))

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["settlement"]] = counts.get(row["settlement"], 0) + 1

    still = [r for r in rows if r["settlement"] == STILL_REACHED]

    payload = {
        "note": "D-362 — 남은 55자리를 익명·캐시우회로 **전수 호출**한 결과. "
                "쓰기는 transaction.atomic() 안에서 부르고 언제나 되돌렸다. "
                "3갈래는 D-362 가 정한 이름 그대로이고, reached_no_data 는 "
                "셋 중 어디에도 접지 않고 따로 낸 넷째 수다 (D-301).",
        "measured_at": os.environ.get("GX_MEASURED_AT", ""),
        "cache_handling": "우회 — X-No-Cache 헤더 (D-341)",
        "write_handling": "transaction.atomic() + 롤백. DB 밖 부작용은 되돌릴 수 없다 — "
                          "그래서 이 도구는 개발 컨테이너 전용이다",
        "control_closed": control,
        "control_ok": control_ok,
        "totals": {
            "gap_routes": len(targets),
            "by_method": {m: sum(1 for r in targets if r["method"] == m)
                          for m in sorted({r["method"] for r in targets})},
            "by_settlement": dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))),
            "still_reached": len(still),
            "envelope_split": sum(1 for r in rows if r.get("envelope_split")),
        },
        "still_reached_routes": [{"method": r["method"], "path": r["path"],
                                  "view": r["view"], "bytes": r["bytes"]} for r in still],
        "calls": rows,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("[SETTLE] [입력] 우리 층의 관문 없는 자리 %d건 전수 호출 "
          "(%s) — 쓰기는 롤백 안에서"
          % (len(targets), " · ".join("%s %d" % (m, n) for m, n
                                      in payload["totals"]["by_method"].items())))
    print("[SETTLE] 캐시 처리: 우회 (X-No-Cache)")
    print("[SETTLE] 음성 대조(닫힌 것으로 아는 자리 %d): %s" % (
        len(control), " · ".join("%s=%s" % (c["path"].rsplit("/", 1)[-1], c["status"])
                                 for c in control)))
    for name in (BLOCKED, STILL_REACHED, NOT_APPLICABLE):
        print("[SETTLE] %-22s %d건" % (name, counts.get(name, 0)))
    print("[SETTLE] %-22s %d건  ← 3갈래에 안 접은 넷째 수 (관문은 지났으나 본문 없음)"
          % (REACHED_NO_DATA, counts.get(REACHED_NO_DATA, 0)))
    if still:
        print("[SETTLE] ★ still_reached %d건 — **이것이 최우선이다** (D-362)" % len(still))
        for r in still:
            print("         %s %s  (%d B) %s" % (r["method"], r["path"], r["bytes"],
                                                 r["view"]))
    else:
        print("[SETTLE] ★ still_reached **0건** — 55자리를 래칫에 넣고 종결한다 (D-362)")
    print("[SETTLE] → %s" % args.out)

    if not control_ok:
        print("[SETTLE] ★ 음성 대조 실패 — 이 환경에서는 인증 자체가 안 걸린다. "
              "위 숫자를 인용하지 마라")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
