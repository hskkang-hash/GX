#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""authz 는 있는데 authn 이 없는 자리 — **호출로** 잰다 (D-342 · D-210 · D-343 ①).

왜 이 도구가 인벤토리와 따로인가
--------------------------------
`probe_route_inventory.py` 는 레지스트리를 읽는다. 거기서 나온 [실측] 하나가

    **`@path_permission` 은 활성인데 `auth=` 콜백이 없는 라우트 24자리**

인데, 이 상태의 뜻은 **읽어서는 정해지지 않는다.** D-342 가 정확히 그 경계다:

    A = 인가(authz) — 무엇을 할 수 있나 · B = 인증(authn) — 누구인가

`auth=` 가 없으면 익명이 **관문을 지난다.** 그러나 활성 `@path_permission` 이 그
익명을 역할 판정에서 떨어뜨릴 수도 있다. 즉 이 24자리는

    「열린 문」일 수도 있고,  「인증 없이도 권한이 막는 문」일 수도 있다.

**둘 중 무엇인지는 때려 봐야 안다.** 읽어서 답하면 D-210 위반이고, 양쪽으로 틀린다
(D-342: 「권한이 꺼졌을 뿐」으로 읽으면 열린 문을 놓치고, 반대로 읽으면 사고를 부풀린다).

이 도구가 하는 일
-----------------
    · **GET 만** 때린다. 쓰기 메서드는 부작용이 있어 부르지 않는다 —
      그 자리는 레지스트리 단언이 지킨다(`test_commented_guards.py` 와 같은 분담)
    · **익명으로** 때린다. 인증 헤더를 붙이지 않는다
    · **캐시를 우회한다** (D-341 착시 ⑦). `X-No-Cache` 를 붙인다 —
      우회하지 않으면 익명으로 채워진 캐시 항목이 관문 대신 대답한다
    · 상태 코드를 그대로 적는다. **200 은 200 이라고 적는다.** 해석은 사람이 한다

    docker exec gx-shell python /repo/scripts/probe_authn_gap_calls.py \
        /docs/agent/evidence/D-343/route_inventory.json \
        /docs/agent/evidence/D-343/authn_gap_calls.json

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

#: 캐시를 우회하는 헤더 (D-341). `UniversalCacheMiddleware` 가 보는 자리와 같아야 한다 —
#: 여기가 틀리면 이 도구는 관문이 아니라 **캐시를 잰다.**
NO_CACHE_HEADER = {"HTTP_X_NO_CACHE": "true"}

#: 경로 파라미터를 채우는 값. 존재하지 않아도 좋다 — 우리가 재는 것은 **관문**이지
#: 자원이 아니다. 401 이 나오면 관문이 있고, 404 가 나오면 **관문을 지났다는 뜻이다.**
_PARAM = re.compile(r"\{[^}]+\}")

#: ★ **음성 대조** (D-289 · D-300). 전부 200 이 나오면 그것은
#: 「열려 있다」일 수도 있고 **「이 환경에서 인증이 통째로 꺼져 있다」**일 수도 있다.
#: 둘을 가르는 유일한 것이 **닫혀 있다고 알려진 자리**다. D-334 가 막은 15자리 중 셋을 쓴다 —
#: 여기서 401 이 나오지 않으면 이 측정 전체가 무효다.
CONTROL_CLOSED = (
    "/api/terminals/days-of-week",
    "/api/terminals/terminal-types",
    "/api/dronehw/drone-communication-management/online-drones",
)


def concrete(path: str) -> str:
    return _PARAM.sub("1", path)


#: dj-core 는 금지구역이다 (§0.4 · D-207) — 세되 우리 분모에 넣지 않는다.
DJ_CORE_TOPS = ("core", "ninja", "ninja_extra", "ninja_jwt", "django")


def _ours(view: str) -> bool:
    return view.split(".")[0] not in DJ_CORE_TOPS


def effective_status(status: int, body: bytes) -> tuple[int, bool]:
    """★ **봉투가 아니라 내용을 읽는다** — 이 저장소의 200 은 200 이 아닐 수 있다.

    [실측 2026-09-08 · 이 도구가 처음 돌 때 잡힌 것]
        `GET /api/terminals/terminals` 를 익명으로 때리면 **HTTP 200** 이 오는데
        본문이 `{"success": false, "status_code": 403, "message": "Permission denied"}` 다.
        권한이 막았고 **막았다고 본문에 적혀 있는데 봉투에는 200 이 찍혀 있다.**

    처음 판정에서 이 자리 18건을 「익명이 데이터를 받았다」로 셌다. 틀렸다 —
    **판정기가 봉투를 읽고 내용을 안 읽었다.** D-284(거짓 성공)의 측정기 판이고,
    D-341 착시 ⑦의 사촌이다: 측정 대상과 측정 사이에 낀 것이 결과를 대신 답한다.

    돌려주는 것: (실효 상태 코드, 봉투와 내용이 갈렸는가)
    """
    if not (200 <= status < 300) or not body:
        return status, False
    try:
        data = json.loads(body.decode("utf-8", "replace"))
    except (ValueError, UnicodeDecodeError):
        return status, False
    if not isinstance(data, dict):
        return status, False
    inner = data.get("status_code")
    if isinstance(inner, int) and inner != status:
        return inner, True
    if data.get("success") is False:
        # 코드는 없고 success=false 만 있는 모양. **성공이 아니라고 적혀 있으면 성공이 아니다.**
        return 400, True
    return status, False


def verdict(status: int, body: bytes = b"") -> str:
    """관문이 **걸렸는가**. 「안전하다」를 말하지 않는다.

    403 은 인증 없이 **권한이** 막은 것이다 — 인증 관문이 있다는 뜻이 아니다(D-342).
    """
    status, _ = effective_status(status, body)
    if status == 401:
        return "authn_blocked"       # 인증이 막았다
    if status == 403:
        return "authz_blocked"       # 권한이 막았다 (인증은 없었다)
    if 200 <= status < 300:
        return "REACHED_WITH_DATA"   # ★ 익명이 데이터를 받았다
    return "reached_no_data"         # 핸들러에 닿았고 다른 이유로 실패했다


def self_test() -> int:
    """출생 표본 (D-310) — **2026-09-07 사고 ①의 상태 코드 그대로.**

    그때 익명 15자리의 응답은 200×3 · 422 · 400×2 · 404×2 · 500 이었다.
    401 은 **한 자리도 없었다.** 그래서 이 판정기의 첫 갈래는
    **200 을 「도달」로, 404 를 「도달」로 읽는가**다.
    404 를 「막혔다」로 읽으면 그날의 9자리를 안전하다고 셌을 것이다.
    """
    cases = [
        ("★ 출생표본 200 — 빈 봉투면 익명이 데이터를 받은 것이다", 200, b"", "REACHED_WITH_DATA"),
        ("★ 출생표본 404 — 자원이 없는 것이지 막힌 것이 아니다", 404, b"", "reached_no_data"),
        ("★ 출생표본 422 — 검증에서 떨어진 것도 도달이다", 422, b"", "reached_no_data"),
        ("★ 출생표본 500 — 핸들러가 돌다 터진 것도 도달이다", 500, b"", "reached_no_data"),
        ("401 만이 인증이 막은 것이다", 401, b"", "authn_blocked"),
        ("403 은 권한이 막은 것이다 — 인증이 아니다 (D-342)", 403, b"", "authz_blocked"),
        # ★ **이 도구가 자기 첫 실행에서 틀린 그 표본** (D-310)
        ("★ 출생표본 — 200 봉투 안의 403 을 읽는다 (D-284)", 200,
         b'{"success": false, "message": "Permission denied.", "status_code": 403}',
         "authz_blocked"),
        ("★ 200 봉투 안의 401 도 읽는다", 200,
         b'{"success": false, "status_code": 401}', "authn_blocked"),
        ("success=false 만 있고 코드가 없으면 성공으로 세지 않는다", 200,
         b'{"success": false}', "reached_no_data"),
        ("진짜 200 은 그대로 200 이다 — 내용을 읽는다고 다 막힌 것이 아니다", 200,
         b'{"success": true, "data": [{"id": 1}]}', "REACHED_WITH_DATA"),
        ("JSON 이 아니면 봉투를 믿는다 (억지로 해석하지 않는다)", 200,
         b"\x89PNG\r\n", "REACHED_WITH_DATA"),
    ]
    bad = 0
    for label, status, body, expect in cases:
        got = verdict(status, body)
        ok = got == expect
        bad += 0 if ok else 1
        print("  %s   %s  (실측 %s)" % ("OK  " if ok else "FAIL", label, got))

    for raw, want in (("/api/x/{id}", "/api/x/1"), ("/api/x/{int:event_id}/clip", "/api/x/1/clip")):
        got = concrete(raw)
        ok = got == want
        bad += 0 if ok else 1
        print("  %s   경로 파라미터를 채운다 %s → %s" % ("OK  " if ok else "FAIL", raw, got))

    print("[AUTHN-GAP] 자기시험 %d건 중 %d건 실패" % (len(cases) + 2, bad))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("inventory", nargs="?",
                    default="/docs/agent/evidence/D-343/route_inventory.json")
    ap.add_argument("out", nargs="?",
                    default="/docs/agent/evidence/D-343/authn_gap_calls.json")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    sys.path.insert(0, "/app")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()

    from django.test import Client

    with open(args.inventory, encoding="utf-8") as f:
        inventory = json.load(f)

    # ★ 대상은 **우리 층의 관문 없는 자리 전부**다. authz 가 붙은 24자리만 보면
    #   「권한이 막아 준다」는 자리만 세고, **아무것도 안 붙은 자리를 못 본다** — 그쪽이 더 나쁘다.
    #   dj-core 는 §0.4 라 고칠 수 없고, 고칠 수 없는 것을 세면 분모가 영원히 안 내려간다.
    targets = [
        r for r in inventory["routes"]
        if r["inbound_key"] == "open_anonymous" and _ours(r["view"])
    ]
    gets = [r for r in targets if r["method"] == "GET"]
    if not targets:
        print("[AUTHN-GAP] 대상 0건 — 인벤토리에 authz 있고 authn 없는 자리가 없다")
        return 1

    client = Client(raise_request_exception=False, **NO_CACHE_HEADER)

    def call(path: str) -> dict:
        try:
            resp = client.get(concrete(path))
        except Exception as exc:                       # 터진 것도 **도달**이다
            return {"status": 500, "effective": 500, "envelope_split": False,
                    "bytes": 0, "verdict": verdict(500), "note": type(exc).__name__}
        body = getattr(resp, "content", b"") or b""
        eff, split = effective_status(resp.status_code, body)
        return {"status": resp.status_code, "effective": eff, "envelope_split": split,
                "bytes": len(body), "verdict": verdict(resp.status_code, body), "note": ""}

    # ★ 음성 대조를 **먼저** 돈다. 여기가 깨지면 아래 숫자는 읽을 가치가 없다.
    control = []
    for path in CONTROL_CLOSED:
        control.append(dict(path=path, **call(path)))
    control_ok = all(c["verdict"] == "authn_blocked" for c in control)

    rows = []
    for r in gets:
        rows.append(dict(method=r["method"], path=r["path"], view=r["view"],
                         authz=r["authz_path_permission"], **call(r["path"])))

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1

    payload = {
        "note": "D-342 · D-343 ① — @path_permission 은 활성인데 auth= 가 없는 자리를 "
                "익명으로 때린 결과. 캐시 우회(X-No-Cache) 상태에서 쟀다(D-341).",
        "measured_at": os.environ.get("GX_MEASURED_AT", ""),
        "cache_handling": "우회 — X-No-Cache 헤더 (D-341)",
        "control_closed": control,
        "control_ok": control_ok,
        "totals": {
            "gap_routes": len(targets),
            "with_authz": sum(1 for r in targets if r["authz_path_permission"]),
            "without_any_gate": sum(1 for r in targets if not r["authz_path_permission"]),
            "called_get": len(gets),
            "not_called_write": len(targets) - len(gets),
            "by_verdict": dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))),
            "envelope_split": sum(1 for r in rows if r["envelope_split"]),
        },
        "calls": rows,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("[AUTHN-GAP] [입력] 우리 층의 인증 관문 없는 자리 %d건 "
          "(authz 활성 %d · 아무 관문도 없음 %d) · GET %d건을 호출 · 쓰기 %d건은 부르지 않음"
          % (len(targets), payload["totals"]["with_authz"],
             payload["totals"]["without_any_gate"], len(gets), len(targets) - len(gets)))
    print("[AUTHN-GAP] 캐시 처리: 우회 (X-No-Cache)")
    print("[AUTHN-GAP] 음성 대조(닫힌 것으로 아는 자리 %d): %s" % (
        len(control), " · ".join("%s=%s" % (c["path"].rsplit("/", 1)[-1], c["status"])
                                 for c in control)))
    split = payload["totals"]["envelope_split"]
    if split:
        print("[AUTHN-GAP] ★ 봉투와 내용이 갈린 응답 %d건 — HTTP 200 인데 본문이 실패다 (D-284)"
              % split)
    print("[AUTHN-GAP] 판정: " + " · ".join("%s %d" % (k, v) for k, v in
                                            payload["totals"]["by_verdict"].items()))
    print("[AUTHN-GAP] → %s" % args.out)
    if not control_ok:
        # 대조가 깨졌다 — 이 측정은 무효다. 초록으로 끝내면 그 숫자가 다음 판정의 근거가 된다.
        print("[AUTHN-GAP] ★ 음성 대조 실패 — 이 환경에서는 인증 자체가 안 걸린다. "
              "위 숫자를 인용하지 마라")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
