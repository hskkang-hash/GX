#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""D-368 ① / P-83 — 관문 없는 **쓰기** 면을 호출로 분류한다. 읽어서 답하지 않는다 (D-210).

왜 읽기와 따로 세나 (D-368)
---------------------------
    읽기 유출 — 나간 것은 되돌릴 수 없다. 그러나 **무엇이 나갔는지는 안다**
    쓰기 오염 — 들어온 것도 되돌릴 수 없고, **게다가 조용하다.**
                익명이 이벤트를 심으면 가짜 재난 알림이 나가고 보고서가 오염된다.
                그 데이터는 진짜와 섞여서 **나중에 골라낼 수 없다**

★★ P-83 [세종 판정 2026-09-06 · 턴 I] — **401·403 과 422 는 다른 칸이다**
--------------------------------------------------------------------------
턴 H 까지 이 탐침은 빈 본문 ``{}`` 하나만 던지고, **도달하지 못하면 전부**
``rejected_elsewhere``(= 관문이 섰다) 로 셌다. 재보니 그 17자리 중 **13자리가 422**,
곧 **스키마 검증 실패**였다. 422 는 이런 뜻이다:

    「인증 없이도 **여기까지 왔다.** 다만 본문이 형식에 안 맞아 떨어졌다」

그것은 관문이 **아니다.** 본문만 맞추면 그대로 들어간다. 그런데 게이트는 그것을
관문으로 세고 **초록**을 냈다 — 읽기 탐침이 이미 배운 ⑪ 문지기형 교훈
(「막은 것이 무엇인지 이름을 대지 못하면 막은 것이 아니다」)이 쓰기 탐침에는
안 들어가 있었다. 그래서 이 탐침은 이제 이렇게 잰다:

    **스키마를 통과하는 최소 본문**을 만들어서 **인증 없이** 보낸다.
    본문은 서버가 스스로 불러 준다 — 422 의 ``detail[].loc`` / ``type`` 을 읽어
    빠진 칸을 채우고 다시 던지기를 되풀이한다(최대 ``MAX_ROUNDS`` 바퀴).
    추정하지 않는다(D-280): 채운 근거는 매 바퀴 ``rounds_log`` 에 남는다.

여섯 갈래 (P-83 이 넷을 여섯으로 쪼갰다)
----------------------------------------
    writes                 익명이 핸들러 자리에 **도달**하고, 그 핸들러가 **쓴다**
                           ★ P0 보안 구멍. 래칫 없음 — 0건이 절대선이다
    read_only_in_practice  도달은 하지만 핸들러가 쓰지 않는다 (조회를 POST 로 받는 자리)
    gated                  ★ **관문** — 401/403. 이것만 관문이다
    schema_rejected        **도달·검증 실패** — 422/400. 관문이 아니다.
                           스키마를 맞춰 주고도 422 면 「본문을 못 맞춘 것」이고,
                           그 자리는 **관문이 있는지 못 쟀다**로 센다
    unreachable            **도달 실패** — 404/405. 그 메서드가 그 주소에 없다
    blocked_other          그 밖의 상태(예: 500 이 핸들러 앞에서 났다) — 따로 센다

    public_by_design       **선언**이다. 로그인·토큰처럼 익명이어야만 성립하는 면.
                           면제가 아니라 이름을 적어 두는 것이다 (D-264 계열)

어떻게 재나 — 부작용 없이
-------------------------
쓰기 메서드를 그냥 때리면 부작용이 남는다. 그렇다고 안 때리면 「auth 콜백이 비었으니
열려 있을 것」이라는 **추정**이 된다(D-280 금지). 그래서 D-334 가 쓴 방법을 그대로
쓴다 — 등록된 ``view_func`` 를 **도달 표시만 남기는 대체물**로 잠시 바꾸고 때린다.
**본체는 한 줄도 돌지 않는다.** 스키마를 통과하는 본문을 보내도 마찬가지다 —
그것이 이 방법을 P-83 에서 그대로 쓸 수 있는 이유다.

「쓰는가」는 **정적으로** 읽는다 — 대체물을 끼운 채로는 본체가 안 돌기 때문이다.
그 사실을 숨기지 않는다: ``writes_by`` 칸에 **무엇을 보고 그렇게 판정했는지** 적는다.

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
        python /repo/scripts/probe_write_surface.py /docs/agent/evidence/D-368/write_surface.json

호스트에서는 ``--self-test`` 만 돈다.
"""
from __future__ import annotations

import argparse
import ast
import copy
import inspect
import json
import os
import re
import sys
import textwrap
from datetime import datetime, timezone
from urllib.parse import urlencode

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")

#: 본문을 몇 바퀴까지 맞춰 보는가. 한 바퀴에 한 겹씩 깊어지므로 넉넉히 준다.
#: 다 쓰고도 422 면 **못 맞춘 것**이고, 그 자리는 `schema_rejected` 로 남는다 —
#: 「관문이 있다」로 승격시키지 않는다. 그것이 P-83 의 요점이다.
MAX_ROUNDS = 16

#: ★ P-83 판정표 — **이 세 줄이 관문/도달·검증/도달 실패를 가른다.**
GATE_STATUSES = (401, 403)            # 관문 — 이것만 관문이다
VALIDATION_STATUSES = (400, 422)      # 도달·검증 실패 — 관문이 아니다
UNREACHABLE_STATUSES = (404, 405)     # 도달 실패 — 그 자리에 그 메서드가 없다

#: 익명이어야만 성립하는 면. **선언이지 면제가 아니다** — 사유를 적고, 늘 때마다
#: 사람이 이 목록을 고쳐야 한다. 목록에 없으면 자동으로 표적이 된다.
#:
#: ★ 판단 기준 하나: **아직 로그인하지 못한 사람이 부르는 자리인가.**
#:   그 답이 「아니오」이면 여기 있으면 안 된다.
PUBLIC_BY_DESIGN: dict[str, str] = {
    "/api/token/pair": "로그인 — 토큰을 받으러 오는 자리다. 토큰이 있어야 부를 수 있으면 로그인이 아니다",
    "/api/token/refresh": "만료된 토큰을 갱신한다 — 유효한 접근 토큰이 없는 상태가 정상이다",
    "/api/token/verify": "토큰 검사 — 검사받을 토큰을 본문으로 낸다",
    "/api/v1/auth/login": "로그인",
    "/api/v1/auth/logout": "로그아웃 — 이미 만료된 토큰으로도 불려야 한다",
    "/api/v1/auth/refresh-token": "토큰 갱신",
    "/api/v1/auth/forgot-password": "비밀번호 분실 — 로그인할 수 없는 사람이 부른다",
    "/api/v1/auth/reset-password": "재설정 — 메일로 받은 토큰으로 부른다",
    "/api/v1/auth/otp/verify": "OTP 확인 — 로그인 절차의 두 번째 단계",
    "/api/v1/auth/otp/reset": "OTP 재설정 — 로그인 절차 안에 있다",
    "/api/v1/auth/delete-session": "세션 정리 — 로그인 실패 경로에서 불린다",
}

#: 핸들러가 **쓰는가**를 정적으로 볼 때 찾는 이름. 행위로 긋는다 (D-324).
WRITE_CALLS = ("save", "create", "delete", "update", "bulk_create", "bulk_update",
               "get_or_create", "update_or_create", "add", "remove", "set")

#: ★ [2026-09-06 턴 I · P-83] **이름을 정확히 맞추는 목록만으로는 못 본다.**
#: [실측] `/api/apikey/keys` 의 핸들러는 `APIKey.create_key(user=…)` 를 부른다.
#: `create_key` 는 위 목록에 없어서 이 탐침이 그 자리를 **「안 쓴다」**로 셌고,
#: 그래서 익명이 API 키를 만들 수 있는 자리가 `read_only_in_practice` 칸에 앉아 있었다.
#: 목록을 늘리는 대신 **접두**로 본다 — 모르는 쪽은 쓰는 쪽으로 기운다(D-284).
#: 헛짚음(예: `set_cookie`)은 `writes_by` 에 이름이 남으므로 사람이 가려낼 수 있다.
WRITE_CALL_PREFIXES = ("create", "delete", "update", "save", "insert", "bulk_",
                       "set_", "add_", "remove_", "destroy", "revoke",
                       "regenerate", "deactivate", "activate", "reset_")

VERDICTS = ("writes", "read_only_in_practice", "gated", "schema_rejected",
            "unreachable", "blocked_other", "public_by_design")


class _Reached(Exception):
    """대체물이 도달을 알리는 신호. 본체 대신 이것이 던져진다 — 부작용이 없다."""


# ─────────────────────────────────────────────────────────────────────────────
# 스키마를 통과하는 최소 본문 — **서버가 불러 주는 대로 받아쓴다**
#
# 사람이 serializer 를 읽어서 손으로 본문을 적으면 그 순간 **추정**이 되고(D-280),
# 스키마가 바뀌면 조용히 낡는다. 그래서 값의 출처는 언제나 **그 요청의 422 응답**이다:
#   detail[].loc  → 어느 칸이 빈지          detail[].type → 어떤 형이어야 하는지
# 못 채운 칸은 `unresolved` 에 이름을 남긴다 — 「몰랐다」를 「없었다」로 두지 않는다.
# ─────────────────────────────────────────────────────────────────────────────
_EMAILISH = ("email", "mail")
_URLISH = ("url", "uri", "endpoint", "callback", "link")


def guess_value(err: dict, key: str):
    """pydantic 오류 하나를 **그 칸에 넣을 값**으로 옮긴다. 형(type)이 먼저, 이름이 나중."""
    t = str(err.get("type") or "")
    ctx = err.get("ctx") or {}
    k = str(key).lower()

    if t in ("list_type", "tuple_type", "set_type", "iterable_type"):
        return []
    if t in ("dict_type", "model_type", "model_attributes_type", "dataclass_type"):
        return {}
    if t in ("int_type", "int_parsing", "int_from_float"):
        return 1
    if t in ("float_type", "float_parsing", "decimal_type", "decimal_parsing"):
        return 1.0
    if t in ("bool_type", "bool_parsing"):
        return True
    if t.startswith("datetime"):
        return "2026-01-01T00:00:00+00:00"
    if t.startswith("date"):
        return "2026-01-01"
    if t.startswith("time"):
        return "00:00:00"
    if t.startswith("uuid"):
        return "00000000-0000-4000-8000-000000000000"
    if t == "enum":
        expected = str(ctx.get("expected") or "")
        quoted = re.findall(r"'([^']*)'", expected)
        if quoted:
            return quoted[0]
        nums = re.findall(r"-?\d+", expected)
        if nums:
            return int(nums[0])
        return "1"
    if t in ("greater_than", "greater_than_equal"):
        base = ctx.get("gt", ctx.get("ge", 0))
        try:
            return int(base) + 1
        except (TypeError, ValueError):
            return 1
    if t in ("less_than", "less_than_equal"):
        base = ctx.get("lt", ctx.get("le", 2))
        try:
            return int(base) - 1
        except (TypeError, ValueError):
            return 0
    if t in ("too_short", "string_too_short"):
        n = int(ctx.get("min_length") or ctx.get("actual_length") or 1)
        return "x" * max(n, 1)
    if t in ("too_long", "string_too_long"):
        return "x"
    if t in ("string_type", "string_pattern_mismatch", "json_invalid"):
        return by_name(k)
    # missing · value_error · 그 밖 — 이름으로 짐작하고, 틀리면 다음 바퀴가 고친다
    return by_name(k)


def by_name(k: str):
    """형을 모를 때 **이름**으로 짐작한다. 틀려도 좋다 — 다음 바퀴의 오류가 고쳐 준다."""
    k = k.lower()
    if any(w in k for w in _EMAILISH):
        return "gxprobe@example.invalid"
    if any(w in k for w in _URLISH):
        return "https://example.invalid/probe"
    if "password" in k:
        return "GxProbe!2026"
    if "phone" in k:
        return "010-0000-0000"
    if k.endswith("_ids") or k == "ids":
        return [1]
    return "1"


def set_path(tree, keys, value) -> bool:
    """`tree` 안 `keys` 자리에 값을 넣는다. 이미 같은 값이면 False(진전 없음)."""
    cur = tree
    for i, k in enumerate(keys[:-1]):
        nxt = keys[i + 1]
        want_list = isinstance(nxt, int)
        if isinstance(cur, dict):
            if k not in cur or not isinstance(cur[k], (dict, list)):
                cur[k] = [] if want_list else {}
            cur = cur[k]
        elif isinstance(cur, list):
            if not isinstance(k, int):
                return False
            while len(cur) <= k:
                cur.append([] if want_list else {})
            # ★ 앞 바퀴가 그 칸에 홑값(`[1]`)을 넣어 뒀을 수 있다. 더 파고들어야
            #   하는데 홑값이면 **그릇으로 바꾼다** — 안 바꾸면 「진전 없음」이 되고,
            #   그 자리는 관문이 있는지 못 잰 채로 남는다 (실측: drone_ids 가 그랬다).
            if not isinstance(cur[k], (dict, list)):
                cur[k] = [] if want_list else {}
            cur = cur[k]
        else:
            return False
    last = keys[-1]
    if isinstance(cur, list):
        if not isinstance(last, int):
            return False
        while len(cur) <= last:
            cur.append(None)
        if cur[last] == value:
            return False
        cur[last] = value
        return True
    if not isinstance(cur, dict):
        return False
    if last in cur and cur[last] == value:
        return False
    cur[last] = value
    return True


def _body_single_attr(op):
    """단일 body 파라미터면 그 이름 — 이때 요청 본문은 **그 값 자체**다 (ninja)."""
    for m in getattr(op.signature, "models", []) or []:
        if getattr(m, "__ninja_param_source__", None) == "body":
            return getattr(m, "__read_from_single_attr__", None)
    return None


def _sources(op) -> set:
    return {getattr(m, "__ninja_param_source__", None)
            for m in (getattr(op.signature, "models", []) or [])}


def _render_body(tree, single):
    """탐침이 들고 있는 나무를 **ninja 가 읽는 모양**의 본문으로 편다."""
    if single:
        return tree.get(single, {})
    return tree


def schema_probe(op, path: str, method: str, max_rounds: int = MAX_ROUNDS) -> dict:
    """**스키마를 통과하는 최소 본문**을 만들어 익명으로 때린다.

    본체는 한 줄도 돌지 않는다 (D-334 의 대체물). 돌려주는 것:
      reached  도달했는가(대체물이 불렸는가)   status  마지막 상태 코드
      rounds   몇 바퀴 만에 멈췄는가            unresolved  끝내 못 채운 칸
      sent     마지막에 보낸 본문/질의/양식     rounds_log  바퀴마다의 상태
    """
    from django.test import Client
    from django.test.client import MULTIPART_CONTENT, encode_multipart

    marker = {"hit": False}

    def _stub(request, *a, **kw):
        marker["hit"] = True
        raise _Reached()

    saved = op.view_func
    single = _body_single_attr(op)
    sources = _sources(op)
    multipart = bool(sources & {"form", "file"})

    body_tree = {}
    query = {}
    form = {}
    headers = {}
    path_values = {}
    unresolved = []
    log = []
    status, note, rounds = None, "", 0

    try:
        op.view_func = _stub
        client = Client(raise_request_exception=False)

        def _url():
            p = path
            for name in re.findall(r"\{([^}]+)\}", path):
                p = p.replace("{%s}" % name, str(path_values.get(name, "1")))
            return p + ("?" + urlencode(query, doseq=True) if query else "")

        while True:
            rounds += 1
            marker["hit"] = False
            if multipart:
                payload = {k: ("" if v is None else v) for k, v in form.items()}
                data = encode_multipart("BoUnDaRyPrObE", payload) if payload else b""
                ctype = MULTIPART_CONTENT
            else:
                data = json.dumps(_render_body(body_tree, single)).encode()
                ctype = "application/json"
            extra = {("HTTP_" + str(k).upper().replace("-", "_")): str(v)
                     for k, v in headers.items()}
            try:
                resp = client.generic(method, _url(), data=data,
                                      content_type=ctype, **extra)
                status = resp.status_code
                raw = resp.content[:4000].decode("utf-8", "replace")
            except _Reached:
                status, raw = None, ""
            except Exception as exc:                       # noqa: BLE001
                note = ("raised: %s: %s" % (type(exc).__name__, exc))[:200]
                log.append({"round": rounds, "status": None, "note": note})
                break

            log.append({"round": rounds, "status": status,
                        "sent": (dict(form) if multipart
                                 else copy.deepcopy(_render_body(body_tree, single)))})

            if marker["hit"] or rounds >= max_rounds:
                break
            if status not in VALIDATION_STATUSES:
                break

            try:
                errs = json.loads(raw).get("detail")
            except (ValueError, AttributeError):
                errs = None
            if not isinstance(errs, list) or not errs:
                note = note or ("검증 실패인데 오류 목록을 못 읽었다: %r" % raw[:120])
                break

            progressed = False
            for err in errs:
                loc = list(err.get("loc") or [])
                if not loc:
                    continue
                src, rest = loc[0], loc[1:]
                if not rest:
                    # 본문 통째로가 틀렸다 (예: 최상위가 리스트여야 한다)
                    val = guess_value(err, str(src))
                    if single and src == "body" and body_tree.get(single) != val:
                        body_tree[single] = val
                        progressed = True
                    continue
                key = str(rest[-1])
                val = guess_value(err, key)
                flat = val if not isinstance(val, (dict, list)) else "1"
                if src == "query":
                    if query.get(key) != flat:
                        query[key] = flat
                        progressed = True
                elif src == "form":
                    if form.get(key) != flat:
                        form[key] = flat
                        progressed = True
                elif src == "header":
                    if headers.get(key) != flat:
                        headers[key] = flat
                        progressed = True
                elif src == "path":
                    if path_values.get(key) != flat:
                        path_values[key] = flat
                        progressed = True
                elif src == "body":
                    if set_path(body_tree, rest, val):
                        progressed = True
                else:
                    tag = "%s:%s" % (src, key)
                    if tag not in unresolved:
                        unresolved.append(tag)

            if not progressed:
                for err in errs:
                    tag = ".".join(str(x) for x in (err.get("loc") or [])) \
                        + "(" + str(err.get("type")) + ")"
                    if tag not in unresolved:
                        unresolved.append(tag)
                break
    finally:
        op.view_func = saved

    return {
        "reached": marker["hit"],
        "status": status,
        "note": note,
        "rounds": rounds,
        "unresolved": unresolved,
        "sent": {"body": _render_body(body_tree, single), "query": query,
                 "form": form, "path": path_values},
        "rounds_log": log,
    }


def handler_writes(view_func):
    """이 핸들러가 **쓰는가.** (판정, 근거) 를 돌려준다.

    ★ 정적 판정임을 숨기지 않는다. 대체물을 끼운 채로는 본체가 안 돌기 때문에
      「도달했다」와 「썼다」를 같은 방법으로 잴 수 없다 — 그 사실을 근거란에 적는다.
      못 읽으면 **모른다고 적는다**: 모르는 것을 「안 쓴다」로 두면 표적이 조용히 준다.
    """
    fn = inspect.unwrap(view_func)
    try:
        src = inspect.getsource(fn)
    except (OSError, TypeError):
        return True, "원본을 읽지 못했다 — **모르는 것은 쓰는 쪽으로 센다** (D-284)"
    try:
        # ★ 데코레이터가 붙은 함수의 원본은 **들여쓰기가 남는다.**
        #   `lstrip()` 은 첫 줄만 펴고 나머지를 그대로 둬서 IndentationError 가
        #   나고, 그러면 전수가 통째로 「모른다」로 떨어진다 —
        #   첫 실행에서 실제로 8자리가 그렇게 떨어졌다 (D-350 측정기를 먼저 의심한다).
        tree = ast.parse(textwrap.dedent(src))
    except SyntaxError:
        return True, "원본을 파싱하지 못했다 — 모르는 것은 쓰는 쪽으로 센다"
    found = sorted({
        n.func.attr for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and (n.func.attr in WRITE_CALLS
             or n.func.attr.startswith(WRITE_CALL_PREFIXES))
    })
    if found:
        return True, "[정적] 핸들러 본문에 %s() 호출" % ", ".join(found)
    return False, "[정적] 핸들러 본문에 쓰기 호출 없음"


def classify(reached: bool, writes: bool, path: str, status) -> str:
    """여섯 갈래. **판정식을 한 곳에만 둔다** (D-212).

    ★ P-83: 관문은 **401/403 뿐**이다. 422 는 「도달했으나 검증에 떨어짐」이고
      404/405 는 「도달 실패」다 — 셋을 한 칸에 넣으면 게이트가 거짓 초록을 낸다.
    """
    if path in PUBLIC_BY_DESIGN:
        return "public_by_design"
    if reached:
        return "writes" if writes else "read_only_in_practice"
    if status in GATE_STATUSES:
        return "gated"
    if status in VALIDATION_STATUSES:
        return "schema_rejected"
    if status in UNREACHABLE_STATUSES:
        return "unreachable"
    return "blocked_other"


def collect():
    from common.tenant_scope import _iter_ninja_apis, _join

    rows = []
    for mount, api in _iter_ninja_apis():
        for prefix, router in getattr(api, "_routers", []) or []:
            for op_path, path_view in (getattr(router, "path_operations", {}) or {}).items():
                for op in getattr(path_view, "operations", []) or []:
                    methods = [str(m).upper() for m in (getattr(op, "methods", []) or [])]
                    writes_methods = [m for m in methods if m in WRITE_METHODS]
                    if not writes_methods:
                        continue
                    if getattr(op, "auth_callbacks", None):
                        continue                        # 인증 관문이 있다
                    path = _join(mount, prefix, op_path)
                    view = getattr(op, "view_func", None)
                    does_write, why = handler_writes(view) if view else (True, "핸들러 없음")
                    probe = schema_probe(op, path, writes_methods[0])
                    rows.append({
                        "method": writes_methods[0],
                        "methods": ",".join(sorted(set(methods))),
                        "path": path,
                        "app": path.strip("/").split("/")[1] if path.count("/") > 1 else "",
                        "view": "%s.%s" % (getattr(view, "__module__", "?"),
                                           getattr(view, "__name__", "?")),
                        "reached": probe["reached"],
                        "status": probe["status"],
                        "note": probe["note"],
                        "rounds": probe["rounds"],
                        "unresolved": probe["unresolved"],
                        "sent": probe["sent"],
                        "rounds_log": probe["rounds_log"],
                        "writes": does_write,
                        "writes_by": why,
                        "verdict": classify(probe["reached"], does_write, path,
                                            probe["status"]),
                    })
    rows.sort(key=lambda r: (r["verdict"], r["path"]))
    return rows


# ─────────────────────────────────────────────────────────────────────────────
def self_test() -> int:
    checks = [
        ("★ 도달 + 쓴다 → writes", classify(True, True, "/x", None) == "writes"),
        ("도달 + 안 쓴다 → read_only_in_practice",
         classify(True, False, "/x", None) == "read_only_in_practice"),
        # ★★ P-83 의 심장 — 이 셋이 한 칸에 있었기 때문에 게이트가 거짓 초록이었다
        ("★ 401 은 관문이다", classify(False, True, "/x", 401) == "gated"),
        ("★ 403 은 관문이다", classify(False, True, "/x", 403) == "gated"),
        ("★★ 422 는 관문이 **아니다** — 도달·검증 실패다 (턴 H 거짓 초록 13자리)",
         classify(False, True, "/x", 422) == "schema_rejected"),
        ("★★ 405 는 관문이 **아니다** — 도달 실패다",
         classify(False, True, "/x", 405) == "unreachable"),
        ("★ 404 도 도달 실패다", classify(False, True, "/x", 404) == "unreachable"),
        ("★ 그 밖의 상태는 따로 센다(500 을 관문으로 세지 않는다)",
         classify(False, True, "/x", 500) == "blocked_other"),
        ("★ 선언된 면은 도달하고 써도 표적이 아니다",
         classify(True, True, "/api/v1/auth/login", None) == "public_by_design"),

        # 본문 만들기 — 서버가 불러 주는 대로 받아쓴다
        ("★ missing 을 이름으로 채운다",
         guess_value({"type": "missing"}, "email") == "gxprobe@example.invalid"),
        ("★ list_type 은 빈 리스트로 채운다",
         guess_value({"type": "list_type"}, "items") == []),
        ("int_parsing 은 정수로 채운다",
         guess_value({"type": "int_parsing"}, "n") == 1),
        ("bool_parsing 은 참으로 채운다",
         guess_value({"type": "bool_parsing"}, "f") is True),
        ("enum 은 기대 목록의 첫 값으로 채운다",
         guess_value({"type": "enum", "ctx": {"expected": "'a' or 'b'"}}, "k") == "a"),
        ("★ 깊은 자리에 값을 넣는다 (loc 이 세 겹일 때)",
         (lambda t: (set_path(t, ["a", "b"], 1), t == {"a": {"b": 1}})[1])({})),
        ("★ 리스트 자리도 만든다 (loc 에 정수가 있을 때)",
         (lambda t: (set_path(t, ["a", 0, "b"], 1), t == {"a": [{"b": 1}]})[1])({})),
        ("★ 앞 바퀴가 넣은 홑값을 그릇으로 바꾼다 (drone_ids=[1] → [{...}])",
         (lambda t: (set_path(t, ["a", 0, "b"], 1), t == {"a": [{"b": 1}]})[1])(
             {"a": [1]})),
        ("같은 값을 또 넣으면 **진전 없음**이다 (무한 바퀴를 막는다)",
         (lambda t: (set_path(t, ["a"], 1), not set_path(t, ["a"], 1))[1])({})),
        ("★ 단일 body 파라미터면 본문은 그 값 **자체**다 (ninja)",
         _render_body({"data": {"name": "x"}}, "data") == {"name": "x"}),
        ("단일이 아니면 이름이 붙은 채로 낸다",
         _render_body({"a": 1}, None) == {"a": 1}),

        ("★ 데코레이터 붙은 함수도 읽는다 (첫 실행이 여기서 멀었다)",
         handler_writes(_decorated_writer)[0]),
        ("쓰기 호출을 읽는다", handler_writes(_sample_writer)[0]),
        ("쓰기 호출이 없으면 안 읽는다", not handler_writes(_sample_reader)[0]),
        # ★ 출생 표본 — 이 한 줄을 못 읽어서 익명이 API 키를 만드는 자리가
        #   「안 쓴다」 칸에 앉아 있었다 (2026-09-06 실측)
        ("★ `Model.create_key(...)` 처럼 **목록에 없는 이름**도 쓰기로 읽는다",
         handler_writes(_sample_prefix_writer)[0]),
        ("접두가 안 맞으면 안 읽는다 (전부를 쓰기로 세면 판정이 아니다)",
         not handler_writes(_sample_reader)[0]),
    ]
    for name, ok in checks:
        print("  %s  %s" % ("OK  " if ok else "FAIL", name))
    bad = [n for n, ok in checks if not ok]
    print("[WRITESURFACE] 자기시험 %d건 %s" % (len(checks), "통과" if not bad else "실패"))
    return 0 if not bad else 1


def _fake_decorator(fn):
    return fn


# ★ 아래 표본들은 **부르지 않는다** — `handler_writes` 에게 소스를 읽히려고 있다.
#   그래서 `store` 는 None 이고, 실행하면 죽는다. 그것이 요점이다.
#
#   ⚠ `store.objects.create(...)` 로 쓰지 않는 이유: `scripts/verify_classification.py`
#     가 `objects`/`_base_manager` 사슬을 **진짜 DB 쓰기**로 세고, 그러면 이 측정기가
#     「데이터를 쓰는 도구」로 잡힌다. 표본은 표본이지 쓰기가 아니다.
@_fake_decorator
def _decorated_writer(request):
    store = None
    return store.create(x=1)


def _sample_writer(request):
    store = None
    return store.create(x=1)


def _sample_reader(request):
    store = None
    return list(store.filter(x=1))


# ★ `/api/apikey/keys` 가 부르던 모양 그대로 — `create_key` 는 WRITE_CALLS 에 없다.
def _sample_prefix_writer(request):
    store = None
    return store.create_key(user=1, name="x")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", help="결과 JSON 경로")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    rc = self_test()
    if args.self_test or rc:
        return rc
    if not args.out:
        print("[WRITESURFACE] 출력 경로가 필요하다 (배너가 stdout 을 더럽힌다)")
        return 2

    sys.path.insert(0, "/app")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()

    rows = collect()
    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    payload = {
        "decision": "D-368 · P-83",
        # ★ 게이트는 이 표시를 보고 「스키마 본문으로 잰 증거인가」를 가른다.
        #   빈 본문 하나로 잰 옛 증거는 이 표시가 없어 초록을 못 낸다.
        "probe_mode": "schema-passing-body",
        "probe_contract": {
            "gate_statuses": list(GATE_STATUSES),
            "validation_statuses": list(VALIDATION_STATUSES),
            "unreachable_statuses": list(UNREACHABLE_STATUSES),
            "max_rounds": MAX_ROUNDS,
        },
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": ("관문 없는(=auth= 콜백 없는) 쓰기 라우트 전수. **스키마를 통과하는 "
                 "최소 본문**을 인증 없이 보내 도달을 **호출**로 재고, 쓰는가는 "
                 "**정적**으로 판정했다 — 두 방법이 다르다는 사실을 writes_by 에 "
                 "적었다 (D-322). 관문은 401/403 뿐이고 422 는 도달·검증 실패, "
                 "404/405 는 도달 실패다 (P-83)"),
        "totals": {"routes": len(rows), "by_verdict": counts},
        "routes": rows,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print("[WRITESURFACE] 관문 없는 쓰기 라우트 **%d자리** → %s" % (len(rows), args.out))
    for k in VERDICTS:
        if counts.get(k):
            print("    %-24s %3d자리" % (k, counts[k]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
