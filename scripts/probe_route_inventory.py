#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""라우트 인벤토리 **전수** — 무엇이 얼마나 열려 있는가 (D-343 ①②).

왜 인벤토리가 먼저인가
----------------------
D-343 은 inbound X-API-Key 의 기본값 거절을 **전역으로** 올리라고 판정하면서 순서를 못박았다:

    수백 개 라우트를 한 번에 뒤집으면 **무엇이 깨졌는지 모르는 채로 초록이 된다.**
    ① 라우트 인벤토리 전수 — 경로·메서드·현재 인증 수단·inbound `X-API-Key` 수용 여부·
       테넌트 범위 검사 유무. **건수를 출력하라**(D-301). 나는 그 수를 모른다

그리고 D-333 의 세 번째 얼굴(D-340)이 이 도구의 이유다:

    ① 밖에 사러 가기 전에 안을 뒤진다 · ② 만들기 전에 이미 있는지 뒤진다
    ③ **이미 있으면, 그것이 얼마나 열려 있는지부터 잰다**

무엇을 재나 — 라우트마다 여섯
------------------------------
    · 경로 · 메서드                     `_join(mount, prefix, op_path)`
    · 현재 인증 수단                    `Operation.auth_callbacks` 의 클래스
    · **들어오는 키 수용 여부**          아래 `inbound_key_state` 의 술어
    · 테넌트 범위 검사 유무             `@tenant_scoped` 표식(`SCOPE_ATTR`)
    · 권한 대장 유무                    `view._path_override` (**인증이 아니다** — D-342)
    · 3갈래 분류                        기본값 `session_only` (판단이 서지 않으면 좁은 쪽)

★ 「들어오는 키 수용」의 술어 — 왜 레지스트리로 재나 (D-210 과의 관계)
---------------------------------------------------------------------
D-210 은 **호출로 재라**고 한다. 그런데 쓰기 메서드를 포함한 수백 자리를 실제 키로
때리면 그 시험 자체가 사고다. 그래서 이 도구는 **호출로 이미 증명된 사실 하나**에
레지스트리 판정을 얹는다:

    [인용 · D-335 2026-09-07 호출 실측] dj-core 의 `CustomJWTAuth` 는 inbound X-API-Key 와
    `Authorization: apikey`(inbound) 를 **받는다.** 키 하나가 F-05 진입면 7자리에 전부 닿았다.

따라서 **인증 콜백이 `CustomJWTAuth` 이면 그 라우트는 들어오는 키를 받는다.**
우리 `JwtOrInboundKey` 만이 그 갈래를 선언으로 좁힌다. 이 술어가 인벤토리의 심장이다.

★ 「인증 없음」은 「키를 거절함」이 아니다 (D-342)
------------------------------------------------
콜백이 아예 없는 라우트는 키를 **검사하지 않는다** — 익명이 그대로 지나간다.
그것은 「좁다」가 아니라 **「관문이 없다」**이고, 이 인벤토리에서 가장 나쁜 칸이다.
`open_anonymous` 로 따로 센다.

    docker exec gx-shell python /repo/scripts/probe_route_inventory.py \
        /docs/agent/evidence/D-343/route_inventory.json

호스트에서는 `--self-test` 만 돈다 (Django 없이 술어만 시험한다).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

# ═══════════════════════════════════════════════════════════════════════════
# 술어 — Django 없이 시험할 수 있게 여기 둔다 (자기시험이 런타임을 요구하면 안 돈다)
# ═══════════════════════════════════════════════════════════════════════════

#: 3갈래 (D-343 ②). **기본값은 좁은 쪽이다.**
CLASS_INBOUND = "inbound_key_allowed"    # 외부 App 이 부를 면. 선언한 것만
CLASS_SESSION = "session_only"           # 사람 UI 전용. **분류의 기본값**
CLASS_INTERNAL = "internal_only"         # 내부 호출 전용

#: 들어오는 키 수용 상태.
KEY_ACCEPTS = "accepts"          # 지금 키가 닿는다 — 좁혀지지 않은 자리
KEY_DECLARED = "declared"        # 우리가 **선언해서** 연 자리 (사유 있음)
KEY_REFUSES = "refuses"          # 우리 문지기가 기본값 거절로 막는다
KEY_NO_GATE = "open_anonymous"   # 관문 자체가 없다 — 키를 검사하지도 않는다
KEY_UNKNOWN = "unknown"          # 우리가 모르는 인증 클래스. **모른다고 적는다**(D-301)


def inbound_key_state(auth_names: list[str], declared: bool | None) -> str:
    """이 라우트가 **들어오는 키**를 받는가.

    `auth_names` 는 인증 콜백의 클래스 이름들(상속 사슬 포함), `declared` 는
    `JwtOrInboundKey.inbound_key` 값(그 클래스가 아니면 None).

    ★ 순서가 중요하다. 우리 문지기의 판정이 dj-core 의 기본 수용보다 **앞선다** —
      `JwtOrInboundKey` 는 `CustomJWTAuth` 를 상속하므로 이름 사슬에 둘 다 있다.
    """
    if not auth_names:
        return KEY_NO_GATE
    if declared is True:
        return KEY_DECLARED
    if declared is False:
        return KEY_REFUSES
    if "CustomJWTAuth" in auth_names:
        return KEY_ACCEPTS
    return KEY_UNKNOWN


def classify(state: str) -> tuple[str, str]:
    """3갈래 분류와 그 근거. **판단이 서지 않으면 `session_only`** (D-343 ②).

    이 함수는 **넓히지 않는다.** 지금 키가 닿는다(`accepts`)는 사실은
    「그 자리가 외부 App 의 면이다」를 뜻하지 않는다 — 그것이 사고 ②의 내용이었다.
    선언한 자리만 `inbound_key_allowed` 다.
    """
    if state == KEY_DECLARED:
        return CLASS_INBOUND, "라우트가 inbound_key=True 로 선언했다 (사유 기재)"
    return CLASS_SESSION, "기본값 — 판단이 서지 않으면 좁은 쪽 (D-343 ②)"


# ═══════════════════════════════════════════════════════════════════════════
# 수집 — 런타임 레지스트리를 읽는다 (정적 grep 이 아니다)
# ═══════════════════════════════════════════════════════════════════════════

def collect() -> list[dict]:
    sys.path.insert(0, "/app")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()

    from common.tenant_scope import SCOPE_ATTR, _iter_ninja_apis, _join

    try:
        from common.inbound_api_key import JwtOrInboundKey
    except Exception:                                     # pragma: no cover
        JwtOrInboundKey = None                            # noqa: N806

    rows: list[dict] = []
    for mount, api in _iter_ninja_apis():
        for prefix, router in getattr(api, "_routers", []) or []:
            for op_path, path_view in (getattr(router, "path_operations", {}) or {}).items():
                for op in getattr(path_view, "operations", []) or []:
                    view = getattr(op, "view_func", None)
                    path = _join(mount, prefix, op_path)
                    callbacks = getattr(op, "auth_callbacks", None) or []

                    auth_names: list[str] = []
                    declared: bool | None = None
                    reason = ""
                    for cb in callbacks:
                        for klass in type(cb).__mro__:
                            if klass is object:
                                continue
                            if klass.__name__ not in auth_names:
                                auth_names.append(klass.__name__)
                        if JwtOrInboundKey is not None and isinstance(cb, JwtOrInboundKey):
                            declared = bool(getattr(cb, "inbound_key", False))
                            reason = getattr(cb, "reason", "") or ""

                    scope = getattr(view, SCOPE_ATTR, None)
                    state = inbound_key_state(auth_names, declared)
                    klass_name, why = classify(state)
                    parts = [p for p in path.split("/") if p]
                    for method in [str(m).upper() for m in (getattr(op, "methods", []) or [])]:
                        rows.append({
                            "method": method,
                            "path": path,
                            "app": parts[1] if len(parts) > 1 else (parts[0] if parts else "?"),
                            "view": "{}.{}".format(
                                getattr(view, "__module__", "?"),
                                getattr(view, "__qualname__", getattr(view, "__name__", "?")),
                            ),
                            "authn": auth_names[0] if auth_names else "",
                            "authn_chain": auth_names,
                            "inbound_key": state,
                            "inbound_key_reason": reason,
                            "tenant_scope": (
                                "required"
                                if scope is not None and getattr(scope, "required", False)
                                else "exempt" if scope is not None else "none"
                            ),
                            "authz_path_permission": bool(getattr(view, "_path_override", None)),
                            "classification": klass_name,
                            "classified_by": why,
                        })
    rows.sort(key=lambda r: (r["path"], r["method"]))
    return rows


def summarize(rows: list[dict]) -> dict:
    def count(key: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in rows:
            out[r[key]] = out.get(r[key], 0) + 1
        return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))

    return {
        "routes": len(rows),
        "by_inbound_key": count("inbound_key"),
        "by_classification": count("classification"),
        "by_tenant_scope": count("tenant_scope"),
        "by_authn": count("authn"),
        "authz_path_permission": sum(1 for r in rows if r["authz_path_permission"]),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-310) — **출생 표본은 사고 ②다**
# ═══════════════════════════════════════════════════════════════════════════

def self_test() -> int:
    """출생 표본 [실측 2026-09-07 · D-335]:

    발급된 키 하나가 F-05 진입면 7자리 전부에 닿았고 거기에 `/clip/stream` 이 있었다.
    그 7자리의 인증 콜백은 `CustomJWTAuth` 였다 — **인증은 성했고 범위가 성하지 않았다.**
    그래서 첫 갈래는 **`CustomJWTAuth` 만 붙은 자리를 `accepts` 로 잡는가**다.
    거기서 `refuses` 가 나오면 이 인벤토리는 사고를 못 본다.
    """
    cases: list[tuple[str, tuple[list[str], bool | None], str | None]] = [
        ("★ 출생표본 — CustomJWTAuth 뿐이면 키가 닿는다",
         (["CustomJWTAuth"], None), KEY_ACCEPTS),
        ("★ 출생표본 — 그런데 그 자리는 inbound_key_allowed 가 아니다",
         (["CustomJWTAuth"], None), None),
        ("선언한 자리는 declared",
         (["JwtOrInboundKey", "CustomJWTAuth"], True), KEY_DECLARED),
        ("선언 안 한 우리 문지기는 refuses",
         (["JwtOrInboundKey", "CustomJWTAuth"], False), KEY_REFUSES),
        ("콜백이 없으면 open_anonymous — 「거절」이 아니다 (D-342)",
         ([], None), KEY_NO_GATE),
        ("모르는 인증 클래스는 unknown 이라고 적는다 (D-301)",
         (["SomeOtherAuth"], None), KEY_UNKNOWN),
    ]
    bad = 0
    for label, (names, declared), expect in cases:
        got = inbound_key_state(list(names), declared)
        if expect is None:                       # 분류를 보는 갈래
            klass, _ = classify(got)
            ok = klass == CLASS_SESSION
            shown = klass
        else:
            ok = got == expect
            shown = got
        bad += 0 if ok else 1
        print("  %s   %s  (실측 %s)" % ("OK  " if ok else "FAIL", label, shown))

    # 음성 대조 — 분류가 넓어지지 않는가
    for state in (KEY_ACCEPTS, KEY_REFUSES, KEY_NO_GATE, KEY_UNKNOWN):
        klass, _ = classify(state)
        ok = klass == CLASS_SESSION
        bad += 0 if ok else 1
        print("  %s   %s 는 넓히지 않는다 → %s" % ("OK  " if ok else "FAIL", state, klass))

    print("[ROUTE-INVENTORY] 자기시험 %d건 중 %d건 실패" % (len(cases) + 4, bad))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default="/docs/agent/evidence/D-343/route_inventory.json")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    rows = collect()
    if not rows:
        # D-301 — 0건은 「볼 것이 없었다」일 수도 「보지 못했다」일 수도 있다.
        print("[ROUTE-INVENTORY] 라우트 0건 — 열거기 고장이다. 레지스트리를 못 읽었다")
        return 1

    totals = summarize(rows)
    payload = {
        "note": "D-343 ①② 라우트 인벤토리 전수. inbound_key=accepts 가 「지금 키가 닿는 자리」다. "
                "classification 의 기본값은 session_only — 판단이 서지 않으면 좁은 쪽(D-343 ②).",
        "measured_at": os.environ.get("GX_MEASURED_AT", ""),
        "totals": totals,
        "routes": rows,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("[ROUTE-INVENTORY] [입력] 라우트 %d건 (런타임 레지스트리 전수)" % totals["routes"])
    print("[ROUTE-INVENTORY] 들어오는 키: " + " · ".join(
        "%s %d" % (k, v) for k, v in totals["by_inbound_key"].items()))
    print("[ROUTE-INVENTORY] 3갈래: " + " · ".join(
        "%s %d" % (k, v) for k, v in totals["by_classification"].items()))
    print("[ROUTE-INVENTORY] 테넌트 범위: " + " · ".join(
        "%s %d" % (k, v) for k, v in totals["by_tenant_scope"].items()))
    print("[ROUTE-INVENTORY] → %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
