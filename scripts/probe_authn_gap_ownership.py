#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SEC-04 — 인증 관문 없는 라우트가 **누구 관할인가**를 가른다 (D-343 ① · D-279).

왜 이 측정기가 따로 필요한가
----------------------------
SEC-04 는 *"**우리 층**에 인증 관문 없는 라우트 0건"* 이다. 그런데 인벤토리
(`probe_route_inventory.py`)가 내는 수는 **전체**다 — 그 안에는 dj-core 소유도,
§0.4 금지구역(`delivery`·`orders`·`terminals`)도 섞여 있다. 섞인 수로는

    · 「0 으로 만들라」는 표적이 **몇 건인지 모르고**,
    · 못 고치는 것을 못 고쳤다는 이유로 판정이 영원히 빨강이 된다.

그래서 관할을 가른다. 가르는 술어는 **추측이 아니라 파일 경로**다 (D-279 —
"금지구역은 파일 경로로 확인한 뒤에만 붙인다"). 핸들러 모듈을 실제로 import 해
`__file__` 을 보고, 그 경로로만 판정한다.

★ 「모듈 해석 실패」를 **0 으로 세지 않는다** (D-301)
----------------------------------------------------
import 가 안 되는 라우트는 「우리 것 아님」이 아니라 **못 본 것**이다. 그것을 조용히
「저장소 밖」으로 떨어뜨리면 우리 층의 수가 그만큼 작아 보이고, 작아 보이는 모수 위의
「0건」은 초록이 아니다. 그래서 별도 갈래로 세고, 그 수를 결과에 그대로 적는다.

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
        python /repo/scripts/probe_authn_gap_ownership.py \
        /tmp/route_inventory.json /tmp/authn_gap_ownership.json

호스트에서는 `--self-test` 만 돈다 (Django·dj-core 가 없다).
"""
from __future__ import annotations

import argparse
import collections
import importlib
import json
import os
import sys
from datetime import date
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: ★ 마운트가 셋이다 — `/app`(=backend) · `/repo/{backend,scripts}` · `/docs`.
#:   컨테이너에서 `/repo/scripts/…` 로 부르면 `backend` 패키지가 경로에 없다.
#:   **같은 디렉터리인데 경로가 둘**이라 생기는 일이고, 도구 쪽에서 잇는다.
for _cand in ("/app", str(Path(__file__).resolve().parent.parent / "backend"),
              str(Path(__file__).resolve().parent)):
    if _cand not in sys.path and Path(_cand).is_dir():
        sys.path.insert(0, _cand)

#: ★ 관할 술어는 **여기 없다** — `scripts/route_ownership.py` 한 벌뿐이다 (D-369).
#:   이 계측기와 부작위 시험(`tests/test_authn_gap_closed.py`)이 같은 술어를 봐야 한다.
#:   두 벌이면 어긋나고, 어긋나면 **계측기는 0을 내고 시험은 통과하는데 실제로는 열려 있는**
#:   상태가 만들어진다.
from route_ownership import (                 # noqa: E402
    FORBIDDEN,
    FORBIDDEN_APPS,
    OURS,
    OUTSIDE,
    UNRESOLVED,
    classify_path,
)


def handler_file(view: str) -> str:
    """`a.b.Controller.handler` → 그 모듈의 `__file__`. 못 찾으면 빈 문자열."""
    parts = view.split(".")
    for cut in range(len(parts) - 1, 0, -1):
        try:
            mod = importlib.import_module(".".join(parts[:cut]))
        except Exception:                                      # noqa: BLE001
            continue
        return getattr(mod, "__file__", "") or ""
    return ""


def census(routes: list[dict]) -> dict:
    """인증 콜백 없는 라우트를 관할별로 센다."""
    gap = [r for r in routes if not (r.get("authn") or "").strip()]
    buckets: dict[str, list[dict]] = collections.defaultdict(list)
    for r in gap:
        where = classify_path(handler_file(r.get("view", "")))
        buckets[where].append({
            "method": r.get("method", ""), "path": r.get("path", ""),
            "view": r.get("view", ""), "app": r.get("app", ""),
            "authz_path_permission": bool(r.get("authz_path_permission")),
        })
    return {
        "measured_at": date.today().isoformat(),
        "note": ("SEC-04 모수 — **인증 콜백이 없는 라우트**를 관할별로 가른다. "
                 "「우리 층」이 SEC-04 가 0 으로 만들어야 하는 수이고, "
                 "「모듈 해석 실패」는 0 이 아니라 **못 본 것**이다 (D-301)."),
        "totals": {
            "routes": len(routes),
            "no_authn": len(gap),
            **{k: len(v) for k, v in sorted(buckets.items())},
            "ours_with_authz": sum(1 for x in buckets.get(OURS, [])
                                   if x["authz_path_permission"]),
            "ours_without_anything": sum(1 for x in buckets.get(OURS, [])
                                         if not x["authz_path_permission"]),
        },
        "by_owner": {k: sorted(v, key=lambda x: (x["path"], x["method"]))
                     for k, v in sorted(buckets.items())},
    }


def self_test() -> int:
    cases = (
        ("dj-core 는 저장소 밖이다",
         "/usr/local/lib/python3.11/site-packages/core/logger/views.py", OUTSIDE),
        ("§0.4 delivery 는 금지구역이다", "/app/delivery/views.py", FORBIDDEN),
        ("§0.4 orders 도 금지구역이다", "/app/orders/views/x.py", FORBIDDEN),
        ("§0.4 terminals 도 금지구역이다", "/app/terminals/views.py", FORBIDDEN),
        ("우리 앱은 우리 층이다", "/app/stream_monitors/views/stream_monitors.py", OURS),
        ("호스트 경로로도 우리 층을 안다",
         "C:/GuardianX/guardianx-source/backend/surveillance/views/x.py", OURS),
        ("★ 못 찾은 모듈은 **0 이 아니라 못 본 것**이다 (D-301)", "", UNRESOLVED),
        ("이름만 비슷한 남의 패키지는 금지구역이 아니다",
         "/usr/local/lib/python3.11/site-packages/orders_sdk/api.py", OUTSIDE),
    )
    bad = 0
    for label, path, want in cases:
        got = classify_path(path)
        ok = got == want
        print(f"  {'OK  ' if ok else 'FAIL'} {label}")
        if not ok:
            bad += 1
            print(f"       기대 {want} · 실제 {got}  ({path})")
    empty = census([])
    ok = empty["totals"]["no_authn"] == 0 and empty["totals"]["routes"] == 0
    print(f"  {'OK  ' if ok else 'FAIL'} 빈 입력에서 0 을 0 이라고 말한다")
    bad += 0 if ok else 1
    if bad:
        print(f"[SEC04-OWN] 자기시험 {bad}건 실패")
        return 1
    print(f"[SEC04-OWN] 자기시험 {len(cases) + 1}건 통과")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("inventory", nargs="?",
                    default="/docs/agent/evidence/D-343/route_inventory.json")
    ap.add_argument("out", nargs="?", default="")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    # ★ Django 를 먼저 세운다. 안 세우면 앱 모듈 import 가 전부 실패하고, 그러면
    #   **모든 라우트가 「모듈 해석 실패」로 떨어져 우리 층이 0 으로 보인다** —
    #   0 으로 보이는 표적은 "닫혔다" 와 모양이 같다. 여기서 죽는 편이 옳다.
    try:
        #: 컨테이너는 `backend/` 를 `/app` 로, 저장소 스크립트를 `/repo/scripts` 로
        #: 마운트한다. `/repo/scripts/…` 를 직접 부르면 sys.path[0] 이 스크립트 자리라
        #: `config` 를 못 찾는다 — `probe_route_inventory.py` 와 같은 부트스트랩이다.
        sys.path.insert(0, "/app")
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
        import django

        django.setup()
    except Exception as exc:                                   # noqa: BLE001
        print(f"[SEC04-OWN] Django 를 못 세웠다: {type(exc).__name__}: {exc}. "
              f"이 도구는 gx-shell 안에서 DJANGO_SETTINGS_MODULE 과 함께 돈다 — "
              f"세우지 못한 채 세면 표적이 0 으로 보인다")
        return 2

    src = Path(args.inventory)
    if not src.is_file():
        print(f"[SEC04-OWN] 인벤토리를 못 찾았다: {src} — "
              f"probe_route_inventory.py 를 먼저 돌려라. 없는 모수 위에서 세지 않는다")
        return 2
    data = json.loads(src.read_text(encoding="utf-8"))
    result = census(data.get("routes", []))

    t = result["totals"]
    print(f"[SEC04-OWN] [입력] 라우트 {t['routes']}건 — 인증 콜백 없음 {t['no_authn']}건")
    for key in (OURS, OUTSIDE, FORBIDDEN, UNRESOLVED):
        print(f"    {key:14s} {t.get(key, 0)}")
    print(f"[SEC04-OWN] SEC-04 표적(우리 층) {t.get(OURS, 0)}건 "
          f"— 그중 authz 있음 {t['ours_with_authz']} · 아무것도 없음 "
          f"{t['ours_without_anything']}")
    if t.get(UNRESOLVED, 0):
        print(f"[SEC04-OWN] ⚠ 모듈 해석 실패 {t[UNRESOLVED]}건 — **0 이 아니라 못 본 것**이다. "
              f"이 수가 남아 있는 동안 「우리 층 {t.get(OURS, 0)}건」은 하한이다 (D-301)")
    if args.out:
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        print(f"[SEC04-OWN] 기록 → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
