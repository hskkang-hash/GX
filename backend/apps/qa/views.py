# -*- coding: utf-8 -*-
"""QA 진입(`/qa/*`) — WO-GRDX-20261002-09 · 규격 09 M1(이중 잠금) · M2(진입) · M7(outbox).

잠금 둘(AC-1 · 바꾸지 않았다):
  ① 등록 — `config/urls.py` 가 `settings.QA_BUILD` 가 참일 때만 `qa/` 조각을 include 한다.
     거짓이면 라우트 자체가 없다 → 장고 404(고객 말 「없는 화면입니다」).
  ② 런타임 — 등록됐더라도 **모든 뷰가** 요청마다 `settings.QA_BUILD` 를 다시 본다. 거짓이면 404.
운영 프로필(`settings_prod`)에는 `QA_BUILD` 가 없다 — 기본값 거짓.

★ 진입은 인증을 건너뛰지 않는다 (WO-GRDX-20261003-04 레인 C · 인수 인증 코드 0줄)
-----------------------------------------------------------------------------------
`GET /qa/as/<키>` 는 **사람이 로그인 단추를 누를 때와 같은 함수**(dj-core `login_user`)를
그 키의 계정 이름 · 그 판에서만 통하는 비밀번호(`keys.password_for`)로 부른다. 그래서
잠금 · OTP · 동시 세션 1개(`end_previous_session`) · 보안 로그가 사람의 로그인과 똑같이 돈다.
토큰을 여기서 손으로 짓지 않는다 — 짓는 순간 그 길이 제품의 길과 갈라진다.

받는 것은 **표(`keys.QA_KEYS`)에 있는 키 하나**뿐이다. 임의 id · 메일 · username 을 받는
갈래가 없다. 표 밖의 키는 404.

토큰을 주소에 싣지 않는다 — 인계표(handoff)
-------------------------------------------
로그인 응답(토큰 둘 + 사용자)은 60초짜리 **일회용 인계표**로 캐시에 두고, 브라우저는
`/qa/enter?h=<인계표>` 로 보낸다. 화면(QA 번들의 `QaEntry`)이 `POST /qa/handoff` 로 한 번만
받아 로그인 화면과 같은 「로그인 뒤 절차」를 밟는다. 두 번째 수령은 404 — 방문 기록·
`Referer` 에 남는 것은 이미 쓴 인계표뿐이다.

진입마다 감사 줄 1 — `gx.qa.entry` 로거(키 · 결과 · 출처 IP). dj-core 도 제 보안 로그를 남긴다.
"""
from __future__ import annotations

import json
import logging
import secrets
import urllib.request

from django.conf import settings
from django.core.cache import cache
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.decorators import ratelimit

from apps.qa import keys as qa_keys

audit = logging.getLogger("gx.qa.entry")

HANDOFF_TTL_SECONDS = 60
_HANDOFF_KEY = "gx:qa:handoff:%s"
ENTER_PATH = "/qa/enter"


def _locked() -> bool:
    return not bool(getattr(settings, "QA_BUILD", False))


def _guard() -> None:
    """잠금 ② — 모든 뷰의 첫 줄."""
    if _locked():
        raise Http404()


def _client_ip(request) -> str:
    return request.META.get("REMOTE_ADDR", "") or "-"


def _real_login(request, key: str):
    """dj-core 의 로그인 함수를 **그대로** 부른다. 돌려받은 응답 본문(dict)과 상태코드."""
    from core.api.v1.auth import login_user  # 인수 코드 — 읽기·호출만(§0.4)
    from core.api.v1.schemas import LoginInput

    data = LoginInput(
        username=qa_keys.username_for(key),
        password=qa_keys.password_for(key),
        end_previous_session=True,  # 키 하나에 탭 하나 — 앞 탭은 사람의 로그인처럼 끊긴다
    )
    response = login_user(request, data)
    try:
        body = json.loads(response.content or b"{}")
    except ValueError:
        body = {}
    return body, response.status_code


@ratelimit(key="ip", rate="30/m", method="GET", block=True)
@require_GET
def qa_as(request, key: str):
    _guard()
    if not qa_keys.is_known(key):
        audit.info("qa-entry key=%s result=unknown-key ip=%s", key[:40], _client_ip(request))
        raise Http404()

    body, status = _real_login(request, key)
    user = body.get("user") if isinstance(body, dict) else None
    ok = bool(body.get("success")) and isinstance(user, dict) and user.get("access_token")
    if not ok:
        # 계정이 없다(시드 전) · 잠겼다 · 비밀번호 규칙 — 무엇이든 **들여보내지 않는다.**
        audit.warning("qa-entry key=%s result=login-refused status=%s ip=%s", key, status, _client_ip(request))
        return JsonResponse(
            {"detail": "이 키로 들어가지 못했습니다 — QA 시드(qa_seed)를 다시 돌렸는지 확인하세요.", "key": key},
            status=409,
        )

    handoff = secrets.token_urlsafe(24)
    cache.set(_HANDOFF_KEY % handoff, {"key": key, "user": user}, HANDOFF_TTL_SECONDS)
    request.session["qa_key"] = key
    audit.info("qa-entry key=%s result=ok user_id=%s ip=%s", key, user.get("user_id"), _client_ip(request))
    return HttpResponseRedirect(f"{ENTER_PATH}?h={handoff}")


@csrf_exempt  # 인계표 자체가 일회용 비밀이다 — 쿠키로 권한을 얻는 요청이 아니다
@require_POST
def qa_handoff(request):
    _guard()
    try:
        handoff = str(json.loads(request.body or b"{}").get("h", ""))
    except ValueError:
        handoff = ""
    if not handoff:
        raise Http404()
    slot = _HANDOFF_KEY % handoff
    payload = cache.get(slot)
    cache.delete(slot)  # 한 번만
    if not payload:
        raise Http404()
    key = payload["key"]
    meta = qa_keys.QA_KEYS[key]
    return JsonResponse({"key": key, "type": meta["type"], "first_path": meta["first_path"], "user": payload["user"]})


@require_GET
def qa_keys_list(request):
    """QA 바가 읽는 표 — 키 · 유형 · 데이터 상태(비밀 0). `current` 는 이 브라우저가 마지막에 들어간 키."""
    _guard()
    current_key = request.session.get("qa_key")
    current = None
    if current_key in qa_keys.QA_KEYS:
        current = {"key": current_key, "type": qa_keys.QA_KEYS[current_key]["type"]}
    rows = [{"key": k, "type": v["type"], "state": v["state"]} for k, v in qa_keys.QA_KEYS.items()]
    return JsonResponse({"current": current, "keys": rows})


def _mask(addr: str) -> str:
    name, _, domain = (addr or "").partition("@")
    return f"{name[:2]}***@{domain}" if domain else "***"


@require_GET
def qa_outbox(request):
    """M7 — QA 판의 메일은 바깥으로 나가지 않고 QA 전용 메일함(`QA_OUTBOX_URL` · mailpit)에만 쌓인다.

    여기서는 그 메일함의 목록을 **요약만** 보여 준다(받는 주소는 가린다 · 본문·링크 값 0).
    """
    _guard()
    base = getattr(settings, "QA_OUTBOX_URL", "") or ""
    if not base:
        return JsonResponse({"available": False, "detail": "QA_OUTBOX_URL 이 비어 있다", "messages": []})
    try:
        with urllib.request.urlopen(f"{base.rstrip('/')}/api/v1/messages?limit=50", timeout=5) as resp:
            data = json.loads(resp.read() or b"{}")
    except Exception as exc:  # 메일함이 죽었으면 그렇다고 말한다 — 0통으로 꾸미지 않는다
        return JsonResponse({"available": False, "detail": f"메일함에 닿지 못했다: {type(exc).__name__}", "messages": []}, status=502)
    rows = [
        {
            "created": m.get("Created"),
            "subject": m.get("Subject"),
            "to": [_mask(t.get("Address", "")) for t in (m.get("To") or [])],
        }
        for m in (data.get("messages") or [])
    ]
    return JsonResponse({"available": True, "total": data.get("total", len(rows)), "messages": rows})
