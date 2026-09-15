#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-41 — **실발송 허용 도메인 게이트** (2026-09-05 · 턴 C · 차선 Q).

    "채널을 켜기 전에 「실발송 허용 도메인 목록」 게이트를 먼저 건다.
     목록 밖 도메인(yopmail · seed.invalid · example.invalid · 개발 도메인)은
     채널이 `email` 이어도 **로그 어댑터로 강제**한다.
     판정기: 목록 밖 실발송 시도 **0**."                        — 세종 판정 P-41

왜 이 게이트가 채널 스위치보다 앞에 서는가
------------------------------------------
[실측 2026-09-05 · 턴 B] 규칙이 고르는 수신자 **42명**의 도메인은
**yopmail.com 24 · org.kr 12 · seed.invalid 6** 이다. 즉 지금 `K2_ALERT_CHANNEL=email`
로 바꾸면 **개발 계정 30명에게 진짜 경보가 나간다.** 「보내기로 정했다」와
「이 사람에게 보내도 된다」는 다른 판단이고, 뒤엣것을 앞엣것이 대신하게 두면
**첫 발송이 곧 사고**다.

무엇을 재는가 — **일곱 수**
---------------------------
    ① 강제가 **코드에 있다** — `EmailChannel.send` 가 `send_mail` **앞에서** 막는다 (AST)
    ② 목록이 **비면 전부 로그** — 「잊었다」가 「전부 허용」이 되지 않는다
    ③ **음성 대조** — 목록 밖 주소로 실제로 불러서 **안 나가는 것**을 본다
    ④ **양성 대조** — 목록 안 주소는 **나간다** (전부 막는 문지기는 고장난 문지기다)
    ⑤ **꼬리 일치로 새지 않는다** — `notyopmail.com` 이 `yopmail.com` 을 타지 못한다
    ⑥ **지금 규칙의 수신자 조사** — 채널을 켰을 때 개발 계정에 나갈 사람 **0명**
    ⑦ **운영 경보 역할은 U5 뿐** — 당직 관제요원에게 디스크 사용률을 보내지 않는다

★ ③이 이 판정기의 심장이다 — **물지 않는 문지기는 세워 둔 것과 같다**
---------------------------------------------------------------------
「막는 코드가 있다」는 ①이 본다. 그러나 코드가 있어도 순서가 어긋나면, 설정이 다른
이름으로 읽히면, 어댑터가 바뀌면 그것은 안 문다. 그래서 ③은 **실제로 부른다** —
목록 밖 주소로 `EmailChannel().send()` 를 부르고, 발송함이 **0통인 것**과 그 통지가
**로그 어댑터로 떨어진 것**을 둘 다 잰다.

⚠ 이 판정기는 **진짜 SMTP 로 보내지 않는다.** 컨테이너의 `EMAIL_BACKEND` 는 smtp 지만,
  ③④는 그 자리에서 locmem 백엔드로 바꿔 놓고 잰다. 「보냈다」의 증거는 발송함이지
  남의 수신함이 아니다 — 판정기가 사람에게 메일을 보내면 그 판정기 자체가 사고다.

    docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
        python /repo/scripts/verify_send_allowlist.py
    python scripts/verify_send_allowlist.py --self-test    # 판정 규칙만 (Django 없이)

종료 코드: 0 쟀고 통과 · 1 쟀고 실패 · 2 **못 쟀다**(환경 없음)
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

TAG = "[SEND-ALLOWLIST]"

#: 강제가 있어야 하는 자리. **한 곳이다** — 부르는 쪽마다 막으면 한 곳이 빠지고,
#: 빠진 그 한 곳이 사고가 된다.
TARGET = ("kernels/k2_notify/channels.py", "EmailChannel", "send")

#: 허용 목록 판정을 부르는 이름. 이름이 바뀌면 이 게이트는 **빨개져야 한다** —
#: 조용히 통과하면 강제가 사라진 날을 아무도 모른다.
GUARD_CALL = "send_allowed"

#: 실제로 메일을 내보내는 부름. 이 앞에 문지기가 서야 한다.
SEND_CALLS = ("send_mail", "get_connection")

#: **덫**이다 — 차단 목록이 아니다.
#:
#: 정책은 허용 목록 하나뿐이다(P-41). 그러나 허용 목록에도 사람이 손으로 적는다.
#: 급할 때 `K2_SEND_ALLOWED_DOMAINS=yopmail.com` 이라고 적는 순간 개발 계정 24명에게
#: 진짜로 나가고, 게이트가 「목록 안이므로 통과」라고 말하면 그 게이트는 사고를 승인한 것이다.
#: 그래서 **허용 목록에 개발 도메인이 섞여 들어간 것**만 따로 잡는다.
#: 이 목록이 정책을 대신하지 않는다 — 여기 없는 개발 도메인도 허용 목록 밖이면 막힌다.
DEV_DOMAINS = (
    "yopmail.com",          # [실측 2026-09-05 · 턴 B] 수신자 42명 중 24명
    "mailinator.com", "guerrillamail.com", "10minutemail.com",
    "example.com", "example.org", "example.net",     # RFC 2606 예약
)

#: RFC 2606 이 「절대 존재하지 않는다」고 못 박은 꼬리. `seed.invalid`(6명) ·
#: `test.invalid` 가 여기 걸린다. 설정을 읽을 수 있으면 설정이 답한다(D-212).
FALLBACK_UNDELIVERABLE_SUFFIXES = (".invalid", ".test", ".example", ".localhost")


def _is_dev_domain(domain: str) -> bool:
    """이 도메인이 **사람의 업무 주소가 아닌 것**으로 알려져 있는가.

    ★ 설정의 꼬리 목록과 여기 바닥값을 **합집합**으로 쓴다. 덫은 넓은 쪽이 안전하다 —
      좁혀서 놓친 덫은 놓친 줄도 모른다.
    """
    dom = (domain or "").strip().lower().rstrip(".")
    if not dom:
        return True                     # 도메인을 못 읽은 주소를 업무 주소로 세지 않는다
    if dom in DEV_DOMAINS:
        return True
    try:
        from django.conf import settings

        tails = tuple(getattr(settings, "UNDELIVERABLE_EMAIL_SUFFIXES", None) or ())
    except Exception:                                           # noqa: BLE001
        tails = ()
    for tail in set(tails) | set(FALLBACK_UNDELIVERABLE_SUFFIXES):
        bare = tail.lstrip(".")
        if dom == bare or dom.endswith("." + bare):
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════
# ① 강제가 코드에 있는가 — **낱말이 아니라 AST 로 본다**
# ═══════════════════════════════════════════════════════════════════════════
#
# 낱말로 세면 주석 한 줄이 게이트를 통과시킨다. 「# 허용 도메인을 본다」라고 적고
# 아무것도 안 하는 코드가 정확히 그 모양이다. 그래서 **구문 나무**를 본다:
#   · `send_allowed` 부름이 `send_mail` 부름보다 **앞 줄**에 있는가
#   · 그 판정이 거짓일 때 **되돌아가는가**(return) — 통과해 버리면 막은 것이 아니다
#   · 되돌아가기 전에 **다른 어댑터로 떨어뜨리는가**(`.send(...)`)
def _call_names(node: ast.AST):
    """이 나무 안의 모든 부름 이름과 줄 번호."""
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        func = sub.func
        if isinstance(func, ast.Name):
            yield func.id, sub.lineno
        elif isinstance(func, ast.Attribute):
            yield func.attr, sub.lineno


def judge_ast(source: str) -> dict:
    """`EmailChannel.send` 의 구문 나무를 읽어 **네 사실**을 낸다.

    돌려주는 값은 판정이 아니라 **사실**이다 — 판정은 `judge` 가 한다.
    ★ 못 읽으면 `None` 이다. `None` 은 「없다」가 아니라 **「못 쟀다」**다 (D-301).
    """
    out = {"parsed": False, "guard_line": None, "send_line": None,
           "guard_returns": False, "guard_falls_back": False,
           "guard_reads_setting": False}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return out
    out["parsed"] = True

    klass = next((n for n in ast.walk(tree)
                  if isinstance(n, ast.ClassDef) and n.name == TARGET[1]), None)
    if klass is None:
        return out
    method = next((n for n in klass.body
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and n.name == TARGET[2]), None)
    if method is None:
        return out

    guard_lines = [ln for (name, ln) in _call_names(method) if name == GUARD_CALL]
    send_lines = [ln for (name, ln) in _call_names(method) if name in SEND_CALLS]
    out["guard_line"] = min(guard_lines) if guard_lines else None
    out["send_line"] = min(send_lines) if send_lines else None

    # 판정이 거짓일 때 **되돌아가고**, 되돌아가기 전에 **다른 어댑터로 떨어뜨리는가**.
    for branch in [n for n in ast.walk(method) if isinstance(n, ast.If)]:
        if out["guard_line"] is None or branch.lineno < out["guard_line"]:
            continue
        body = list(branch.body)
        returns = any(isinstance(s, ast.Return) for s in ast.walk(branch)
                      if isinstance(s, ast.Return))
        fell = any(name == "send" for stmt in body for (name, _l) in _call_names(stmt))
        if returns and fell:
            out["guard_returns"] = True
            out["guard_falls_back"] = True
            break
        if returns:
            out["guard_returns"] = True

    # 목록을 **설정에서** 읽는가. 상수로 박아 두면 운영에서 못 바꾼다.
    reader = next((n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "_allowed_domains"),
                  None)
    if reader is not None:
        out["guard_reads_setting"] = any(
            isinstance(s, ast.Constant) and s.value == "K2_SEND_ALLOWED_DOMAINS"
            for s in ast.walk(reader))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — **함수로 떼어 둔 이유는 시험하기 위해서다** (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge(counts: dict) -> list:
    """일곱 수를 판정한다. `(이름, 통과, 사유)`. `None` 은 **못 쟀다**다 (D-301)."""
    out: list = []

    a = counts.get("ast")
    if not a or not a.get("parsed"):
        out.append(("강제가 코드에 있다 (AST)", False,
                    "**못 쟀다** — 어댑터 파일을 못 읽거나 못 폈다"))
    else:
        g, s = a.get("guard_line"), a.get("send_line")
        ordered = (g is not None and s is not None and g < s)
        ok = ordered and a.get("guard_returns") and a.get("guard_falls_back") \
            and a.get("guard_reads_setting")
        why = f"{GUARD_CALL} @{g} · send_mail @{s}"
        if not ordered:
            why += (" — **문지기가 발송 뒤에 있거나 없다.** 보내고 나서 세는 것은 "
                    "늦다: 나간 메일은 취소되지 않는다")
        elif not a.get("guard_falls_back"):
            why += " — 막기만 하고 **로그 어댑터로 떨어뜨리지 않는다**(P-41)"
        elif not a.get("guard_returns"):
            why += " — 판정만 하고 **되돌아가지 않는다**. 통과하면 막은 것이 아니다"
        elif not a.get("guard_reads_setting"):
            why += " — 목록을 `K2_SEND_ALLOWED_DOMAINS` 에서 읽지 않는다(코드에 박혀 있다)"
        out.append(("강제가 코드에 있다 (AST)", bool(ok), why))

    empty = counts.get("empty_list_blocks")
    if empty is None:
        out.append(("빈 목록이면 전부 로그", False, "**못 쟀다**"))
    else:
        out.append(("빈 목록이면 전부 로그", bool(empty),
                    "목록이 비면 실발송 0" if empty else
                    "**목록이 비었는데 통과시킨다** — 「목록을 잊었다」가 「전부 허용」이 "
                    "되면 잊은 날 42명에게 나간다"))

    neg = counts.get("negative")
    if neg is None:
        out.append(("음성 대조 — 목록 밖은 안 나간다", False, "**못 쟀다** — 못 불렀다"))
    else:
        ok = (neg.get("outbox") == 0 and neg.get("ok") is False
              and neg.get("fell_back") is True)
        out.append(("음성 대조 — 목록 밖은 안 나간다", ok,
                    f"주소 {neg.get('address')!r} → 발송함 {neg.get('outbox')}통 · "
                    f"outcome.ok={neg.get('ok')} · 로그 어댑터로 떨어짐="
                    f"{neg.get('fell_back')}"
                    + ("" if ok else " — **물지 않는 문지기다.** 세워 둔 것과 같다")))

    pos = counts.get("positive")
    if pos is None:
        out.append(("양성 대조 — 목록 안은 나간다", False, "**못 쟀다** — 못 불렀다"))
    else:
        ok = (pos.get("outbox") == 1 and pos.get("ok") is True)
        out.append(("양성 대조 — 목록 안은 나간다", ok,
                    f"주소 {pos.get('address')!r} → 발송함 {pos.get('outbox')}통 · "
                    f"outcome.ok={pos.get('ok')}"
                    + ("" if ok else " — 전부 막는 문지기는 **고장난 문지기**다. "
                                     "그 상태로는 켤 수 없으니 게이트가 무의미해진다")))

    tail = counts.get("suffix_leak")
    if tail is None:
        out.append(("꼬리 일치로 새지 않는다", False, "**못 쟀다**"))
    else:
        out.append(("꼬리 일치로 새지 않는다", tail is False,
                    "notyopmail.com 은 yopmail.com 을 타지 못한다" if tail is False else
                    "**꼬리 일치로 샌다** — `notyopmail.com` 이 허용 목록을 타고 나간다"))

    census = counts.get("census")
    if census is None:
        out.append(("개발 계정에 실발송 0 (실측)", False, "**못 쟀다** — DB 를 못 읽었다"))
    else:
        leak = census.get("dev_would_send")
        hit = census.get("dev_domains_hit") or []
        out.append(("개발 계정에 실발송 0 (실측)", leak == 0,
                    f"규칙이 고르는 수신자 항목 {census.get('entries')} · 고유 주소 "
                    f"{census.get('people')}명 · 도메인 "
                    f"{census.get('domains')} · **채널을 email 로 켜면** 실발송 "
                    f"{census.get('would_send')}명 / 로그 강제 "
                    f"{census.get('forced_to_log')}명"
                    + ("" if leak == 0 else
                       f" — **개발 계정 {leak}명이 허용 목록을 타고 나간다"
                       f"({', '.join(hit)}).** 이 수만큼 사고가 난다")))

    ops = counts.get("ops_roles")
    if ops is None:
        out.append(("운영 경보는 U5 시스템관리자만", False, "**못 쟀다**"))
    else:
        bad = ops.get("outside_sysops") or []
        note = (f"K2_OPS_ALERT_ROLE_CODES={ops.get('codes')} · "
                f"U5(K3_ROLE_SYSOPS)={ops.get('sysops')}")
        if not ops.get("codes"):
            note += " — 비어 있다: **아무도 안 받는다**(안전한 쪽). 운영에서 채운다"
        out.append(("운영 경보는 U5 시스템관리자만", not bad,
                    note + ("" if not bad else
                            f" — **{', '.join(bad)} 는 U5 가 아니다.** 당직 관제요원에게 "
                            f"디스크 사용률을 보내면 그 사람은 할 수 있는 일이 없고, "
                            f"다음부터 경보를 안 읽는다")))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — **판정기를 먼저 의심한다** (D-350)
# ═══════════════════════════════════════════════════════════════════════════
#: **출생 표본** (D-310) — 이 게이트를 만들게 한 코드다. 2026-09-05 턴 C **이전**의
#: `EmailChannel.send` 가 정확히 이 모양이었다: 주소가 비었는지만 보고 **바로 보낸다.**
#: 첫 갈래가 이 표본에서 빨강을 내지 못하면 이 판정기는 자기가 태어난 이유를 못 본다.
BIRTH_SOURCE = '''
class EmailChannel:
    name = "email"

    def send(self, *, address, subject, body):
        from django.core.mail import get_connection, send_mail
        if not address:
            return SendOutcome(False, "수신 주소가 비었다")
        connection = get_connection(timeout=self.timeout())
        sent = send_mail(subject=subject, message=body, recipient_list=[address],
                         connection=connection, fail_silently=False)
        return SendOutcome(bool(sent))
'''

#: **함정** — 문지기가 발송 **뒤에** 서 있다. 세고는 있으나 이미 나갔다.
LATE_GUARD_SOURCE = '''
def _allowed_domains():
    return getattr(settings, "K2_SEND_ALLOWED_DOMAINS", ())

class EmailChannel:
    def send(self, *, address, subject, body):
        from django.core.mail import get_connection, send_mail
        sent = send_mail(subject=subject, message=body, recipient_list=[address])
        gate = self.send_allowed(address)
        if not gate.ok:
            LogChannel().send(address=address, subject=subject, body=body)
            return SendOutcome(False, gate.reason)
        return SendOutcome(bool(sent))
'''

#: **함정 둘** — 판정은 앞에 있는데 **되돌아가지 않는다.** 사유만 적고 그대로 보낸다.
FALLTHROUGH_SOURCE = '''
def _allowed_domains():
    return getattr(settings, "K2_SEND_ALLOWED_DOMAINS", ())

class EmailChannel:
    def send(self, *, address, subject, body):
        from django.core.mail import get_connection, send_mail
        gate = self.send_allowed(address)
        if not gate.ok:
            log.warning("목록 밖이다: %s", address)
        sent = send_mail(subject=subject, message=body, recipient_list=[address])
        return SendOutcome(bool(sent))
'''


def _green() -> dict:
    """다 선 표본."""
    return {
        "ast": {"parsed": True, "guard_line": 10, "send_line": 20,
                "guard_returns": True, "guard_falls_back": True,
                "guard_reads_setting": True},
        "empty_list_blocks": True,
        "negative": {"address": "dev@yopmail.com", "outbox": 0, "ok": False,
                     "fell_back": True},
        "positive": {"address": "duty@allowed.example", "outbox": 1, "ok": True},
        "suffix_leak": False,
        # [실측 2026-09-05 · 턴 B] 이 표본의 수는 지어낸 것이 아니다.
        "census": {"people": 42, "entries": 42, "domains": {"yopmail.com": 24, "org.kr": 12,
                                             "seed.invalid": 6},
                   "would_send": 12, "forced_to_log": 30,
                   "dev_would_send": 0, "dev_domains_hit": []},
        "ops_roles": {"codes": ["admin"], "sysops": ["admin"], "outside_sysops": []},
    }


def self_test() -> int:
    bad: list = []

    def names(rows):
        return {n: ok for (n, ok, _why) in rows}

    # ── 출생 표본 · 함정 둘 — **AST 판정이 이것들을 빨강으로 읽어야 한다** ──────
    for label, src in (("출생 표본(문지기 없음)", BIRTH_SOURCE),
                       ("함정(문지기가 발송 뒤)", LATE_GUARD_SOURCE),
                       ("함정(막지 않고 통과)", FALLTHROUGH_SOURCE)):
        sample = dict(_green(), ast=judge_ast(src))
        if names(judge(sample)).get("강제가 코드에 있다 (AST)"):
            bad.append(f"**{label}**을 통과로 읽는다 — 낱말이 아니라 구문을 보라 (D-373)")

    # ── 초록 표본 ────────────────────────────────────────────────────────────
    got = names(judge(_green()))
    if not all(got.values()):
        bad.append(f"다 선 표본을 통과로 읽지 못한다: {got}")

    # ── 음성 갈래 — 하나씩 무너뜨린다 ────────────────────────────────────────
    for path, value, expect_red in (
        (("empty_list_blocks",), False, "빈 목록이면 전부 로그"),
        (("negative", "outbox"), 1, "음성 대조 — 목록 밖은 안 나간다"),
        (("negative", "ok"), True, "음성 대조 — 목록 밖은 안 나간다"),
        (("negative", "fell_back"), False, "음성 대조 — 목록 밖은 안 나간다"),
        (("positive", "outbox"), 0, "양성 대조 — 목록 안은 나간다"),
        (("suffix_leak",), True, "꼬리 일치로 새지 않는다"),
        # ★ 이 갈래가 이 판정기의 **덫**이다: 급할 때 허용 목록에 `yopmail.com` 을
        #   적으면 개발 계정 24명에게 진짜로 나간다. 「목록 안이니 통과」라고 말하는
        #   게이트는 사고를 승인한 게이트다.
        (("census", "dev_would_send"), 24, "개발 계정에 실발송 0 (실측)"),
        (("ops_roles", "outside_sysops"), ["fire_user"],
         "운영 경보는 U5 시스템관리자만"),
    ):
        sample = _green()
        if len(path) == 1:
            sample[path[0]] = value
        else:
            sample[path[0]] = dict(sample[path[0]], **{path[1]: value})
        if names(judge(sample)).get(expect_red):
            bad.append(f"{'.'.join(path)}={value!r} 인데 「{expect_red}」를 통과로 읽는다")

    # ── **못 쟀다 ≠ 거짓** (D-301) ──────────────────────────────────────────
    for key, label in (("negative", "음성 대조 — 목록 밖은 안 나간다"),
                       ("census", "개발 계정에 실발송 0 (실측)")):
        sample = dict(_green(), **{key: None})
        hit = [(n, ok, why) for (n, ok, why) in judge(sample) if n == label][0]
        if hit[1] or "못 쟀다" not in hit[2]:
            bad.append(f"{key} 를 **못 쟀는데** 통과로 읽거나 사유에 그 사실이 없다")

    # ── 도메인 대조 규칙 자체 — 커널을 Django 없이 부를 수 없으므로 여기서는
    #    **판정기가 기대하는 규칙**만 적어 둔다. 실물 대조는 ③④⑤가 한다.
    if bad:
        print(f"{TAG} 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print(f"{TAG} 자기시험 통과 — 출생 표본 1 · 함정 2 · 초록 1 · 음성 8 · 판정 불가 2")
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 실측
# ═══════════════════════════════════════════════════════════════════════════
def _channels_source() -> str | None:
    """어댑터 파일을 **파일로** 읽는다. `/repo` 와 `/app` 이 따로 마운트돼 있어
    이름 공간만으로는 못 찾는다 — 저장소가 이미 아는 함정이다."""
    here = Path(__file__).resolve().parent.parent
    for cand in (here / "backend" / TARGET[0], Path("/app") / TARGET[0],
                 here / TARGET[0]):
        if cand.is_file():
            return cand.read_text(encoding="utf-8")
    return None


def collect() -> dict:
    """③④⑤⑥⑦ 을 실제로 잰다. **아무것도 쓰지 않는다** — 읽기와 발송함뿐이다."""
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.path.insert(0, "/app")
    django.setup()

    from django.apps import apps
    from django.conf import settings
    from django.core import mail
    from django.test.utils import override_settings

    from common.tenant_scope import TenantScope
    from kernels.k2_notify import channels as ch
    from kernels.k2_notify import resolve_recipients

    out: dict = {"ast": None, "empty_list_blocks": None, "negative": None,
                 "positive": None, "suffix_leak": None, "census": None,
                 "ops_roles": None,
                 "configured_allowlist": sorted(ch._allowed_domains()),
                 "email_backend": str(getattr(settings, "EMAIL_BACKEND", ""))}

    src = _channels_source()
    out["ast"] = judge_ast(src) if src else {"parsed": False}

    # ── ② 목록이 **비면** 아무것도 안 나간다 ────────────────────────────────
    with override_settings(K2_SEND_ALLOWED_DOMAINS=[]):
        out["empty_list_blocks"] = not any(
            ch.EmailChannel.send_allowed(a).ok
            for a in ("duty@city.go.kr", "ops@guardianx.example", "a@b.com"))

    # ── ③④⑤ 실물 대조 — **locmem 발송함으로 잰다** ──────────────────────
    #    ⚠ 컨테이너의 백엔드는 smtp 다. 그대로 부르면 판정기가 사람에게 메일을 보낸다.
    #      「보냈다」의 증거는 발송함이지 남의 수신함이 아니다.
    LOCMEM = "django.core.mail.backends.locmem.EmailBackend"
    allow = "allowed.example"
    with override_settings(EMAIL_BACKEND=LOCMEM, K2_SEND_ALLOWED_DOMAINS=[allow],
                           DEFAULT_FROM_EMAIL="gate@guardianx.example"):
        adapter = ch.EmailChannel()

        # ③ 음성 — 목록 **밖** (실측 도메인 셋 중 가장 위험한 것: 진짜로 닿는다)
        seen: list = []
        undo = ch.register(_SpyLog(seen))
        try:
            mail.outbox = []
            outside = "dev-account-12@yopmail.com"
            verdict = adapter.send(address=outside, subject="[게이트] 나가면 안 된다",
                                   body="P-41 음성 대조 — 이 본문이 발송함에 있으면 사고다")
            out["negative"] = {"address": outside, "outbox": len(mail.outbox),
                               "ok": bool(verdict.ok), "fell_back": bool(seen),
                               "reason": verdict.reason}
        finally:
            undo()

        # ④ 양성 — 목록 **안**
        mail.outbox = []
        inside = f"duty@{allow}"
        verdict = adapter.send(address=inside, subject="[게이트] 나가야 한다",
                               body="P-41 양성 대조")
        out["positive"] = {"address": inside, "outbox": len(mail.outbox),
                           "ok": bool(verdict.ok), "reason": verdict.reason}

    # ⑤ 꼬리 일치 — `yopmail.com` 을 허용해도 `notyopmail.com` 은 못 탄다
    with override_settings(K2_SEND_ALLOWED_DOMAINS=["yopmail.com"]):
        out["suffix_leak"] = bool(ch.EmailChannel.send_allowed("x@notyopmail.com").ok)

    # ── ⑥ 지금 규칙이 고르는 수신자 조사 — **읽기만 한다** ───────────────────
    out["census"] = _census(apps, resolve_recipients, TenantScope, ch)

    # ── ⑦ 운영 경보 역할 ────────────────────────────────────────────────────
    from config.k3_roles import K3_ROLE_SYSOPS

    codes = [str(c).strip() for c in
             (getattr(settings, "K2_OPS_ALERT_ROLE_CODES", None) or []) if str(c).strip()]
    out["ops_roles"] = {"codes": codes, "sysops": list(K3_ROLE_SYSOPS),
                        "outside_sysops": [c for c in codes if c not in K3_ROLE_SYSOPS]}
    return out


class _SpyLog:
    """로그 어댑터 자리에 잠깐 앉아 **떨어진 통지를 받아 적는다.**

    ★ 합성 mock 이 아니다 — 진짜 `LogChannel` 과 같은 계약을 지키고, 받은 것을
      진짜 `LogChannel` 에 그대로 넘긴다. 이 자리가 필요한 이유는 하나다:
      **「안 나갔다」만으로는 부족하고 「로그로 갔다」까지 봐야** 강제가 강제이기 때문이다.
      떨어뜨리지 않고 그냥 버리면 그 통지는 **없었던 일**이 된다.
    """

    name = "log"

    def __init__(self, sink: list) -> None:
        self._sink = sink

    def send(self, *, address: str, subject: str, body: str):
        from kernels.k2_notify.channels import LogChannel

        self._sink.append(address)
        return LogChannel().send(address=address, subject=subject, body=body)


def _census(apps, resolve_recipients, TenantScope, ch) -> dict:
    """규칙이 고르는 수신자 전원의 **도메인**을 센다. 이름·주소는 적지 않는다 —
    개인 주소를 증거 문서에 남기지 않기 위해서다. 도메인만으로 답이 나온다.

    ★ **채널로 거르지 않는다.** 지금 규칙은 전부 `log` 라서 채널로 거르면 「수신자 0명」
      이 나오고, 그 0은 **안전해서 0이 아니라 아직 안 켜서 0**이다. 이 게이트가 답해야
      하는 질문은 「지금 나가고 있나」가 아니라 **「켜면 누구에게 나가나」**다.
    """
    from kernels.k1_event.services import _owner_field

    Rule = apps.get_model("stream_monitors", "NotificationRule")
    User = apps.get_model("user", "CoreUser")
    field = _owner_field(Rule)

    addresses: set = set()
    entries = 0                 # **중복을 포함한** 수신자 항목 수 (턴 B 의 42명이 이 수다)
    for rule in Rule._base_manager.select_related("role").all().order_by("pk"):
        if not getattr(rule, "is_active", True):
            continue
        groups = (list(rule.groups.all()) if field == "groups"
                  else ([rule.group] if getattr(rule, "group", None) else []))
        for group in groups:
            actor = User.objects.filter(userprofilelink__group=group,
                                        is_active=True).first()
            scope = (TenantScope.of(actor) if actor is not None else
                     TenantScope.system(reason="P-41 허용 도메인 게이트 — 읽기만 한다"))
            try:
                people = resolve_recipients(scope=scope, severity=rule.severity,
                                            group=group)
            except Exception:                                   # noqa: BLE001
                continue
            for p in people:
                if p.rule_id == rule.pk and p.address:
                    entries += 1
                    addresses.add(p.address.strip().lower())

    domains: dict = {}
    would_send = 0      # 채널을 email 로 켜면 **실제로 나갈** 사람
    dev_leak = 0        # 그중 **개발 계정** — 0이 아니면 그 수만큼 사고다
    dev_hit: set = set()
    for addr in addresses:
        dom = ch._domain_of(addr) or "(주소없음)"
        domains[dom] = domains.get(dom, 0) + 1
        if ch.EmailChannel.send_allowed(addr).ok:
            would_send += 1
            if _is_dev_domain(dom):
                dev_leak += 1
                dev_hit.add(dom)
    return {"people": len(addresses), "entries": entries,
            "domains": dict(sorted(domains.items())),
            "would_send": would_send, "forced_to_log": len(addresses) - would_send,
            "dev_would_send": dev_leak, "dev_domains_hit": sorted(dev_hit)}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="P-41 실발송 허용 도메인 게이트 — 목록 밖 실발송 0")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    try:
        counts = collect()
    except Exception as exc:                                    # noqa: BLE001
        print(f"{TAG} **판정 불가** — 환경을 세우지 못했다: {type(exc).__name__}: {exc}")
        print(f"{TAG} 컨테이너 안에서 DJANGO_SETTINGS_MODULE 를 주고 돌린다")
        return EXIT_UNDECIDABLE

    shown = counts["configured_allowlist"] or "(비어 있음 — 전부 로그)"
    print("%s [설정] 허용 도메인 %s · EMAIL_BACKEND=%s"
          % (TAG, shown, counts["email_backend"]))
    print(f"{TAG} [대조] ③④는 locmem 발송함으로 잰다 — 판정기는 사람에게 메일을 "
          f"보내지 않는다")

    rc = EXIT_OK
    for (name, ok, why) in judge(counts):
        print(f"{TAG} {'  ' if ok else 'X '}{name:28} {why}")
        if not ok:
            rc = EXIT_FAIL
    if args.json:
        print(f"{TAG} JSON " + json.dumps(counts, ensure_ascii=False, sort_keys=True,
                                          default=str))
    print(f"{TAG} " + ("통과 — 목록 밖 실발송 0. 문지기가 **문다**"
                       if rc == EXIT_OK else
                       "실패 — 위의 X 를 고치기 전에 채널을 켜면 그 순간이 사고다"))
    return rc


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(
        __file__,
        target="gx-shell 컨테이너 · DJANGO_SETTINGS_MODULE=config.settings (앱과 같은 설정) · 호스트에서 부르면 docker exec 로 위임한다",
        as_="(HTTP 계정 없음) — gx-shell 안 Django ORM 으로 읽는다 · DB 자격은 앱이 들고 있는 것 그대로(이름: DATABASE_URL / POSTGRES_*)",
        source="살아 있는 DB·앱 레지스트리 (django.setup 뒤 ORM) — 파일 사진이 아니다",
    )
    sys.exit(main())
